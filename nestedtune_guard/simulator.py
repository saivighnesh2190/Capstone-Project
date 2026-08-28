"""Bounded deterministic simulator.

The simulator runs a workload definition under a given policy with a
bounded time horizon. It produces a SimulationResult containing:
  - per-trial final state
  - per-trial event log
  - wait-for observer history (per-tick cycle snapshots)
  - telemetry time series (sampled every tick)
  - summary metrics

The simulator is deterministic: given the same workload and policy,
the result is byte-identical across runs. This is enforced by:
  - integer-valued time deltas (we use a fixed tick of 0.1s)
  - deterministic ordering of trials (arrival_time, then id)
  - no use of wall-clock or random sources
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable

from .model import (
    Cluster,
    PlacementGroup,
    ResourceBundle,
    Trial,
    TrialState,
    Workload,
)
from .observer import ObserverResult, observe
from .policies import Policy, FIFOPolicy, GreedyPolicy, DeadlockAwarePolicy
from .schema import WorkloadDefinition
from .telemetry import TelemetrySample, summarize, Summary


TICK_S = 0.1  # 100 ms deterministic tick


@dataclass
class SimulationResult:
    """A full simulation result for one (workload, policy) run."""

    fixture: str
    policy: str
    horizon_s: float
    trials: list[Trial]
    events: list[dict]                     # ordered event log
    telemetry: list[TelemetrySample]
    wait_for_history: list[ObserverResult]
    summary: Summary
    cluster_snapshot: dict                # final cluster state

    def to_dict(self) -> dict:
        return {
            "fixture": self.fixture,
            "policy": self.policy,
            "horizon_s": self.horizon_s,
            "trials": [t.to_dict() for t in self.trials],
            "events": self.events,
            "telemetry": [s.to_dict() for s in self.telemetry],
            "wait_for_history": [w.to_dict() for w in self.wait_for_history],
            "summary": self.summary.to_dict(),
            "cluster_snapshot": self.cluster_snapshot,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


def get_policy(name: str) -> Policy:
    name = name.lower().replace("-", "_")
    if name in ("fifo",):
        return FIFOPolicy()
    if name in ("greedy", "backfill"):
        return GreedyPolicy()
    if name in ("deadlock_aware", "deadlockaware", "cp2", "da"):
        return DeadlockAwarePolicy()
    raise ValueError(f"unknown policy {name!r}; expected fifo|greedy|deadlock_aware")


def simulate(workload_def: WorkloadDefinition, policy_name: str) -> SimulationResult:
    """Simulate a workload under a policy. Returns a SimulationResult.

    The simulator runs deterministically:
      - time advances in TICK_S steps
      - at each tick, the policy is asked to decide on the queue
      - admitted trials have their parent PG placed immediately
      - child PG placement is attempted after parent placement
      - if child cannot fit, trial enters WAITING_CHILD state
      - WAITING_CHILD trials are recorded in the wait-for graph
      - trials complete when their duration elapses after start
      - the run ends at the bounded horizon
    """
    policy = get_policy(policy_name)
    workload = Workload.from_definition(workload_def)
    cluster = workload.cluster
    horizon = workload.bounded_horizon_s

    events: list[dict] = []
    telemetry: list[TelemetrySample] = []
    wait_for_history: list[ObserverResult] = []

    # Track currently running trials (state RUNNING or WAITING_CHILD)
    # The "running" set in policy context = trials that have parent PG
    # admitted but may or may not have started the actual workload.
    running: list[Trial] = []

    t = 0.0
    tick_idx = 0
    while t <= horizon + 1e-9:
        # 1. Apply any capacity events scheduled for this tick.
        for event in list(workload.capacity_events):
            if event.time <= t + 1e-9:
                new_cap = event.capacity
                cluster.apply_capacity_change(new_cap)
                workload.capacity_events.remove(event)
                policy.on_capacity_change(cluster, t)
                events.append({
                    "t": round(t, 4),
                    "type": "capacity_change",
                    "new_capacity": {
                        "cpu": new_cap.cpu, "gpu": new_cap.gpu,
                        "memory": new_cap.memory, "workers": new_cap.workers,
                    },
                })

        # 2. Mark newly-arrived trials as PENDING (still in queue).
        for trial in workload.trials_in_arrival_order:
            if (
                trial.schema.arrival_time <= t + 1e-9
                and trial.state == TrialState.PENDING
                and trial not in running
                and trial.admitted_at is None
            ):
                # Trial has arrived and is waiting to be admitted.
                # It stays in PENDING; the policy will pick it up.
                events.append({
                    "t": round(t, 4),
                    "type": "trial_arrived",
                    "trial_id": trial.id,
                })

        # 3. Check for trials whose nested child has become feasible.
        # A WAITING_CHILD trial whose child now fits transitions to RUNNING.
        for trial in list(running):
            if trial.state != TrialState.WAITING_CHILD:
                continue
            assert trial.child_pg is not None
            if cluster.can_admit(trial.child_pg.bundle):
                cluster.admit(trial.child_pg.bundle)
                trial.child_pg.ready = True
                trial.state = TrialState.RUNNING
                trial.started_at = t
                events.append({
                    "t": round(t, 4),
                    "type": "child_admitted",
                    "trial_id": trial.id,
                    "started_at": t,
                })

        # 4. Check for trials that have completed.
        for trial in list(running):
            if trial.state != TrialState.RUNNING:
                continue
            assert trial.started_at is not None
            if t >= trial.started_at + trial.schema.duration - 1e-9:
                # Release child PG and parent PG, mark COMPLETED.
                if trial.child_pg is not None and trial.child_pg.ready:
                    cluster.release(trial.child_pg.bundle)
                    trial.child_pg = None
                if trial.parent_pg is not None:
                    cluster.release(trial.parent_pg.bundle)
                    trial.parent_pg = None
                trial.state = TrialState.COMPLETED
                trial.finished_at = t
                running.remove(trial)
                policy.on_trial_finished(trial, t)
                events.append({
                    "t": round(t, 4),
                    "type": "trial_completed",
                    "trial_id": trial.id,
                    "finished_at": t,
                })

        # 5. Build the current queue (arrived, pending, not rejected).
        queue = [
            t_ for t_ in workload.trials_in_arrival_order
            if t_.state == TrialState.PENDING
            and t_.schema.arrival_time <= t + 1e-9
        ]

        # 6. Ask the policy to admit one trial (if any).
        if queue:
            decision = policy.decide(queue, cluster, t, running)
            # CP-2 rejection path: policy explicitly rejected the trial.
            if (
                not decision.admitted
                and decision.trial_id
                and decision.reason == "cp2_reject_infeasible_combined"
            ):
                trial = workload.trials[decision.trial_id]
                trial.state = TrialState.REJECTED
                trial.rejection_reason = "combined_parent_child_demand_exceeds_cluster_capacity"
                events.append({
                    "t": round(t, 4),
                    "type": "trial_rejected",
                    "trial_id": trial.id,
                    "reason": trial.rejection_reason,
                    "trace": decision.trace,
                })
            elif decision.admitted and decision.trial_id:
                trial = workload.trials[decision.trial_id]
                # Admit the parent PG.
                from .policies.fifo import _bundle_from_trial
                parent_bundle = _bundle_from_trial(trial, role="parent")
                cluster.admit(parent_bundle)
                pg = PlacementGroup(
                    owner_id=trial.id,
                    role="parent",
                    bundle=parent_bundle,
                    ready=True,
                    created_at=t,
                )
                trial.parent_pg = pg
                trial.admitted_at = t
                events.append({
                    "t": round(t, 4),
                    "type": "parent_admitted",
                    "trial_id": trial.id,
                    "admitted_at": t,
                    "trace": decision.trace,
                })
                # Try to place the child PG immediately.
                if trial.schema.child is not None:
                    from .policies.fifo import _bundle_from_trial as _bft
                    child_bundle = _bft(trial, role="child")
                    child_pg = PlacementGroup(
                        owner_id=trial.id,
                        role="child",
                        bundle=child_bundle,
                        ready=False,
                        created_at=t,
                    )
                    trial.child_pg = child_pg
                    if cluster.can_admit(child_bundle):
                        cluster.admit(child_bundle)
                        child_pg.ready = True
                        trial.state = TrialState.RUNNING
                        trial.started_at = t
                        events.append({
                            "t": round(t, 4),
                            "type": "child_admitted",
                            "trial_id": trial.id,
                            "started_at": t,
                        })
                    else:
                        # Child cannot fit → trial is in WAITING_CHILD
                        # state. This is the deadlock-prone state.
                        trial.state = TrialState.WAITING_CHILD
                        events.append({
                            "t": round(t, 4),
                            "type": "child_waiting",
                            "trial_id": trial.id,
                            "free_cpu": cluster.free.cpu,
                            "free_gpu": cluster.free.gpu,
                        })
                else:
                    # No nested child — start immediately.
                    trial.state = TrialState.RUNNING
                    trial.started_at = t
                    events.append({
                        "t": round(t, 4),
                        "type": "trial_running",
                        "trial_id": trial.id,
                        "started_at": t,
                    })
                running.append(trial)
            elif decision.trial_id and decision.reason == "cp2_no_feasible_trial":
                # Policy explicitly said no trial is feasible right now.
                # For FIFO and greedy this means the head is blocked; we
                # just advance time and retry next tick.
                pass

        # 7. Take a telemetry sample at this tick (snapshots, not every
        # event, to keep the result compact). We sample at every tick for
        # accuracy; downstream consumers can decimate.
        running_parents = [t_ for t_ in running if t_.parent_pg is not None]
        waiting_parents = [t_ for t_ in running if t_.state == TrialState.WAITING_CHILD]
        running_active = [t_ for t_ in running if t_.state == TrialState.RUNNING]

        reserved_cpu = sum(t_.parent_pg.bundle.cpu for t_ in running_parents if t_.parent_pg)
        # Useful CPU = reserved by parents whose children are running
        # (i.e. the trial is actually making progress).
        useful_cpu = sum(
            t_.parent_pg.bundle.cpu for t_ in running_active
            if t_.parent_pg and t_.state == TrialState.RUNNING
        ) + sum(
            (t_.child_pg.bundle.cpu if t_.child_pg else 0)
            for t_ in running_active
            if t_.child_pg and t_.child_pg.ready
        )
        # Cap useful at reserved (don't count more than reserved)
        useful_cpu = min(useful_cpu, reserved_cpu)
        stranded_cpu = max(0.0, reserved_cpu - useful_cpu)

        telemetry.append(TelemetrySample(
            t=round(t, 4),
            free_cpu=cluster.free.cpu,
            free_gpu=cluster.free.gpu,
            allocated_cpu=cluster.allocated.cpu,
            allocated_gpu=cluster.allocated.gpu,
            reserved_cpu=reserved_cpu,
            useful_cpu=useful_cpu,
            stranded_cpu=stranded_cpu,
            running_trials=len(running_active),
            waiting_trials=len(waiting_parents),
            unresolved_trials=sum(
                1 for t_ in workload.trials.values()
                if t_.state in (TrialState.WAITING_PARENT, TrialState.WAITING_CHILD, TrialState.PENDING)
            ),
        ))

        # 8. Run the wait-for observer.
        observer_result = observe(list(workload.trials.values()))
        wait_for_history.append(observer_result)

        # 9. Advance time.
        t = round(t + TICK_S, 4)
        tick_idx += 1

        # Stop early if everything is done.
        all_done = all(
            t_.state in (TrialState.COMPLETED, TrialState.REJECTED, TrialState.FAILED)
            for t_ in workload.trials.values()
        )
        if all_done and not running:
            break

    # 10. After horizon: any trial still in WAITING_CHILD/PENDING/REJECTED
    # stays in its final state. Compute summary.
    final_observer = wait_for_history[-1] if wait_for_history else ObserverResult()
    summary = summarize(
        policy=policy.name,
        trials=list(workload.trials.values()),
        cycles_count=final_observer.cycle_count,
        telemetry=telemetry,
        horizon_s=horizon,
    )

    return SimulationResult(
        fixture=workload_def.name,
        policy=policy.name,
        horizon_s=horizon,
        trials=list(workload.trials.values()),
        events=events,
        telemetry=telemetry,
        wait_for_history=wait_for_history,
        summary=summary,
        cluster_snapshot=cluster.snapshot(),
    )

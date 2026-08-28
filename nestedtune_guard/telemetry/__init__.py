"""Telemetry — derived metrics from a simulation run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..model import Trial


@dataclass
class TelemetrySample:
    """A single point-in-time telemetry sample."""

    t: float
    free_cpu: float
    free_gpu: float
    allocated_cpu: float
    allocated_gpu: float
    reserved_cpu: float       # sum of parent PG reservations
    useful_cpu: float         # CPU actually used by running parents (not waiting)
    stranded_cpu: float       # reserved by waiting parents (parent stuck, child can't fit)
    running_trials: int
    waiting_trials: int
    unresolved_trials: int

    def to_dict(self) -> dict:
        return {
            "t": self.t,
            "free_cpu": self.free_cpu,
            "free_gpu": self.free_gpu,
            "allocated_cpu": self.allocated_cpu,
            "allocated_gpu": self.allocated_gpu,
            "reserved_cpu": self.reserved_cpu,
            "useful_cpu": self.useful_cpu,
            "stranded_cpu": self.stranded_cpu,
            "running_trials": self.running_trials,
            "waiting_trials": self.waiting_trials,
            "unresolved_trials": self.unresolved_trials,
        }


def jain_fairness(values: list[float]) -> float:
    """Compute the Jain fairness index for a list of non-negative values.

    Jain(·) ∈ [1/n, 1]. 1 = perfectly fair (all equal). 1/n = maximally
    unfair (only one value is non-zero).
    """
    if not values:
        return 0.0
    s = sum(values)
    if s <= 0:
        return 0.0
    sq = sum(v * v for v in values)
    return (s * s) / (len(values) * sq)


def cpu_stranding_pct(reserved_cpu: float, useful_cpu: float) -> float:
    """% of reserved CPU that is stranded (not actually useful)."""
    if reserved_cpu <= 0:
        return 0.0
    stranded = max(0.0, reserved_cpu - useful_cpu)
    return (stranded / reserved_cpu) * 100.0


@dataclass
class Summary:
    """Per-policy run summary."""

    policy: str
    total_trials: int
    completed_trials: int
    unresolved_trials: int
    rejected_trials: int
    observed_cycle_count: int
    bounded_resolution_pct: float
    trials_per_hour: float
    queue_p95_s: float
    jain_fairness: float
    avg_cpu_utilisation_pct: float
    avg_cpu_stranding_pct: float

    def to_dict(self) -> dict:
        return {
            "policy": self.policy,
            "total_trials": self.total_trials,
            "completed_trials": self.completed_trials,
            "unresolved_trials": self.unresolved_trials,
            "rejected_trials": self.rejected_trials,
            "observed_cycle_count": self.observed_cycle_count,
            "bounded_resolution_pct": round(self.bounded_resolution_pct, 4),
            "trials_per_hour": round(self.trials_per_hour, 4),
            "queue_p95_s": round(self.queue_p95_s, 4),
            "jain_fairness": round(self.jain_fairness, 4),
            "avg_cpu_utilisation_pct": round(self.avg_cpu_utilisation_pct, 4),
            "avg_cpu_stranding_pct": round(self.avg_cpu_stranding_pct, 4),
        }


def summarize(
    policy: str,
    trials: list["Trial"],
    cycles_count: int,
    telemetry: list[TelemetrySample],
    horizon_s: float,
) -> Summary:
    """Build a Summary from a finished simulation run."""
    from ..model import TrialState

    total = len(trials)
    completed = sum(1 for t in trials if t.state == TrialState.COMPLETED)
    rejected = sum(1 for t in trials if t.state == TrialState.REJECTED)
    # "unresolved" = anything that is neither COMPLETED nor REJECTED at
    # the end of the bounded horizon. This includes PENDING (never
    # admitted), WAITING_PARENT / WAITING_CHILD (deadlock-prone), RUNNING
    # (started but did not finish before horizon), and FAILED.
    unresolved = sum(
        1 for t in trials
        if t.state not in (TrialState.COMPLETED, TrialState.REJECTED)
    )

    # Queue latency: time from arrival to first admitted
    queue_latencies = []
    for t in trials:
        if t.admitted_at is not None and t.schema.arrival_time is not None:
            queue_latencies.append(max(0.0, t.admitted_at - t.schema.arrival_time))
    queue_latencies.sort()
    if queue_latencies:
        idx = int(0.95 * (len(queue_latencies) - 1))
        queue_p95 = queue_latencies[idx]
    else:
        queue_p95 = 0.0

    # Jain fairness across trials' completed-seconds
    # (proxy: each trial's effective runtime, 0 if unresolved)
    fairness_values = []
    for t in trials:
        if t.started_at is not None and t.finished_at is not None:
            fairness_values.append(t.finished_at - t.started_at)
        else:
            fairness_values.append(0.0)
    jain = jain_fairness(fairness_values)

    # Average CPU utilisation and stranding
    if telemetry:
        avg_util = sum(s.useful_cpu / max(s.reserved_cpu, 1e-9) for s in telemetry) / len(telemetry) * 100
        avg_strand = sum(
            cpu_stranding_pct(s.reserved_cpu, s.useful_cpu)
            for s in telemetry
        ) / len(telemetry)
    else:
        avg_util = 0.0
        avg_strand = 0.0

    # Throughput in trials/hour
    if horizon_s > 0:
        tph = (completed / horizon_s) * 3600.0
    else:
        tph = 0.0

    return Summary(
        policy=policy,
        total_trials=total,
        completed_trials=completed,
        unresolved_trials=unresolved,
        rejected_trials=rejected,
        observed_cycle_count=cycles_count,
        bounded_resolution_pct=(completed / total) * 100.0 if total else 0.0,
        trials_per_hour=tph,
        queue_p95_s=queue_p95,
        jain_fairness=jain,
        avg_cpu_utilisation_pct=avg_util,
        avg_cpu_stranding_pct=avg_strand,
    )

"""Autoscaling advice — advisory-only functions over simulation results.

These functions are PURE: they read a SimulationResult and emit
autoscaling advice. They do NOT modify any scheduling decision, trial
state, or simulation output. The advice is a pure function of the
result so that to_dict() stays deterministic.

Design
------
Advice is grounded in what is actually measurable from a result, and
every unresolved trial is classified by WHY it is unresolved:

* ``horizon_limited``  — trial was admitted and RUNNING when the
  bounded horizon cut it off. More capacity would NOT have helped;
  a longer horizon (or shorter trials) would. Reporting this as a
  capacity shortfall would be dishonest advice.

* ``capacity_shortfall`` — the trial's parent demand exceeds the
  cluster's MAXIMUM capacity (including capacity-change events), so
  it can never be admitted at the current scale. This is the only
  case where scaling the cluster up genuinely helps, and the advice
  states the target capacity needed.

* ``ordering_blocked`` — the trial's demand fits within maximum
  capacity but it was never admitted. Scaling will not fix this:
  the trial is blocked by queue ordering (e.g. FIFO head-of-line
  blocking) or by a nested-resource deadlock, not by capacity.

* ``nested_deadlock`` — the trial is stuck in WAITING_CHILD: its
  parent placement group holds resources while its nested child
  waits for resources the parent itself reserves. This is the
  project's source problem (Ray issue #47439); the remedy is the
  CP-2 deadlock-aware admission controller, not autoscaling.

If the fixture included capacity-change events, a ``scaleup_observed``
item reports the last event and how many trials were still unresolved
after it fired.
"""

from __future__ import annotations

from typing import Any

from nestedtune_guard.simulator import SimulationResult

_EPS = 1e-9


def _parent_demand_cpu(trial) -> float:
    bundle = trial.parent_pg.bundle if trial.parent_pg else None
    if bundle is None:
        # Fall back to the requested schema bundle (never admitted).
        src = trial.schema.parent
        return float(src.cpu)
    return float(bundle.cpu)


def _child_demand_cpu(trial) -> float:
    if trial.child_pg is not None and trial.child_pg.bundle is not None:
        return float(trial.child_pg.bundle.cpu)
    src = trial.schema.child
    return float(src.cpu) if src is not None else 0.0


def build_advice(result: SimulationResult) -> dict[str, Any]:
    """Return autoscaling advice for a finished simulation run.

    Advisory-only: does not mutate `result` or any trial state.
    """
    advice: list[dict[str, Any]] = []
    snap = result.cluster_snapshot
    final_free = snap.get("free", {})
    max_cap = snap.get("max_capacity") or {}
    final_cap = snap.get("capacity", {})

    final_free_cpu = float(final_free.get("cpu", 0.0) or 0.0)
    max_cpu = float(max_cap.get("cpu", 0.0) or 0.0)
    final_cap_cpu = float(final_cap.get("cpu", 0.0) or 0.0)

    # Classify every unresolved trial by WHY it is unresolved.
    horizon_limited: list[dict[str, Any]] = []
    shortfall: list[dict[str, Any]] = []
    ordering_blocked: list[dict[str, Any]] = []
    nested_deadlock: list[dict[str, Any]] = []

    for t in result.trials:
        state = str(t.state).rsplit(".", 1)[-1]  # "TrialState.RUNNING" -> "RUNNING"
        if state in ("COMPLETED", "REJECTED", "FAILED"):
            continue
        demand = _parent_demand_cpu(t)
        child_demand = _child_demand_cpu(t)
        entry = {
            "trial_id": t.id,
            "state": state,
            "parent_cpu": demand,
            "child_cpu": child_demand,
            "rejection_reason": t.rejection_reason,
        }
        if state == "RUNNING":
            horizon_limited.append(entry)
        elif state == "WAITING_CHILD":
            nested_deadlock.append(entry)
        elif demand > max_cpu + _EPS:
            shortfall.append(entry)
        else:
            ordering_blocked.append(entry)

    unresolved_total = (
        len(horizon_limited) + len(shortfall) + len(ordering_blocked) + len(nested_deadlock)
    )

    if unresolved_total == 0:
        return {
            "has_advice": False,
            "summary": "All trials completed or rejected; no autoscaling recommendation.",
            "deferred_trials": [],
            "capacity": {
                "final_free_cpu": round(final_free_cpu, 4),
                "max_cpu": round(max_cpu, 4) if max_cap else None,
                "final_capacity_cpu": round(final_cap_cpu, 4),
            },
        }

    # 1) Genuine capacity shortfall: demand exceeds even max capacity.
    if shortfall:
        needed = max(e["parent_cpu"] for e in shortfall)
        target = max(final_cap_cpu, needed)
        advice.append(
            {
                "type": "capacity_shortfall",
                "trial_ids": [e["trial_id"] for e in shortfall],
                "deferred_trial_count": len(shortfall),
                "max_parent_cpu_demand": round(needed, 4),
                "final_free_cpu": round(final_free_cpu, 4),
                "target_capacity_cpu": round(target, 4),
                "message": (
                    f"{len(shortfall)} trial(s) demand more CPU than the cluster's "
                    f"maximum capacity ({max_cpu:.0f} CPU); scale to at least "
                    f"{target:.0f} CPU to admit them."
                ),
            }
        )

    # 2) Ordering-blocked trials: capacity is NOT the problem.
    if ordering_blocked:
        advice.append(
            {
                "type": "ordering_blocked",
                "trial_ids": [e["trial_id"] for e in ordering_blocked],
                "deferred_trial_count": len(ordering_blocked),
                "final_free_cpu": round(final_free_cpu, 4),
                "max_capacity_cpu": round(max_cpu, 4),
                "message": (
                    f"{len(ordering_blocked)} trial(s) fit within maximum capacity "
                    f"({max_cpu:.0f} CPU) but were never admitted — blocked by queue "
                    f"ordering (e.g. FIFO head-of-line) or a nested-resource cycle, "
                    f"not by capacity. Autoscaling will not resolve this; use the "
                    f"deadlock-aware admission controller (CP-2) or a backfilling policy."
                ),
            }
        )

    # 3) Nested deadlock: the source problem of this project.
    if nested_deadlock:
        advice.append(
            {
                "type": "nested_deadlock",
                "trial_ids": [e["trial_id"] for e in nested_deadlock],
                "deferred_trial_count": len(nested_deadlock),
                "message": (
                    f"{len(nested_deadlock)} trial(s) are stuck in WAITING_CHILD — the "
                    f"nested trainer waits for resources its own parent placement group "
                    f"reserves (Ray issue #47439). Autoscaling cannot break a "
                    f"hold-and-wait cycle; the CP-2 deadlock-aware admission controller "
                    f"rejects or defers these trials at admission."
                ),
            }
        )

    # 4) Horizon-limited trials: capacity was fine, time ran out.
    if horizon_limited:
        advice.append(
            {
                "capacity_type": "horizon",
                "type": "horizon_limited",
                "trial_ids": [e["trial_id"] for e in horizon_limited],
                "deferred_trial_count": len(horizon_limited),
                "message": (
                    f"{len(horizon_limited)} trial(s) were admitted and still RUNNING "
                    f"at the {result.horizon_s:.0f}s horizon — they needed more time, "
                    f"not more capacity. Extend the bounded horizon or shorten trials."
                ),
            }
        )

    # 5) Capacity-change events observed during the run.
    scale_events = [e for e in result.events if e.get("type") == "capacity_change"]
    if scale_events:
        last_scale = scale_events[-1]
        advice.append(
            {
                "type": "scaleup_observed",
                "event": last_scale,
                "unresolved_after": unresolved_total,
                "message": (
                    f"Cluster scaled to {last_scale['new_capacity']['cpu']:.0f} CPU at "
                    f"t={last_scale['t']:.1f}s; {unresolved_total} trial(s) remained "
                    f"unresolved after the scale-up."
                ),
            }
        )

    return {
        "has_advice": True,
        "advice": advice,
        "deferred_trials": horizon_limited + shortfall + ordering_blocked + nested_deadlock,
        "capacity": {
            "final_free_cpu": round(final_free_cpu, 4),
            "max_cpu": round(max_cpu, 4) if max_cap else None,
            "final_capacity_cpu": round(final_cap_cpu, 4),
        },
    }


def format_advice(result: SimulationResult) -> str:
    """Human-readable single-string rendering of autoscaling advice."""
    info = build_advice(result)
    lines = [f"Fixture: {result.fixture}  Policy: {result.policy}"]
    lines.append("")
    if not info["has_advice"]:
        lines.append(info["summary"])
    else:
        lines.append(f"Autoscaling advice ({len(info['advice'])} item(s)):")
        lines.append("")
        for item in info["advice"]:
            lines.append(f"  • [{item['type']}] {item['message']}")
        lines.append("")
        lines.append("Unresolved trials:")
        for d in info["deferred_trials"]:
            reason = f" ({d['rejection_reason']})" if d["rejection_reason"] else ""
            lines.append(
                f"  - {d['trial_id']}: state={d['state']} parent_cpu={d['parent_cpu']:.0f} "
                f"child_cpu={d['child_cpu']:.0f}{reason}"
            )
        lines.append("")
        lines.append(
            f"Capacity: final_free_cpu={info['capacity']['final_free_cpu']:.0f} "
            f"final_capacity_cpu={info['capacity']['final_capacity_cpu']:.0f}"
            f"{' max_cpu=' + format(info['capacity']['max_cpu'], '.0f') if info['capacity']['max_cpu'] is not None else ''}"
        )
    return "\n".join(lines)

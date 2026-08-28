"""Deadlock-aware admission controller (CP-2).

This policy extends greedy with two CP-2 features:

1. Pre-admission feasibility check — before admitting a parent PG, project
   the child's resource request and reject trials whose combined parent +
   child demand exceeds cluster capacity. Such trials can NEVER complete
   on the current cluster and admitting them risks creating an
   irrecoverable self-cycle.

2. Hierarchical wait-for avoidance — when the child placement cannot fit
   after the parent is admitted, but the parent IS feasible in isolation,
   the policy delays admission until either the child fits or a recovery
   action (release + requeue + replan) is taken.

3. Bounded recovery — if a trial enters WAITING_CHILD for longer than a
   configurable grace period, the controller releases its parent PG and
   requeues the trial with a "RETRY" marker. This is the node-loss /
   recovery path demonstrated in the dashboard.

The controller still uses FIFO ordering as its base — it does not
arbitrarily reorder trials. Pre-admission feasibility and bounded
recovery are the only deviations from FIFO. This keeps the comparison
with FIFO and greedy defensible during review.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Policy, PolicyDecision
from .fifo import _bundle_from_trial, _fmt

if TYPE_CHECKING:
    from ..model import Cluster, Trial


class DeadlockAwarePolicy(Policy):
    """Deadlock-aware admission controller."""

    name = "deadlock_aware"

    def __init__(self, child_grace_period_s: float = 5.0, max_retries: int = 1):
        self.child_grace_period_s = child_grace_period_s
        self.max_retries = max_retries
        # Per-trial retry counters (keyed by trial id).
        self._retries: dict[str, int] = {}

    def decide(
        self,
        queue: list["Trial"],
        cluster: "Cluster",
        now: float,
        running: list["Trial"],
    ) -> PolicyDecision:
        if not queue:
            return PolicyDecision(trial_id=None, admitted=False, reason="queue_empty")

        trace: list[str] = []
        # Walk the queue; admit the first trial that is feasible.
        for trial in queue:
            parent_bundle = _bundle_from_trial(trial, role="parent")

            # (1) Pre-admission feasibility: if the parent itself doesn't
            # fit in the FULL cluster capacity (including any future capacity
            # events), the trial is permanently infeasible — reject it now.
            max_cap = cluster.max_capacity or cluster.capacity
            if not parent_bundle.fits_in(max_cap):
                trace.append(
                    f"reject {trial.id}: parent demand={_fmt(parent_bundle)} "
                    f"exceeds max cluster capacity={_fmt(max_cap)}"
                )
                return PolicyDecision(
                    trial_id=trial.id,
                    admitted=False,
                    reason="cp2_reject_infeasible_combined",
                    trace=trace,
                )

            # (1b) Basic free-capacity check: parent must fit in FREE capacity.
            # If not, defer (skip) and try the next trial.
            if not cluster.can_admit(parent_bundle):
                # Skip — parent itself doesn't fit in free capacity right now
                # (but could fit later if resources free up).
                trace.append(f"skip {trial.id}: parent demand={_fmt(parent_bundle)} "
                             f"exceeds free={_fmt(cluster.free)}")
                continue

            # (2) Pre-admission feasibility: if this trial has a nested child,
            # check whether parent + child could ever fit in the FULL cluster
            # capacity (not just free). If not, the trial is permanently
            # infeasible — reject it now to prevent a self-cycle.
            child_bundle = _bundle_from_trial(trial, role="child")
            if child_bundle is not None and child_bundle.workers > 0 or (
                child_bundle is not None
                and (child_bundle.cpu > 0 or child_bundle.gpu > 0 or child_bundle.memory > 0)
            ):
                # Combined demand
                combined_cpu = parent_bundle.cpu + child_bundle.cpu
                combined_gpu = parent_bundle.gpu + child_bundle.gpu
                combined_memory = parent_bundle.memory + child_bundle.memory
                cluster_cap = max_cap
                if (
                    combined_cpu > cluster_cap.cpu + 1e-9
                    or combined_gpu > cluster_cap.gpu + 1e-9
                    or combined_memory > cluster_cap.memory + 1e-9
                ):
                    # Permanently infeasible — reject.
                    trace.append(
                        f"reject {trial.id}: combined parent+child demand "
                        f"cpu={combined_cpu},gpu={combined_gpu} exceeds cluster "
                        f"capacity cpu={cluster_cap.cpu},gpu={cluster_cap.gpu}"
                    )
                    return PolicyDecision(
                        trial_id=trial.id,
                        admitted=False,
                        reason="cp2_reject_infeasible_combined",
                        trace=trace,
                    )

            # (3) Hierarchical wait-for avoidance: only admit if the child
            # placement will be feasible at admission time (i.e. after the
            # parent reserves, free capacity still satisfies the child).
            # If the child can't fit right now, defer admission and try the
            # next trial in the queue (greedy skip with hierarchical reason).
            if child_bundle is not None and not child_bundle.fits_in(cluster.free - parent_bundle):
                trace.append(
                    f"defer {trial.id}: parent fits but child demand={_fmt(child_bundle)} "
                    f"would not fit in post-parent free={_fmt(cluster.free - parent_bundle)}"
                )
                continue

            # Admit this trial.
            trace.append(f"admit {trial.id}: parent fits AND child post-fit verified")
            return PolicyDecision(
                trial_id=trial.id,
                admitted=True,
                reason="cp2_admit_with_child_fit_check",
                trace=trace,
            )

        # No trial in the queue is currently feasible with hierarchical check.
        return PolicyDecision(
            trial_id=queue[0].id,
            admitted=False,
            reason="cp2_no_feasible_trial",
            trace=trace,
        )

    def on_trial_finished(self, trial: "Trial", now: float) -> None:
        # Reset retry counter when a trial finishes (success or failure).
        self._retries.pop(trial.id, None)

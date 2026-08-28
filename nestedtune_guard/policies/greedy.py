"""Greedy / backfilling policy — skip infeasible head, admit next feasible trial.

The greedy policy improves throughput by allowing feasible jobs to bypass
an infeasible head-of-line request. It does NOT preempt or reorder
already-running trials. It is still hierarchy-blind: it does not check
whether a trial's nested child will fit; it only checks the parent PG.

Because greedy admits more trials than FIFO, it tends to complete more
trials within the bounded horizon. However, it observes the SAME wait-for
cycles as FIFO for trials that do get admitted — both policies are
hierarchy-blind, so neither prevents the deadlock.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Policy, PolicyDecision
from .fifo import _bundle_from_trial, _fmt

if TYPE_CHECKING:
    from ..model import Cluster, Trial


class GreedyPolicy(Policy):
    name = "greedy"

    def decide(
        self,
        queue: list["Trial"],
        cluster: "Cluster",
        now: float,
        running: list["Trial"],
    ) -> PolicyDecision:
        if not queue:
            return PolicyDecision(trial_id=None, admitted=False, reason="queue_empty")
        # Walk the queue in arrival order; admit the first trial that fits.
        # Trials that do NOT fit (and are infeasible at this moment) are
        # skipped — they remain in the queue and may be admitted later if
        # resources free up.
        for trial in queue:
            parent_bundle = _bundle_from_trial(trial, role="parent")
            if cluster.can_admit(parent_bundle):
                # Greedy skips any trials ahead of this one in the queue.
                # We log skipped trial ids so the operator can see why.
                skipped = [t.id for t in queue if t is not trial]
                return PolicyDecision(
                    trial_id=trial.id,
                    admitted=True,
                    reason="greedy_skipped_infeasible_head" if skipped else "greedy_head_admitted",
                    trace=[
                        f"admit {trial.id}: parent fits in free capacity",
                        *(f"skip {s}: parent demand exceeds free capacity" for s in skipped),
                    ],
                )
        # No trial in the queue fits the free capacity right now.
        return PolicyDecision(
            trial_id=queue[0].id,
            admitted=False,
            reason="greedy_no_feasible_trial",
            trace=[f"hold {queue[0].id}: no trial in queue fits free={_fmt(cluster.free)}"],
        )

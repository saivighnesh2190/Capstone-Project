"""FIFO policy — admit trials in arrival order, head-of-line blocking.

This is the simplest baseline. The trial at the head of the queue is the
only candidate for admission. If it cannot fit, no other trial is tried
and the simulator must wait for resources to free up (or for the bounded
horizon to expire).

This policy is hierarchy-blind: it does not check whether the trial's
nested child will fit; it only checks the parent PG.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Policy, PolicyDecision

if TYPE_CHECKING:
    from ..model import Cluster, Trial


class FIFOPolicy(Policy):
    name = "fifo"

    def decide(
        self,
        queue: list["Trial"],
        cluster: "Cluster",
        now: float,
        running: list["Trial"],
    ) -> PolicyDecision:
        if not queue:
            return PolicyDecision(trial_id=None, admitted=False, reason="queue_empty")
        # FIFO does not reorder: head of queue is the only candidate.
        head = queue[0]
        parent_bundle = _bundle_from_trial(head, role="parent")
        if cluster.can_admit(parent_bundle):
            return PolicyDecision(
                trial_id=head.id,
                admitted=True,
                reason="fifo_head_admitted",
                trace=[f"admit {head.id}: parent fits in free capacity"],
            )
        return PolicyDecision(
            trial_id=head.id,
            admitted=False,
            reason="fifo_head_blocked",
            trace=[
                f"hold {head.id}: parent demand={_fmt(parent_bundle)} "
                f"exceeds free={_fmt(cluster.free)}"
            ],
        )


def _bundle_from_trial(trial: "Trial", role: str):
    """Return the requested bundle for parent or child role."""
    from ..model import ResourceBundle, PlacementStrategy

    schema = trial.schema
    src = schema.parent if role == "parent" else schema.child
    if src is None:
        return ResourceBundle.zero()
    return ResourceBundle(
        cpu=src.cpu,
        gpu=src.gpu,
        memory=src.memory,
        workers=src.workers,
        strategy=PlacementStrategy(src.strategy),
    )


def _fmt(bundle) -> str:
    return f"cpu={bundle.cpu},gpu={bundle.gpu},workers={bundle.workers}"

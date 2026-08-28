"""Base policy interface."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..model import Cluster, Trial


@dataclass
class PolicyDecision:
    """The result of a policy choosing the next trial to admit."""

    trial_id: str | None           # None = no admission this step
    admitted: bool                  # True if resources were reserved
    reason: str                     # human-readable reason code
    trace: list[str] = field(default_factory=list)  # operator-facing trace


class Policy(abc.ABC):
    """Abstract scheduling policy.

    A policy is asked, at each simulation tick, to look at the queue of
    pending trials and decide whether to admit the head (or skip it, in
    which case the simulator may advance time without admitting).

    The policy MUST NOT modify the cluster directly. If it returns
    `admitted=True`, the simulator performs the actual placement. This
    keeps the simulator authoritative for resource accounting and makes
    policy implementations testable in isolation.
    """

    name: str = "policy"

    @abc.abstractmethod
    def decide(
        self,
        queue: list["Trial"],
        cluster: "Cluster",
        now: float,
        running: list["Trial"],
    ) -> PolicyDecision:
        """Choose the next trial to admit (or skip).

        Args:
            queue: trials that have arrived but not yet admitted,
                   in the order the policy prefers (the policy may reorder).
            cluster: current cluster state (free capacity, etc.).
            now: current simulation time (seconds).
            running: currently running trials (parent + child placements).

        Returns:
            A PolicyDecision. If `admitted=True`, `trial_id` must be set
            and the simulator will reserve the parent PG immediately.
        """
        raise NotImplementedError

    def on_trial_finished(self, trial: "Trial", now: float) -> None:
        """Hook called when a trial finishes (default: no-op)."""
        return None

    def on_capacity_change(self, cluster: "Cluster", now: float) -> None:
        """Hook called when cluster capacity changes (default: no-op)."""
        return None

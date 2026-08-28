"""Scheduling policies.

A policy decides, at each simulation step, which pending trial to admit
next and whether to admit it. CP-1 ships with FIFO and greedy baselines;
CP-2 adds the deadlock-aware controller.

The observer (wait-for graph) is independent of policy and never modifies
scheduling decisions — this is the design constraint that keeps CP-1
baselines fair and prevents CP-2 behaviour from leaking into CP-1 results.
"""

from __future__ import annotations

from .base import Policy, PolicyDecision
from .fifo import FIFOPolicy
from .greedy import GreedyPolicy
from .deadlock_aware import DeadlockAwarePolicy

__all__ = [
    "Policy",
    "PolicyDecision",
    "FIFOPolicy",
    "GreedyPolicy",
    "DeadlockAwarePolicy",
]

"""NestedTune Guard — deadlock-aware distributed hyperparameter tuning.

CINT-11 capstone project. Models the Ray placement-group deadlock
described in https://github.com/ray-project/ray/issues/47439 and provides
a deterministic, bounded, reproducible evaluation framework with FIFO and
greedy baselines (CP-1) plus a deadlock-aware admission controller (CP-2).
"""

from __future__ import annotations

__version__ = "1.0.0"
__project_code__ = "CINT-11"
__title__ = "Deadlock-Aware Distributed Hyperparameter Tuning for Nested Trainers"

# Public symbols
from .model import (
    Cluster,
    ResourceBundle,
    PlacementGroup,
    PlacementStrategy,
    Trial,
    TrialState,
    Workload,
    WorkloadDefinition,
)
from .simulator import simulate, SimulationResult
from .policies import Policy, FIFOPolicy, GreedyPolicy, DeadlockAwarePolicy

__all__ = [
    "__version__",
    "__project_code__",
    "__title__",
    "Cluster",
    "ResourceBundle",
    "PlacementGroup",
    "PlacementStrategy",
    "Trial",
    "TrialState",
    "Workload",
    "WorkloadDefinition",
    "simulate",
    "SimulationResult",
    "Policy",
    "FIFOPolicy",
    "GreedyPolicy",
    "DeadlockAwarePolicy",
]

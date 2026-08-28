"""Test fixtures for nestedtune_guard.

Run from project root:
  PYTHONPATH=. python3 -m pytest nestedtune_guard/tests/ -v
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from nestedtune_guard import (
    Cluster,
    ResourceBundle,
    PlacementStrategy,
    WorkloadDefinition,
    simulate,
)
from nestedtune_guard.schema import (
    ResourceBundleSchema,
    TrialSchema,
    CapacityEventSchema,
    SchemaError,
    validate_workload_file,
)
from nestedtune_guard.model import TrialState, Workload
from nestedtune_guard.observer import observe, build_wait_for_graph, detect_cycles
from nestedtune_guard.oracle import EXPECTED_OUTCOMES, expected_for, totals_for_policy, all_fixtures
from nestedtune_guard.policies import FIFOPolicy, GreedyPolicy, DeadlockAwarePolicy

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = PROJECT_ROOT / "fixtures"
DEV_FIXTURES = FIXTURES_DIR / "development"
ACC_FIXTURES = FIXTURES_DIR / "acceptance"

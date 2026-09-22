"""Tests for the autoscaling advisor (nestedtune_guard.advisor).

These run inside the existing pytest suite under nestedtune_guard/tests/.

The advisor classifies every unresolved trial by WHY it is unresolved:
horizon_limited (RUNNING at horizon), capacity_shortfall (demand exceeds
max capacity), ordering_blocked (fits in max capacity but never admitted),
and nested_deadlock (WAITING_CHILD — the Ray #47439 source case).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nestedtune_guard import simulate
from nestedtune_guard.advisor import build_advice, format_advice
from nestedtune_guard.schema import validate_workload_file

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = PROJECT_ROOT / "fixtures"


@pytest.fixture
def scaleup_def():
    return validate_workload_file(FIXTURE_ROOT / "development" / "dev_changing_capacity_scaleup.json")


@pytest.fixture
def hol_def():
    return validate_workload_file(FIXTURE_ROOT / "development" / "dev_fifo_hol_blocking.json")


@pytest.fixture
def ray47439_def():
    return validate_workload_file(FIXTURE_ROOT / "development" / "dev_ray47439_xgboost_deadlock.json")


@pytest.fixture
def safe_gang_def():
    return validate_workload_file(FIXTURE_ROOT / "development" / "dev_safe_gang_scheduled.json")


def _types(info):
    return [a["type"] for a in info["advice"]]


class TestAdvisorBuildAdvice:
    def test_scaleup_fifo_horizon_limited_not_capacity(self, scaleup_def):
        """FIFO on dev_changing_capacity_scaleup leaves scale-small RUNNING
        at the 30s horizon (admitted at t=28). The advisor must classify it
        horizon_limited — NOT recommend a capacity scale-up."""
        result = simulate(scaleup_def, "fifo")
        info = build_advice(result)
        assert info["has_advice"] is True
        types = _types(info)
        assert "horizon_limited" in types
        assert "capacity_shortfall" not in types
        hl = [a for a in info["advice"] if a["type"] == "horizon_limited"][0]
        assert hl["trial_ids"] == ["scale-small"]
        assert "not more capacity" in hl["message"]
        # A scaleup_observed item must also be present (fixture has a capacity event)
        assert "scaleup_observed" in types

    def test_scaleup_greedy_produces_no_advice(self, scaleup_def):
        """Greedy admits both trials; the advisor should report no advice."""
        result = simulate(scaleup_def, "greedy")
        info = build_advice(result)
        assert info["has_advice"] is False
        assert info["deferred_trials"] == []
        assert "All trials completed or rejected" in info["summary"]
        assert info["capacity"]["final_free_cpu"] >= 0

    def test_scaleup_deadlock_aware_no_advice(self, scaleup_def):
        """Deadlock-aware completes both on this fixture."""
        result = simulate(scaleup_def, "deadlock_aware")
        info = build_advice(result)
        assert info["has_advice"] is False

    def test_hol_fifo_flags_capacity_shortfall(self, hol_def):
        """hol-stuck demands 6 CPU on a 4-CPU cluster — a genuine capacity
        shortfall; the advisor must recommend scaling to at least 6 CPU."""
        result = simulate(hol_def, "fifo")
        info = build_advice(result)
        assert info["has_advice"] is True
        types = _types(info)
        assert "capacity_shortfall" in types
        sf = [a for a in info["advice"] if a["type"] == "capacity_shortfall"][0]
        assert sf["trial_ids"] == ["hol-stuck"]
        assert sf["max_parent_cpu_demand"] == 6.0
        assert sf["target_capacity_cpu"] == 6.0
        # hol-bypass fits (2 CPU < 4 max) and was never admitted -> ordering_blocked
        assert "ordering_blocked" in types
        ob = [a for a in info["advice"] if a["type"] == "ordering_blocked"][0]
        assert ob["trial_ids"] == ["hol-bypass"]

    def test_hol_greedy_flags_shortfall_without_ordering_block(self, hol_def):
        """Under greedy, hol-bypass completes; only the genuinely infeasible
        hol-stuck remains -> capacity_shortfall only, no ordering_blocked."""
        result = simulate(hol_def, "greedy")
        info = build_advice(result)
        assert info["has_advice"] is True
        types = _types(info)
        assert "capacity_shortfall" in types
        assert "ordering_blocked" not in types

    def test_ray47439_flags_nested_deadlock(self, ray47439_def):
        """The source case: xgb-001 is WAITING_CHILD — the advisor must
        classify it nested_deadlock and point at the CP-2 controller, not
        autoscaling."""
        result = simulate(ray47439_def, "fifo")
        info = build_advice(result)
        assert info["has_advice"] is True
        types = _types(info)
        assert "nested_deadlock" in types
        nd = [a for a in info["advice"] if a["type"] == "nested_deadlock"][0]
        assert nd["trial_ids"] == ["xgb-001"]
        assert "47439" in nd["message"]
        # No bogus capacity advice on the deadlock case
        assert "capacity_shortfall" not in types

    def test_safe_gang_no_advice(self, safe_gang_def):
        """dev_safe_gang_scheduled has no unresolved trials and no capacity events."""
        result = simulate(safe_gang_def, "fifo")
        info = build_advice(result)
        assert info["has_advice"] is False
        assert info["deferred_trials"] == []

    def test_advice_capacity_fields_populated(self, scaleup_def):
        result = simulate(scaleup_def, "fifo")
        info = build_advice(result)
        cap = info["capacity"]
        assert "final_free_cpu" in cap
        assert "final_capacity_cpu" in cap
        assert "max_cpu" in cap

    def test_advice_deterministic(self, scaleup_def):
        """Two runs of the same (fixture, policy) must produce identical advice."""
        r1 = simulate(scaleup_def, "fifo")
        r2 = simulate(scaleup_def, "fifo")
        assert build_advice(r1) == build_advice(r2)
        assert format_advice(r1) == format_advice(r2)

    def test_format_advice_is_nonempty_string(self, scaleup_def):
        result = simulate(scaleup_def, "fifo")
        text = format_advice(result)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "Fixture:" in text
        assert "Policy:" in text
        assert "Autoscaling advice" in text or "All trials completed" in text

    def test_advice_pure_no_mutation(self, scaleup_def):
        """build_advice must not mutate the result it reads."""
        import json

        result = simulate(scaleup_def, "fifo")
        before = json.dumps(result.to_dict(), sort_keys=True, default=str)
        build_advice(result)
        after = json.dumps(result.to_dict(), sort_keys=True, default=str)
        assert before == after

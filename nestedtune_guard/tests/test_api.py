"""Tests for the FastAPI service (nestedtune_guard.api).

These run inside the existing pytest suite under nestedtune_guard/tests/.
We use fastapi.testclient.TestClient (starlette, bundled with fastapi) so
no extra httpx dependency is required.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nestedtune_guard.api import app
from nestedtune_guard.schema import validate_workload_file

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = PROJECT_ROOT / "fixtures"


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_version(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["package"] == "nestedtune-guard"
        assert body["version"] == "1.0.0"
        assert body["project_code"] == "CINT-11"
        assert "python_version" in body


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

class TestScenarios:
    def test_scenarios_lists_dev_and_acceptance(self, client):
        r = client.get("/scenarios")
        assert r.status_code == 200
        body = r.json()
        assert "development" in body
        assert "acceptance" in body
        # dev_changing_capacity_scaleup must be present
        assert "dev_changing_capacity_scaleup" in body["development"]
        # acc fixtures present
        assert len(body["acceptance"]) >= 2


# ---------------------------------------------------------------------------
# Simulate
# ---------------------------------------------------------------------------

class TestSimulate:
    def test_simulate_valid_fixture_name(self, client):
        r = client.post("/simulate", json={"fixture": "dev_safe_gang_scheduled", "policy": "fifo"})
        assert r.status_code == 200
        body = r.json()
        assert body["fixture"] == "dev_safe_gang_scheduled"
        assert body["policy"] == "fifo"
        assert "summary" in body
        assert body["summary"]["completed_trials"] == 2

    def test_simulate_valid_fixture_path(self, client):
        path = str(FIXTURE_ROOT / "development" / "dev_safe_gang_scheduled.json")
        r = client.post("/simulate", json={"fixture": path, "policy": "greedy"})
        assert r.status_code == 200
        body = r.json()
        assert body["fixture_path"] == path
        assert body["policy"] == "greedy"

    def test_simulate_bad_policy(self, client):
        r = client.post("/simulate", json={"fixture": "dev_safe_gang_scheduled", "policy": "notapolicy"})
        assert r.status_code == 422
        detail = r.json()["detail"]
        # pydantic pattern validation produces a list of error dicts
        assert isinstance(detail, list) or "policy" in str(detail).lower()

    def test_simulate_unknown_fixture(self, client):
        r = client.post("/simulate", json={"fixture": "nope_ghost_fixture", "policy": "fifo"})
        assert r.status_code == 404

    def test_simulate_deadlock_fixture(self, client):
        r = client.post("/simulate", json={"fixture": "dev_ray47439_xgboost_deadlock", "policy": "fifo"})
        assert r.status_code == 200
        body = r.json()
        assert body["summary"]["completed_trials"] == 0
        assert body["summary"]["unresolved_trials"] == 1
        assert body["summary"]["observed_cycle_count"] == 1

    def test_simulate_deadlock_aware(self, client):
        r = client.post("/simulate", json={"fixture": "dev_ray47439_xgboost_deadlock", "policy": "deadlock_aware"})
        assert r.status_code == 200
        body = r.json()
        assert body["summary"]["rejected_trials"] == 1
        assert body["summary"]["unresolved_trials"] == 0

    def test_simulate_json_contract(self, client):
        """The result dict must contain the canonical keys produced by to_dict()."""
        r = client.post("/simulate", json={"fixture": "dev_safe_nested_xgboost", "policy": "fifo"})
        assert r.status_code == 200
        body = r.json()
        for key in ("fixture", "policy", "horizon_s", "trials", "events", "telemetry", "wait_for_history", "summary", "cluster_snapshot"):
            assert key in body, f"missing key {key!r} in simulate response"


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

class TestBenchmark:
    def test_benchmark_returns_fixtures_and_totals(self, client):
        r = client.get("/benchmark")
        assert r.status_code == 200
        body = r.json()
        assert "fixtures" in body
        assert "totals" in body
        assert len(body["fixtures"]) == 7  # 7 development fixtures
        for policy in ("fifo", "greedy", "deadlock_aware"):
            assert policy in body["totals"]
            t = body["totals"][policy]
            assert "completed" in t
            assert "unresolved" in t
            assert "cycles" in t

    def test_benchmark_totals_match_known_cp1(self, client):
        r = client.get("/benchmark")
        body = r.json()
        fifo = body["totals"]["fifo"]
        greedy = body["totals"]["greedy"]
        assert fifo["completed"] == 5
        assert fifo["unresolved"] == 7
        assert fifo["cycles"] == 4
        assert greedy["completed"] == 7
        assert greedy["unresolved"] == 5
        assert greedy["cycles"] == 4


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

class TestValidate:
    def test_validate_passes(self, client):
        r = client.get("/validate")
        assert r.status_code == 200
        body = r.json()
        assert body["pass"] is True
        assert body["fail_count"] == 0
        assert body["total_pairs"] == 14  # 7 fixtures x 2 policies (fifo, greedy)

"""Determinism + repeatability tests (3 tests)."""
import json
from nestedtune_guard import simulate
from nestedtune_guard.schema import WorkloadDefinition
from nestedtune_guard.tests.conftest import DEV_FIXTURES


class TestDeterminism:
    def test_same_run_produces_identical_results(self):
        """Two consecutive runs of the same (fixture, policy) pair must
        produce byte-identical JSON output."""
        path = DEV_FIXTURES / "dev_pytorch_nested_contention.json"
        d = WorkloadDefinition.from_file(path)
        r1 = simulate(d, "fifo")
        r2 = simulate(d, "fifo")
        j1 = json.dumps(r1.to_dict(), sort_keys=True, default=str)
        j2 = json.dumps(r2.to_dict(), sort_keys=True, default=str)
        assert j1 == j2

    def test_all_fixtures_deterministic_across_policies(self):
        """Every (fixture, policy) pair must be deterministic."""
        for path in sorted(DEV_FIXTURES.glob("*.json")):
            d = WorkloadDefinition.from_file(path)
            for policy in ("fifo", "greedy", "deadlock_aware"):
                r1 = simulate(d, policy)
                r2 = simulate(d, policy)
                j1 = json.dumps(r1.to_dict(), sort_keys=True, default=str)
                j2 = json.dumps(r2.to_dict(), sort_keys=True, default=str)
                assert j1 == j2, f"non-deterministic: {path.stem}/{policy}"

    def test_bounded_horizon_is_enforced(self):
        """Every fixture must terminate at its bounded_horizon_s."""
        for path in sorted(DEV_FIXTURES.glob("*.json")):
            d = WorkloadDefinition.from_file(path)
            r = simulate(d, "fifo")
            # The last telemetry sample's t should not exceed horizon + tick.
            assert r.horizon_s == d.bounded_horizon_s
            # Telemetry should have ≤ horizon_s / TICK_S + small overhead samples.
            # (TICK_S = 0.1, so a 30s horizon yields ≤ ~301 samples.)
            assert len(r.telemetry) <= (d.bounded_horizon_s / 0.1) + 2

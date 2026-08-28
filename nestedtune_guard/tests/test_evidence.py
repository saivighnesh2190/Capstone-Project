"""Evidence generation tests (3 tests) + Oracle agreement tests (5 tests)."""
import json
from nestedtune_guard import simulate
from nestedtune_guard.schema import WorkloadDefinition, validate_workload_file
from nestedtune_guard.oracle import EXPECTED_OUTCOMES, expected_for, totals_for_policy, all_fixtures
from nestedtune_guard.tests.conftest import DEV_FIXTURES


class TestEvidenceGeneration:
    def test_simulate_output_contains_required_fields(self):
        path = DEV_FIXTURES / "dev_safe_gang_scheduled.json"
        d = WorkloadDefinition.from_file(path)
        result = simulate(d, "fifo")
        out = result.to_dict()
        for key in ("fixture", "policy", "horizon_s", "trials",
                    "events", "telemetry", "wait_for_history", "summary", "cluster_snapshot"):
            assert key in out, f"missing field {key!r}"

    def test_summary_contains_required_metrics(self):
        path = DEV_FIXTURES / "dev_safe_gang_scheduled.json"
        d = WorkloadDefinition.from_file(path)
        result = simulate(d, "fifo")
        s = result.summary.to_dict()
        for key in ("policy", "total_trials", "completed_trials", "unresolved_trials",
                    "rejected_trials", "observed_cycle_count", "bounded_resolution_pct",
                    "trials_per_hour", "queue_p95_s", "jain_fairness",
                    "avg_cpu_utilisation_pct", "avg_cpu_stranding_pct"):
            assert key in s, f"missing summary metric {key!r}"

    def test_wait_for_history_records_each_tick(self):
        path = DEV_FIXTURES / "dev_safe_gang_scheduled.json"
        d = WorkloadDefinition.from_file(path)
        result = simulate(d, "fifo")
        # Wait-for history should have one entry per tick (matches telemetry length).
        assert len(result.wait_for_history) == len(result.telemetry)


class TestOracleAgreement:
    """All (fixture, policy) pairs must match the oracle."""

    def test_all_21_pairs_match_oracle(self):
        failures = []
        for fixture_name in all_fixtures():
            path = DEV_FIXTURES / f"{fixture_name}.json"
            d = validate_workload_file(path)
            for policy in ("fifo", "greedy", "deadlock_aware"):
                expected = expected_for(fixture_name, policy)
                if expected is None:
                    continue
                result = simulate(d, policy)
                ok = (
                    result.summary.completed_trials == expected.completed
                    and result.summary.unresolved_trials == expected.unresolved
                    and result.summary.rejected_trials == expected.rejected
                    and result.summary.observed_cycle_count == expected.cycles
                )
                if not ok:
                    failures.append(
                        f"{fixture_name}/{policy}: "
                        f"expected (c={expected.completed},u={expected.unresolved},"
                        f"r={expected.rejected},cy={expected.cycles}) "
                        f"got (c={result.summary.completed_trials},"
                        f"u={result.summary.unresolved_trials},"
                        f"r={result.summary.rejected_trials},"
                        f"cy={result.summary.observed_cycle_count})"
                    )
        assert not failures, "Oracle mismatches:\n  " + "\n  ".join(failures)

    def test_fifo_headline_totals_match_chat_spec(self):
        """FIFO must produce 5/12 completed, 7 unresolved, 4 cycles."""
        t = totals_for_policy("fifo")
        total_c = 0
        total_u = 0
        total_cy = 0
        for fixture_name in all_fixtures():
            path = DEV_FIXTURES / f"{fixture_name}.json"
            d = validate_workload_file(path)
            r = simulate(d, "fifo")
            total_c += r.summary.completed_trials
            total_u += r.summary.unresolved_trials
            total_cy += r.summary.observed_cycle_count
        assert total_c == 5, f"FIFO completed mismatch: got {total_c}, expected 5"
        assert total_u == 7, f"FIFO unresolved mismatch: got {total_u}, expected 7"
        assert total_cy == 4, f"FIFO cycles mismatch: got {total_cy}, expected 4"

    def test_greedy_headline_totals_match_chat_spec(self):
        """Greedy must produce 7/12 completed, 5 unresolved, 4 cycles."""
        total_c = 0
        total_u = 0
        total_cy = 0
        for fixture_name in all_fixtures():
            path = DEV_FIXTURES / f"{fixture_name}.json"
            d = validate_workload_file(path)
            r = simulate(d, "greedy")
            total_c += r.summary.completed_trials
            total_u += r.summary.unresolved_trials
            total_cy += r.summary.observed_cycle_count
        assert total_c == 7, f"Greedy completed mismatch: got {total_c}, expected 7"
        assert total_u == 5, f"Greedy unresolved mismatch: got {total_u}, expected 5"
        assert total_cy == 4, f"Greedy cycles mismatch: got {total_cy}, expected 4"

    def test_cp2_produces_zero_unresolved_deadlocks(self):
        """CP-2 deadlock-aware controller must produce zero unresolved
        deadlocks across all development fixtures."""
        total_unresolved = 0
        total_cycles = 0
        for fixture_name in all_fixtures():
            path = DEV_FIXTURES / f"{fixture_name}.json"
            d = validate_workload_file(path)
            r = simulate(d, "deadlock_aware")
            total_unresolved += r.summary.unresolved_trials
            total_cycles += r.summary.observed_cycle_count
        assert total_unresolved == 0, f"CP-2 has {total_unresolved} unresolved trials (expected 0)"
        assert total_cycles == 0, f"CP-2 has {total_cycles} cycles (expected 0)"

    def test_cp1_gate_passes(self):
        """The CP-1 gate command must exit 0."""
        import subprocess
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parents[2]
        proc = subprocess.run(
            [sys.executable, "-m", "nestedtune_guard.cli", "gate"],
            cwd=str(project_root),
            env={**__import__("os").environ, "PYTHONPATH": str(project_root)},
            capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 0, f"Gate failed:\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        assert "CP1 GATE PASS" in proc.stdout

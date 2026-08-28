"""Wait-for cycle detection tests (4 tests)."""
from nestedtune_guard import simulate
from nestedtune_guard.model import Trial, TrialState
from nestedtune_guard.observer import observe, build_wait_for_graph, detect_cycles, WaitForEdge, Cycle
from nestedtune_guard.schema import WorkloadDefinition
from nestedtune_guard.tests.conftest import DEV_FIXTURES


class TestWaitForGraph:
    def test_waiting_child_produces_self_cycle(self):
        """Ray #47439 source case: a single trial in WAITING_CHILD must
        produce exactly one self-cycle in the wait-for graph."""
        path = DEV_FIXTURES / "dev_ray47439_xgboost_deadlock.json"
        d = WorkloadDefinition.from_file(path)
        result = simulate(d, "fifo")
        # The trial should be in WAITING_CHILD state.
        trial_states = [t.state for t in result.trials]
        assert TrialState.WAITING_CHILD in trial_states
        # Observer should report exactly 1 cycle.
        final_obs = result.wait_for_history[-1]
        assert final_obs.cycle_count == 1
        # The cycle should be a self-cycle on xgb-001.
        cycle = final_obs.cycles[0]
        assert cycle.kind == "self_cycle"
        assert "xgb-001" in cycle.members

    def test_safe_control_produces_zero_cycles(self):
        """Safe nested XGBoost control: observer must report 0 cycles."""
        path = DEV_FIXTURES / "dev_safe_nested_xgboost.json"
        d = WorkloadDefinition.from_file(path)
        result = simulate(d, "fifo")
        final_obs = result.wait_for_history[-1]
        assert final_obs.cycle_count == 0

    def test_gpu_fragmentation_produces_two_cycles(self):
        """GPU STRICT_PACK fragmentation: 2 trials each in WAITING_CHILD
        must produce 2 self-cycles."""
        path = DEV_FIXTURES / "dev_gpu_strict_pack_fragmentation.json"
        d = WorkloadDefinition.from_file(path)
        result = simulate(d, "fifo")
        final_obs = result.wait_for_history[-1]
        assert final_obs.cycle_count == 2

    def test_observer_never_modifies_scheduling_decisions(self):
        """The observer is observer-only. Running observe() before and
        after a simulate() call must not change trial states."""
        path = DEV_FIXTURES / "dev_ray47439_xgboost_deadlock.json"
        d = WorkloadDefinition.from_file(path)
        from nestedtune_guard.model import Workload
        workload = Workload.from_definition(d)
        trials_before = list(workload.trials.values())
        states_before = [t.state for t in trials_before]
        _ = observe(trials_before)
        states_after = [t.state for t in workload.trials.values()]
        assert states_before == states_after

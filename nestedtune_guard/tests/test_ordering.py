"""FIFO and greedy ordering tests (4 tests)."""
from nestedtune_guard import ResourceBundle, Cluster, simulate
from nestedtune_guard.policies import FIFOPolicy, GreedyPolicy
from nestedtune_guard.schema import WorkloadDefinition
from nestedtune_guard.tests.conftest import DEV_FIXTURES


class TestOrdering:
    def test_fifo_admits_head_when_feasible(self):
        policy = FIFOPolicy()
        from nestedtune_guard.model import Trial, TrialState
        from nestedtune_guard.schema import TrialSchema, ResourceBundleSchema
        cluster = Cluster(capacity=ResourceBundle(cpu=4))
        t = Trial(schema=TrialSchema(
            id="t1", arrival_time=0, duration=1,
            parent=ResourceBundleSchema(cpu=2),
        ))
        d = policy.decide([t], cluster, 0.0, [])
        assert d.admitted
        assert d.trial_id == "t1"

    def test_fifo_holds_head_when_infeasible(self):
        policy = FIFOPolicy()
        from nestedtune_guard.model import Trial
        from nestedtune_guard.schema import TrialSchema, ResourceBundleSchema
        cluster = Cluster(capacity=ResourceBundle(cpu=2))
        t = Trial(schema=TrialSchema(
            id="big", arrival_time=0, duration=1,
            parent=ResourceBundleSchema(cpu=4),
        ))
        d = policy.decide([t], cluster, 0.0, [])
        assert not d.admitted

    def test_greedy_skips_infeasible_head(self):
        policy = GreedyPolicy()
        from nestedtune_guard.model import Trial
        from nestedtune_guard.schema import TrialSchema, ResourceBundleSchema
        cluster = Cluster(capacity=ResourceBundle(cpu=4))
        head = Trial(schema=TrialSchema(
            id="big", arrival_time=0, duration=1,
            parent=ResourceBundleSchema(cpu=6),
        ))
        bypass = Trial(schema=TrialSchema(
            id="small", arrival_time=0.1, duration=1,
            parent=ResourceBundleSchema(cpu=2),
        ))
        d = policy.decide([head, bypass], cluster, 0.1, [])
        assert d.admitted
        assert d.trial_id == "small"

    def test_fifo_hol_blocking_fixture_produces_hol_under_fifo(self):
        """Fix4 under FIFO should produce 0 completed (both blocked) and 2 unresolved."""
        path = DEV_FIXTURES / "dev_fifo_hol_blocking.json"
        d = WorkloadDefinition.from_file(path)
        result = simulate(d, "fifo")
        assert result.summary.completed_trials == 0
        assert result.summary.unresolved_trials == 2
        assert result.summary.observed_cycle_count == 0

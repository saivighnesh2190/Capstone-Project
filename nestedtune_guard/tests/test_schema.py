"""Schema validation tests (6 tests)."""
from nestedtune_guard.schema import (
    ResourceBundleSchema, TrialSchema, CapacityEventSchema,
    WorkloadDefinition, validate_workload_file, SchemaError,
)
from nestedtune_guard.tests.conftest import DEV_FIXTURES, ACC_FIXTURES


class TestResourceBundleSchema:
    def test_resource_bundle_accepts_all_fields(self):
        b = ResourceBundleSchema.from_dict({"cpu": 4, "gpu": 2, "memory": 8, "workers": 4, "strategy": "PACK"})
        assert b.cpu == 4
        assert b.gpu == 2
        assert b.memory == 8
        assert b.workers == 4
        assert b.strategy == "PACK"

    def test_resource_bundle_rejects_negative_values(self):
        with __import__("pytest").raises(SchemaError):
            ResourceBundleSchema.from_dict({"cpu": -1})


class TestTrialSchema:
    def test_trial_requires_id(self):
        import pytest
        with pytest.raises(SchemaError):
            TrialSchema.from_dict({"arrival_time": 0.0, "duration": 1.0, "parent": {"cpu": 1}})

    def test_trial_requires_positive_duration(self):
        import pytest
        with pytest.raises(SchemaError):
            TrialSchema.from_dict({"id": "t1", "arrival_time": 0, "duration": 0, "parent": {"cpu": 1}})

    def test_trial_accepts_optional_child(self):
        t = TrialSchema.from_dict({
            "id": "t1", "arrival_time": 0, "duration": 1,
            "parent": {"cpu": 1}, "child": {"cpu": 1}
        })
        assert t.child is not None
        assert t.child.cpu == 1


class TestWorkloadDefinition:
    def test_workload_requires_cluster(self):
        import pytest
        with pytest.raises(SchemaError):
            WorkloadDefinition.from_dict({"trials": [{"id": "t", "duration": 1, "parent": {"cpu": 1}}]})

    def test_workload_rejects_duplicate_trial_ids(self):
        import pytest
        with pytest.raises(SchemaError):
            WorkloadDefinition.from_dict({
                "cluster": {"cpu": 4},
                "trials": [
                    {"id": "dup", "arrival_time": 0, "duration": 1, "parent": {"cpu": 1}},
                    {"id": "dup", "arrival_time": 0, "duration": 1, "parent": {"cpu": 1}},
                ]
            })

    def test_all_dev_fixtures_validate(self):
        for path in sorted(DEV_FIXTURES.glob("*.json")):
            d = validate_workload_file(path)
            assert d.name == path.stem

    def test_all_acceptance_fixtures_validate(self):
        for path in sorted(ACC_FIXTURES.glob("*.json")):
            d = validate_workload_file(path)
            assert d.name == path.stem

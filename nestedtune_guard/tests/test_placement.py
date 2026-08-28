"""Placement strategy and atomic allocation tests (5 tests)."""
from nestedtune_guard import ResourceBundle, PlacementStrategy, Cluster


class TestPlacementStrategies:
    def test_all_four_strategies_parse(self):
        for s in ["PACK", "STRICT_PACK", "SPREAD", "STRICT_SPREAD"]:
            b = ResourceBundle(cpu=1, strategy=PlacementStrategy(s))
            assert b.strategy.value == s


class TestAtomicAllocation:
    def test_admit_consumes_free_capacity(self):
        c = Cluster(capacity=ResourceBundle(cpu=4))
        c.admit(ResourceBundle(cpu=3))
        assert c.free.cpu == 1

    def test_admit_fails_when_not_enough_free(self):
        import pytest
        c = Cluster(capacity=ResourceBundle(cpu=2))
        with pytest.raises(RuntimeError):
            c.admit(ResourceBundle(cpu=3))

    def test_release_restores_free_capacity(self):
        c = Cluster(capacity=ResourceBundle(cpu=4))
        b = ResourceBundle(cpu=2)
        c.admit(b)
        c.release(b)
        assert c.free.cpu == 4

    def test_bundle_subtraction_clamps_at_zero(self):
        c = Cluster(capacity=ResourceBundle(cpu=2))
        c.admit(ResourceBundle(cpu=2))
        # Release more than allocated → clamped at 0, not negative
        c.release(ResourceBundle(cpu=5))
        assert c.allocated.cpu == 0

    def test_bundle_fits_in_respects_all_dimensions(self):
        a = ResourceBundle(cpu=4, gpu=2, memory=8, workers=4)
        b = ResourceBundle(cpu=4, gpu=2, memory=8, workers=4)
        assert b.fits_in(a)
        # One dimension over → doesn't fit
        assert not ResourceBundle(cpu=5).fits_in(a)
        assert not ResourceBundle(gpu=3).fits_in(a)

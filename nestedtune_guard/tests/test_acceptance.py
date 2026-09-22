"""CP-2 acceptance behavior tests."""

from nestedtune_guard import simulate
from nestedtune_guard.model import TrialState
from nestedtune_guard.schema import validate_workload_file
from nestedtune_guard.tests.conftest import ACC_FIXTURES


def test_node_loss_requires_deadlock_aware_retry():
    definition = validate_workload_file(
        ACC_FIXTURES / "acc_cp2_node_loss_recovery.json"
    )

    fifo = simulate(definition, "fifo")
    recovered = simulate(definition, "deadlock_aware")

    assert fifo.trials[0].state == TrialState.FAILED
    assert recovered.trials[0].state == TrialState.COMPLETED
    assert [event["type"] for event in recovered.events].count("trial_requeued") == 1
    assert [event["type"] for event in recovered.events].count("node_lost") == 1


def test_deadlock_aware_preempts_low_priority_trial():
    definition = validate_workload_file(
        ACC_FIXTURES / "acc_cp2_priority_preempt.json"
    )

    fifo = simulate(definition, "fifo")
    preemptive = simulate(definition, "deadlock_aware")

    assert not any(event["type"] == "trial_preempted" for event in fifo.events)
    preemptions = [
        event for event in preemptive.events if event["type"] == "trial_preempted"
    ]
    assert len(preemptions) == 1
    assert preemptions[0]["trial_id"] == "low-prio-001"
    assert preemptions[0]["preempted_by"] == "high-prio-001"

    completed = [
        event["trial_id"]
        for event in preemptive.events
        if event["type"] == "trial_completed"
    ]
    assert completed == ["high-prio-001", "low-prio-001"]

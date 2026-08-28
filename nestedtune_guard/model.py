"""Resource model — cluster, placement groups, trials.

These are the runtime types used by the simulator. They wrap the schema
types with mutable state (allocated, reserved, useful, stranded) and a
few simulation-only fields (parent/child placement groups, end time).
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from typing import Iterable

from .schema import ResourceBundleSchema, TrialSchema, WorkloadDefinition


class PlacementStrategy(str, enum.Enum):
    PACK = "PACK"
    STRICT_PACK = "STRICT_PACK"
    SPREAD = "SPREAD"
    STRICT_SPREAD = "STRICT_SPREAD"


class TrialState(str, enum.Enum):
    PENDING = "PENDING"           # not yet admitted
    WAITING_PARENT = "WAITING_PARENT"  # parent PG pending
    WAITING_CHILD = "WAITING_CHILD"    # child PG pending (the deadlock state)
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"          # admission refused (CP-2)


@dataclass
class ResourceBundle:
    """A resource bundle at runtime (cluster capacity or PG reservation)."""

    cpu: float = 0.0
    gpu: float = 0.0
    memory: float = 0.0
    workers: int = 0
    strategy: PlacementStrategy = PlacementStrategy.PACK

    @classmethod
    def from_schema(cls, s: ResourceBundleSchema) -> "ResourceBundle":
        return cls(
            cpu=s.cpu,
            gpu=s.gpu,
            memory=s.memory,
            workers=s.workers,
            strategy=PlacementStrategy(s.strategy),
        )

    @classmethod
    def zero(cls) -> "ResourceBundle":
        return cls()

    def fits_in(self, other: "ResourceBundle") -> bool:
        """Return True iff this bundle's demand can be satisfied by `other`."""
        return (
            self.cpu <= other.cpu + 1e-9
            and self.gpu <= other.gpu + 1e-9
            and self.memory <= other.memory + 1e-9
            and self.workers <= other.workers
        )

    def __add__(self, other: "ResourceBundle") -> "ResourceBundle":
        return ResourceBundle(
            cpu=self.cpu + other.cpu,
            gpu=self.gpu + other.gpu,
            memory=self.memory + other.memory,
            workers=self.workers + other.workers,
            strategy=self.strategy,
        )

    def __sub__(self, other: "ResourceBundle") -> "ResourceBundle":
        return ResourceBundle(
            cpu=max(0.0, self.cpu - other.cpu),
            gpu=max(0.0, self.gpu - other.gpu),
            memory=max(0.0, self.memory - other.memory),
            workers=max(0, self.workers - other.workers),
            strategy=self.strategy,
        )


@dataclass
class Cluster:
    """Mutable cluster state. Free capacity = current capacity - allocated.

    `max_capacity` is the maximum capacity the cluster will ever reach
    (initial capacity + all capacity-event peaks). Policies use it to
    decide permanent infeasibility: a trial whose demand exceeds
    `max_capacity` can NEVER run on this cluster and should be rejected.
    """

    capacity: ResourceBundle
    allocated: ResourceBundle = field(default_factory=ResourceBundle.zero)
    pending_events: list = field(default_factory=list)
    max_capacity: ResourceBundle | None = None

    @property
    def free(self) -> ResourceBundle:
        return self.capacity - self.allocated

    def can_admit(self, bundle: ResourceBundle) -> bool:
        return bundle.fits_in(self.free)

    def admit(self, bundle: ResourceBundle) -> None:
        if not self.can_admit(bundle):
            raise RuntimeError("admit() called on a bundle that does not fit")
        self.allocated = self.allocated + bundle

    def release(self, bundle: ResourceBundle) -> None:
        self.allocated = self.allocated - bundle

    def apply_capacity_change(self, new_capacity: ResourceBundle) -> None:
        """Replace the cluster capacity (used for scale-up events).

        Note: we do not touch `allocated` — existing reservations stay valid.
        """
        self.capacity = new_capacity
        # Update max_capacity if this event's capacity exceeds current max.
        if self.max_capacity is None:
            self.max_capacity = new_capacity
        else:
            self.max_capacity = ResourceBundle(
                cpu=max(self.max_capacity.cpu, new_capacity.cpu),
                gpu=max(self.max_capacity.gpu, new_capacity.gpu),
                memory=max(self.max_capacity.memory, new_capacity.memory),
                workers=max(self.max_capacity.workers, new_capacity.workers),
                strategy=self.max_capacity.strategy,
            )

    def snapshot(self) -> dict:
        free = self.free
        return {
            "capacity": _bundle_dict(self.capacity),
            "allocated": _bundle_dict(self.allocated),
            "free": _bundle_dict(free),
            "max_capacity": _bundle_dict(self.max_capacity) if self.max_capacity else None,
        }


def _bundle_dict(b: ResourceBundle) -> dict:
    return {
        "cpu": b.cpu,
        "gpu": b.gpu,
        "memory": b.memory,
        "workers": b.workers,
        "strategy": b.strategy.value,
    }


@dataclass
class PlacementGroup:
    """A placement group created by a trial (parent or child)."""

    owner_id: str            # trial id that owns this PG
    role: str                # "parent" or "child"
    bundle: ResourceBundle
    ready: bool = False      # True once admitted
    created_at: float = 0.0

    @property
    def is_parent(self) -> bool:
        return self.role == "parent"


@dataclass
class Trial:
    """A single tuning trial at runtime."""

    schema: TrialSchema
    state: TrialState = TrialState.PENDING
    parent_pg: PlacementGroup | None = None
    child_pg: PlacementGroup | None = None
    admitted_at: float | None = None
    started_at: float | None = None
    finished_at: float | None = None
    rejection_reason: str | None = None
    cycle_id: int | None = None  # set by observer if part of a wait-for cycle

    @property
    def id(self) -> str:
        return self.schema.id

    @property
    def tags(self) -> tuple[str, ...]:
        return self.schema.tags

    @property
    def has_child(self) -> bool:
        return self.schema.child is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "state": self.state.value,
            "admitted_at": self.admitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "rejection_reason": self.rejection_reason,
            "cycle_id": self.cycle_id,
            "has_child": self.has_child,
            "tags": list(self.tags),
            "parent_bundle": _bundle_dict(self.parent_pg.bundle) if self.parent_pg else None,
            "child_bundle": _bundle_dict(self.child_pg.bundle) if self.child_pg else None,
        }


@dataclass
class Workload:
    """Runtime view of a validated workload definition."""

    definition: WorkloadDefinition
    cluster: Cluster
    trials: dict[str, Trial]
    # Sorted-by-time list of pending capacity-change events. Mutated by the
    # simulator as events are applied. Lives on Workload so the simulator
    # has a single mutable surface for capacity evolution.
    capacity_events: list = field(default_factory=list)

    @classmethod
    def from_definition(cls, definition: WorkloadDefinition) -> "Workload":
        initial_cap = ResourceBundle.from_schema(definition.cluster)
        # Pre-compute max_capacity as the max over initial + all capacity events.
        # This lets the CP-2 policy make correct permanent-feasibility decisions
        # at t=0 (before any capacity event has fired).
        events = sorted(definition.capacity_events, key=lambda e: e.time)
        event_bundles = [ResourceBundle.from_schema(e.capacity) for e in events]
        max_cap = ResourceBundle(
            cpu=max([initial_cap.cpu] + [b.cpu for b in event_bundles]),
            gpu=max([initial_cap.gpu] + [b.gpu for b in event_bundles]),
            memory=max([initial_cap.memory] + [b.memory for b in event_bundles]),
            workers=max([initial_cap.workers] + [b.workers for b in event_bundles]),
            strategy=initial_cap.strategy,
        )
        cluster = Cluster(capacity=initial_cap, max_capacity=max_cap)
        trials = {
            t.id: Trial(schema=t)
            for t in definition.trials
        }
        # Convert schema bundles to runtime bundles for the simulator.
        events = [
            type("E", (), {"time": e.time, "capacity": ResourceBundle.from_schema(e.capacity)})()
            for e in events
        ]
        return cls(definition=definition, cluster=cluster, trials=trials, capacity_events=events)

    @property
    def trials_in_arrival_order(self) -> list[Trial]:
        return sorted(self.trials.values(), key=lambda t: (t.schema.arrival_time, t.id))

    @property
    def bounded_horizon_s(self) -> float:
        return self.definition.bounded_horizon_s

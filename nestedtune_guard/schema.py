"""Workload schema and validation.

A workload definition is a JSON document describing:

  - cluster capacity (CPU, GPU, memory, workers)
  - an optional list of capacity-change events (for scale-up tests)
  - a list of trials, each with:
      - id
      - arrival_time
      - duration (s)
      - parent resource request (a placement-group bundle)
      - optional child resource request (the nested trainer)
      - tags (e.g. "xgb", "pytorch", "gang")

The schema is intentionally permissive about unknown keys — operators may
attach metadata (owner, team, ticket) without breaking the simulator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class SchemaError(ValueError):
    """Raised when a workload definition fails schema validation."""


@dataclass(frozen=True)
class ResourceBundleSchema:
    """A resource bundle as it appears in the workload JSON."""

    cpu: float = 0.0
    gpu: float = 0.0
    memory: float = 0.0
    workers: int = 0
    strategy: str = "PACK"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResourceBundleSchema":
        if not isinstance(data, dict):
            raise SchemaError(f"resource bundle must be a JSON object, got {type(data).__name__}")
        cpu = float(data.get("cpu", 0))
        gpu = float(data.get("gpu", 0))
        memory = float(data.get("memory", 0))
        workers = int(data.get("workers", 0))
        strategy = str(data.get("strategy", "PACK")).upper()
        if strategy not in {"PACK", "STRICT_PACK", "SPREAD", "STRICT_SPREAD"}:
            raise SchemaError(
                f"unknown placement strategy {strategy!r}; expected one of "
                "PACK/STRICT_PACK/SPREAD/STRICT_SPREAD"
            )
        if cpu < 0 or gpu < 0 or memory < 0 or workers < 0:
            raise SchemaError("resource values must be non-negative")
        return cls(cpu=cpu, gpu=gpu, memory=memory, workers=workers, strategy=strategy)


@dataclass(frozen=True)
class TrialSchema:
    """A trial definition as it appears in the workload JSON."""

    id: str
    arrival_time: float
    duration: float
    parent: ResourceBundleSchema
    child: ResourceBundleSchema | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrialSchema":
        if not isinstance(data, dict):
            raise SchemaError(f"trial must be a JSON object, got {type(data).__name__}")
        trial_id = data.get("id")
        if not isinstance(trial_id, str) or not trial_id:
            raise SchemaError("trial.id must be a non-empty string")
        arrival = data.get("arrival_time")
        if arrival is None:
            arrival = 0.0
        try:
            arrival = float(arrival)
        except (TypeError, ValueError) as exc:
            raise SchemaError(f"trial.arrival_time for {trial_id!r} must be a number") from exc
        if arrival < 0:
            raise SchemaError(f"trial.arrival_time for {trial_id!r} must be non-negative")
        duration = data.get("duration")
        try:
            duration = float(duration)
        except (TypeError, ValueError) as exc:
            raise SchemaError(f"trial.duration for {trial_id!r} must be a number") from exc
        if duration <= 0:
            raise SchemaError(f"trial.duration for {trial_id!r} must be positive")
        parent_raw = data.get("parent")
        if parent_raw is None:
            raise SchemaError(f"trial {trial_id!r} is missing parent resource bundle")
        parent = ResourceBundleSchema.from_dict(parent_raw)
        child_raw = data.get("child")
        child = ResourceBundleSchema.from_dict(child_raw) if child_raw is not None else None
        tags_raw = data.get("tags", [])
        if not isinstance(tags_raw, list):
            raise SchemaError(f"trial.tags for {trial_id!r} must be a list of strings")
        tags = tuple(str(t) for t in tags_raw)
        return cls(
            id=trial_id,
            arrival_time=arrival,
            duration=duration,
            parent=parent,
            child=child,
            tags=tags,
        )


@dataclass(frozen=True)
class CapacityEventSchema:
    """A scheduled change to cluster capacity (for scale-up tests)."""

    time: float
    capacity: ResourceBundleSchema

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapacityEventSchema":
        if not isinstance(data, dict):
            raise SchemaError("capacity event must be a JSON object")
        t = data.get("time")
        try:
            t = float(t)
        except (TypeError, ValueError) as exc:
            raise SchemaError("capacity event.time must be a number") from exc
        if t < 0:
            raise SchemaError("capacity event.time must be non-negative")
        cap_raw = data.get("capacity")
        if cap_raw is None:
            raise SchemaError("capacity event is missing capacity bundle")
        return cls(time=t, capacity=ResourceBundleSchema.from_dict(cap_raw))


@dataclass(frozen=True)
class WorkloadDefinition:
    """A fully validated workload definition ready for simulation."""

    name: str
    description: str
    cluster: ResourceBundleSchema
    trials: tuple[TrialSchema, ...]
    capacity_events: tuple[CapacityEventSchema, ...] = ()
    bounded_horizon_s: float = 30.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkloadDefinition":
        if not isinstance(data, dict):
            raise SchemaError(f"workload must be a JSON object, got {type(data).__name__}")
        name = str(data.get("name", "untitled"))
        description = str(data.get("description", ""))
        cluster_raw = data.get("cluster")
        if cluster_raw is None:
            raise SchemaError("workload is missing cluster capacity")
        cluster = ResourceBundleSchema.from_dict(cluster_raw)
        trials_raw = data.get("trials", [])
        if not isinstance(trials_raw, list):
            raise SchemaError("workload.trials must be a list")
        if not trials_raw:
            raise SchemaError("workload.trials must contain at least one trial")
        trials = tuple(TrialSchema.from_dict(t) for t in trials_raw)
        # uniqueness check
        ids = [t.id for t in trials]
        if len(set(ids)) != len(ids):
            raise SchemaError(f"duplicate trial ids in workload: {sorted(ids)}")
        events_raw = data.get("capacity_events", [])
        if not isinstance(events_raw, list):
            raise SchemaError("workload.capacity_events must be a list")
        events = tuple(CapacityEventSchema.from_dict(e) for e in events_raw)
        horizon = float(data.get("bounded_horizon_s", 30.0))
        if horizon <= 0:
            raise SchemaError("bounded_horizon_s must be positive")
        return cls(
            name=name,
            description=description,
            cluster=cluster,
            trials=trials,
            capacity_events=events,
            bounded_horizon_s=horizon,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "WorkloadDefinition":
        path = Path(path)
        if not path.exists():
            raise SchemaError(f"workload file not found: {path}")
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise SchemaError(f"workload file {path} is not valid JSON: {exc}") from exc
        return cls.from_dict(data)


def validate_workload_file(path: str | Path) -> WorkloadDefinition:
    """Validate a workload JSON file and return the parsed definition.

    Raises SchemaError on any validation failure.
    """
    return WorkloadDefinition.from_file(path)

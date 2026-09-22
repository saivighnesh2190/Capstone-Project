"""NestedTune Guard — FastAPI service.

Thin HTTP layer over the existing simulator. All scheduling logic lives in
nestedtune_guard.simulator / policies — this module only validates input,
reuses existing internals, and returns JSON.

Endpoints
---------
GET  /health            package + python version
GET  /scenarios         list available development fixtures
POST /simulate          run one (fixture, policy) pair in-process
GET  /benchmark         all development fixtures x all policies
GET  /validate          oracle agreement across CP-1 pairs
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from nestedtune_guard import __version__
from nestedtune_guard.schema import validate_workload_file
from nestedtune_guard.simulator import simulate, get_policy
from nestedtune_guard.oracle import expected_for, all_fixtures

app = FastAPI(
    title="NestedTune Guard API",
    version=__version__,
    description="Deadlock-aware hyperparameter-tuning simulator HTTP API (CINT-11).",
)

# Fixture root: try __file__-relative first, then fall back to cwd-relative
# so the API works both from a PYTHONPATH=. checkout and from an installed
# editable package.
_Fixture_root_candidates = [
    Path(__file__).resolve().parents[2] / "fixtures",
    Path.cwd() / "fixtures",
]
FIXTURE_ROOT = next(
    (p for p in _Fixture_root_candidates if (p / "development").is_dir()),
    _Fixture_root_candidates[0],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SimulateRequest(BaseModel):
    fixture: str = Field(
        ...,
        description="Fixture name (e.g. dev_ray47439_xgboost_deadlock) or path to a JSON fixture file.",
    )
    policy: str = Field(
        ...,
        description="Scheduling policy: fifo, greedy, or deadlock_aware.",
        pattern=r"^(fifo|greedy|deadlock_aware)$",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_fixture(name_or_path: str) -> Path:
    """Resolve a fixture name or path to an absolute Path, mirroring the CLI."""
    p = Path(name_or_path)
    if p.exists():
        return p.resolve()
    dev = FIXTURE_ROOT / "development" / f"{name_or_path}.json"
    if dev.exists():
        return dev
    acc = FIXTURE_ROOT / "acceptance" / f"{name_or_path}.json"
    if acc.exists():
        return acc
    raise FileNotFoundError(f"fixture not found: {name_or_path}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, Any]:
    """Package version and Python version."""
    return {
        "package": "nestedtune-guard",
        "version": __version__,
        "project_code": "CINT-11",
        "python_version": sys.version.split()[0],
    }


@app.get("/scenarios")
def scenarios() -> dict[str, list[str]]:
    """List available fixture names (development + acceptance)."""
    dev = sorted(p.stem for p in (FIXTURE_ROOT / "development").glob("*.json"))
    acc = sorted(p.stem for p in (FIXTURE_ROOT / "acceptance").glob("*.json"))
    return {"development": dev, "acceptance": acc}


@app.post("/simulate")
def simulate_endpoint(body: SimulateRequest) -> dict[str, Any]:
    """Run a single (fixture, policy) pair in-process."""
    try:
        path = _resolve_fixture(body.fixture)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        definition = validate_workload_file(path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"schema validation failed: {exc}") from exc

    try:
        policy_name = body.policy.lower().replace("-", "_")
        get_policy(policy_name)  # raises ValueError if unknown
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = simulate(definition, policy_name)
    out = result.to_dict()
    out["fixture_path"] = str(path)
    return out


@app.get("/benchmark")
def benchmark() -> dict[str, Any]:
    """Run all development fixtures under fifo/greedy/deadlock_aware and return a table + totals."""
    fixtures: list[dict[str, Any]] = []
    totals: dict[str, dict[str, Any]] = {}

    for fixture_name in all_fixtures():
        path = _resolve_fixture(fixture_name)
        definition = validate_workload_file(path)
        row_policies: dict[str, dict[str, Any]] = {}
        for policy in ("fifo", "greedy", "deadlock_aware"):
            result = simulate(definition, policy)
            expected = expected_for(fixture_name, policy)  # type: ignore[arg-type]
            row_policies[policy] = {
                "summary": result.summary.to_dict(),
                "oracle_match": (
                    expected is not None
                    and result.summary.completed_trials == expected.completed
                    and result.summary.unresolved_trials == expected.unresolved
                    and result.summary.rejected_trials == expected.rejected
                    and result.summary.observed_cycle_count == expected.cycles
                ),
            }
        fixtures.append({"fixture": fixture_name, "policies": row_policies})

    for policy in ("fifo", "greedy", "deadlock_aware"):
        t: dict[str, Any] = {
            "policy": policy,
            "completed": 0,
            "unresolved": 0,
            "rejected": 0,
            "cycles": 0,
            "total_trials": 12,
        }
        for row in fixtures:
            s = row["policies"][policy]["summary"]
            t["completed"] += s["completed_trials"]
            t["unresolved"] += s["unresolved_trials"]
            t["rejected"] += s["rejected_trials"]
            t["cycles"] += s["observed_cycle_count"]
        totals[policy] = t

    return {"fixtures": fixtures, "totals": totals}


@app.get("/validate")
def validate_endpoint() -> dict[str, Any]:
    """Oracle agreement check across all CP-1 (fixture, policy) pairs."""
    pass_count = 0
    fail_count = 0
    failures: list[str] = []

    for fixture_name in all_fixtures():
        path = _resolve_fixture(fixture_name)
        try:
            definition = validate_workload_file(path)
        except Exception as exc:
            failures.append(f"  {fixture_name}: schema error: {exc}")
            fail_count += 1
            continue
        for policy in ("fifo", "greedy"):
            expected = expected_for(fixture_name, policy)  # type: ignore[arg-type]
            if expected is None:
                continue
            result = simulate(definition, policy)
            ok = (
                result.summary.completed_trials == expected.completed
                and result.summary.unresolved_trials == expected.unresolved
                and result.summary.rejected_trials == expected.rejected
                and result.summary.observed_cycle_count == expected.cycles
            )
            if ok:
                pass_count += 1
            else:
                fail_count += 1
                failures.append(
                    f"  {fixture_name}/{policy}: "
                    f"expected completed={expected.completed} unresolved={expected.unresolved} "
                    f"rejected={expected.rejected} cycles={expected.cycles}, "
                    f"got completed={result.summary.completed_trials} "
                    f"unresolved={result.summary.unresolved_trials} "
                    f"rejected={result.summary.rejected_trials} "
                    f"cycles={result.summary.observed_cycle_count}"
                )

    return {
        "pass": fail_count == 0,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "total_pairs": pass_count + fail_count,
        "failures": failures,
    }

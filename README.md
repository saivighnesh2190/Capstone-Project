# NestedTune Guard

**Deadlock-aware distributed hyperparameter tuning for nested trainers.**

Project code **CINT-11** — KL University capstone.

## Problem

Ray issue [#47439](https://github.com/ray-project/ray/issues/47439) describes a
deadlock that arises when a hyperparameter-tuning trial's outer placement group
reserves all cluster CPUs, then its nested trainer requests a child placement
group that can never be admitted. The concrete resource accounting for the
source case:

| Resource | Count |
|---|---|
| Cluster CPUs | 4 |
| Reserved by parent PG | 4 |
| Actually useful (child running) | 1 |
| Stranded inside parent reservation | 3 |
| New child request | 3 CPU |

The child request can never be satisfied because the parent itself holds the
resources the child needs — a self-cycle `xgb-001 → xgb-001` that hangs the
Ray scheduler indefinitely in `WAITING_CHILD` state.

NestedTune Guard provides a **deterministic, bounded, reproducible** simulator
that models this class of deadlock and evaluates scheduling policies against it
within a 30-second horizon, converting an indefinite hang into measurable
experiment results.

## CP-2 primary results (CP-1 controls frozen)

7 development fixtures, 12 trials total. FIFO and Greedy are retained as the
frozen CP-1 comparison controls; the deadlock-aware policy is the CP-2
contribution.

| Policy | Completed | Unresolved | Cycles |
|---|---|---:|---:|
| FIFO | 5/12 | 7 | 4 |
| Greedy | 7/12 | 5 | 4 |
| Deadlock-aware (CP-2) | 7/12 | 0 | 0 (5 rejected at admission) |

CP-2 rejects 5 permanently-infeasible trials at admission and resolves all
deadlocks — zero unresolved.

## Quickstart

### 1. Run the CP-2 validation (with frozen CP-1 controls)

```bash
./scripts/run_cp1.sh
python3 -m nestedtune_guard.cli validate
```

The existing gate script protects the frozen CP-1 comparison contract. The
validation command additionally checks the CP-2 evidence pairs and prints
`VALIDATION PASSED` when the oracle agreement is intact.

### 2. FastAPI service

```bash
# Install the package with API dependencies (one-time)
pip install -e '.[dev]'

# Launch the API server (port 8123)
uvicorn nestedtune_guard.api:app --port 8123
```

Example curl against the running server:

```bash
# Health
curl http://localhost:8123/health

# List scenarios
curl http://localhost:8123/scenarios

# Simulate one fixture
curl -X POST http://localhost:8123/simulate \
  -H "Content-Type: application/json" \
  -d '{"fixture": "dev_ray47439_xgboost_deadlock", "policy": "fifo"}'

# Full benchmark (all fixtures x all policies)
curl http://localhost:8123/benchmark

# Oracle validation
curl http://localhost:8123/validate
```

### 3. Autoscaling advice CLI

```bash
# Advice for the capacity scale-up fixture (FIFO leaves one trial
# unresolved at the horizon, so advice is emitted)
python3 -m nestedtune_guard.cli advise fixtures/development/dev_changing_capacity_scaleup.json --policy fifo

# Advice for the source case (flags the WAITING_CHILD nested deadlock)
python3 -m nestedtune_guard.cli advise fixtures/development/dev_ray47439_xgboost_deadlock.json --policy fifo

# Advice for deadlock-aware (both trials complete, no advice)
python3 -m nestedtune_guard.cli advise fixtures/development/dev_changing_capacity_scaleup.json --policy deadlock_aware
```

The advisor classifies every unresolved trial by *why* it is unresolved —
`horizon_limited` (needs more time, not capacity), `capacity_shortfall`
(demand exceeds maximum cluster capacity — the only case where scaling
helps), `ordering_blocked` (fits but never admitted, e.g. FIFO
head-of-line), or `nested_deadlock` (WAITING_CHILD — the Ray #47439
source case, remedied by the CP-2 controller, not autoscaling).

### 4. Dashboard

The dashboard is a Next.js 16 app in `src/`. Run it with bun:

```bash
bun run dev
```

This starts the Next.js dev server on port 3000. In Docker, the dashboard
calls the Python simulator live. The public Vercel deployment below serves the
same deterministic CP-2 outputs from a checked-in evidence bundle because
Vercel's Node runtime does not include the repository's Python interpreter.

**Public CP-2 dashboard:** https://nestedtune-guard-cp2.vercel.app

The Vercel API labels this mode as `vercel-static-cp2-evidence`; it is a
permanent hosted dashboard, not a claim that Vercel is running a Python worker.

### 5. Docker deployment

```bash
docker compose -f deploy/docker/docker-compose.yml up --build -d
curl http://localhost:3000/api/health
```

The Docker path is the full live Python + Next.js integration; the Vercel path
is the public evidence dashboard.

## Repo map

| Path | Purpose |
|---|---|
| `nestedtune_guard/` | Python package: simulator, model, policies, observer, telemetry, oracle, schema, CLI, API, advisor |
| `nestedtune_guard/policies/` | FIFO, greedy, deadlock-aware scheduling policies |
| `nestedtune_guard/observer/` | Wait-for graph construction + cycle detection (observer-only) |
| `nestedtune_guard/oracle/` | Hand-coded expected outcomes for CP-1 validation |
| `nestedtune_guard/tests/` | Pytest suite (70 tests) |
| `fixtures/development/` | 7 development fixtures (12 trials) |
| `fixtures/acceptance/` | 2 hash-frozen CP-2 acceptance fixtures |
| `scripts/run_cp1.sh` | Single-command CP-1 gate |
| `scripts/generate_evidence.py` | Generate evidence CSV/JSON for the dashboard |
| `src/` | Next.js 16 dashboard (bun) |
| `evidence/` | Generated simulation output for the dashboard |
| `deploy/` | Docker, Kubernetes, Helm |
| `docs/CP1_ENGINEERING_CONTRACT.md` | Frozen CP-1 acceptance criteria |
| `docs/RAY_REPRODUCTION_PROTOCOL.md` | Real-Ray reproduction protocol (see status below) |

## Status

- **Deterministic simulator.** The simulator is a bounded, deterministic model —
  not a production-cluster benchmark. It reproduces the structural deadlock from
  Ray #47439 within a 30-second horizon. The bug was **also reproduced on real
  Ray 2.10.0 in Docker** — see `docs/RAY_REPRODUCTION_PROTOCOL.md` and
  `ray-repro/evidence/` (child PG stuck PENDING for the full bounded wait,
  4/4/1/3 resource accounting matching the simulator exactly).

- **Mutual-cycle analysis.** A textbook two-trial mutual wait-for cycle cannot
  form in this model (atomic parent+child placement); the real adjacent hazard —
  collateral blocking of a feasible trial by a self-infeasible one — is
  demonstrated and already prevented by the CP-2 controller. See
  `docs/CP2_MUTUAL_CYCLE.md` and `fixtures/demonstrations/`.

- **Frozen CP-1 baseline.** The CP-1 headline totals (FIFO 5/12, Greedy 7/12)
  and per-fixture oracle values are frozen in
  `docs/CP1_ENGINEERING_CONTRACT.md`. They must never change without a contract
  amendment. The determinism gate byte-compares `to_dict()` output across
  repeated runs.

- **CP-2 contribution.** The deadlock-aware admission policy is the primary
  contribution: it performs combined parent+child feasibility checks, rejects
  permanently infeasible work before admission, and supports bounded
  release/requeue recovery for the deterministic node-loss scenario. Priority
  pre-emption and recovery are evaluated against the frozen CP-1 baseline.
  The public dashboard presents this CP-2 evidence first.

- **Dashboard.** The Next.js dashboard visualizes simulation output but does not
  modify scheduling decisions.

- **FastAPI API.** The API layer (`nestedtune_guard.api`) exposes the simulator
  over HTTP — health, scenarios, simulate, benchmark, and validate endpoints.
  It reuses existing internals without duplicating scheduling logic.

- **Autoscaling advisor.** The advisor (`nestedtune_guard.advisor`) is
  advisory-only: it reads a simulation result, classifies each unresolved
  trial by cause (horizon-limited, capacity shortfall, ordering-blocked,
  nested deadlock), and recommends cluster scaling only when a trial's
  demand genuinely exceeds maximum capacity. It does not change any
  scheduling decision or trial outcome.

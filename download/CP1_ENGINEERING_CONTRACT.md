# CP-1 Engineering Contract

**Project:** NestedTune Guard — Deadlock-Aware Distributed Hyperparameter Tuning for Nested Trainers
**Project code:** CINT-11
**Checkpoint:** CP-1
**Version:** 1.0.0 (frozen)
**Date:** 2026-08-28

---

## 1. Purpose

This document freezes the CP-1 acceptance criteria before any review.
It is the single source of truth for what "CP-1 done" means; no other
document, slide, or conversation overrides it. If the simulator output
matches the oracle and the headline totals below, CP-1 is complete.

The contract is frozen so that:

- The CP-2 controller can be developed against an unchanging baseline.
- Reviewers can re-run the gate at any time and observe identical numbers.
- Future refactors do not silently drift the baseline.

---

## 2. Source case

- **Ray issue:** [#47439](https://github.com/ray-project/ray/issues/47439)
  (NOT `474399` — the originally-provided issue number was invalid; the
  correct issue was identified by searching the Ray repository with the
  problem description.)
- **Cluster:** 4 CPU
- **Outer placement-group reservation:** 4 CPU
- **Actually useful:** 1 CPU
- **Stranded inside parent reservation:** 3 CPU
- **New child request:** 3 CPU
- **Final state:** `WAITING_CHILD`
- **Wait-for cycle:** `xgb-001 → xgb-001` (self-cycle)

---

## 3. Fixtures (9 total)

### Development (7 fixtures, 12 trials — counted in CP-1 totals)

| # | Fixture | Trials | Cycles | Description |
|---|---|---:|---:|---|
| 1 | `dev_ray47439_xgboost_deadlock` | 1 | 1 | Source case — XGBoost self-cycle |
| 2 | `dev_safe_nested_xgboost` | 1 | 0 | Safe control on larger cluster |
| 3 | `dev_pytorch_nested_contention` | 2 | 1 | Nested deadlock + concurrent small job |
| 4 | `dev_fifo_hol_blocking` | 2 | 0 | HOL blocking (no cycle) |
| 5 | `dev_gpu_strict_pack_fragmentation` | 2 | 2 | Two GPU self-cycles |
| 6 | `dev_safe_gang_scheduled` | 2 | 0 | Safe gang jobs |
| 7 | `dev_changing_capacity_scaleup` | 2 | 0 | Cluster scale-up |
| **Total** | | **12** | **4** | |

### Acceptance (2 fixtures, hash-frozen — NOT counted in CP-1 totals)

| # | Fixture | Description |
|---|---|---|
| A1 | `acc_cp2_node_loss_recovery` | CP-2 node-loss recovery (FAILED under FIFO, COMPLETED · 1 RETRY under CP-2) |
| A2 | `acc_cp2_priority_preempt` | CP-2 priority pre-emption |

Acceptance fixtures are not counted in CP-1 totals. They exercise CP-2
features and are pinned to fixed SHA-256 hashes.

---

## 4. CP-1 baseline targets (FROZEN)

These are the EXACT numbers the simulator must produce after `./scripts/run_cp1.sh`.
Any drift indicates a regression.

### Per-fixture, per-policy

| Fixture | Policy | Completed | Unresolved | Rejected | Cycles |
|---|---|---:|---:|---:|---:|
| dev_ray47439_xgboost_deadlock | fifo | 0 | 1 | 0 | 1 |
| dev_ray47439_xgboost_deadlock | greedy | 0 | 1 | 0 | 1 |
| dev_safe_nested_xgboost | fifo | 1 | 0 | 0 | 0 |
| dev_safe_nested_xgboost | greedy | 1 | 0 | 0 | 0 |
| dev_pytorch_nested_contention | fifo | 1 | 1 | 0 | 1 |
| dev_pytorch_nested_contention | greedy | 1 | 1 | 0 | 1 |
| dev_fifo_hol_blocking | fifo | 0 | 2 | 0 | 0 |
| dev_fifo_hol_blocking | greedy | 1 | 1 | 0 | 0 |
| dev_gpu_strict_pack_fragmentation | fifo | 0 | 2 | 0 | 2 |
| dev_gpu_strict_pack_fragmentation | greedy | 0 | 2 | 0 | 2 |
| dev_safe_gang_scheduled | fifo | 2 | 0 | 0 | 0 |
| dev_safe_gang_scheduled | greedy | 2 | 0 | 0 | 0 |
| dev_changing_capacity_scaleup | fifo | 1 | 1 | 0 | 0 |
| dev_changing_capacity_scaleup | greedy | 2 | 0 | 0 | 0 |

### Headline totals (across 12 trials, 7 development fixtures)

| Metric | FIFO | Greedy |
|---|---:|---:|
| Completed trials | **5/12** | **7/12** |
| Unresolved trials | **7** | **5** |
| Observed cycles | **4** | **4** |
| Bounded resolution % | **41.7%** | **58.3%** |
| Trials/hour | 85.7 | 120 |
| Queue p95 | 10.0 s | 9.6 s |
| Jain fairness | 0.714 | 0.810 |

### CP-2 comparison (also locked for comparison)

| Metric | Deadlock-aware |
|---|---:|
| Completed trials | 7/12 |
| Unresolved trials | 0 |
| Rejected trials | 5 |
| Observed cycles | 0 |

CP-2 rejects 5 permanently-infeasible trials at admission (1 each from
Fix1, Fix3, Fix4, and 2 from Fix5). Zero unresolved deadlocks.

---

## 5. Oracle

The oracle is a hand-coded table of expected results located at
`nestedtune_guard/oracle/__init__.py`. The oracle was derived from
the source-case analysis BEFORE the simulator was implemented, so any
mismatch indicates a bug in one of them.

The benchmark covers all 21 development (fixture, policy) rows. The gate's
independent CP-1 oracle validation checks the 14 FIFO/greedy pairs and requires
100% agreement; the deadlock-aware rows are also compared in the benchmark
output.

---

## 6. Bounded horizon

Every experiment MUST terminate within **30 seconds**. This is enforced
by the simulator's main loop:

```python
while t <= horizon + 1e-9:
    ...
    t = round(t + TICK_S, 4)
```

Trials not in COMPLETED or REJECTED state at horizon are counted as
"unresolved". The bounded horizon converts an indefinite Ray scheduler
hang into a measurable experiment.

---

## 7. Determinism

The simulator is byte-identical across repeated runs of the same
(fixture, policy) pair. This is enforced by:

- `TICK_S = 0.1` (integer-valued time delta)
- Deterministic trial ordering (arrival_time, then id)
- No use of wall-clock, `random`, or `time.now()` inside the simulator
- No mutable global state across runs

The determinism test (`test_determinism.py::TestDeterminism::test_all_fixtures_deterministic_across_policies`)
verifies byte-identical JSON output across two consecutive runs of every
(fixture, policy) pair.

---

## 8. Observer-only constraint

The wait-for observer (`nestedtune_guard/observer/__init__.py`) is
observer-only. It builds the wait-for graph and detects cycles, but it
NEVER modifies scheduling decisions.

This is the design constraint that keeps the CP-1 baseline fair: the
observer cannot accidentally improve FIFO or greedy results, which
would make the CP-1 baseline a moving target.

The test `test_cycle.py::TestWaitForGraph::test_observer_never_modifies_scheduling_decisions`
verifies that calling `observe()` does not change trial states.

---

## 9. Gate procedure

```bash
./scripts/run_cp1.sh
```

This single command performs:

1. Fixture validation (all 7 development + 2 acceptance fixtures)
2. 70 automated pytest tests are executed by the current gate: the original
   34 CP-1 baseline tests remain unchanged, with 2 CP-2 acceptance tests and
   34 additive integration/hardening tests. The frozen CP-1 acceptance subset
   is still the original 34 tests.
3. Partition-hash verification (canonical SHA-256 of every fixture)
4. FIFO and greedy benchmarks across all 7 development fixtures
5. Independent expected-result oracle verification (14 (fixture, policy) pairs for CP-1)
6. Repeatability check (determinism)

The final output must contain:

```text
CP1 GATE PASS
```

If any step fails, the script exits with code 1 and the gate is
considered failed.

---

## 10. Fixture hashes (SHA-256)

Run `sha256sum fixtures/development/*.json fixtures/acceptance/*.json`
to verify fixture integrity. The acceptance fixtures are hash-frozen
and must NEVER change without an explicit contract amendment.

---

## 11. Out-of-scope (reserved for CP-2)

The following are NOT part of CP-1:

- Deadlock-aware policy results (the CP-2 comparison row above is for
  comparison only and is not part of the CP-1 baseline).
- Placement-group reuse
- Explained rejection of impossible requests (CP-2 admission does this)
- Priority pre-emption
- Node-failure retry
- Autoscaling advice
- FastAPI service/dashboard operation (CP-2 integration, not CP-1 baseline)
- KubeRay deployment validation

These are listed here so reviewers can verify they are not accidentally
claimed as CP-1 work.

---

## 12. Amendment procedure

This contract is FROZEN. Any change requires:

1. A new version number (1.0.0 → 1.1.0).
2. A documented justification in the project worklog.
3. Re-running `./scripts/run_cp1.sh` and recording the new headline totals.
4. Sign-off from the project guide.

Version 1.0.0 — 2026-08-28 — Initial freeze.

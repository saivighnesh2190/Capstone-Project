# Project Review Checklist (CINT-11 — NestedTune Guard)

**Reviewer:** ______________________  **Date:** ______________________

Use this checklist during the viva. Each item maps to a section of the
CP-1 report and to a live artifact the reviewer can verify.

---

## A. Source case (Ray #47439)

- [ ] A1. The corrected GitHub issue is https://github.com/ray-project/ray/issues/47439 (NOT 474399).
- [ ] A2. The 4/4/1/3 resource accounting is explained:
  - Cluster capacity: 4 CPU
  - Outer reservation: 4 CPU
  - Actually useful: 1 CPU
  - Stranded inside parent reservation: 3 CPU
  - New child request: 3 CPU
  - Final state: `WAITING_CHILD`
- [ ] A3. The hold-and-wait cycle is shown:
  - Parent holds 4 reserved CPUs → Parent waits for nested trainer → Nested trainer requests 3 CPUs → Unavailable (parent holds them)
- [ ] A4. The key sentence is articulated:
  - "Aggregate capacity appears sufficient, but the nested trainer duplicates the reservation, producing a parent–child hold-and-wait self-cycle."

## B. Stakeholders and requirements

- [ ] B1. Stakeholders identified:
  - ML platform developer
  - Cluster operator
  - Ray maintainer
  - Evaluator
  - CP-2 team
- [ ] B2. CP-1 requirements:
  - Hierarchical parent-child workload schema
  - Atomic placement of resource bundles
  - FIFO and greedy baseline scheduling
  - Observer-only wait-for graph
  - Bounded execution instead of an infinite hang
  - CPU/GPU utilization, fragmentation, stranding metrics
  - Deterministic evidence and automated validation

## C. Architecture

- [ ] C1. The CP-1 data flow is presented:
  - Workload JSON → Schema validation → Atomic placement → FIFO or Greedy → Bounded simulator → Wait-for observer → Metrics and evidence
- [ ] C2. The observer-only constraint is emphasized:
  - "The wait-for observer detects and reports cycles, but it does not change scheduling decisions. Therefore, it does not artificially improve the CP-1 baselines."

## D. Experimental scenarios

- [ ] D1. The 7 development fixtures (12 trials) are listed:
  1. Ray #47439 XGBoost deadlock
  2. Safe nested XGBoost control
  3. PyTorch nested contention
  4. FIFO head-of-line blocking
  5. GPU STRICT_PACK fragmentation
  6. Safe gang-scheduled jobs
  7. Changing-capacity scale-up
- [ ] D2. The safe XGBoost control is explained:
  - "It proves that the observer does not label every nested request or normal waiting condition as a deadlock."
- [ ] D3. The 2 acceptance fixtures are mentioned as hash-frozen and NOT included in CP-1 totals.

## E. Live demonstration

- [ ] E1. The single-command gate is run:
  ```bash
  ./scripts/run_cp1.sh
  ```
- [ ] E2. The final output contains `CP1 GATE PASS`.
- [ ] E3. The source case is demonstrated:
  ```bash
  PYTHONPATH=src python3 -m nestedtune_guard.cli simulate \
    fixtures/development/dev_ray47439_xgboost_deadlock.json \
    --policy fifo
  ```
- [ ] E4. The displayed fields match:
  - state: `WAITING_CHILD`
  - reserved.cpu: 4
  - useful.cpu: 1
  - cpu_stranding_pct: ~100% (reserved=4, useful=1, stranded=3)
  - observed_cycle_count: 1
  - wait-for edge: `xgb-001 → xgb-001`
  - unresolved_trials: 1
- [ ] E5. The safe control is demonstrated:
  ```bash
  PYTHONPATH=src python3 -m nestedtune_guard.cli simulate \
    fixtures/development/dev_safe_nested_xgboost.json \
    --policy fifo
  ```
- [ ] E6. The safe control result matches:
  - trial state: `COMPLETED`
  - observed cycles: 0
  - unresolved trials: 0

## F. CP-1 results

- [ ] F1. The headline totals are presented:

| Metric | FIFO | Greedy |
|---|---:|---:|
| Completed trials | 5/12 | 7/12 |
| Unresolved trials | 7 | 5 |
| Observed cycles | 4 | 4 |
| Bounded resolution % | 41.7% | 58.3% |
| Trials/hour | 85.7 | 120 |
| Queue p95 | 10.0 s | 9.6 s |
| Jain fairness | 0.714 | 0.810 |

- [ ] F2. The interpretation is articulated:
  - "Greedy improves throughput by allowing feasible jobs to bypass an impossible head-of-line request. However, both FIFO and greedy remain hierarchy-blind and observe the same four nested-resource cycles."

## G. Testing and validation

- [ ] G1. 34 automated tests pass (Python pytest).
- [ ] G2. 100% agreement with the independent expected-result oracle.
- [ ] G3. 7 development fixtures evaluated under both baseline policies.
- [ ] G4. Stable semantic digest across repeated executions (determinism).
- [ ] G5. Canonical SHA-256 hashes prevent fixture modification.
- [ ] G6. Every experiment has a 30-second bounded horizon.
- [ ] G7. Raw JSON and CSV evidence is generated.

## H. Limitations (stated honestly)

- [ ] H1. The reviewer can articulate:
  - "The deterministic simulator and evidence framework were executed and verified. It models Ray placement-group behaviour, but it is not a replacement for production-cluster benchmarking. A Ray 2.10 Docker reproduction protocol is provided separately, and live-Ray claims require an attached runtime trace."

## I. Out-of-scope (CP-2 reserved)

- [ ] I1. The reviewer confirms the following are NOT claimed as CP-1 results:
  - Deadlock-aware policy result of 7/12 completed (CP-2 preview only)
  - Placement-group reuse
  - Explained rejection of impossible requests
  - Priority pre-emption
  - Node-failure retry
  - Autoscaling advice
  - FastAPI/dashboard operation (visualization only)
  - KubeRay deployment

## J. Files carried

- [ ] J1. CP-1 Report PDF (`download/CINT-11_CP1_Report.pdf`)
- [ ] J2. CP-1 Editable Report (`download/CINT-11_CP1_Report.docx`)
- [ ] J3. CP-1 Engineering Contract (`docs/CP1_ENGINEERING_CONTRACT.md`)
- [ ] J4. Review Checklist (`docs/PROJECT_REVIEW_CHECKLIST.md`)
- [ ] J5. Source code repository
- [ ] J6. Generated CSV/JSON evidence (`evidence/`)
- [ ] J7. Terminal screenshot showing `CP1 GATE PASS`
- [ ] J8. Local copy of the chart and report in case internet access fails

## K. Personalization (before submission)

- [ ] K1. All member names filled in (replacing "Member 1–3")
- [ ] K2. Registration numbers filled in
- [ ] K3. Guide name filled in
- [ ] K4. Evaluator name filled in
- [ ] K5. Individual module ownership declared
- [ ] K6. Signatures and dates filled in for each weekly entry

## L. Strong closing statement

The reviewer can confirm the closing claim is supported:

> "CP-1 successfully converts an indefinite Ray scheduler hang into a
> bounded, repeatable and measurable experiment. We reproduced the exact
> 4/4/1/3 source condition, detected the self-cycle independently,
> validated safe and negative controls, froze FIFO and greedy baselines,
> and achieved 100% oracle agreement across 34 automated tests. CP-2
> will use this unchanged baseline to evaluate the deadlock-prevention
> controller."

---

## Reviewer's overall assessment

- CP-1 scope met: ☐ Yes ☐ Partially ☐ No
- CP-1 baseline frozen: ☐ Yes ☐ No
- CP-2 unblocked: ☐ Yes ☐ No
- Comments: _________________________________________________________________

________________________________________________________

________________________________________________________

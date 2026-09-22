# CP-2 Mutual-Cycle Analysis — Honest Negative Result

**Project:** NestedTune Guard (CINT-11)
**Question investigated:** the CP-2 deadlock-aware controller prevents
SELF-cycles (one trial's parent+child demand vs. cluster capacity). Does it
also need MUTUAL-cycle avoidance — two concurrently-admitted parents each
holding resources the other's nested child needs (A waits-for B, B waits-for A)?

**Answer: no — a mutual cycle cannot form in this model.** This document
records the empirical investigation, the negative result, and the real hazard
that the investigation surfaced instead (collateral blocking, which the CP-2
controller already prevents).

---

## 1. The investigation

Design target: an 8-CPU cluster with two trials, each requesting a 4-CPU parent
PG and a 4-CPU child PG. Both trials are feasible in isolation (4+4 = 8 ≤ 8).
The textbook expectation: both parents admit (4+4 = 8 fits), then each child
waits for CPUs the other parent holds → mutual wait-for cycle A→B→A.

Empirical result (`fixtures/demonstrations/dev_mutual_cycle.json`, verified by
`nestedtune_guard/tests/test_mutual_cycle.py`):

| Policy | trial-a | trial-b | Cycles |
|---|---|---|---|
| FIFO | COMPLETED | COMPLETED | 0 |
| Greedy | COMPLETED | COMPLETED | 0 |
| Deadlock-aware | COMPLETED | COMPLETED | 0 |

**No deadlock forms under any policy.** Both trials complete.

## 2. Why the mutual cycle cannot form

Two properties of the simulator make a cross-trial mutual cycle structurally
impossible:

1. **Atomic parent+child placement.** When a policy admits a trial, the
   simulator places the parent PG and *immediately attempts the child PG in
   the same tick* (`nestedtune_guard/simulator.py`, admission block). A trial
   never holds a parent PG in isolation while "planning" a child: either the
   child fits at admission time (trial goes RUNNING) or it does not (trial
   goes WAITING_CHILD immediately).

2. **Self-cycle semantics of WAITING_CHILD.** A WAITING_CHILD trial is stuck
   because *its own parent's reservation* makes its child infeasible. The
   observer therefore emits a self-edge `t → t` for every WAITING_CHILD trial
   — never a cross-trial edge. The observer's mutual-cycle DFS
   (`detect_cycles`) is implemented and correct, but it is unreachable in this
   model: there is no edge `a → b` with `a ≠ b` to traverse.

Consequently: any trial that ends up WAITING_CHILD was **already
self-infeasible at its admission moment** (parent+child > free capacity at
that tick) — the deadlock is always attributable to a single trial's own
demand, never to a circular dependency between two trials.

## 3. The real hazard: collateral blocking

Investigating the mutual-cycle design space surfaced the hazard that actually
exists — **collateral blocking** (`fixtures/demonstrations/dev_collateral_blocking.json`):

- 8-CPU cluster. `deadlocked-a`: parent 4 + child 5 = 9 > 8 max capacity —
  **self-infeasible**. `feasible-b`: parent 4 + child 4 = 8 ≤ 8 — feasible in
  isolation.
- Under FIFO **and greedy**, `deadlocked-a`'s parent is admitted (4 CPU fits),
  its child can never be placed, and it sits in WAITING_CHILD holding 4 CPUs
  forever. `feasible-b`'s parent also admits into the remaining 4 CPUs, but
  its child (needing 4 more) cannot be placed — so **both trials end
  unresolved at the horizon**. Greedy cannot rescue this: greedy skips trials
  whose *parent* doesn't fit, but `feasible-b`'s parent DOES fit — the child
  is what cannot, and greedy is hierarchy-blind.
- Under **deadlock_aware**, `deadlocked-a` is rejected at admission (combined
  demand 9 > 8), so its parent never holds resources; `feasible-b` completes.

Empirical summary (asserted in `test_mutual_cycle.py`):

| Policy | deadlocked-a | feasible-b | Unresolved | Cycles |
|---|---|---|---:|---:|
| FIFO | WAITING_CHILD | WAITING_CHILD | 2 | 2 (self) |
| Greedy | WAITING_CHILD | WAITING_CHILD | 2 | 2 (self) |
| Deadlock-aware | REJECTED (explained) | COMPLETED | 0 | 0 |

This is a stronger CP-2 story than the mutual-cycle gap would have been: the
per-trial pre-admission feasibility check protects not just the infeasible
trial itself but also **the feasible trials it would otherwise collaterally
block**.

## 4. Design decision

**No new avoidance logic was added to `DeadlockAwarePolicy`.** Rationale:

- The specified gap (mutual cycles) does not exist in this model — adding
  "mutual-cycle avoidance" would be dead code guarding an unreachable state.
- The adjacent real hazard (collateral blocking) is already prevented by the
  existing per-trial pre-admission feasibility check. Verified by test.
- The frozen CP-1 baseline and the CP-2 oracle entries remain untouched
  (demonstration fixtures live in `fixtures/demonstrations/`, which the gate,
  benchmark, and oracle do not enumerate — asserted by test).

## 5. Mapping to the observer

The observer's `detect_cycles` implements general DFS cycle detection,
including mutual cycles (`kind="mutual"`), and is honest about whatever
topology the simulator produces. In this model it only ever reports
`self_cycle` entries — one per WAITING_CHILD trial. The mutual-cycle code
path remains as forward-compatible instrumentation: if the simulator's
placement model ever changes (e.g. deferred/non-atomic child placement), the
observer will detect the new topology without modification.

## 6. Limitations

- The negative result is specific to this simulator's **atomic placement
  model**. Real Ray placement-group scheduling is not atomic in this sense: a
  Tune trial's parent PG is created first and the nested trainer's child PG
  request arrives later, from inside the running trial. A true cross-trial
  mutual cycle is therefore not impossible in real Ray — it is impossible in
  *this model of it*. The real-Ray reproduction
  (`docs/RAY_REPRODUCTION_PROTOCOL.md`) demonstrates the self-cycle form of
  the bug, which is the form Ray issue #47439 reports.
- The collateral-blocking analysis covers two concurrent trials. Larger
  arrival sets can produce longer chains of collateral blocking; the CP-2
  controller prevents each link of the chain by the same mechanism.

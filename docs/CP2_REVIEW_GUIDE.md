# NestedTune Guard — CP-2 Review Guide

**Project ID:** CINT-11  
**Repository:** https://github.com/saivighnesh2190/Capstone-Project  
**Purpose:** A truthful, viva-ready explanation of CP-1, CP-2, the algorithms, the research background, publication options, and GitHub Actions.

> **Important honesty rule:** This project is a deterministic simulator/evidence framework plus a real-Ray reproduction protocol. It is not a claim that a new production scheduler has been deployed at cluster scale. The project implements a deadlock-aware admission controller and evaluates it against baselines.

---

## 1. The 30-second answer

> **NestedTune Guard studies a nested scheduling problem in distributed hyperparameter tuning. An outer Ray Tune trial reserves a parent placement group, while the training process inside that trial requests a child placement group. If the parent holds the resources that the child needs, the trial can remain stuck in `WAITING_CHILD`; this is a hold-and-wait deadlock pattern. CP-1 builds a deterministic simulator and compares two hierarchy-blind baselines: FIFO and Greedy/backfilling. CP-2 adds a deadlock-aware admission controller that checks the combined parent-plus-child demand before admitting a trial, defers unsafe temporary fits, rejects permanently infeasible trials, and supports priority/node-loss recovery paths. In the verified benchmark, FIFO completed 5/12 trials, Greedy completed 7/12, while the CP-2 policy completed 7/12 and rejected 5 trials instead of leaving them unresolved.**

If you remember only one sentence:

> **CP-1 measures the problem; CP-2 prevents unsafe admission and turns an indefinite hang into an explicit bounded decision.**

---

## 2. Basic vocabulary

- **Cluster:** The available CPU, GPU, memory, and worker capacity.
- **Trial:** One hyperparameter configuration being trained.
- **Placement group (PG):** A reservation of resources for a trial or its nested work.
- **Parent PG:** The outer trial's reservation.
- **Child PG:** The nested training job's reservation.
- **Nested scheduling:** The parent is already holding resources when it requests more resources for its child.
- **Pending:** The trial has arrived but has not been admitted.
- **Running:** Parent and child resources are available and the training work has started.
- **`WAITING_CHILD`:** The parent is holding resources, but the child cannot be placed.
- **Head-of-line blocking:** The first queue item blocks later items even if a later item could fit.
- **Wait-for graph:** A graph in which a blocked trial points to the resource/trial it is waiting for. A cycle is evidence of circular waiting.

### Simple example

Suppose the cluster has 4 CPUs:

- Parent request: 1 CPU
- Child request: 3 CPUs
- Another running job uses 3 CPUs

The parent can reserve 1 CPU, but after that only 0 CPUs are free. Its child needs 3 CPUs and waits. The parent cannot finish without the child, and the child cannot start because the parent is holding resources. The important question is not only **“Does the parent fit?”** but **“Does the parent and its child fit together?”**

---

## 3. CP-1 — baseline and problem measurement

### CP-1 objective

CP-1 establishes a frozen, repeatable reference implementation. It answers:

1. How should parent and child resource reservations be represented?
2. What happens under ordinary FIFO scheduling?
3. What improves when a scheduler skips a blocked queue head?
4. Can the same result be reproduced deterministically and checked against an oracle?

### CP-1 execution model

The simulator:

1. Reads workload JSON fixtures.
2. Validates cluster capacity, trial arrival times, durations, resource bundles, and placement strategy.
3. Advances time in deterministic 0.1-second ticks.
4. Lets a policy decide which pending trial to admit.
5. Admits the parent PG first.
6. Attempts the child PG after the parent has reserved resources.
7. Records `RUNNING`, `WAITING_CHILD`, completed, failed, rejected, and unresolved states.
8. Builds wait-for observations and checks cycles.
9. Stops at a bounded 30-second horizon instead of hanging forever.

The simulator is not pretending that every detail of a production Ray cluster is modeled. Its purpose is controlled comparison: same workload, same capacity, different policy.

### CP-1 algorithm 1: FIFO

**Rule:** Inspect only the first pending trial in arrival order.

- If its **parent** fits in currently free capacity, admit it.
- If its parent does not fit, hold the queue.
- Do not skip the head.
- Do not check whether the nested child will fit after the parent is admitted.

**Strength:** Very simple and easy to understand as a baseline.  
**Weakness:** Head-of-line blocking and hierarchy blindness. It can admit a parent that strands its own child.

### CP-1 algorithm 2: Greedy/backfilling

**Rule:** Walk the queue in arrival order and admit the first trial whose **parent** fits.

- If the head does not fit, skip it temporarily.
- Try a later trial that fits the current free capacity.
- Do not preempt already running trials.
- Still do not check the nested child before parent admission.

**Strength:** Better short-term throughput than FIFO because later feasible trials can bypass a blocked head.  
**Weakness:** It is still hierarchy-blind. It may make progress on other trials while admitting a parent that later waits forever for its child.

### CP-1 verified headline results

Across the frozen 12-trial baseline scenario:

| Policy | Completed | Unresolved | Cycles | Meaning |
|---|---:|---:|---:|---|
| FIFO | 5/12 | 7 | 4 | Strict order, strong head-of-line blocking |
| Greedy | 7/12 | 5 | 4 | More throughput, but the same hierarchy blind spot |
| CP-2 deadlock-aware | 7/12 | 0 unresolved | 0 in the CP-2 result rows | Unsafe cases are explicitly rejected rather than left waiting |

CP-1 also validates the frozen FIFO/Greedy oracle pairs. The current verified suite reports **70 automated tests**, with **14/14 selected CP-1 FIFO/Greedy oracle pairs** matching.

### What CP-1 contributes

CP-1 is not “the old code that failed.” It is the controlled baseline. Without it, CP-2 could claim improvement without proving what changed. CP-1 gives the project:

- a workload schema;
- a deterministic simulator;
- baseline policies;
- cycle/stranding telemetry;
- frozen fixtures and oracle values;
- reproducible evidence.

---

## 4. CP-2 — the safety-aware extension

### CP-2 objective

CP-2 asks:

> Can the scheduler avoid admitting a parent that cannot safely launch its nested child, while preserving measurable progress and explaining each decision?

### CP-2 algorithm: Deadlock-aware admission

The CP-2 controller extends the baseline idea with hierarchy-aware checks.

#### Step 1 — Check parent capacity

If the parent itself cannot fit in the current free capacity, defer it and try another pending trial when appropriate.

#### Step 2 — Check permanent feasibility

Compare demand against the maximum available cluster capacity.

- If the parent alone exceeds the maximum capacity, reject it.
- If the combined parent-plus-child demand exceeds maximum capacity, reject it.
- Reason: no amount of waiting can make an impossible request fit on that cluster.

This is a **safe rejection**, not a failure. The system is saying: “This trial cannot complete under the declared capacity; do not create a hanging reservation.”

#### Step 3 — Check child fit after parent reservation

Project the remaining capacity after the parent is admitted. If the child does not fit in that post-parent capacity, defer the trial instead of creating a known parent-holds-child-waits state.

This is the key CP-2 difference:

> **FIFO and Greedy ask only whether the parent fits; CP-2 asks whether the parent and child can progress together.**

#### Step 4 — Priority handoff

For the acceptance scenario with priority tags, a high-priority pending trial can trigger preemption/release of a low-priority running trial. The low-priority trial is returned to pending so resources can be used for the high-priority work.

#### Step 5 — Bounded recovery for node loss

The simulator includes a deterministic node-loss acceptance event. Under CP-2, the affected trial releases resources, is requeued, and retries once. The baseline behavior records failure instead. This demonstrates recovery as a bounded state transition rather than an infinite wait.

#### Step 6 — Explain every decision

Each decision records a reason and trace, such as:

- `cp2_admit_with_child_fit_check`
- `cp2_reject_infeasible_combined`
- `cp2_no_feasible_trial`
- “parent fits AND child post-fit verified”
- “combined parent+child demand exceeds cluster capacity”

### CP-2 result

The CP-2 benchmark covers the 7 development fixtures and 12 total trials:

- **7 completed**
- **0 unresolved**
- **5 rejected as permanently infeasible**
- **No unresolved CP-2 deadlocks in the benchmark result**
- **Every CP-2 result row matches its expected oracle output**

The interpretation matters: CP-2 does not magically make an impossible workload complete. It prevents impossible trials from becoming silent hangs and reports the reason.

### Advisor and API

CP-2 also adds integration features:

- **FastAPI:** `/health`, `/scenarios`, `/simulate`, `/benchmark`, `/validate`.
- **Advisor:** classifies whether a result is horizon-limited, a real capacity shortfall, ordering-blocked, or nested-deadlock-like; then gives an explainable recommendation.
- **Next.js dashboard:** visualizes scenarios, states, events, metrics, and policy comparisons.
- **Evidence files:** JSON, CSV, charts, test outputs, and a real-Ray reproduction capture.

The advisor is **rule-based advice**, not an ML model and not an automatic cluster scaler.

### Important limitation to say confidently

The current simulator places a trial's parent and child atomically within one simulation admission flow. Therefore, a true two-trial mutual cycle cannot be formed by the current model. The project documents that negative result honestly and demonstrates the adjacent **collateral-blocking** hazard instead. Do not claim that CP-2 solved a mutual-cycle case that the simulator cannot generate.

---

## 5. CP-1 versus CP-2

| Aspect | CP-1 | CP-2 |
|---|---|---|
| Purpose | Establish and measure the scheduling problem | Add safety-aware admission and explainable integration |
| Main policies | FIFO and Greedy | Deadlock-aware policy, compared with the CP-1 baselines |
| Admission check | Parent fit only | Parent fit + combined parent/child feasibility + post-parent child fit |
| Queue behavior | FIFO blocks at head; Greedy skips blocked head | Priority-aware selection, defer unsafe temporary fits, reject impossible fits |
| Deadlock behavior | Can leave `WAITING_CHILD` trials unresolved | Rejects or defers unsafe admissions; bounds recovery paths |
| Output | Completed, unresolved, cycles, stranding | Completed, rejected, reasons, traces, recovery, API/dashboard evidence |
| Evidence | Frozen fixtures, oracle, deterministic gate | Additive tests, CP-2 fixtures, Ray 2.10.0 Docker reproduction |
| Claim level | Simulator baseline | Simulator + protocol/captured Ray reproduction; not production deployment |

### The one-line algorithm difference

> **FIFO:** first trial whose parent fits.  
> **Greedy:** first later trial whose parent fits.  
> **Deadlock-aware:** first trial whose parent fits and whose child can also fit safely, otherwise defer or reject with a reason.

---

## 6. Research papers to study

Read at least the abstract, introduction, and conclusion of the first four before the review. Do not claim to have implemented an algorithm when the project only uses it as background.

### 1. Ray [1]


**Philipp Moritz et al.** “Ray: A Distributed Framework for Emerging AI Applications.” **OSDI 2018**, pp. 561–577.  
Official source: https://www.usenix.org/conference/osdi18/presentation/moritz

**Brief:** Ray presents a distributed execution system with task-parallel and actor-based computation, a distributed scheduler, and fault-tolerant control state.  
**Connection:** NestedTune Guard uses a Ray-style resource and placement-group setting. The project studies a scheduling failure mode around nested reservations; it does not reimplement Ray’s scheduler.

### 2. Tune [2]


**Richard Liaw, Eric Liang, Robert Nishihara, Philipp Moritz, Joseph E. Gonzalez, Ion Stoica.** “Tune: A Research Platform for Distributed Model Selection and Training.” **2018**, presented at the ICML AutoML workshop; arXiv:1807.05118.  
Official source: https://arxiv.org/abs/1807.05118

**Brief:** Tune gives model-selection algorithms a common interface to training scripts and makes distributed hyperparameter search easier to scale.  
**Connection:** It motivates the outer hyperparameter-tuning context and the need for reliable resource management around trials and training jobs.

### 3. Dominant Resource Fairness [3]


**Ali Ghodsi, Matei Zaharia, Benjamin Hindman, Andy Konwinski, Scott Shenker, Ion Stoica.** “Dominant Resource Fairness: Fair Allocation of Multiple Resource Types.” **NSDI 2011**.  
Official source: https://www.usenix.org/conference/nsdi11/dominant-resource-fairness-fair-allocation-multiple-resource-types

**Brief:** DRF proposes a fairness policy for allocating multiple resource types such as CPU and memory, using each user’s dominant resource share.  
**Connection:** NestedTune Guard reports fairness-related metrics such as Jain fairness, but it does **not** implement DRF. Say that DRF informed the fairness discussion, not that CP-2 is a DRF implementation.

### 4. Distributed Deadlock Detection [4]


**K. Mani Chandy, Jayadev Misra, Laura M. Haas.** “Distributed Deadlock Detection.” **ACM Transactions on Computer Systems**, 1983. DOI: https://doi.org/10.1145/357360.357365  
Official source: https://research.ibm.com/publications/distributed-deadlock-detection

**Brief:** The paper presents distributed algorithms for resource and communication deadlocks and aims to detect true deadlocks without false reports, without one process maintaining all global information.  
**Connection:** The project uses a simpler simulator-side wait-for graph and cycle detection to make nested resource waiting observable and testable. It is inspired by the concept, not a reproduction of the distributed algorithm.

### 5. Hyperband [5]


**Lisha Li, Kevin Jamieson, Giulia DeSalvo, Afshin Rostamizadeh, Ameet Talwalkar.** “Hyperband: A Novel Bandit-Based Approach to Hyperparameter Optimization.” **JMLR 18(185), 2018**.  
Official source: https://jmlr.org/papers/v18/16-558.html

**Brief:** Hyperband allocates training resources adaptively and stops poor configurations early, speeding up hyperparameter search.  
**Connection:** It is related to the tuning workload, but CP-2 focuses on safe nested resource admission. CP-2 does **not** implement Hyperband’s early-stopping algorithm.

### 6. ASHA [6]


**Liam Li, Kevin Jamieson, Afshin Rostamizadeh, Ekaterina Gonina, Moritz Hardt, Benjamin Recht, Ameet Talwalkar.** “A System for Massively Parallel Hyperparameter Tuning.” **arXiv:1810.05934**, 2018/2020 version.  
Official source: https://arxiv.org/abs/1810.05934

**Brief:** The paper introduces ASHA, an asynchronous successive-halving method that uses aggressive early stopping and scales to massive parallelism.  
**Connection:** ASHA is a possible future search policy that could run on top of a safe resource-admission layer. It is not part of the current CP-2 controller.

### Primary technical source used for the Ray case [7]


**Ray GitHub issue #47439:** https://github.com/ray-project/ray/issues/47439

This is not a peer-reviewed research paper. It is the source issue/topology that motivated the reproduction. The project’s captured run used Ray 2.10.0 and observed the child placement group stuck in `PENDING`, with the 4/4/1/3 accounting matching the simulator abstraction.

---

## 7. Exact answer to “Did you read research papers?”

Use this only after reading the abstracts/intros above:

> “Yes. I studied the Ray paper and the Tune paper for the distributed AI and hyperparameter-tuning context. I also reviewed Dominant Resource Fairness for multi-resource fairness and Chandy–Misra–Haas for distributed deadlock detection. Hyperband and ASHA are related hyperparameter-optimization methods that I considered as background, but they are not implemented in this project. My implementation is a deadlock-aware admission controller for nested resource reservations, evaluated against FIFO and Greedy baselines; it is not a reimplementation of those papers.”

If they ask whether the project is a novel paper contribution:

> “The contribution is an engineering and evaluation contribution: a deterministic nested-resource simulator, hierarchy-aware admission checks, bounded recovery scenarios, explainable evidence, and a Ray reproduction protocol. I am careful not to claim a new general-purpose scheduling theorem or production deployment.”

If you have not actually read the papers yet, say:

> “I have reviewed the abstracts and the parts directly related to my design, and I am completing the detailed literature review with my guide.”

That is safer than pretending to have read every page.

---

## 8. Where to publish

### Recommended route

1. **Supervisor review first.** Confirm authorship, institutional affiliation, data/code release, and whether the Ray issue/evidence can be cited.
2. **Prepare a preprint** on arXiv if your guide approves. This gives a public timestamp and makes the work easy to share, but arXiv is not peer review and is not the same as acceptance.
3. **Target a student symposium or workshop** in cloud computing, distributed systems, cluster scheduling, or applied machine learning. This is the most realistic first peer-reviewed target for the current engineering/evaluation scope.
4. **Aim at a full conference later** after adding multi-node experiments, repeated runs, larger workloads, comparisons against more schedulers, and a stronger related-work section.

### Specific venue suggestions

- **IEEE CLOUD:** strong fit for cloud resource management and distributed systems; competitive.
- **IEEE CLUSTER:** strong fit for cluster scheduling, resource management, and reproducible systems evaluation; competitive.
- **IEEE CloudCom:** relevant cloud-computing venue; check the current call for papers and indexing requirements.
- **IEEE Access:** broad peer-reviewed journal; practical for an expanded systems/evaluation manuscript, but check article-processing charges and current scope.
- **Journal of Cloud Computing (Springer):** relevant journal option; expect a full peer-review process and expand the evaluation before submitting.
- **University/IEEE student research conference or a relevant workshop:** most realistic near-term option if the goal is a first presentation/publication.

### My recommendation for this project

> **Near term:** submit an improved version to a student symposium or workshop, with the deterministic simulator and reproducibility package as the focus.  
> **Longer term:** expand the evaluation and target IEEE CLUSTER or IEEE CLOUD.  
> **Journal option:** IEEE Access or Journal of Cloud Computing after adding stronger experimental depth.

Do not say “I will definitely publish in IEEE CLOUD.” Say:

> “My proposed target is a student/workshop venue first, then IEEE CLUSTER or IEEE CLOUD after strengthening the multi-node evaluation. A journal extension could target IEEE Access or the Journal of Cloud Computing.”

Before submission, add:

- a formal related-work section;
- multiple Ray versions and multi-node experiments;
- repeated runs and confidence intervals where randomness exists;
- clearer comparison to existing placement/admission policies;
- a threat-to-validity section;
- supervisor-approved author list and affiliation;
- code/evidence availability statement.

Never submit the same manuscript to multiple peer-reviewed venues at the same time.

---

## 9. Why GitHub Actions was added

### Plain-English explanation

GitHub is the remote copy of the project. **GitHub Actions is an automated robot that checks the project whenever code is pushed or a pull request is opened.**

It prevents the project from depending only on “it worked on my laptop.” A clean GitHub runner checks the same repository from scratch.

### What this project’s workflow does

The file is `.github/workflows/ci.yml`.

1. **Python tests:** installs Python 3.11 and runs the 70 automated tests.
2. **CP-1 gate:** runs `scripts/run_cp1.sh` and protects the frozen CP-1 totals/oracle checks.
3. **Evidence upload:** stores evidence and charts from the run.
4. **Dashboard check:** installs Node 22, runs frontend lint, and creates a production Next.js build.
5. **Docker check:** builds the application image as a smoke test; this job does not push the image.
6. **Helm check:** lints the chart and renders Kubernetes templates.
7. **Release job on `main`:** after all checks pass, builds and pushes a tagged Docker image to GitHub Container Registry using the repository’s GitHub token.

### What GitHub Actions does not do

- It does not improve the scheduling algorithm by itself.
- It does not prove production-scale performance.
- It does not mean the application is deployed to a Kubernetes cluster.
- It does not replace unit tests or a research evaluation.

### Viva answer

> “I added GitHub Actions as continuous integration and delivery automation. On every push, it creates a clean environment, runs the Python tests and CP-1 gate, validates the dashboard build, checks Docker and Helm packaging, and uploads evidence. On a successful push to `main`, the release job publishes a versioned container image to GHCR. This gives reproducible verification and catches regressions; it is separate from the scheduling algorithm and is not a production deployment claim.”

---

## 10. What to say for each slide in the supplied 12-slide structure

1. **Title:** “Our project is NestedTune Guard, project ID CINT-11. It studies safe nested resource admission in distributed hyperparameter tuning.”
2. **Outline:** “I will cover the problem, requirements, alternatives, architecture, design flow, implementation, results, and future work.”
3. **Introduction:** “An outer trial owns a parent reservation, while inner training requests a child reservation. The child can wait for resources held by its parent.”
4. **Problem/objectives:** “Existing FIFO and Greedy decisions inspect the parent but not the child. We measure the failure and add a hierarchy-aware safety check.”
5. **Requirements:** “The system must be deterministic, bounded, testable, and reproducible; the acceptance result is explicit evidence rather than an indefinite hang.”
6. **Alternatives:** “FIFO is strict arrival order. Greedy skips a blocked head. CP-2 checks parent plus child and rejects/defer unsafe admissions. The papers provide the systems, fairness, deadlock, and tuning background.”
7. **Architecture:** “JSON fixtures go through schema validation, the simulator, the policy engine, the observer, and the API/dashboard evidence layer.”
8. **Data flow:** “At each tick, the policy decides; the simulator admits the parent, checks the child, updates state, and records an event.”
9. **Progress:** “The main implementation and verification pieces are complete; remaining work before submission is metadata, rehearsal, and literature finalization.”
10. **Results:** “FIFO completed 5/12 and Greedy 7/12 with unresolved work. CP-2 completed 7/12 and explicitly rejected 5 impossible trials, leaving 0 unresolved.”
11. **Conclusion/future:** “CP-2 improves safety and observability, but the current simulator is deterministic and atomic. Multi-node and wider Ray-version validation are future work.”
12. **Questions:** “Thank you. I can explain the policy decision, the evidence, the limitation, or the research connection.”

---

## 11. Fast viva questions and answers

**Q: What is the novelty?**  
A: “The practical contribution is hierarchy-aware admission for nested parent/child reservations, with deterministic evidence and explicit reject/defer reasons. I do not claim a new universal scheduling theory.”

**Q: Why not just use Greedy?**  
A: “Greedy improves throughput by skipping a blocked head, but it only checks the parent. It can still admit a parent whose child cannot start. CP-2 checks the combined hierarchy.”

**Q: Why reject a trial instead of waiting?**  
A: “If combined parent-plus-child demand exceeds maximum cluster capacity, waiting cannot help. Rejecting it prevents a silent infinite wait and gives an actionable reason.”

**Q: Did you implement Hyperband or ASHA?**  
A: “No. They are related search/early-stopping methods. Our focus is resource admission safety around nested jobs; they are future integration possibilities.”

**Q: Is the advisor machine learning?**  
A: “No. It is a rule-based diagnostic advisor that classifies the observed state and recommends whether more time, capacity, ordering changes, or nested-admission changes are relevant.”

**Q: Is it deployed in production?**  
A: “No. The repository includes Docker/Kubernetes/Helm packaging and a captured Ray 2.10.0 reproduction. CI validates packaging, but production deployment and multi-node benchmarking are future work.”

**Q: What does 4/4/1/3 mean?**  
A: “In the captured Ray reproduction: 4 CPUs total, 4 reserved, 1 CPU useful/used, and 3 CPUs stranded while the child placement group remained pending.”

**Q: What is the biggest limitation?**  
A: “The deterministic simulator models the structural failure and uses atomic placement; it cannot generate every possible distributed mutual cycle. That limitation is documented, and the adjacent collateral-blocking case is tested.”

**Q: Why use a 30-second horizon?**  
A: “A bounded horizon makes unresolved behavior measurable and prevents a deadlock from hanging the experiment forever. The horizon is an evaluation parameter, not a claim that every real workload should time out at exactly 30 seconds.”

---

## 12. Last-minute study plan

1. Read the six paper abstracts and the first/last sections of Ray, Tune, DRF, and Distributed Deadlock Detection.
2. Memorize the 30-second answer and the one-line algorithm difference.
3. Memorize the result table: FIFO 5/12, Greedy 7/12, CP-2 7/12 + 5 rejected + 0 unresolved.
4. Practice explaining the 4/4/1/3 Ray evidence.
5. Cover slide is already final: four team members with registration numbers, Guide ID 8199 / Mr. Rambabu Kalathoti, Batch CSE-2. Regenerate from `scripts/create_cp2_review_deck.py` rather than editing the PPTX by hand, so the two stay in sync.
6. Do not claim Hyperband, ASHA, DRF, or Chandy–Misra–Haas was implemented. Say they informed the background/design discussion.
7. If asked something unknown, say: “That is outside the current simulator scope; it is a limitation/future-work item.”

## Sources

[1] https://www.usenix.org/conference/osdi18/presentation/moritz — Ray: A Distributed Framework for Emerging AI Applications
[2] https://arxiv.org/abs/1807.05118 — Tune: A Research Platform for Distributed Model Selection and Training
[3] https://www.usenix.org/conference/nsdi11/dominant-resource-fairness-fair-allocation-multiple-resource-types — Dominant Resource Fairness
[4] https://research.ibm.com/publications/distributed-deadlock-detection — Distributed Deadlock Detection
[5] https://jmlr.org/papers/v18/16-558.html — Hyperband
[6] https://arxiv.org/abs/1810.05934 — A System for Massively Parallel Hyperparameter Tuning (ASHA)
[7] https://github.com/ray-project/ray/issues/47439 — Ray Issue #47439 source case

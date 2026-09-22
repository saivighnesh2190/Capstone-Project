# Ray #47439 Real-Cluster Reproduction Protocol

**Project:** NestedTune Guard (CINT-11)
**Purpose:** reproduce the source-case deadlock of this capstone — Ray issue
[#47439](https://github.com/ray-project/ray/issues/47439) — on a real Ray
cluster inside Docker, capture hard evidence, and map the observed state onto
the simulator's model. The protocol is now backed by a completed, captured
Ray 2.10.0 run rather than an unverified future claim.

**Status: REPRODUCED on Ray 2.10.0** (see evidence excerpts below). This
protocol substantiates the earlier report claim with a real captured run, rather
than merely promising a separate reproduction artifact.
---

## 1. What is reproduced

The source case: a tuning trial's **parent placement group** reserves the whole
4-CPU cluster; a **nested trainer running inside that reservation** then
requests a **3-CPU child placement group**. The child can never be admitted —
the CPUs it needs are reserved by its own trial's parent — so the nested
request waits forever. On real Ray the child PG stays `PENDING`; in the
simulator the trial enters `WAITING_CHILD` with the wait-for self-cycle
`xgb-001 → xgb-001`.

The reproduction uses the core placement-group API directly (no xgboost-ray
needed): the deadlock is in PG scheduling, not in the trainer. The parent PG
reserves all 4 CPUs as two PACK bundles `[{"CPU": 1}, {"CPU": 3}]` — the 1-CPU
bundle runs the trial driver actor; the nested child request for 3 CPUs
originates **from inside the parent's reservation** (an actor scheduled with
`PlacementGroupSchedulingStrategy` on the parent's 1-CPU bundle).

## 2. Prerequisites

- Docker (tested: Docker 29.7.2 on Manjaro Linux, kernel 6.12)
- ~7 GB free disk (the `rayproject/ray:2.10.0` image is ~3.1 GB; the built
  repro image adds ~30 MB on top)
- No GPU, no multi-machine setup — a single container is sufficient; Ray counts
  **logical** CPUs, so `ray.init(num_cpus=4)` works on any host

## 3. Steps

```bash
cd "/home/nsaivighnesh/Downloads/capstone project/ray-repro"
docker compose up --build
```

That is the entire procedure. The compose file caps memory at 3 GB and sets
`COLORFUL_DISABLE=1` (Ray 2.10's `colorful` import chain calls
`sys.stdout.isatty()`, which fails on the script's tee'd stdout — disabling
color at the source avoids the crash; `TERM=dumb` is belt-and-braces). The
container:

1. `ray.init(num_cpus=4)` — fresh local cluster
2. Creates the parent PG `parent_47439` (PACK, `[{"CPU": 1}, {"CPU": 3}]`)
3. Launches the trial driver actor pinned to the parent's 1-CPU bundle
4. From inside that actor, requests the 3-CPU child PG `child_47439`
5. Polls the child PG state for up to 90 s (bounded wait)
6. Dumps evidence into `evidence/<run-timestamp>/` and exits 0

The full run takes ~3–4 minutes (image build already done: ~20 s; Ray startup
~15 s; bounded wait ~92 s; evidence dump ~20 s).

## 4. Expected output (real excerpts from `evidence/run_20260922_070557/`)

The console tail (`00_console_transcript.txt`):

```text
[07:07:53]   Deadlock reproduced: True
[07:07:53]   Bounded wait       : 91.8s (30 polls)
[07:07:53]   Evidence           : /app/evidence/run_20260922_070557
```

`ray status` at the end of the wait (`07_ray_status_final.txt`) — the money
lines:

```text
Usage:
 1.0/4.0 CPU (1.0 used of 4.0 reserved in placement groups)

Demands:
 {'CPU': 3.0} * 1 (PACK): 1+ pending placement groups
```

The placement-group table (`08_ray_list_placement_groups_detail.txt`):

```yaml
-   placement_group_id: 441fd889fa9f693bc9f3a5f2ab0701000000
    name: parent_47439
    state: CREATED                      # parent holds all 4 CPUs
    bundles:
    - { unit_resources: { CPU: 1.0 } }  # runs the trial driver actor
    - { unit_resources: { CPU: 3.0 } }  # stranded inside the reservation
-   placement_group_id: 76e86fee138cce6589c11d06f80d01000000
    name: child_47439
    state: PENDING                      # ← the deadlock: never admitted
    bundles:
    - { unit_resources: { CPU: 3.0 }, node_id: '' }   # unplaced
```

Resource accounting at the moment of the hang (`14_resource_accounting.json`):

```json
{
  "cluster_total_cpus": 4.0,
  "reserved_by_parent_pg": 4.0,
  "in_use_inside_parent": 1.0,
  "stranded_inside_parent": 3.0,
  "free_cpus_outside_pgs": 0.0,
  "matches_simulator_4_4_1_3": true
}
```

## 5. Mapping real Ray → simulator model

| Real Ray 2.10.0 observation | Simulator model |
|---|---|
| `child_47439` stuck `PENDING` for the full 91.8 s bounded wait (`scheduling_state: NO_RESOURCES_C...` in the PG stats) | Trial state `WAITING_CHILD` at the 30 s horizon |
| `1.0/4.0 CPU (1.0 used of 4.0 reserved in placement groups)` | The 4/4/1/3 accounting: 4 total, 4 reserved, 1 useful, 3 stranded |
| `{'CPU': 3.0} * 1 (PACK): 1+ pending placement groups` demand line | The nested child request that can never be satisfied |
| Parent and child PG share `creator_job_id` — the nested request waits on CPUs reserved by **its own trial's parent** | Wait-for self-cycle `xgb-001 → xgb-001` |
| Parent `CREATED` + child `PENDING` indefinitely, no error, no timeout | Bounded horizon converts the indefinite hang into a measurable experiment |

## 6. Version scope

- **Reproduces:** Ray 2.10.0 (`rayproject/ray:2.10.0`, Python 3.9.18)
- Not tested: other Ray versions. The reports' "Ray 2.10" reference matches
  the pinned base image; no claim is made about 2.8–2.12 or current releases.
- The GitHub issue page could not be re-fetched during the final protocol
  write-up (network restriction); the reproduction is grounded in the issue's
  documented behavior (nested placement-group request inside a parent
  reservation) and matches the simulator's frozen model.

## 6b. Known-good environment facts (captured in `00_environment.json`)

- Host: Manjaro Linux, kernel 6.12.108-1, Docker 29.7 issue-free
- Container /dev/shm = 64 MB → Ray logs "object store is using /tmp instead of
  /dev/shm". Harmless here (no large objects; the reproduction exercises
  scheduling, not object transfer).

## 7. Cleanup

```bash
cd ray-repro
docker compose down -v --remove-orphans
```

This removes the `ray47439-repro` container and any network/volumes created by
the compose project. The two images (`rayproject/ray:2.10.0`,
`ray-repro-ray-repro:latest`) are intentionally kept on disk so the
reproduction can be re-run at any time; delete them with
`docker rmi ray-repro-ray-repro:latest rayproject/ray:2.10.0` if you need the
disk space back.

## 8. Honest limitations

- **Single node.** One Ray node inside one container; the issue's multi-node
  topology is not exercised (the deadlock mechanism — a nested PG request
  waiting on its own parent's reservation — is node-count independent).
- **Logical CPUs.** `ray.init(num_cpus=4)` advertises 4 logical CPUs to Ray;
  the host's physical core count is irrelevant to the scheduling behavior.
- **Core PG API, not Ray Train/Tune.** The reproduction models the nested-PG
  request with the core API. The issue's original stack (xgboost-ray via Ray
  Train inside a Tune trial) produces the same PG topology and the same
  pending child; the trainer itself is not what deadlocks.
- **Version drift.** Evidence is pinned to Ray 2.10.0. Re-running on a newer
  Ray may behave differently; the reports only claim Ray 2.10.
- **Bounded wait = 90 s.** "Forever pending" is demonstrated as "pending for
  the entire bounded observation window with no progress and no error", which
  is the strongest claim a terminating experiment can make.

## 9. Files

| File | Purpose |
|------|---|
| `ray-repro/docker-compose.yml` | One-command reproduction (3 GB mem cap, colorful disabled) |
| `ray-repro/Dockerfile` | `FROM rayproject/ray:2.10.0`, copies the repro script |
| `ray-repro/reproduce_47439.py` | The reproduction + evidence-capture script (runs in-container) |
| `ray-repro/README.md` | Short instructions |
| `ray-repro/evidence/run_20260922_070557/` | 17 evidence files from the successful run (console transcript, ray status snapshots, PG tables, actor table, GCS/raylet log excerpts, resource accounting, simulator mapping) |

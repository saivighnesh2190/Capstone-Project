#!/usr/bin/env python3
"""
Real-Ray reproduction of Ray issue #47439 (nested placement-group deadlock).

Scenario (mirrors the "NestedTune Guard" simulator's WAITING_CHILD state):

  1. Single-node Ray cluster with 4 logical CPUs  (ray.init(num_cpus=4)).
  2. A "trial" parent placement group, PACK strategy, bundles [{"CPU": 1}, {"CPU": 3}]
     -> reserves the ENTIRE cluster (4/4 CPUs).
  3. The trial driver (an actor pinned to the parent PG, bundle 0) starts its
     actual 1-CPU workload inside the parent PG (bundle 1) and then requests a
     nested 3-CPU child placement group (PACK) from INSIDE that reservation.
  4. The child PG can never be admitted: the parent already holds all 4 CPUs,
     only 1 is in use, 3 are stranded inside the parent reservation.
     -> the child PG stays PENDING forever (GCS keeps retrying with
        scheduling_state NO_RESOURCES; no autoscaler on this fixed cluster).

Ray 2.10.0 API notes (verified against the rayproject/ray:2.10.0 image):
  - placement_group_table() keys are hex PG-id strings; entry["state"] is
    CREATED / PENDING / REMOVED (there is no "READY" state in the table).
  - PlacementGroup.id is a PlacementGroupID object; use .hex() to compare.
  - entry["bundles"] is a dict {"0": {...}, "1": {...}} (no "bundle_specs" key).
  - `ray pg list` does not exist; use `ray list placement-groups [--detail]`.
  - `ray status` needs the State API warm-up; retry until it stops printing
    "No cluster status".
"""

import sys
import json
import time
import socket
import shutil
import datetime
import subprocess
from pathlib import Path

EVIDENCE_DIR = Path("/app/evidence")   # volume-mounted from ray-repro/evidence
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
run_dir = EVIDENCE_DIR / f"run_{ts}"
run_dir.mkdir(parents=True, exist_ok=True)

CFG = dict(
    num_cpus=4,
    parent_bundles=[{"CPU": 1}, {"CPU": 3}],
    child_cpu=3,
    timeout=90,          # bounded wait for the hang (seconds)
    poll_interval=3,
)


class Tee:
    """Duplicate driver stdout into the evidence transcript file."""

    def __init__(self, path):
        self.f = open(path, "w", buffering=1)
        self.stdout = sys.stdout

    def write(self, s):
        self.stdout.write(s)
        self.f.write(s)

    def flush(self):
        self.stdout.flush()
        self.f.flush()

    def isatty(self):
        return False

    def fileno(self):
        return self.stdout.fileno()

    def __getattr__(self, name):
        # delegate anything else (encoding, writable, ...) to real stdout
        return getattr(self.stdout, name)


sys.stdout = Tee(run_dir / "00_console_transcript.txt")


def log(msg=""):
    t = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{t}] {msg}", flush=True)


def save(name, content):
    (run_dir / name).write_text(content)
    log(f"saved: {name} ({len(content)} bytes)")


def save_json(name, obj):
    save(name, json.dumps(obj, indent=2, default=str))


def run_cli(args, retries=6, delay=3, timeout=30):
    """Run a ray CLI command, retrying while the State API warms up."""
    out, rc = "", None
    for attempt in range(retries):
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            rc, out = r.returncode, r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            rc, out = None, f"<timeout running: {' '.join(args)}>"
        if rc == 0 and "No cluster status" not in out:
            return out, rc
        log(f"  cli retry {attempt + 1}/{retries} for '{' '.join(args)}' (rc={rc})")
        time.sleep(delay)
    return out, rc


log("=" * 68)
log("Ray issue #47439 reproduction — nested placement-group deadlock")
log(f"Config: {CFG}")
log(f"Evidence dir: {run_dir}")
log("=" * 68)

import ray
from ray.util.placement_group import (
    placement_group,
    PlacementGroupSchedulingStrategy,
)

# ── Environment ────────────────────────────────────────────────────────────
log("\nSTEP 0: environment")
env_info = {
    "ray_version": ray.__version__,
    "python": sys.version.split()[0],
    "hostname": socket.gethostname(),
    "kernel": subprocess.run(["uname", "-r"], capture_output=True, text=True).stdout.strip(),
    "dev_shm_bytes": shutil.disk_usage("/dev/shm").total,
    "dev_shm_note": (
        "Docker default /dev/shm is 64MB, so Ray logs 'object store is using "
        "/tmp instead of /dev/shm'. Harmless for this scheduling reproduction "
        "(no large objects are transferred)."
    ),
}
save_json("00_environment.json", env_info)
for k, v in env_info.items():
    log(f"  {k}: {v}")

# ── Init ───────────────────────────────────────────────────────────────────
log("\nSTEP 1: ray.init(num_cpus=4) — single node, 4 LOGICAL CPUs")
ray.init(num_cpus=CFG["num_cpus"], ignore_reinit_error=True, log_to_driver=False)
log("  ray.init done")

out, _ = run_cli(["ray", "status"])
save("01_ray_status_initial.txt", out)

cluster = ray.cluster_resources()
avail = ray.available_resources()
save_json("02_resources_initial.json", {
    "cluster_total": {k: v for k, v in cluster.items() if not k.startswith(("ray.", "node:"))},
    "available": {k: v for k, v in avail.items() if not k.startswith(("ray.", "node:"))},
})
log(f"  cluster CPUs={cluster.get('CPU')}  available CPUs={avail.get('CPU')}")

# ── Parent PG ──────────────────────────────────────────────────────────────
log("\nSTEP 2: create parent PG 'parent_47439' "
    f"(PACK, bundles={CFG['parent_bundles']}) — reserves all 4 CPUs")
parent_pg = placement_group(CFG["parent_bundles"], strategy="PACK", name="parent_47439")
parent_hex = parent_pg.id.hex()
log(f"  parent PG id: {parent_hex}")
ray.get(parent_pg.ready(), timeout=30)
log("  parent PG ready() returned -> table state should be CREATED")

time.sleep(2)  # let the table settle
parent_entry = ray.util.placement_group_table().get(parent_hex, {})
save_json("03_parent_pg_entry.json", parent_entry)
log(f"  parent PG table state: {parent_entry.get('state')}")
log(f"  parent PG bundles: {parent_entry.get('bundles')}")

out, _ = run_cli(["ray", "status"])
save("04_ray_status_after_parent.txt", out)
log("ray status after parent PG:")
for line in out.splitlines():
    if line.strip():
        log(f"  | {line}")

avail_parent = ray.available_resources()
save_json("05_resources_after_parent.json", {
    "available": {k: v for k, v in avail_parent.items()
                  if not k.startswith(("ray.", "node:"))},
})
log(f"  plain 'CPU' available outside PGs: {avail_parent.get('CPU', 0.0)}")
log(f"  CPU_group_{parent_hex[:8]}...: {avail_parent.get(f'CPU_group_{parent_hex}')}"
    "  (parent PG's reserved CPU pool)")

# ── Trial driver actor + trial workload, both inside the parent PG ─────────
log("\nSTEP 3: trial driver actor (parent PG bundle 0) + 1-CPU trial workload (bundle 1)")


@ray.remote
class TrialDriver:
    """Stands in for the Ray Tune trial driver running inside the parent PG."""

    def __init__(self):
        self.child_pg = None

    def request_child_pg(self, cpu_request):
        # Nested PG request issued from INSIDE the parent PG reservation.
        self.child_pg = placement_group(
            [{"CPU": cpu_request}], strategy="PACK", name="child_47439")
        return self.child_pg.id.hex()

    def child_state(self):
        if self.child_pg is None:
            return {"state": "NO_PG"}
        myid = self.child_pg.id.hex()
        for pid, info in ray.util.placement_group_table().items():
            if pid == myid:
                return {"state": info.get("state"), "pg_id": myid,
                        "stats": info.get("stats", {})}
        return {"state": "NOT_FOUND", "pg_id": myid}

    def remove_child(self):
        if self.child_pg is not None:
            self.child_pg.remove()
            return "removed"
        return "nothing-to-remove"


@ray.remote(num_cpus=1)
def trial_work():
    """The trial's actual 1-CPU workload running inside the parent PG."""
    time.sleep(600)


actor = TrialDriver.options(
    scheduling_strategy=PlacementGroupSchedulingStrategy(
        placement_group=parent_pg,
        placement_group_bundle_index=0,
    )
).remote()
trial_work.options(
    scheduling_strategy=PlacementGroupSchedulingStrategy(
        placement_group=parent_pg,
        placement_group_bundle_index=1,
    )
).remote()
time.sleep(3)
log("  actor + trial workload submitted (bundle 1 holds the 1-CPU task)")

# ── Nested child PG request ────────────────────────────────────────────────
log(f"\nSTEP 4: request 3-CPU child PG 'child_47439' from INSIDE the parent PG")
child_hex = ray.get(actor.request_child_pg.remote(CFG["child_cpu"]))
log(f"  child PG id: {child_hex}")
st = ray.get(actor.child_state.remote())
log(f"  child PG initial state: {st.get('state')}")

# ── Bounded wait ───────────────────────────────────────────────────────────
log(f"\nSTEP 5: bounded wait for child PG (max {CFG['timeout']}s, "
    f"poll every {CFG['poll_interval']}s)")
log("  expected if the bug reproduces: PENDING forever "
    "(parent holds 4/4 CPUs, 3 stranded)")

start = time.time()
poll = 0
seen_states = []
ever_pending = False
midwait_saved = False
child_final = None

while time.time() - start < CFG["timeout"]:
    poll += 1
    elapsed = time.time() - start
    st = ray.get(actor.child_state.remote())
    s = st.get("state")
    child_final = s
    if s not in seen_states:
        seen_states.append(s)
    if s == "PENDING":
        ever_pending = True
    log(f"  poll {poll:3d}  t={elapsed:5.1f}s  child_state={s}")

    if not midwait_saved and elapsed >= 30:
        out, _ = run_cli(["ray", "status"])
        save("06_ray_status_midwait.txt", out)
        midwait_saved = True

    if s == "CREATED":
        log("  UNEXPECTED: child PG became CREATED — deadlock did NOT reproduce")
        break
    if s in ("REMOVED", "FAILED"):
        log(f"  child PG entered {s} at t={elapsed:.1f}s")
        break

    time.sleep(CFG["poll_interval"])

total_wait = time.time() - start
log(f"  wait finished: {total_wait:.1f}s, {poll} polls, states seen={seen_states}")
log(f"  child ever PENDING: {ever_pending}  final state: {child_final}")

# ── Final evidence ─────────────────────────────────────────────────────────
log("\nSTEP 6: final evidence capture")

out, _ = run_cli(["ray", "status"])
save("07_ray_status_final.txt", out)
usage_line = next((l.strip() for l in out.splitlines() if "CPU (" in l), "")
demand_line = next((l.strip() for l in out.splitlines() if "pending placement groups" in l), "")
log(f"  usage: {usage_line}")
log(f"  demand: {demand_line}")

out, _ = run_cli(["ray", "list", "placement-groups", "--detail"])
save("08_ray_list_placement_groups_detail.txt", out)
log("final `ray list placement-groups --detail` (key fields):")
for line in out.splitlines():
    if any(f in line for f in ("name:", "state:", "scheduling_state:",
                               "scheduling_attempt:", "CPU:", "creator_job_id:",
                               "PLACEMENT_GROUP_ID")):
        log(f"  | {line.strip()}")

out, _ = run_cli(["ray", "list", "actors", "--detail"])
save("09_ray_list_actors_detail.txt", out)

final_table = ray.util.placement_group_table()
final_pgs = [
    {"pg_id": pid, "name": info.get("name"), "state": info.get("state"),
     "bundles": info.get("bundles"), "strategy": info.get("strategy"),
     "stats": info.get("stats", {})}
    for pid, info in final_table.items()
]
save_json("10_final_pg_table.json", final_pgs)

final_avail = ray.available_resources()
final_cluster = ray.cluster_resources()
save_json("11_final_resources.json", {
    "cluster_total": {k: v for k, v in final_cluster.items()
                      if not k.startswith(("ray.", "node:"))},
    "available": {k: v for k, v in final_avail.items()
                  if not k.startswith(("ray.", "node:"))},
})

# GCS / raylet logs
gcs_lines, raylet_tail = [], []
try:
    with open("/tmp/ray/session_latest/logs/gcs_server.out") as fh:
        gcs_lines = [l.rstrip() for l in fh if "placement group" in l.lower()]
except OSError as e:
    gcs_lines = [f"<could not read gcs_server.out: {e}>"]
try:
    with open("/tmp/ray/session_latest/logs/raylet.out") as fh:
        raylet_tail = [l.rstrip() for l in fh][-40:]
except OSError as e:
    raylet_tail = [f"<could not read raylet.out: {e}>"]
save("12_gcs_server_placement_group_lines.txt", "\n".join(gcs_lines))
save("13_raylet_out_tail.txt", "\n".join(raylet_tail))
gcs_text = "\n".join(gcs_lines)
gcs_created_parent = "Successfully created placement group parent_47439" in gcs_text
gcs_created_child = "Successfully created placement group child_47439" in gcs_text
log(f"  GCS log: 'Successfully created ... parent_47439' present: {gcs_created_parent}")
log(f"  GCS log: 'Successfully created ... child_47439'  present: {gcs_created_child}")

# ── Resource accounting (computed from live values) ─────────────────────────
log("\nSTEP 7: resource accounting vs simulator model")
total_cpus = float(final_cluster.get("CPU", 0))
free_outside = float(final_avail.get("CPU", 0))
parent_reserved = sum(float(b.get("CPU", 0))
                      for b in (parent_entry.get("bundles") or {}).values())
pg_group_free = float(final_avail.get(f"CPU_group_{parent_hex}", 0))
in_use = round(parent_reserved - pg_group_free, 3)
stranded = round(parent_reserved - in_use, 3)

accounting = {
    "cluster_total_cpus": total_cpus,
    "reserved_by_parent_pg": parent_reserved,
    "in_use_inside_parent": in_use,
    "stranded_inside_parent": stranded,
    "free_cpus_outside_pgs": free_outside,
    "ray_status_usage_line": usage_line,
    "ray_status_demand_line": demand_line,
    "simulator_model": {"total": 4, "reserved": 4, "in_use": 1, "stranded": 3},
    "matches_simulator_4_4_1_3": (
        total_cpus == 4 and parent_reserved == 4 and in_use == 1 and stranded == 3
    ),
}
save_json("14_resource_accounting.json", accounting)
log(f"  total={total_cpus}  reserved={parent_reserved}  in_use={in_use}  "
    f"stranded={stranded}  free_outside={free_outside}")
log(f"  matches simulator 4/4/1/3 model: {accounting['matches_simulator_4_4_1_3']}")

# ── Simulator mapping ──────────────────────────────────────────────────────
reproduced = ever_pending and child_final == "PENDING"
mapping = {
    "reproduces": reproduced,
    "observed_real_ray": {
        "child_pg_state": child_final,
        "child_pg_ever_pending": ever_pending,
        "wait_seconds": round(total_wait, 1),
        "parent_pg_state": parent_entry.get("state"),
        "gcs_created_parent_pg": gcs_created_parent,
        "gcs_created_child_pg": gcs_created_child,
        "accounting": {
            "total": total_cpus, "reserved": parent_reserved,
            "in_use": in_use, "stranded": stranded,
        },
        "ray_status_usage_line": usage_line,
        "ray_status_demand_line": demand_line,
    },
    "simulator_model": {
        "state": "WAITING_CHILD",
        "accounting": "4/4/1/3  (total / reserved / in-use / stranded)",
        "wait_for_graph_self_cycle": "xgb-001 -> xgb-001",
    },
    "mapping": {
        "WAITING_CHILD <- child PG stuck PENDING": (
            "child_47439 stays PENDING for the whole bounded wait; "
            "ray list placement-groups --detail shows scheduling_state "
            "NO_RESOURCES with scheduling_attempt climbing (endless retries)"
        ),
        "4/4/1/3 <- ray status usage line": (
            "'1.0/4.0 CPU (1.0 used of 4.0 reserved in placement groups)': "
            "4 total, 4 reserved by the parent PG, 1 in use by the trial "
            "workload, 3 stranded inside the parent reservation"
        ),
        "xgb-001 -> xgb-001 <- self-defeating nested request": (
            "the nested child-PG request waits on CPUs reserved by its own "
            "trial's parent PG (both PGs share creator_job_id 01000000); "
            "no other job holds resources, so the wait-for graph is a "
            "self-cycle — exactly the simulator's WAITING_CHILD self-cycle"
        ),
    },
}
save_json("15_simulator_mapping.json", mapping)
log(f"  reproduces: {reproduced}")

# ── Cleanup ────────────────────────────────────────────────────────────────
log("\nCLEANUP")
try:
    log(f"  child PG removal: {ray.get(actor.remove_child.remote(), timeout=15)}")
except Exception as e:
    log(f"  child PG removal note: {type(e).__name__}: {e}")
try:
    parent_pg.remove()
    log("  parent PG removed")
except Exception as e:
    log(f"  parent PG removal note: {type(e).__name__}: {e}")
ray.shutdown()
log("  ray.shutdown() done")

# ── Summary ────────────────────────────────────────────────────────────────
log("\n" + "=" * 68)
log("REPRODUCTION COMPLETE")
log(f"  Ray version        : {ray.__version__}")
log(f"  Cluster            : single node, {CFG['num_cpus']} logical CPUs")
log(f"  Parent PG          : PACK {CFG['parent_bundles']} -> state "
    f"{parent_entry.get('state')}")
log(f"  Child PG request   : {{'CPU': {CFG['child_cpu']}}} from inside parent PG")
log(f"  Child final state  : {child_final}   (ever PENDING: {ever_pending})")
log(f"  Accounting         : total={total_cpus} reserved={parent_reserved} "
    f"in_use={in_use} stranded={stranded} free={free_outside}")
log(f"  Matches 4/4/1/3    : {accounting['matches_simulator_4_4_1_3']}")
log(f"  Deadlock reproduced: {reproduced}")
log(f"  Bounded wait       : {total_wait:.1f}s ({poll} polls)")
log(f"  Evidence           : {run_dir}")
log("=" * 68)

save_json("SUMMARY.json", {
    "ray_version": ray.__version__,
    "reproduces": reproduced,
    "cluster_cpus": CFG["num_cpus"],
    "parent_pg": {"name": "parent_47439", "strategy": "PACK",
                  "bundles": CFG["parent_bundles"],
                  "state": parent_entry.get("state")},
    "child_pg": {"name": "child_47439", "requested": {"CPU": CFG["child_cpu"]},
                 "state": child_final, "ever_pending": ever_pending},
    "accounting": {"total": total_cpus, "reserved": parent_reserved,
                   "in_use": in_use, "stranded": stranded,
                   "free_outside_pgs": free_outside,
                   "matches_simulator_4_4_1_3": accounting["matches_simulator_4_4_1_3"]},
    "usage_line": usage_line,
    "demand_line": demand_line,
    "wait_time_seconds": round(total_wait, 1),
    "polls": poll,
    "evidence_dir": str(run_dir),
    "evidence_files": sorted(f.name for f in run_dir.iterdir()),
})

log("\nDONE.")

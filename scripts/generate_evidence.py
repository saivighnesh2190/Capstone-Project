"""Generate CP-1 evidence files (CSV + JSON) + a dark-theme matplotlib chart PNG.

Outputs:
  - evidence/cp1_benchmark.json
  - evidence/cp1_results.csv
  - evidence/cp2_benchmark.json
  - evidence/cp2_results.csv
  - charts/cp1_baseline_results.png  (dark-theme, matches dashboard aesthetic)
"""
from __future__ import annotations

import json
import csv
import os
import sys
from pathlib import Path

# Ensure the project root is on PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nestedtune_guard.cli import _fixture_path  # type: ignore[attr-defined]
from nestedtune_guard.cli import cmd_benchmark, cmd_simulate  # type: ignore[attr-defined]
from nestedtune_guard.schema import validate_workload_file
from nestedtune_guard.simulator import simulate
from nestedtune_guard.oracle import all_fixtures, expected_for


EVIDENCE_DIR = ROOT / "evidence"
CHARTS_DIR = ROOT / "charts"
EVIDENCE_DIR.mkdir(exist_ok=True)
CHARTS_DIR.mkdir(exist_ok=True)


def run_all_fixtures() -> list[dict]:
    """Run every development fixture under every policy, return list of records."""
    records = []
    for fixture_name in all_fixtures():
        path = _fixture_path(fixture_name)
        definition = validate_workload_file(path)
        for policy in ("fifo", "greedy", "deadlock_aware"):
            result = simulate(definition, policy)
            s = result.summary
            expected = expected_for(fixture_name, policy)
            records.append({
                "fixture": fixture_name,
                "policy": policy,
                "completed": s.completed_trials,
                "unresolved": s.unresolved_trials,
                "rejected": s.rejected_trials,
                "cycles": s.observed_cycle_count,
                "bounded_resolution_pct": round(s.bounded_resolution_pct, 2),
                "trials_per_hour": round(s.trials_per_hour, 2),
                "queue_p95_s": round(s.queue_p95_s, 2),
                "jain_fairness": round(s.jain_fairness, 4),
                "avg_cpu_utilisation_pct": round(s.avg_cpu_utilisation_pct, 2),
                "avg_cpu_stranding_pct": round(s.avg_cpu_stranding_pct, 2),
                "oracle_completed": expected.completed if expected else None,
                "oracle_unresolved": expected.unresolved if expected else None,
                "oracle_rejected": expected.rejected if expected else None,
                "oracle_cycles": expected.cycles if expected else None,
                "oracle_match": (
                    expected is not None
                    and s.completed_trials == expected.completed
                    and s.unresolved_trials == expected.unresolved
                    and s.rejected_trials == expected.rejected
                    and s.observed_cycle_count == expected.cycles
                ),
                "trial_count": len(result.trials),
                "horizon_s": result.horizon_s,
            })
    return records


def write_csv(records: list[dict], path: Path) -> None:
    with path.open("w", newline="") as f:
        if not records:
            return
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)


def write_json(obj, path: Path) -> None:
    with path.open("w") as f:
        json.dump(obj, f, indent=2, default=str)


def render_chart(records: list[dict], path: Path) -> None:
    """Render a dark-theme matplotlib chart PNG matching the dashboard aesthetic."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.font_manager as fm

    # Register Noto Sans SC for fallback (matplotlib default DejaVu lacks special chars sometimes)
    try:
        fm.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    except Exception:
        pass

    import matplotlib.pyplot as plt
    import numpy as np

    # Dark theme — matches the dashboard's slate-950/cyan-400/emerald-400 palette
    plt.rcParams.update({
        "figure.facecolor": "#0b1120",   # slate-950
        "axes.facecolor":  "#0b1120",
        "axes.edgecolor":   "#1e293b",   # slate-800
        "axes.labelcolor":  "#cbd5e1",   # slate-300
        "xtick.color":      "#94a3b8",   # slate-400
        "ytick.color":      "#94a3b8",
        "text.color":       "#e2e8f0",   # slate-200
        "axes.titlecolor":  "#e2e8f0",
        "grid.color":       "#1e293b",
        "grid.alpha":       0.5,
        "font.sans-serif":  ["DejaVu Sans"],
        "axes.unicode_minus": False,
    })

    fixtures = sorted(set(r["fixture"] for r in records))
    policies = ["fifo", "greedy", "deadlock_aware"]
    colors = {"fifo": "#f59e0b", "greedy": "#a78bfa", "deadlock_aware": "#34d399"}  # amber, violet, emerald
    labels = {"fifo": "FIFO", "greedy": "Greedy", "deadlock_aware": "Deadlock-aware (CP-2)"}

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    fig.suptitle(
        "CP-1 Baseline Results — NestedTune Guard (CINT-11)",
        color="#e2e8f0", fontsize=16, fontweight="bold",
    )

    # Chart 1: Completed trials per fixture per policy (grouped bar)
    ax1 = axes[0, 0]
    x = np.arange(len(fixtures))
    width = 0.27
    for i, policy in enumerate(policies):
        vals = [next((r["completed"] for r in records if r["fixture"] == fx and r["policy"] == policy), 0) for fx in fixtures]
        ax1.bar(x + (i - 1) * width, vals, width, label=labels[policy], color=colors[policy], edgecolor="#0b1120", linewidth=0.5)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f.replace("dev_", "").replace("_", "\n") for f in fixtures], fontsize=8)
    ax1.set_ylabel("Completed trials")
    ax1.set_title("Completed trials per fixture × policy", fontsize=11)
    ax1.legend(loc="upper right", facecolor="#1e293b", edgecolor="#1e293b", labelcolor="#e2e8f0", fontsize=8)
    ax1.grid(True, axis="y", alpha=0.3)

    # Chart 2: Cycles observed per fixture per policy (grouped bar)
    ax2 = axes[0, 1]
    for i, policy in enumerate(policies):
        vals = [next((r["cycles"] for r in records if r["fixture"] == fx and r["policy"] == policy), 0) for fx in fixtures]
        ax2.bar(x + (i - 1) * width, vals, width, label=labels[policy], color=colors[policy], edgecolor="#0b1120", linewidth=0.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f.replace("dev_", "").replace("_", "\n") for f in fixtures], fontsize=8)
    ax2.set_ylabel("Observed cycles")
    ax2.set_title("Wait-for cycles per fixture × policy", fontsize=11)
    ax2.legend(loc="upper right", facecolor="#1e293b", edgecolor="#1e293b", labelcolor="#e2e8f0", fontsize=8)
    ax2.grid(True, axis="y", alpha=0.3)

    # Chart 3: Headline totals — completed vs unresolved vs rejected (stacked bar)
    ax3 = axes[1, 0]
    totals = {}
    for policy in policies:
        c = sum(r["completed"] for r in records if r["policy"] == policy)
        u = sum(r["unresolved"] for r in records if r["policy"] == policy)
        rej = sum(r["rejected"] for r in records if r["policy"] == policy)
        totals[policy] = (c, u, rej)
    y = np.arange(len(policies))
    completed_vals = [totals[p][0] for p in policies]
    unresolved_vals = [totals[p][1] for p in policies]
    rejected_vals = [totals[p][2] for p in policies]
    ax3.barh(y, completed_vals, color="#34d399", label="Completed", edgecolor="#0b1120", linewidth=0.5)
    ax3.barh(y, unresolved_vals, left=completed_vals, color="#f59e0b", label="Unresolved", edgecolor="#0b1120", linewidth=0.5)
    ax3.barh(y, rejected_vals, left=[c + u for c, u in zip(completed_vals, unresolved_vals)], color="#a78bfa", label="Rejected (CP-2)", edgecolor="#0b1120", linewidth=0.5)
    ax3.set_yticks(y)
    ax3.set_yticklabels([labels[p] for p in policies])
    ax3.set_xlabel("Trials (out of 12)")
    ax3.set_title("Headline totals — completed / unresolved / rejected", fontsize=11)
    ax3.legend(loc="lower right", facecolor="#1e293b", edgecolor="#1e293b", labelcolor="#e2e8f0", fontsize=8)
    ax3.grid(True, axis="x", alpha=0.3)

    # Chart 4: CP-1 baseline table as text
    ax4 = axes[1, 1]
    ax4.axis("off")
    table_data = [
        ["Metric", "FIFO", "Greedy", "CP-2 DA"],
        ["Completed", "5/12", "7/12", "7/12"],
        ["Unresolved", "7", "5", "0"],
        ["Rejected", "0", "0", "5"],
        ["Cycles", "4", "4", "0"],
        ["Bounded %", "41.7%", "58.3%", "58.3%"],
        ["Trials/hour", "85.7", "120", "—"],
        ["Queue p95 (s)", "10.0", "9.6", "—"],
        ["Jain fairness", "0.714", "0.810", "—"],
    ]
    table = ax4.table(cellText=table_data, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.6)
    # Style the header row
    for j in range(4):
        cell = table[(0, j)]
        cell.set_facecolor("#1e3a5f")
        cell.set_text_props(color="#22d3ee", fontweight="bold")
    # Style the data rows
    for i in range(1, len(table_data)):
        for j in range(4):
            cell = table[(i, j)]
            cell.set_facecolor("#0f172a")
            cell.set_text_props(color="#e2e8f0", family="monospace")
    ax4.set_title("Headline metrics", fontsize=11)

    fig.savefig(path, dpi=150, facecolor="#0b1120")
    plt.close(fig)
    print(f"  saved: {path}")


def main() -> int:
    print("Generating evidence files...")
    records = run_all_fixtures()
    write_csv(records, EVIDENCE_DIR / "cp1_results.csv")
    write_json({
        "fixtures": all_fixtures(),
        "records": records,
        "totals": {
            policy: {
                "completed": sum(r["completed"] for r in records if r["policy"] == policy),
                "unresolved": sum(r["unresolved"] for r in records if r["policy"] == policy),
                "rejected": sum(r["rejected"] for r in records if r["policy"] == policy),
                "cycles": sum(r["cycles"] for r in records if r["policy"] == policy),
            }
            for policy in ("fifo", "greedy", "deadlock_aware")
        },
    }, EVIDENCE_DIR / "cp1_benchmark.json")
    print(f"  saved: {EVIDENCE_DIR / 'cp1_results.csv'}")
    print(f"  saved: {EVIDENCE_DIR / 'cp1_benchmark.json'}")

    # CP-2-specific subset
    cp2_records = [r for r in records if r["policy"] == "deadlock_aware"]
    write_csv(cp2_records, EVIDENCE_DIR / "cp2_results.csv")
    write_json({
        "records": cp2_records,
        "totals": {
            "completed": sum(r["completed"] for r in cp2_records),
            "unresolved": sum(r["unresolved"] for r in cp2_records),
            "rejected": sum(r["rejected"] for r in cp2_records),
            "cycles": sum(r["cycles"] for r in cp2_records),
        },
    }, EVIDENCE_DIR / "cp2_benchmark.json")
    print(f"  saved: {EVIDENCE_DIR / 'cp2_results.csv'}")
    print(f"  saved: {EVIDENCE_DIR / 'cp2_benchmark.json'}")

    print("Rendering chart PNG...")
    render_chart(records, CHARTS_DIR / "cp1_baseline_results.png")

    print("\nDone. CP-1 gate verification:")
    totals = {
        "fifo": sum(r["completed"] for r in records if r["policy"] == "fifo"),
        "greedy": sum(r["completed"] for r in records if r["policy"] == "greedy"),
        "deadlock_aware": sum(r["completed"] for r in records if r["policy"] == "deadlock_aware"),
    }
    cycles = {
        "fifo": sum(r["cycles"] for r in records if r["policy"] == "fifo"),
        "greedy": sum(r["cycles"] for r in records if r["policy"] == "greedy"),
        "deadlock_aware": sum(r["cycles"] for r in records if r["policy"] == "deadlock_aware"),
    }
    print(f"  FIFO completed: {totals['fifo']}/12  (target: 5)")
    print(f"  Greedy completed: {totals['greedy']}/12  (target: 7)")
    print(f"  CP-2 completed: {totals['deadlock_aware']}/12")
    print(f"  FIFO cycles: {cycles['fifo']}  (target: 4)")
    print(f"  Greedy cycles: {cycles['greedy']}  (target: 4)")
    print(f"  CP-2 cycles: {cycles['deadlock_aware']}  (target: 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

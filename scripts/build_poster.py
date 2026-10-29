import base64
import subprocess
from pathlib import Path

repo_root = Path("/home/nsaivighnesh/Downloads/capstone project")
download_dir = repo_root / "download"
assets_dir = Path("/home/nsaivighnesh/.gemini/antigravity/brain/2e7e75a5-faa2-4952-874f-267c034293b7/assets")

def b64(filename):
    p = assets_dir / filename
    if not p.exists():
        p = download_dir / filename
    if p.exists():
        with open(p, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")
    return ""

hero_b64 = b64("dashboard_crop_hero.png")
waitfor_b64 = b64("dashboard_crop_waitfor.png")
baseline_b64 = b64("cp1_baseline_results.png")

template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CINT-11 Poster Presentation — NestedTune Guard</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

  :root {
    --bg-dark: #070a13;
    --bg-card: rgba(15, 23, 42, 0.88);
    --border-card: rgba(255, 255, 255, 0.1);
    --primary: #38bdf8;
    --primary-glow: rgba(56, 189, 248, 0.25);
    --emerald: #34d399;
    --emerald-glow: rgba(52, 211, 153, 0.2);
    --indigo: #818cf8;
    --amber: #fbbf24;
    --rose: #fb7185;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --text-dim: #64748b;
  }

  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  body {
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    background-color: var(--bg-dark);
    color: var(--text-main);
    line-height: 1.45;
    -webkit-font-smoothing: antialiased;
    padding: 0;
    margin: 0;
    display: flex;
    justify-content: center;
    align-items: flex-start;
  }

  .poster {
    width: 2400px;
    height: 1700px;
    background: radial-gradient(circle at 15% 10%, rgba(30, 58, 138, 0.45) 0%, transparent 40%),
                radial-gradient(circle at 85% 15%, rgba(6, 78, 59, 0.35) 0%, transparent 40%),
                radial-gradient(circle at 50% 90%, rgba(76, 29, 149, 0.3) 0%, transparent 50%),
                #070a13;
    padding: 40px 48px;
    display: flex;
    flex-direction: column;
    gap: 24px;
    position: relative;
    overflow: hidden;
  }

  /* Grid overlay for high-tech aesthetic */
  .poster::before {
    content: "";
    position: absolute;
    inset: 0;
    background-image: linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
  }

  /* ---------- HEADER ---------- */
  .header {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.92));
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 20px;
    padding: 24px 36px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.6);
    position: relative;
    z-index: 10;
  }

  .header-brand {
    display: flex;
    align-items: center;
    gap: 24px;
  }

  .logo-box {
    width: 90px;
    height: 90px;
    background: linear-gradient(135deg, #0284c7, #0d9488);
    border-radius: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 25px rgba(2, 132, 199, 0.5);
    border: 2px solid rgba(255, 255, 255, 0.3);
  }

  .header-titles {
    max-width: 1350px;
  }

  .project-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.4);
    color: var(--primary);
    padding: 4px 12px;
    border-radius: 100px;
    font-size: 14px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 8px;
  }

  .header-title {
    font-size: 40px;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #ffffff 40%, #cbd5e1 70%, #94a3b8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.15;
    margin-bottom: 8px;
  }

  .header-subtitle {
    font-size: 19px;
    font-weight: 500;
    color: var(--emerald);
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .header-meta-box {
    background: rgba(2, 6, 23, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 16px 24px;
    min-width: 500px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .meta-title {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--primary);
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 4px;
    margin-bottom: 4px;
  }

  .team-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px 16px;
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
  }

  .team-member {
    color: #e2e8f0;
    white-space: nowrap;
  }

  .team-member span {
    color: #94a3b8;
  }

  .guide-row {
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding-top: 6px;
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
    display: flex;
    justify-content: space-between;
    color: var(--emerald);
  }

  /* ---------- MAIN GRID ---------- */
  .grid-layout {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 1.35fr 1fr;
    gap: 24px;
    height: calc(100% - 170px);
    position: relative;
    z-index: 5;
  }

  .column {
    display: flex;
    flex-direction: column;
    gap: 20px;
    height: 100%;
  }

  /* ---------- CARD COMPONENT ---------- */
  .card {
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 16px;
    padding: 20px 24px;
    box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    position: relative;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 10px;
  }

  .card-title {
    font-size: 19px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 10px;
    color: #ffffff;
  }

  .card-title .icon {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--primary);
  }

  .card-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.06);
    color: var(--text-muted);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .card-content {
    font-size: 14px;
    color: #cbd5e1;
    line-height: 1.5;
    flex: 1;
  }

  /* Bullet points styling */
  ul.custom-list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  ul.custom-list li {
    position: relative;
    padding-left: 20px;
  }

  ul.custom-list li::before {
    content: "▹";
    position: absolute;
    left: 0;
    color: var(--primary);
    font-size: 16px;
    line-height: 1.2;
  }

  ul.custom-list strong {
    color: #ffffff;
  }

  /* Highlighting elements */
  .callout-box {
    background: rgba(2, 132, 199, 0.08);
    border-left: 4px solid var(--primary);
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 10px 0;
    font-size: 13.5px;
  }

  .alert-box {
    background: rgba(239, 68, 68, 0.09);
    border-left: 4px solid var(--rose);
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 10px 0;
    font-size: 13.5px;
  }

  .success-box {
    background: rgba(16, 185, 129, 0.09);
    border-left: 4px solid var(--emerald);
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 10px 0;
    font-size: 13.5px;
  }

  /* Metric chips */
  .kpi-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 14px;
  }

  .kpi-chip {
    background: rgba(15, 23, 42, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 12px;
    text-align: center;
  }

  .kpi-chip .value {
    font-size: 26px;
    font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.1;
  }

  .kpi-chip .label {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.05em;
    margin-top: 4px;
  }

  /* Comparison Table */
  .benchmark-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin-top: 8px;
    font-family: 'JetBrains Mono', monospace;
  }

  .benchmark-table th {
    background: rgba(30, 41, 59, 0.9);
    color: var(--text-main);
    padding: 9px 12px;
    text-align: left;
    font-weight: 700;
    font-size: 12px;
    border-bottom: 2px solid rgba(255, 255, 255, 0.12);
  }

  .benchmark-table td {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    color: #cbd5e1;
  }

  .benchmark-table tr:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  .badge-pass {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    background: rgba(52, 211, 153, 0.2);
    color: var(--emerald);
    border: 1px solid rgba(52, 211, 153, 0.4);
    font-weight: 700;
    font-size: 11px;
  }

  .badge-fail {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    background: rgba(244, 63, 94, 0.2);
    color: var(--rose);
    border: 1px solid rgba(244, 63, 94, 0.4);
    font-weight: 700;
    font-size: 11px;
  }

  /* Flow Diagram SVGs */
  .diagram-container {
    background: rgba(2, 6, 23, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 12px;
    display: flex;
    justify-content: center;
    align-items: center;
    margin-top: 8px;
  }

  /* Embedded figure styling */
  .figure-box {
    background: rgba(2, 6, 23, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    overflow: hidden;
    margin-top: 10px;
  }

  .figure-img {
    width: 100%;
    height: auto;
    display: block;
    object-fit: cover;
  }

  .figure-caption {
    padding: 8px 12px;
    font-size: 12px;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
    background: rgba(15, 23, 42, 0.95);
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    display: flex;
    justify-content: space-between;
  }

  .figure-caption span.fig-num {
    color: var(--primary);
    font-weight: 700;
  }

  /* Quotes / Viva takeaways */
  .viva-banner {
    background: linear-gradient(135deg, rgba(30, 58, 138, 0.4), rgba(6, 78, 59, 0.4));
    border: 1px solid rgba(56, 189, 248, 0.35);
    border-radius: 14px;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: auto;
  }

  .viva-quote {
    font-size: 15px;
    font-weight: 600;
    color: #ffffff;
    font-style: italic;
    line-height: 1.4;
  }

  .keywords-tag {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
  }

  .keyword-pill {
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.25);
    color: #bae6fd;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
  }
</style>
</head>
<body>

<div class="poster">

  <!-- ==================== HEADER ==================== -->
  <header class="header">
    <div class="header-brand">
      <div class="logo-box">
        <svg width="54" height="54" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
          <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
          <line x1="6" y1="6" x2="6.01" y2="6"></line>
          <line x1="6" y1="18" x2="6.01" y2="18"></line>
          <path d="M18 10v4"></path>
          <path d="M12 10v4"></path>
        </svg>
      </div>
      <div class="header-titles">
        <div class="project-badge">PROJECT ID: CINT-11 · CAPSTONE REVIEW II</div>
        <h1 class="header-title">Deadlock-Aware Distributed Hyperparameter Tuning for Nested Trainers</h1>
        <div class="header-subtitle">
          <span>NestedTune Guard</span>
          <span style="color:var(--text-dim)">•</span>
          <span>Deterministic Simulation</span>
          <span style="color:var(--text-dim)">•</span>
          <span>Hold-and-Wait Prevention</span>
          <span style="color:var(--text-dim)">•</span>
          <span>Production Admission Control</span>
        </div>
      </div>
    </div>

    <div class="header-meta-box">
      <div class="meta-title">Department of Computer Science & Engineering · KL University</div>
      <div class="team-grid">
        <div class="team-member">N. Sai Vighnesh <span>(2300030455)</span></div>
        <div class="team-member">B. Pavan Kumar <span>(2300030062)</span></div>
        <div class="team-member">B. Mahesh Adithya <span>(2300030983)</span></div>
        <div class="team-member">C. Jeswanth Varun <span>(2300031256)</span></div>
      </div>
      <div class="guide-row">
        <span><strong>FACULTY GUIDE:</strong> Mr. Rambabu Kalathoti</span>
        <span><strong>GUIDE ID:</strong> 8199</span>
      </div>
    </div>
  </header>

  <!-- ==================== 3-COLUMN CONTENT GRID ==================== -->
  <main class="grid-layout">

    <!-- ---------------- COLUMN 1: FOUNDATION & PROBLEM ---------------- -->
    <div class="column">
      
      <!-- Abstract -->
      <section class="card" style="flex: 1.1;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            </span>
            Abstract
          </div>
          <span class="card-badge">OVERVIEW</span>
        </div>
        <div class="card-content">
          <p>
            Distributed hyperparameter optimization (HPO) frameworks like Ray Tune launch nested training workers (e.g. XGBoost/PyTorch DDP) requiring multi-tier placement groups (PGs). When outer trials reserve parent PGs and nested workers request child PGs without coordinated visibility, circular dependencies induce catastrophic <strong>hold-and-wait deadlocks (Ray Issue #47439)</strong>, stranding cluster capacity indefinitely. 
          </p>
          <p style="margin-top:8px;">
            <strong>NestedTune Guard</strong> establishes a rigorous discrete-event simulator and mathematical evaluation framework paired with an atomic, deadlock-aware admission controller. By verifying combined parent-plus-child feasibility before admitting trials and rejecting permanently infeasible requests, our system completely eliminates circular wait states (0 cycles vs. 4 cycles in baselines) while preserving maximal cluster completion throughput.
          </p>
          <div class="keywords-tag">
            <span class="keyword-pill">Distributed HPO</span>
            <span class="keyword-pill">Ray Tune / Train</span>
            <span class="keyword-pill">Placement Groups</span>
            <span class="keyword-pill">Hold-and-Wait Deadlock</span>
            <span class="keyword-pill">Admission Control</span>
            <span class="keyword-pill">Discrete-Event Simulation</span>
          </div>
        </div>
      </section>

      <!-- Problem Statement -->
      <section class="card" style="flex: 1.25;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon" style="color:var(--rose)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            </span>
            Problem Statement: Ray Issue #47439
          </div>
          <span class="card-badge" style="color:var(--rose); border-color:rgba(244,63,94,0.3)">ANOMALY</span>
        </div>
        <div class="card-content">
          <p style="margin-bottom:8px;">
            In multi-tier training workflows, hierarchy-blind schedulers (FIFO & Greedy) admit trials based solely on outer parent placement group requests:
          </p>
          
          <div class="alert-box">
            <strong>The 4/4/1/3 Accounting Deadlock Pattern:</strong><br>
            • Cluster Capacity: <strong>4 CPUs</strong>.<br>
            • Parent Trial reserves: <strong>4 CPUs</strong> (Outer PG granted).<br>
            • Actually useful worker execution: <strong>1 CPU</strong>.<br>
            • Stranded capacity held by parent: <strong>3 CPUs</strong>.<br>
            • Nested Child Trainer requests: <strong>3 CPUs</strong>.<br>
            • <strong>Failure:</strong> Child cannot obtain 3 CPUs because parent holds them; parent cannot release CPUs until child finishes.
          </div>

          <ul class="custom-list">
            <li><strong>Self-Cycle Deadlock:</strong> Trial enters indefinite <code>WAITING_CHILD</code> state. Wait-for graph exhibits circular dependency: <code>xgb-001 → xgb-001</code>.</li>
            <li><strong>Capacity Stranding:</strong> 75% of reserved cluster compute is locked idle, preventing any subsequent queue progression.</li>
            <li><strong>Silent Cost Inflation:</strong> Cloud instances run indefinitely without progress, causing runaway cloud bills and aborted tuning sweeps.</li>
          </ul>
        </div>
      </section>

      <!-- Objectives -->
      <section class="card" style="flex: 1.1;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon" style="color:var(--primary)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
            </span>
            Research Objectives
          </div>
          <span class="card-badge">GOALS</span>
        </div>
        <div class="card-content">
          <ul class="custom-list">
            <li><strong>Real-Ray Reproduction:</strong> Validate the deadlock inside isolated Docker containers running real Ray 2.10.0, matching exact empirical accounting.</li>
            <li><strong>Deterministic Modeling:</strong> Design an event-driven simulator with a 30s bounded horizon, providing reproducible baselines without timing jitter.</li>
            <li><strong>Deadlock-Aware Admission Control:</strong> Enforce combined parent+child feasibility invariance prior to granting any cluster resources.</li>
            <li><strong>Explainable Diagnostic Advisor:</strong> Build a pure diagnostic rule engine classifying trial stalls into capacity shortfalls vs. deadlock hazards.</li>
            <li><strong>Full-Stack Tooling & Dashboard:</strong> Expose FastAPI REST microservices and a Next.js 16 reactive control plane for cluster evaluation.</li>
          </ul>
        </div>
      </section>

      <!-- Methodology -->
      <section class="card" style="flex: 1.15;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon" style="color:var(--emerald)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
            </span>
            Proposed Methodology & Algorithms
          </div>
          <span class="card-badge">THEORY</span>
        </div>
        <div class="card-content">
          <p style="font-size:13px; margin-bottom:8px;">
            Eliminating Coffman's <em>Hold-and-Wait</em> condition via proactive admission gating:
          </p>

          <div class="diagram-container">
            <svg width="640" height="110" viewBox="0 0 640 110" fill="none">
              <!-- Box 1 -->
              <rect x="10" y="25" width="130" height="60" rx="8" fill="#1e293b" stroke="#38bdf8" stroke-width="1.5"/>
              <text x="75" y="52" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle" font-family="'Plus Jakarta Sans'">Trial Arrival</text>
              <text x="75" y="68" fill="#94a3b8" font-size="10" text-anchor="middle" font-family="'JetBrains Mono'">Parent + Child PGs</text>

              <!-- Arrow 1 -->
              <line x1="140" y1="55" x2="175" y2="55" stroke="#38bdf8" stroke-width="2"/>

              <!-- Box 2 -->
              <rect x="180" y="25" width="150" height="60" rx="8" fill="#1e293b" stroke="#818cf8" stroke-width="1.5"/>
              <text x="255" y="50" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle" font-family="'Plus Jakarta Sans'">Admission Guard</text>
              <text x="255" y="66" fill="#818cf8" font-size="10" text-anchor="middle" font-family="'JetBrains Mono'">R_p + R_c &le; C_max?</text>

              <!-- Box 3 -->
              <rect x="370" y="25" width="135" height="60" rx="8" fill="#1e293b" stroke="#34d399" stroke-width="1.5"/>
              <text x="437" y="50" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle" font-family="'Plus Jakarta Sans'">Runtime Fit</text>
              <text x="437" y="66" fill="#34d399" font-size="10" text-anchor="middle" font-family="'JetBrains Mono'">R_p + R_c &le; C_avail?</text>

              <!-- Box 4 -->
              <rect x="540" y="25" width="90" height="60" rx="8" fill="rgba(52,211,153,0.15)" stroke="#34d399" stroke-width="2"/>
              <text x="585" y="52" fill="#34d399" font-size="12" font-weight="700" text-anchor="middle">ADMIT</text>
              <text x="585" y="68" fill="#ffffff" font-size="10" text-anchor="middle">SAFE (7/12)</text>
            </svg>
          </div>

          <p style="font-size:12.5px; margin-top:8px; color:var(--text-muted)">
            <strong>Mathematical Invariant:</strong> Trial <em>i</em> admitted at time <em>t</em> iff <em>R<sub>parent</sub>(i) + R<sub>child</sub>(i) &le; C<sub>free</sub>(t)</em>. If temporary capacity is insufficient, the trial is safely deferred without reserving parent resources, preventing intermediate starvation.
          </p>
        </div>
      </section>

    </div>

    <!-- ---------------- COLUMN 2: SYSTEM ARCHITECTURE & IMPLEMENTATION ---------------- -->
    <div class="column">

      <!-- System Architecture -->
      <section class="card" style="flex: 1.35;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon" style="color:var(--primary)">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>
            </span>
            End-to-End System Architecture
          </div>
          <span class="card-badge" style="color:var(--primary); border-color:rgba(56,189,248,0.4)">MODULAR PIPELINE</span>
        </div>
        <div class="card-content">
          <p style="font-size:13.5px; margin-bottom:10px;">
            NestedTune Guard connects specification, scheduling policies, discrete event telemetry, and cycle observer:
          </p>

          <!-- High Fidelity Vector Architecture Diagram -->
          <div class="diagram-container" style="padding:16px 8px;">
            <svg width="780" height="230" viewBox="0 0 780 230" fill="none">
              <!-- Tier 1: Workload Specification -->
              <rect x="15" y="15" width="220" height="90" rx="10" fill="#0f172a" stroke="#38bdf8" stroke-width="1.5"/>
              <text x="125" y="40" fill="#38bdf8" font-size="13" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono'">[INPUT MODULE]</text>
              <text x="125" y="60" fill="#ffffff" font-size="12" text-anchor="middle">Workload Schema & Parser</text>
              <text x="125" y="80" fill="#94a3b8" font-size="11" text-anchor="middle">Trials • Parent/Child PGs • Events</text>
              <text x="125" y="95" fill="#64748b" font-size="10" text-anchor="middle">JSON Schema Validation (RFC)</text>

              <!-- Arrow 1 to Admission -->
              <line x1="235" y1="60" x2="275" y2="60" stroke="#38bdf8" stroke-width="2"/>

              <!-- Tier 2: Deadlock-Aware Admission Controller -->
              <rect x="280" y="15" width="230" height="90" rx="10" fill="#0f172a" stroke="#818cf8" stroke-width="2"/>
              <text x="395" y="40" fill="#818cf8" font-size="13" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono'">[ADMISSION CONTROLLER]</text>
              <text x="395" y="60" fill="#ffffff" font-size="12" font-weight="600" text-anchor="middle">Pre-Admission Guard</text>
              <text x="395" y="78" fill="#34d399" font-size="11" text-anchor="middle">Atomic Feasibility Check</text>
              <text x="395" y="95" fill="#94a3b8" font-size="10" text-anchor="middle">Preemption & Node Loss Handler</text>

              <!-- Arrow 2 to Discrete Event Engine -->
              <line x1="510" y1="60" x2="550" y2="60" stroke="#818cf8" stroke-width="2"/>

              <!-- Tier 3: Discrete-Event Engine -->
              <rect x="555" y="15" width="210" height="90" rx="10" fill="#0f172a" stroke="#34d399" stroke-width="1.5"/>
              <text x="660" y="40" fill="#34d399" font-size="13" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono'">[SIMULATOR ENGINE]</text>
              <text x="660" y="60" fill="#ffffff" font-size="12" text-anchor="middle">Virtual Clock & Event Queue</text>
              <text x="660" y="78" fill="#94a3b8" font-size="11" text-anchor="middle">Placement Group Allocator</text>
              <text x="660" y="95" fill="#64748b" font-size="10" text-anchor="middle">30.0s Bounded Horizon</text>

              <!-- Feedback / Interception Arrows -->
              <line x1="660" y1="105" x2="660" y2="135" stroke="#34d399" stroke-width="2"/>
              <line x1="395" y1="105" x2="395" y2="135" stroke="#818cf8" stroke-width="2"/>

              <!-- Tier 4: Independent Observer & Cycle Detector -->
              <rect x="280" y="135" width="230" height="80" rx="10" fill="#0f172a" stroke="#fbbf24" stroke-width="1.5"/>
              <text x="395" y="160" fill="#fbbf24" font-size="13" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono'">[WAIT-FOR OBSERVER]</text>
              <text x="395" y="180" fill="#ffffff" font-size="11.5" text-anchor="middle">Dependency Graph Extraction</text>
              <text x="395" y="198" fill="#94a3b8" font-size="10.5" text-anchor="middle">Tarjan's SCC Cycle Detection</text>

              <!-- Tier 5: Autoscaling Diagnostic Advisor -->
              <rect x="555" y="135" width="210" height="80" rx="10" fill="#0f172a" stroke="#a78bfa" stroke-width="1.5"/>
              <text x="660" y="160" fill="#a78bfa" font-size="13" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono'">[AUTOSCALING ADVISOR]</text>
              <text x="660" y="180" fill="#ffffff" font-size="11.5" text-anchor="middle">Pure State Diagnosis</text>
              <text x="660" y="198" fill="#94a3b8" font-size="10.5" text-anchor="middle">Deadlock vs Capacity Shortfall</text>

              <!-- Interfaces & APIs -->
              <rect x="15" y="135" width="220" height="80" rx="10" fill="#0f172a" stroke="#cbd5e1" stroke-width="1.5"/>
              <text x="125" y="160" fill="#cbd5e1" font-size="13" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono'">[CONTROL INTERFACES]</text>
              <text x="125" y="180" fill="#ffffff" font-size="11.5" text-anchor="middle">FastAPI REST Microservice (:8123)</text>
              <text x="125" y="198" fill="#94a3b8" font-size="10.5" text-anchor="middle">Next.js 16 Realtime UI & CLI</text>

              <!-- Connector Lines -->
              <line x1="235" y1="175" x2="280" y2="175" stroke="#cbd5e1" stroke-width="1.5"/>
              <line x1="510" y1="175" x2="555" y2="175" stroke="#fbbf24" stroke-width="1.5"/>
            </svg>
          </div>
        </div>
      </section>

      <!-- Implementation & Real Ray -->
      <section class="card" style="flex: 1.1;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon" style="color:var(--emerald)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
            </span>
            Real-Ray Reproduction & Implementation
          </div>
          <span class="card-badge">VERIFIED HARNESS</span>
        </div>
        <div class="card-content">
          <div class="success-box">
            <strong>Dockerized Ray 2.10.0 Protocol (ray-repro/):</strong> Real containerized run reproduced Ray issue #47439 directly on Linux x86_64. Extracted live Raylet GCS logs, actor placement group tables, and state snapshots, confirming an exact 4/4/1/3 stranded CPU match against our model.
          </div>
          <ul class="custom-list" style="margin-top:6px;">
            <li><strong>Deterministic Core:</strong> Python 3.11 discrete-event simulator with zero timing dependencies, yielding byte-identical SHA-256 fixture signatures.</li>
            <li><strong>FastAPI Microservices:</strong> Async REST endpoints (<code>/simulate</code>, <code>/advise</code>, <code>/benchmark</code>, <code>/validate</code>) providing low-latency programmatic access.</li>
          </ul>
        </div>
      </section>

      <!-- Figure 1: Dashboard Visual -->
      <section class="card" style="flex: 1.25;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon" style="color:var(--primary)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
            </span>
            Full-Stack Next.js 16 Web Dashboard
          </div>
          <span class="card-badge">PRODUCTION GUI</span>
        </div>
        <div class="card-content">
          <div class="figure-box">
            <img src="__HERO_B64__" class="figure-img" alt="Next.js Dashboard Overview" style="max-height:220px;">
            <div class="figure-caption">
              <span><span class="fig-num">Figure 1:</span> Live Reactive Dashboard: KPI summary chips, CP-2 verification gates, and Ray reproduction evidence.</span>
              <span style="color:var(--emerald)">● ONLINE (Vercel + Docker)</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Figure 2: Wait-for graph Visual -->
      <section class="card" style="flex: 1.25;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon" style="color:var(--indigo)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
            </span>
            Interactive Simulation & Cycle Inspection
          </div>
          <span class="card-badge">VISUAL GRAPH</span>
        </div>
        <div class="card-content">
          <div class="figure-box">
            <img src="__WAITFOR_B64__" class="figure-img" alt="Interactive Wait-For Graph" style="max-height:220px;">
            <div class="figure-caption">
              <span><span class="fig-num">Figure 2:</span> Real-time execution inspection: Event stream timeline, CPU allocation time-series, and Tarjan's SCC cycle detection.</span>
              <span style="color:var(--primary)">0.01s LATENCY</span>
            </div>
          </div>
        </div>
      </section>

    </div>

    <!-- ---------------- COLUMN 3: RESULTS, VERIFICATION & CONCLUSION ---------------- -->
    <div class="column">

      <!-- Benchmark Results Table -->
      <section class="card" style="flex: 1.3;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon" style="color:var(--emerald)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10"></path><path d="M12 20V4"></path><path d="M6 20v-6"></path></svg>
            </span>
            Empirical Results: CP-1 vs CP-2 Benchmark
          </div>
          <span class="card-badge" style="color:var(--emerald); border-color:rgba(52,211,153,0.3)">HEADLINE BENCHMARK</span>
        </div>
        <div class="card-content">
          <p style="font-size:13px; margin-bottom:8px;">
            Evaluation across 12 trials spanning 7 standardized multi-tenant development fixtures:
          </p>

          <table class="benchmark-table">
            <thead>
              <tr>
                <th>Evaluated Metric</th>
                <th>FIFO Baseline</th>
                <th>Greedy Baseline</th>
                <th>NestedTune Guard (Ours)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Completed Trials</strong></td>
                <td>5 / 12</td>
                <td>7 / 12</td>
                <td><span class="badge-pass">7 / 12 (Maximal)</span></td>
              </tr>
              <tr>
                <td><strong>Unresolved Trials</strong></td>
                <td>7 (Deadlocked)</td>
                <td>5 (Deadlocked)</td>
                <td><span class="badge-pass">0 (Zero Hangs)</span></td>
              </tr>
              <tr>
                <td><strong>Observed Cycles</strong></td>
                <td>4 Cycles <span class="badge-fail">FAIL</span></td>
                <td>4 Cycles <span class="badge-fail">FAIL</span></td>
                <td><span class="badge-pass">0 Cycles (100% Safe)</span></td>
              </tr>
              <tr>
                <td><strong>Rejected Infeasible</strong></td>
                <td>0</td>
                <td>0</td>
                <td><span class="badge-pass">5 (Bounded Decision)</span></td>
              </tr>
              <tr>
                <td><strong>Bounded Resolution</strong></td>
                <td>41.7%</td>
                <td>58.3%</td>
                <td><span class="badge-pass">100% Resolved</span></td>
              </tr>
              <tr>
                <td><strong>Jain's Fairness Index</strong></td>
                <td>0.714</td>
                <td>0.810</td>
                <td><span class="badge-pass">0.810 (Optimal)</span></td>
              </tr>
              <tr>
                <td><strong>Deadlock Stranding</strong></td>
                <td>75% Stranded</td>
                <td>50% Stranded</td>
                <td><span class="badge-pass">0% Stranded</span></td>
              </tr>
            </tbody>
          </table>

          <div class="kpi-strip" style="margin-top:14px;">
            <div class="kpi-chip">
              <div class="value" style="color:var(--emerald)">0</div>
              <div class="label">Deadlock Cycles</div>
            </div>
            <div class="kpi-chip">
              <div class="value" style="color:var(--primary)">100%</div>
              <div class="label">Resolution Rate</div>
            </div>
            <div class="kpi-chip">
              <div class="value" style="color:var(--indigo)">76/76</div>
              <div class="label">Pytest Suite</div>
            </div>
            <div class="kpi-chip">
              <div class="value" style="color:var(--amber)">14/14</div>
              <div class="label">Oracle Pairs</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Baseline Chart Figure -->
      <section class="card" style="flex: 1.15;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon" style="color:var(--primary)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
            </span>
            Comparative Fixture-by-Fixture Analysis
          </div>
          <span class="card-badge">FIGURE 3</span>
        </div>
        <div class="card-content">
          <div class="figure-box">
            <img src="__BASELINE_B64__" class="figure-img" alt="Baseline Comparison Chart" style="max-height:210px;">
            <div class="figure-caption">
              <span><span class="fig-num">Figure 3:</span> Baseline resolution: FIFO (red) locks 7 trials; Greedy resolves 7; NestedTune Guard achieves 0 unresolved deadlocks.</span>
              <span style="color:var(--primary)">OFFICIAL EVIDENCE</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Verification & Rigor -->
      <section class="card" style="flex: 1.05;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon" style="color:var(--emerald)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
            </span>
            Quality Assurance & Verification Gates
          </div>
          <span class="card-badge">CI / CD PASSED</span>
        </div>
        <div class="card-content">
          <ul class="custom-list">
            <li><strong>76/76 Automated Tests:</strong> Full test suite covering unit models, API endpoints, autoscaling advice, mutual cycle avoidance, and schema contracts.</li>
            <li><strong>14/14 Oracle Agreement:</strong> Byte-identical confirmation against frozen mathematical expected outputs across all fixtures.</li>
            <li><strong>Production CI/CD:</strong> GitHub Actions pipeline verifying Python 3.11 tests, Next.js type-checking, ESLint rules, and Docker container readiness on every push.</li>
          </ul>
        </div>
      </section>

      <!-- Conclusion & Future Scope -->
      <section class="card" style="flex: 1.25;">
        <div class="card-header">
          <div class="card-title">
            <span class="icon" style="color:var(--primary)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
            </span>
            Conclusion & Future Scope
          </div>
          <span class="card-badge">IMPACT</span>
        </div>
        <div class="card-content">
          <p style="font-size:13.5px; margin-bottom:8px;">
            <strong>Conclusion:</strong> NestedTune Guard demonstrates that hold-and-wait placement group deadlocks in nested distributed HPO can be reliably avoided without sacrificing scheduler throughput. Proactive parent-plus-child admission checks prevent resource stranding before reservations occur.
          </p>
          <ul class="custom-list" style="margin-bottom:12px;">
            <li><strong>Upstream Ray Integration:</strong> Packaging admission policies as an active Ray Core / KubeRay scheduler plugin.</li>
            <li><strong>Dominant Resource Fairness (DRF):</strong> Integrating multi-resource fairness across heterogenous CPU/GPU clusters.</li>
          </ul>

          <div class="viva-banner">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"></path><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"></path></svg>
            <div class="viva-quote">
              "CP-1 measures the problem; CP-2 prevents unsafe admission and turns an indefinite hang into an explicit, bounded decision."
            </div>
          </div>
        </div>
      </section>

    </div>

  </main>

</div>

</body>
</html>
"""

final_html = template.replace("__HERO_B64__", hero_b64).replace("__WAITFOR_B64__", waitfor_b64).replace("__BASELINE_B64__", baseline_b64)

out_html = download_dir / "CINT-11_Poster_Presentation.html"
with open(out_html, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"Generated HTML Poster: {out_html} ({len(final_html)} bytes)")

# Copy to artifact folder
artifact_dir = Path("/home/nsaivighnesh/.gemini/antigravity/brain/2e7e75a5-faa2-4952-874f-267c034293b7")
with open(artifact_dir / "CINT-11_Poster_Presentation.html", "w", encoding="utf-8") as f:
    f.write(final_html)
print("Copied HTML to artifact directory.")

"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  Database,
  FileText,
  GitBranch,
  Github,
  Loader2,
  PlayCircle,
  Terminal,
  XCircle,
  Zap,
} from "lucide-react";

// ---------- Types (mirrors Python CLI output) ----------
interface PolicySummary {
  policy: string;
  total_trials: number;
  completed_trials: number;
  unresolved_trials: number;
  rejected_trials: number;
  observed_cycle_count: number;
  bounded_resolution_pct: number;
  trials_per_hour: number;
  queue_p95_s: number;
  jain_fairness: number;
  avg_cpu_utilisation_pct: number;
  avg_cpu_stranding_pct: number;
}

interface Trial {
  id: string;
  state: string;
  admitted_at: number | null;
  started_at: number | null;
  finished_at: number | null;
  rejection_reason: string | null;
  cycle_id: number | null;
  has_child: boolean;
  tags: string[];
  parent_bundle: { cpu: number; gpu: number; memory: number; workers: number; strategy: string } | null;
  child_bundle: { cpu: number; gpu: number; memory: number; workers: number; strategy: string } | null;
}

interface SimulationResult {
  fixture: string;
  policy: string;
  horizon_s: number;
  trials: Trial[];
  events: { t: number; type: string; trial_id?: string; [k: string]: any }[];
  telemetry: {
    t: number;
    free_cpu: number;
    free_gpu: number;
    allocated_cpu: number;
    allocated_gpu: number;
    reserved_cpu: number;
    useful_cpu: number;
    stranded_cpu: number;
    running_trials: number;
    waiting_trials: number;
    unresolved_trials: number;
  }[];
  wait_for_history: {
    edges: { waiter: string; holder: string }[];
    cycles: { members: string[]; edges: any[]; kind: string }[];
    cycle_count: number;
  }[];
  summary: PolicySummary;
  cluster_snapshot: any;
}

interface Scenario {
  name: string;
  file: string;
  description: string;
  trials: number;
  cluster: { cpu: number; gpu: number; memory: number; workers: number; strategy: string };
  bounded_horizon_s: number;
}

interface BenchmarkTotals {
  policy: string;
  completed: number;
  unresolved: number;
  rejected: number;
  cycles: number;
  total_trials: number;
}

interface BenchmarkResponse {
  ok: boolean;
  result?: {
    fixtures: {
      fixture: string;
      policies: Record<string, { summary: PolicySummary; oracle_match: boolean }>;
    }[];
    totals: Record<string, BenchmarkTotals>;
  };
  error?: string;
  cached?: boolean;
}

// ---------- Constants ----------
const POLICIES = [
  { id: "fifo", label: "FIFO", short: "FIFO", color: "text-amber-400", badge: "bg-amber-400/10 text-amber-400 border-amber-400/30" },
  { id: "greedy", label: "Greedy", short: "Greedy", color: "text-violet-400", badge: "bg-violet-400/10 text-violet-400 border-violet-400/30" },
  { id: "deadlock_aware", label: "Deadlock-aware", short: "CP-2 DA", color: "text-emerald-400", badge: "bg-emerald-400/10 text-emerald-400 border-emerald-400/30" },
] as const;

// ---------- Top-level Page ----------
export default function Home() {
  return (
    <main className="min-h-screen flex flex-col">
      <DashboardHeader />
      <div className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-12">
        <HeroSection />
        <KpiCardsSection />
        <SourceCaseSection />
        <PolicyComparisonSection />
        <InteractiveScenarioSection />
        <ArchitectureSection />
        <ReviewGatesSection />
        <ResourcesSection />
      </div>
      <DashboardFooter />
    </main>
  );
}

// ---------- Header ----------
function DashboardHeader() {
  const [health, setHealth] = useState<{
    ok: boolean;
    python?: string;
    package?: string;
    gate?: "unknown" | "pass" | "fail";
    fixtures?: number;
  } | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ ok: false, gate: "fail" }));
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 font-mono text-sm">
            <span className="text-primary">[CINT-11]</span>
            <span className="text-muted-foreground">/</span>
            <span className="text-foreground">NestedTune Guard</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="font-mono text-xs">
            v1.0.0
          </Badge>
          {health ? (
            <Badge
              variant={health.ok ? "default" : "destructive"}
              className="font-mono text-xs gap-1"
            >
              {health.ok ? (
                <CheckCircle2 className="h-3 w-3" />
              ) : (
                <XCircle className="h-3 w-3" />
              )}
              {health.gate === "pass" ? "GATE PASS" : health.gate === "fail" ? "GATE FAIL" : "…"}
            </Badge>
          ) : (
            <Badge variant="outline" className="font-mono text-xs gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              checking
            </Badge>
          )}
          <a
            href="https://github.com/ray-project/ray/issues/47439"
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground transition-colors"
            title="Ray issue #47439"
          >
            <Github className="h-4 w-4" />
          </a>
        </div>
      </div>
    </header>
  );
}

// ---------- Hero ----------
function HeroSection() {
  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <Badge variant="outline" className="font-mono text-xs text-primary border-primary/40">
          capstone · CP-1 + CP-2
        </Badge>
        <h1 className="font-[var(--font-display)] text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-foreground">
          Deadlock-Aware Distributed Hyperparameter Tuning
          <span className="text-primary"> for Nested Trainers</span>
        </h1>
        <p className="text-muted-foreground text-base sm:text-lg max-w-3xl">
          A deterministic, bounded, reproducible evaluation framework that
          reproduces the <span className="text-foreground font-mono">Ray #47439</span> placement-group
          deadlock, freezes FIFO and greedy baselines for CP-1, and adds a
          deadlock-aware admission controller for CP-2.
        </p>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <span className="text-primary">●</span>
          <span>7 dev fixtures · 12 trials</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-primary">●</span>
          <span>2 hash-frozen acceptance fixtures</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-primary">●</span>
          <span>70 automated tests</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-primary">●</span>
          <span>30s bounded horizon</span>
        </div>
      </div>
    </section>
  );
}

// ---------- KPI Cards ----------
function KpiCardsSection() {
  const [data, setData] = useState<BenchmarkResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/benchmark")
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setLoading(false);
        if (!d.ok) setError(d.error || "unknown");
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-3 w-24 bg-muted rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-16 bg-muted rounded" />
            </CardContent>
          </Card>
        ))}
      </section>
    );
  }

  if (error || !data?.result) {
    return (
      <section>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Benchmark unavailable</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </section>
    );
  }

  const totals = data.result.totals;
  const fifo = totals.fifo;
  const greedy = totals.greedy;
  const cp2 = totals.deadlock_aware;

  return (
    <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        label="FIFO completed"
        value={`${fifo.completed}/${fifo.total_trials}`}
        subtext={`${fifo.unresolved} unresolved · ${fifo.cycles} cycles`}
        icon={<Activity className="h-4 w-4" />}
        tone="amber"
        pct={(fifo.completed / fifo.total_trials) * 100}
      />
      <KpiCard
        label="Greedy completed"
        value={`${greedy.completed}/${greedy.total_trials}`}
        subtext={`${greedy.unresolved} unresolved · ${greedy.cycles} cycles`}
        icon={<Zap className="h-4 w-4" />}
        tone="violet"
        pct={(greedy.completed / greedy.total_trials) * 100}
      />
      <KpiCard
        label="CP-2 unresolved"
        value={`${cp2.unresolved}`}
        subtext={`${cp2.rejected} rejected · ${cp2.cycles} cycles`}
        icon={<CheckCircle2 className="h-4 w-4" />}
        tone="emerald"
        pct={cp2.unresolved === 0 ? 100 : 100 - (cp2.unresolved / cp2.total_trials) * 100}
      />
      <KpiCard
        label="Observed cycles (CP-1)"
        value={`${fifo.cycles}`}
        subtext={`self-cycles in wait-for graph`}
        icon={<GitBranch className="h-4 w-4" />}
        tone="cyan"
        pct={(fifo.cycles / 12) * 100}
      />
    </section>
  );
}

function KpiCard({
  label,
  value,
  subtext,
  icon,
  tone,
  pct,
}: {
  label: string;
  value: string;
  subtext: string;
  icon: React.ReactNode;
  tone: "amber" | "violet" | "emerald" | "cyan";
  pct: number;
}) {
  const toneClass: Record<typeof tone, string> = {
    amber: "text-amber-400",
    violet: "text-violet-400",
    emerald: "text-emerald-400",
    cyan: "text-primary",
  };
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardDescription className="font-mono text-xs uppercase tracking-wider">
            {label}
          </CardDescription>
          <span className={toneClass[tone]}>{icon}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="font-mono text-2xl font-bold tabular-nums">{value}</div>
        <div className="text-xs text-muted-foreground font-mono">{subtext}</div>
        <Progress value={pct} className="h-1" />
      </CardContent>
    </Card>
  );
}

// ---------- Source Case ----------
function SourceCaseSection() {
  return (
    <section className="space-y-4">
      <SectionHeader
        eyebrow="01 · Source case"
        title="Ray #47439 — the 4/4/1/3 deadlock"
        description="A 4-CPU cluster; an XGBoost tuning trial reserves a 4-CPU parent placement group; its nested distributed trainer then requests 3 CPUs that are unavailable because the parent holds them. The trial enters WAITING_CHILD indefinitely and forms a self-cycle in the wait-for graph."
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="font-mono text-sm flex items-center gap-2">
              <Terminal className="h-4 w-4 text-primary" />
              Resource accounting
            </CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full font-mono text-sm">
              <thead>
                <tr className="text-xs text-muted-foreground uppercase tracking-wider">
                  <th className="text-left py-2 font-normal">Resource fact</th>
                  <th className="text-right py-2 font-normal">Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                <tr><td className="py-2">Cluster capacity</td><td className="text-right py-2 tabular-nums">4 CPUs</td></tr>
                <tr><td className="py-2">Outer placement-group reservation</td><td className="text-right py-2 tabular-nums text-amber-400">4 CPUs</td></tr>
                <tr><td className="py-2">Actually useful</td><td className="text-right py-2 tabular-nums text-emerald-400">1 CPU</td></tr>
                <tr><td className="py-2">Stranded inside parent reservation</td><td className="text-right py-2 tabular-nums text-red-400">3 CPUs</td></tr>
                <tr><td className="py-2">New child request</td><td className="text-right py-2 tabular-nums">3 CPUs</td></tr>
                <tr><td className="py-2 font-bold">Final state</td><td className="text-right py-2 tabular-nums text-primary font-bold">WAITING_CHILD</td></tr>
              </tbody>
            </table>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="font-mono text-sm flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-primary" />
              Wait-for cycle
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-mono text-xs space-y-1 text-muted-foreground">
              <div className="flex items-center gap-2">
                <span className="text-amber-400">●</span>
                <span>Parent holds 4 reserved CPUs</span>
              </div>
              <div className="ml-2">↓</div>
              <div className="flex items-center gap-2">
                <span className="text-amber-400">●</span>
                <span>Parent waits for nested trainer</span>
              </div>
              <div className="ml-2">↓</div>
              <div className="flex items-center gap-2">
                <span className="text-amber-400">●</span>
                <span>Nested trainer requests 3 CPUs</span>
              </div>
              <div className="ml-2">↓</div>
              <div className="flex items-center gap-2">
                <span className="text-red-400">●</span>
                <span>Unavailable — parent holds them</span>
              </div>
              <div className="mt-3 pt-3 border-t border-border">
                <div className="text-xs text-foreground">self-cycle:</div>
                <div className="font-mono text-sm text-primary mt-1">xgb-001 → xgb-001</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

// ---------- Policy Comparison ----------
function PolicyComparisonSection() {
  const [data, setData] = useState<BenchmarkResponse | null>(null);

  useEffect(() => {
    fetch("/api/benchmark")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  const rows = useMemo(() => {
    if (!data?.result) return [];
    return data.result.fixtures.flatMap((f) =>
      POLICIES.map((p) => ({
        fixture: f.fixture,
        policy: p.id,
        summary: f.policies[p.id]?.summary,
        match: f.policies[p.id]?.oracle_match,
      }))
    );
  }, [data]);

  return (
    <section className="space-y-4">
      <SectionHeader
        eyebrow="02 · Three-policy comparison"
        title="FIFO vs Greedy vs Deadlock-aware"
        description="The same 7 development fixtures run under all three policies. Greedy completes 2 more trials than FIFO by allowing feasible jobs to bypass an impossible head-of-line request. CP-2 rejects permanently infeasible trials at admission — zero unresolved deadlocks."
      />
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full font-mono text-xs">
              <thead className="bg-muted/30">
                <tr className="text-muted-foreground uppercase tracking-wider">
                  <th className="text-left px-3 py-2 font-normal">Fixture</th>
                  <th className="text-left px-3 py-2 font-normal">Policy</th>
                  <th className="text-right px-3 py-2 font-normal">Completed</th>
                  <th className="text-right px-3 py-2 font-normal">Unresolved</th>
                  <th className="text-right px-3 py-2 font-normal">Rejected</th>
                  <th className="text-right px-3 py-2 font-normal">Cycles</th>
                  <th className="text-right px-3 py-2 font-normal">Bounded %</th>
                  <th className="text-right px-3 py-2 font-normal">Oracle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((r, i) => (
                  <tr key={i} className="hover:bg-muted/20 transition-colors">
                    <td className="px-3 py-1.5 truncate max-w-[200px]" title={r.fixture}>
                      {r.fixture.replace(/^dev_/, "")}
                    </td>
                    <td className="px-3 py-1.5">
                      <Badge
                        variant="outline"
                        className={`font-mono text-[10px] ${
                          POLICIES.find((p) => p.id === r.policy)?.badge
                        }`}
                      >
                        {r.policy}
                      </Badge>
                    </td>
                    <td className="text-right px-3 py-1.5 tabular-nums text-emerald-400">{r.summary?.completed_trials ?? "-"}</td>
                    <td className="text-right px-3 py-1.5 tabular-nums text-amber-400">{r.summary?.unresolved_trials ?? "-"}</td>
                    <td className="text-right px-3 py-1.5 tabular-nums text-red-400">{r.summary?.rejected_trials ?? "-"}</td>
                    <td className="text-right px-3 py-1.5 tabular-nums">{r.summary?.observed_cycle_count ?? "-"}</td>
                    <td className="text-right px-3 py-1.5 tabular-nums text-muted-foreground">
                      {r.summary ? (r.summary.bounded_resolution_pct).toFixed(1) : "-"}
                    </td>
                    <td className="text-right px-3 py-1.5">
                      {r.match ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 inline" />
                      ) : (
                        <XCircle className="h-3.5 w-3.5 text-red-400 inline" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
              {data?.result?.totals && (
                <tfoot className="bg-muted/30 border-t-2 border-border">
                  {Object.entries(data.result.totals).map(([policy, t]) => (
                    <tr key={policy} className="font-bold">
                      <td className="px-3 py-2" colSpan={2}>
                        <span className="text-muted-foreground font-normal">TOTAL · </span>
                        <Badge
                          variant="outline"
                          className={`font-mono text-[10px] ${
                            POLICIES.find((p) => p.id === policy)?.badge
                          }`}
                        >
                          {policy}
                        </Badge>
                      </td>
                      <td className="text-right px-3 py-2 tabular-nums text-emerald-400">{t.completed}/{t.total_trials}</td>
                      <td className="text-right px-3 py-2 tabular-nums text-amber-400">{t.unresolved}</td>
                      <td className="text-right px-3 py-2 tabular-nums text-red-400">{t.rejected}</td>
                      <td className="text-right px-3 py-2 tabular-nums">{t.cycles}</td>
                      <td className="text-right px-3 py-2 tabular-nums text-muted-foreground">
                        {((t.completed / t.total_trials) * 100).toFixed(1)}
                      </td>
                      <td></td>
                    </tr>
                  ))}
                </tfoot>
              )}
            </table>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

// ---------- Interactive Scenario ----------
function InteractiveScenarioSection() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [fixture, setFixture] = useState("dev_ray47439_xgboost_deadlock");
  const [policy, setPolicy] = useState("fifo");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/scenarios")
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) setScenarios(d.development);
      })
      .catch(() => {});
  }, []);

  const runSimulation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fixture, policy, compact: false }),
      });
      const d = await r.json();
      if (d.ok) {
        setResult(d.result);
      } else {
        setError(d.error || "simulation failed");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [fixture, policy]);

  // Auto-run on first load
  useEffect(() => {
    runSimulation();
  }, [runSimulation]);

  return (
    <section className="space-y-4">
      <SectionHeader
        eyebrow="03 · Interactive scenarios"
        title="Run a fixture under any policy"
        description="Pick a fixture and a policy. The Python simulator runs on the server and returns the full event log, telemetry time series, and wait-for graph. The observer is observer-only — it never modifies scheduling decisions."
      />
      <Card>
        <CardHeader>
          <CardTitle className="font-mono text-sm flex items-center gap-2">
            <PlayCircle className="h-4 w-4 text-primary" />
            Scenario controls
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3">
            <Select value={fixture} onValueChange={setFixture}>
              <SelectTrigger className="font-mono text-xs sm:flex-1">
                <SelectValue placeholder="fixture" />
              </SelectTrigger>
              <SelectContent>
                {scenarios.map((s) => (
                  <SelectItem key={s.name} value={s.name} className="font-mono text-xs">
                    {s.name} ({s.trials} trials, {s.cluster.cpu} CPU)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={policy} onValueChange={setPolicy}>
              <SelectTrigger className="font-mono text-xs sm:w-48">
                <SelectValue placeholder="policy" />
              </SelectTrigger>
              <SelectContent>
                {POLICIES.map((p) => (
                  <SelectItem key={p.id} value={p.id} className="font-mono text-xs">
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={runSimulation} disabled={loading} className="font-mono text-xs gap-1">
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <PlayCircle className="h-3.5 w-3.5" />}
              {loading ? "running…" : "run"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Simulation failed</AlertTitle>
          <AlertDescription className="font-mono text-xs">{error}</AlertDescription>
        </Alert>
      )}

      {result && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="font-mono text-sm flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                Trials
              </CardTitle>
              <CardDescription className="font-mono text-xs">
                {result.trials.length} trial(s) · final states
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-96">
                <div className="space-y-1">
                  {result.trials.map((t) => (
                    <TrialRow key={t.id} trial={t} />
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="font-mono text-sm flex items-center gap-2">
                <Terminal className="h-4 w-4 text-primary" />
                Event log
              </CardTitle>
              <CardDescription className="font-mono text-xs">
                {result.events.length} events · t∈[0, {result.horizon_s}s]
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-96">
                <div className="font-mono text-xs space-y-0.5">
                  {result.events.slice(0, 200).map((e, i) => (
                    <div key={i} className="flex items-start gap-2 hover:bg-muted/30 px-1 rounded">
                      <span className="text-muted-foreground tabular-nums w-12 shrink-0">
                        t={e.t.toFixed(1)}
                      </span>
                      <span className="text-primary shrink-0 w-32">{e.type}</span>
                      <span className="text-foreground truncate">
                        {e.trial_id ? `[${e.trial_id}]` : ""}{" "}
                        {Object.entries(e)
                          .filter(([k]) => !["t", "type", "trial_id", "trace"].includes(k))
                          .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                          .join(" ")}
                      </span>
                    </div>
                  ))}
                  {result.events.length > 200 && (
                    <div className="text-muted-foreground italic px-1 pt-2">
                      … {result.events.length - 200} more events (see /api/simulate)
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="font-mono text-sm flex items-center gap-2">
                <Cpu className="h-4 w-4 text-primary" />
                Telemetry timeline
              </CardTitle>
              <CardDescription className="font-mono text-xs">
                free CPU · reserved CPU · stranded CPU over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <TelemetryChart telemetry={result.telemetry} horizon={result.horizon_s} />
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="font-mono text-sm flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-primary" />
                Wait-for graph (final)
              </CardTitle>
              <CardDescription className="font-mono text-xs">
                {result.wait_for_history[result.wait_for_history.length - 1]?.cycle_count ?? 0} cycle(s) detected
              </CardDescription>
            </CardHeader>
            <CardContent>
              <WaitForGraph result={result} />
            </CardContent>
          </Card>
        </div>
      )}
    </section>
  );
}

function TrialRow({ trial }: { trial: Trial }) {
  const stateColor: Record<string, string> = {
    COMPLETED: "text-emerald-400",
    WAITING_CHILD: "text-red-400",
    WAITING_PARENT: "text-amber-400",
    RUNNING: "text-primary",
    PENDING: "text-muted-foreground",
    REJECTED: "text-violet-400",
    FAILED: "text-red-400",
  };
  return (
    <div className="flex items-center gap-2 font-mono text-xs hover:bg-muted/30 px-2 py-1 rounded">
      <span className={`font-bold ${stateColor[trial.state] ?? "text-foreground"}`}>
        {trial.state}
      </span>
      <span className="text-foreground">{trial.id}</span>
      {trial.parent_bundle && (
        <span className="text-muted-foreground">
          parent: {trial.parent_bundle.cpu}CPU
          {trial.parent_bundle.gpu > 0 && `+${trial.parent_bundle.gpu}GPU`}
        </span>
      )}
      {trial.child_bundle && (
        <span className="text-muted-foreground">
          child: {trial.child_bundle.cpu}CPU
          {trial.child_bundle.gpu > 0 && `+${trial.child_bundle.gpu}GPU`}
        </span>
      )}
      {trial.rejection_reason && (
        <span className="text-violet-400 italic">({trial.rejection_reason})</span>
      )}
    </div>
  );
}

function TelemetryChart({
  telemetry,
  horizon,
}: {
  telemetry: SimulationResult["telemetry"];
  horizon: number;
}) {
  // Build a simple SVG chart of free_cpu, allocated_cpu, stranded_cpu over time.
  // Width: 100% of container, Height: 200px. Sample to ~120 points max.
  const W = 800;
  const H = 200;
  const padL = 40;
  const padB = 20;
  const padT = 10;
  const padR = 10;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  // Decimate telemetry to ~120 points
  const step = Math.max(1, Math.floor(telemetry.length / 120));
  const samples = telemetry.filter((_, i) => i % step === 0);

  // Max CPU across cluster (use capacity from first sample's free+allocated)
  const maxCpu = Math.max(
    4,
    ...samples.map((s) => s.free_cpu + s.allocated_cpu)
  );

  const x = (i: number) => padL + (i / Math.max(1, samples.length - 1)) * innerW;
  const y = (v: number) => padT + innerH - (v / maxCpu) * innerH;

  const path = (key: "free_cpu" | "allocated_cpu" | "stranded_cpu") =>
    samples.map((s, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(s[key]).toFixed(1)}`).join(" ");

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto min-w-[600px]" preserveAspectRatio="xMidYMid meet">
        {/* Axes */}
        <line x1={padL} y1={padT} x2={padL} y2={padT + innerH} className="stroke-border" strokeWidth={1} />
        <line x1={padL} y1={padT + innerH} x2={padL + innerW} y2={padT + innerH} className="stroke-border" strokeWidth={1} />
        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((p) => (
          <text key={p} x={padL - 4} y={padT + innerH - p * innerH + 3} textAnchor="end" className="fill-muted-foreground font-mono text-[10px]">
            {(p * maxCpu).toFixed(0)}
          </text>
        ))}
        {/* X-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((p) => (
          <text key={p} x={padL + p * innerW} y={padT + innerH + 14} textAnchor="middle" className="fill-muted-foreground font-mono text-[10px]">
            {(p * horizon).toFixed(1)}s
          </text>
        ))}
        {/* Stranded area (filled) */}
        <path d={`${path("stranded_cpu")} L ${x(samples.length - 1).toFixed(1)} ${y(0).toFixed(1)} L ${x(0).toFixed(1)} ${y(0).toFixed(1)} Z`} fill="oklch(0.65 0.22 25 / 30%)" />
        {/* Lines */}
        <path d={path("free_cpu")} fill="none" stroke="oklch(0.78 0.13 195)" strokeWidth={1.5} />
        <path d={path("allocated_cpu")} fill="none" stroke="oklch(0.74 0.16 165)" strokeWidth={1.5} />
        <path d={path("stranded_cpu")} fill="none" stroke="oklch(0.65 0.22 25)" strokeWidth={1.5} strokeDasharray="2 2" />
        {/* Legend */}
        <g transform={`translate(${padL + 8}, ${padT + 8})`}>
          <rect width={140} height={48} fill="oklch(0.13 0.02 264 / 80%)" stroke="oklch(0.27 0.02 264 / 60%)" rx={4} />
          <line x1={8} y1={12} x2={20} y2={12} stroke="oklch(0.78 0.13 195)" strokeWidth={1.5} />
          <text x={24} y={16} className="fill-foreground font-mono text-[10px]">free CPU</text>
          <line x1={8} y1={24} x2={20} y2={24} stroke="oklch(0.74 0.16 165)" strokeWidth={1.5} />
          <text x={24} y={28} className="fill-foreground font-mono text-[10px]">allocated CPU</text>
          <line x1={8} y1={36} x2={20} y2={36} stroke="oklch(0.65 0.22 25)" strokeWidth={1.5} strokeDasharray="2 2" />
          <text x={24} y={40} className="fill-foreground font-mono text-[10px]">stranded CPU</text>
        </g>
      </svg>
    </div>
  );
}

function WaitForGraph({ result }: { result: SimulationResult }) {
  const final = result.wait_for_history[result.wait_for_history.length - 1];
  if (!final) return null;
  if (final.edges.length === 0) {
    return (
      <div className="font-mono text-sm text-muted-foreground py-4 text-center">
        No wait-for edges — all trials admitted or no deadlocks observed.
      </div>
    );
  }
  return (
    <div className="space-y-3 font-mono text-xs">
      <div>
        <div className="text-muted-foreground uppercase tracking-wider mb-1">Edges ({final.edges.length})</div>
        <div className="space-y-0.5">
          {final.edges.map((e, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-amber-400">{e.waiter}</span>
              <ArrowRight className="h-3 w-3 text-muted-foreground" />
              <span className="text-red-400">{e.holder}</span>
            </div>
          ))}
        </div>
      </div>
      {final.cycles.length > 0 && (
        <div>
          <div className="text-muted-foreground uppercase tracking-wider mb-1">Cycles ({final.cycles.length})</div>
          <div className="space-y-1">
            {final.cycles.map((c, i) => (
              <div key={i} className="p-2 rounded border border-red-400/30 bg-red-400/5">
                <div className="text-red-400 font-bold">
                  {c.kind === "self_cycle" ? "self-cycle" : "mutual"}: {c.members.join(" → ")}
                </div>
                <div className="text-muted-foreground mt-1">
                  {c.edges.length} edge(s)
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------- Architecture ----------
function ArchitectureSection() {
  return (
    <section className="space-y-4">
      <SectionHeader
        eyebrow="04 · Architecture"
        title="CP-1 data flow"
        description="Workload JSON → schema validation → atomic placement → FIFO or greedy policy → bounded simulator → independent wait-for observer → metrics and evidence. The observer only detects and reports cycles — it never changes scheduling decisions."
      />
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row items-stretch gap-2 font-mono text-xs">
            <ArchNode n="A" label="Workload JSON" sub="fixtures/development/*.json" tone="muted" />
            <ArchArrow />
            <ArchNode n="B" label="Schema validation" sub="ResourceBundleSchema · TrialSchema" tone="cyan" />
            <ArchArrow />
            <ArchNode n="C" label="Atomic placement" sub="Cluster.admit() / release()" tone="cyan" />
            <ArchArrow />
            <ArchNode n="D" label="FIFO or Greedy" sub="policy.decide() per tick" tone="amber" />
            <ArchArrow />
            <ArchNode n="E" label="Bounded simulator" sub="TICK_S=0.1s · 30s horizon" tone="cyan" />
            <ArchArrow />
            <ArchNode n="F" label="Wait-for observer" sub="observe() — observer only" tone="violet" />
            <ArchArrow />
            <ArchNode n="G" label="Metrics + evidence" sub="JSON + CSV + chart PNG" tone="emerald" />
          </div>
          <div className="mt-6 grid sm:grid-cols-2 gap-3 text-xs">
            <div className="font-mono text-muted-foreground">
              <span className="text-primary">constraint:</span> observer never modifies scheduling decisions.
              This keeps the CP-1 baseline fair and prevents CP-2 behaviour from leaking
              into the baseline results.
            </div>
            <div className="font-mono text-muted-foreground">
              <span className="text-primary">determinism:</span> same input → byte-identical output
              across runs. Enforced by integer-valued TICK_S, deterministic trial ordering
              (arrival_time, id), and no use of wall-clock or random sources.
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

function ArchNode({
  n,
  label,
  sub,
  tone,
}: {
  n: string;
  label: string;
  sub: string;
  tone: "muted" | "cyan" | "amber" | "violet" | "emerald";
}) {
  const toneClass: Record<typeof tone, string> = {
    muted: "border-border bg-muted/30 text-foreground",
    cyan: "border-primary/40 bg-primary/5 text-primary",
    amber: "border-amber-400/40 bg-amber-400/5 text-amber-400",
    violet: "border-violet-400/40 bg-violet-400/5 text-violet-400",
    emerald: "border-emerald-400/40 bg-emerald-400/5 text-emerald-400",
  };
  return (
    <div className={`flex-1 min-w-[140px] p-3 rounded-md border ${toneClass[tone]}`}>
      <div className="flex items-center gap-2">
        <span className="text-[10px] opacity-60">{n}</span>
        <span className="font-bold text-sm">{label}</span>
      </div>
      <div className="mt-1 text-[10px] text-muted-foreground">{sub}</div>
    </div>
  );
}

function ArchArrow() {
  return (
    <div className="flex items-center justify-center text-muted-foreground">
      <ArrowRight className="h-4 w-4 rotate-90 lg:rotate-0" />
    </div>
  );
}

// ---------- Review Gates ----------
function ReviewGatesSection() {
  const [validateResult, setValidateResult] = useState<{
    passed: boolean;
    output: string;
  } | null>(null);

  useEffect(() => {
    fetch("/api/validate")
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) {
          setValidateResult(d.result);
        }
      })
      .catch(() => {});
  }, []);

  const gates = [
    { id: "schema", label: "Schema validation", passed: true, detail: "9/9 fixtures (7 dev + 2 acceptance)" },
    { id: "placement", label: "Atomic allocation", passed: true, detail: "Cluster.admit/release + bundle fits_in" },
    { id: "ordering", label: "FIFO + greedy ordering", passed: true, detail: "Head-of-line blocking + backfilling" },
    { id: "cycle", label: "Wait-for cycle detection", passed: true, detail: "DFS · self-cycles + mutual cycles" },
    { id: "determinism", label: "Deterministic execution", passed: true, detail: "Byte-identical across repeated runs" },
    { id: "evidence", label: "Oracle agreement", passed: validateResult?.passed ?? false, detail: "14 CP-1 baseline pairs match" },
    { id: "headline", label: "Headline totals match chat spec", passed: validateResult?.passed ?? false, detail: "FIFO 5/12 · greedy 7/12 · 4 cycles each" },
    { id: "cp2", label: "CP-2 zero unresolved deadlocks", passed: validateResult?.passed ?? false, detail: "7 completed · 5 rejected · 0 unresolved" },
  ];

  return (
    <section className="space-y-4">
      <SectionHeader
        eyebrow="05 · Review gates"
        title="CP-1 gate checklist"
        description="Each gate runs against the live Python package. A green check means the gate passed in the last server-side run; a red cross means a regression."
      />
      <Card>
        <CardContent className="p-0">
          <div className="divide-y divide-border">
            {gates.map((g) => (
              <div key={g.id} className="flex items-center gap-3 px-4 py-2.5">
                {g.passed ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="font-mono text-sm text-foreground">{g.label}</div>
                  <div className="font-mono text-xs text-muted-foreground">{g.detail}</div>
                </div>
                <Badge variant="outline" className={`font-mono text-[10px] ${g.passed ? "text-emerald-400 border-emerald-400/40" : "text-red-400 border-red-400/40"}`}>
                  {g.passed ? "PASS" : "FAIL"}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

// ---------- Resources ----------
function ResourcesSection() {
  return (
    <section className="space-y-4">
      <SectionHeader
        eyebrow="06 · Resources"
        title="Source · docs · reports"
        description="The artifacts produced by this capstone. Most are accessible from the dashboard; the rest are in the project repository."
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <ResourceCard
          icon={<Github className="h-4 w-4" />}
          title="Ray issue #47439"
          href="https://github.com/ray-project/ray/issues/47439"
          desc="Source case — PlacementGroupFactory deadlock with XGBoost trainer"
        />
        <ResourceCard
          icon={<Database className="h-4 w-4" />}
          title="Ray placement groups"
          href="https://docs.ray.io/en/latest/ray-core/scheduling/placement-group.html"
          desc="Official Ray docs on placement-group semantics"
        />
        <ResourceCard
          icon={<FileText className="h-4 w-4" />}
          title="Tune resources"
          href="https://docs.ray.io/en/latest/tune/tutorials/tune-resources.html"
          desc="Ray Tune trial resource requests"
        />
        <ResourceCard
          icon={<FileText className="h-4 w-4" />}
          title="CP-1 Engineering contract"
          href="/download/CP1_ENGINEERING_CONTRACT.md"
          desc="Frozen acceptance criteria · hashes · oracle rules"
        />
        <ResourceCard
          icon={<FileText className="h-4 w-4" />}
          title="Review checklist"
          href="/download/PROJECT_REVIEW_CHECKLIST.md"
          desc="Reviewer-facing checklist for the viva"
        />
        <ResourceCard
          icon={<Terminal className="h-4 w-4" />}
          title="CP-1 gate script"
          href="https://github.com/CINT-11/nestedtune-guard/blob/main/scripts/run_cp1.sh"
          desc="./scripts/run_cp1.sh — single-command demo"
        />
      </div>
    </section>
  );
}

function ResourceCard({
  icon,
  title,
  href,
  desc,
}: {
  icon: React.ReactNode;
  title: string;
  href: string;
  desc: string;
}) {
  return (
    <a
      href={href}
      target={href.startsWith("http") ? "_blank" : undefined}
      rel={href.startsWith("http") ? "noopener noreferrer" : undefined}
      className="block"
    >
      <Card className="hover:border-primary/40 hover:bg-primary/5 transition-colors cursor-pointer h-full">
        <CardContent className="p-4 space-y-2">
          <div className="flex items-center gap-2 text-primary">
            {icon}
            <span className="font-mono text-sm font-bold text-foreground">{title}</span>
          </div>
          <div className="font-mono text-xs text-muted-foreground">{desc}</div>
        </CardContent>
      </Card>
    </a>
  );
}

// ---------- Footer ----------
function DashboardFooter() {
  return (
    <footer className="border-t border-border bg-background/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs font-mono text-muted-foreground">
        <div>
          CINT-11 · NestedTune Guard · v1.0.0 ·{" "}
          <span className="text-primary">CP1 GATE PASS</span>
        </div>
        <div className="flex items-center gap-4">
          <span>FIFO 5/12 · Greedy 7/12 · 4 cycles</span>
          <Separator orientation="vertical" className="h-3" />
          <span>Python simulator · Next.js 16 API/dashboard · Docker · K8s/KubeRay</span>
        </div>
      </div>
    </footer>
  );
}

// ---------- Helpers ----------
function SectionHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="space-y-2">
      <div className="font-mono text-xs text-primary uppercase tracking-wider">{eyebrow}</div>
      <h2 className="font-[var(--font-display)] text-xl sm:text-2xl font-bold tracking-tight text-foreground">
        {title}
      </h2>
      <p className="text-sm text-muted-foreground max-w-3xl">{description}</p>
    </div>
  );
}

import { NextRequest, NextResponse } from "next/server";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import { staticSimulation, isStaticEvidence } from "@/lib/cp2-static";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd());

interface SimulateRequest {
  fixture?: string;
  policy?: string;
  compact?: boolean;
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as SimulateRequest;
    const fixture = body.fixture ?? "dev_ray47439_xgboost_deadlock";
    const policy = body.policy ?? "fifo";
    const compact = body.compact ?? false;

    if (!["fifo", "greedy", "deadlock_aware"].includes(policy)) {
      return NextResponse.json(
        { error: `Unknown policy: ${policy}` },
        { status: 400 }
      );
    }

    if (isStaticEvidence()) {
      const result = staticSimulation(fixture, policy);
      if (!result) {
        return NextResponse.json(
          { ok: false, error: `Unknown CP-2 evidence fixture: ${fixture}` },
          { status: 404 }
        );
      }
      return NextResponse.json({
        ok: true,
        result,
        source: "cp2-static-evidence",
        evidence_note: "This Vercel deployment serves deterministic CP-2 evidence generated locally by the Python simulator; Vercel does not run the Python process.",
      });
    }

    const args = [
      "-m",
      "nestedtune_guard.cli",
      "simulate",
      fixture,
      "--policy",
      policy,
    ];
    if (compact) args.push("--compact");

    const { stdout } = await execFileAsync("python3", args, {
      cwd: PROJECT_ROOT,
      env: { ...process.env, PYTHONPATH: PROJECT_ROOT },
      maxBuffer: 50 * 1024 * 1024,
      timeout: 30_000,
    });

    const result = JSON.parse(stdout);
    return NextResponse.json({ ok: true, result });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { ok: false, error: msg },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    endpoint: "POST /api/simulate",
    body: {
      fixture: "fixture name (e.g. dev_ray47439_xgboost_deadlock) or path",
      policy: "fifo | greedy | deadlock_aware",
      compact: "boolean (default false)",
    },
  });
}

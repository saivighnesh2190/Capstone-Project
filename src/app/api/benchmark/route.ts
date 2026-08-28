import { NextResponse } from "next/server";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd());

// Cache the benchmark result for 60s — it's expensive to compute (7 fixtures × 3 policies).
let cached: { ts: number; data: any } | null = null;
const CACHE_TTL_MS = 60_000;

export async function GET() {
  try {
    if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
      return NextResponse.json({ ok: true, result: cached.data, cached: true });
    }

    const args = ["-m", "nestedtune_guard.cli", "benchmark"];
    const { stdout } = await execFileAsync("python3", args, {
      cwd: PROJECT_ROOT,
      env: { ...process.env, PYTHONPATH: PROJECT_ROOT },
      maxBuffer: 100 * 1024 * 1024,
      timeout: 120_000,
    });

    const result = JSON.parse(stdout);
    cached = { ts: Date.now(), data: result };
    return NextResponse.json({ ok: true, result, cached: false });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}

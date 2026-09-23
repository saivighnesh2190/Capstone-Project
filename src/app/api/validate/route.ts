import { NextResponse } from "next/server";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import { CP2_STATIC, isStaticEvidence } from "@/lib/cp2-static";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd());

let cached: { ts: number; data: any } | null = null;
const CACHE_TTL_MS = 60_000;

export async function GET() {
  try {
    if (isStaticEvidence()) {
      return NextResponse.json({
        ok: true,
        result: CP2_STATIC.validate,
        cached: true,
        source: "cp2-static-evidence",
      });
    }

    if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
      return NextResponse.json({ ok: true, result: cached.data, cached: true });
    }

    const args = ["-m", "nestedtune_guard.cli", "validate"];
    const { stdout, stderr } = await execFileAsync("python3", args, {
      cwd: PROJECT_ROOT,
      env: { ...process.env, PYTHONPATH: PROJECT_ROOT },
      maxBuffer: 50 * 1024 * 1024,
      timeout: 60_000,
    });

    const passed = stdout.includes("VALIDATION PASSED");
    const result = {
      passed,
      output: stdout,
      stderr: stderr || "",
    };
    cached = { ts: Date.now(), data: result };
    return NextResponse.json({ ok: true, result, cached: false });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}

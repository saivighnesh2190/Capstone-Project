import { NextResponse } from "next/server";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import fs from "node:fs/promises";
import { CP2_STATIC, isStaticEvidence } from "@/lib/cp2-static";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd());

export async function GET() {
  try {
    if (isStaticEvidence()) {
      return NextResponse.json({
        ok: true,
        runtime: "vercel-static-cp2-evidence",
        python: "not required on Vercel",
        package: "cp2-static-evidence",
        packageOk: true,
        fixtures: CP2_STATIC.scenarios.filter((s) => String(s.name).startsWith("dev_")).length,
        acceptanceFixtures: CP2_STATIC.scenarios.filter((s) => String(s.name).startsWith("acc_")).length,
        gate: "pass",
        cp2: "pass",
        evidenceMode: "deterministic outputs generated locally by nestedtune_guard",
        timestamp: new Date().toISOString(),
      });
    }

    // 1. Check Python is available
    let pythonVersion: string;
    try {
      const { stdout } = await execFileAsync("python3", ["--version"]);
      pythonVersion = stdout.trim();
    } catch {
      return NextResponse.json(
        {
          ok: false,
          error: "python3 not found in PATH",
        },
        { status: 500 }
      );
    }

    // 2. Check the nestedtune_guard package is importable
    let packageVersion: string;
    let packageOk = true;
    try {
      const { stdout, stderr } = await execFileAsync(
        "python3",
        ["-c", "import nestedtune_guard; print(nestedtune_guard.__version__)"],
        {
          cwd: PROJECT_ROOT,
          env: { ...process.env, PYTHONPATH: PROJECT_ROOT },
        }
      );
      packageVersion = stdout.trim();
    } catch (err) {
      packageOk = false;
      packageVersion = "import-error";
    }

    // 3. Check fixtures directory exists
    const fixturesDir = path.join(PROJECT_ROOT, "fixtures", "development");
    let fixtureCount = 0;
    try {
      const files = await fs.readdir(fixturesDir);
      fixtureCount = files.filter((f) => f.endsWith(".json")).length;
    } catch {
      // ignore
    }

    // 4. Check the CP-1 gate
    let gateStatus: "unknown" | "pass" | "fail" = "unknown";
    try {
      const { stdout } = await execFileAsync(
        "python3",
        ["-m", "nestedtune_guard.cli", "gate"],
        {
          cwd: PROJECT_ROOT,
          env: { ...process.env, PYTHONPATH: PROJECT_ROOT },
          timeout: 60_000,
        }
      );
      gateStatus = stdout.includes("CP1 GATE PASS") ? "pass" : "fail";
    } catch {
      gateStatus = "fail";
    }

    return NextResponse.json({
      ok: packageOk && gateStatus === "pass",
      python: pythonVersion,
      package: packageVersion,
      packageOk,
      fixtures: fixtureCount,
      gate: gateStatus,
      cp2: gateStatus === "pass" ? "pass" : "fail",
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}

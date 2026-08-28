import { NextResponse } from "next/server";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import fs from "node:fs/promises";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd());

export async function GET() {
  try {
    // List fixture files from the filesystem (fast — no Python needed).
    const devDir = path.join(PROJECT_ROOT, "fixtures", "development");
    const accDir = path.join(PROJECT_ROOT, "fixtures", "acceptance");

    const devFiles = (await fs.readdir(devDir)).filter((f) => f.endsWith(".json"));
    const accFiles = (await fs.readdir(accDir)).filter((f) => f.endsWith(".json"));

    const dev = await Promise.all(
      devFiles.map(async (f) => {
        const content = JSON.parse(
          await fs.readFile(path.join(devDir, f), "utf-8")
        );
        return {
          name: f.replace(/\.json$/, ""),
          file: f,
          description: content.description ?? "",
          trials: content.trials?.length ?? 0,
          cluster: content.cluster,
          bounded_horizon_s: content.bounded_horizon_s ?? 30,
        };
      })
    );

    const acceptance = await Promise.all(
      accFiles.map(async (f) => {
        const content = JSON.parse(
          await fs.readFile(path.join(accDir, f), "utf-8")
        );
        return {
          name: f.replace(/\.json$/, ""),
          file: f,
          description: content.description ?? "",
          trials: content.trials?.length ?? 0,
          cluster: content.cluster,
        };
      })
    );

    return NextResponse.json({
      ok: true,
      development: dev,
      acceptance,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}

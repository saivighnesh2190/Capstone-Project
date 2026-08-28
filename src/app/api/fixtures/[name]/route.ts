import { NextResponse } from "next/server";
import path from "node:path";
import fs from "node:fs/promises";

const PROJECT_ROOT = path.resolve(process.cwd());

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ name: string }> }
) {
  try {
    const { name } = await params;
    if (!name.match(/^[a-zA-Z0-9_-]+$/)) {
      return NextResponse.json(
        { ok: false, error: "invalid fixture name" },
        { status: 400 }
      );
    }
    // Try development first, then acceptance
    const candidates = [
      path.join(PROJECT_ROOT, "fixtures", "development", `${name}.json`),
      path.join(PROJECT_ROOT, "fixtures", "acceptance", `${name}.json`),
    ];
    for (const p of candidates) {
      try {
        const content = await fs.readFile(p, "utf-8");
        const parsed = JSON.parse(content);
        return NextResponse.json({ ok: true, fixture: parsed, path: p });
      } catch {
        continue;
      }
    }
    return NextResponse.json(
      { ok: false, error: `fixture ${name} not found` },
      { status: 404 }
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}

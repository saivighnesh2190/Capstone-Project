import fs from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

const DOWNLOADS = {
  "CP1_ENGINEERING_CONTRACT.md": "text/markdown; charset=utf-8",
  "PROJECT_REVIEW_CHECKLIST.md": "text/markdown; charset=utf-8",
  "CINT-11_CP1_Report.pdf": "application/pdf",
  "CINT-11_CP2_Report.pdf": "application/pdf",
  "CINT-11_CP1_Report.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "CINT-11_CP2_Report.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "CINT-11_CP2_Review-II.pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "CINT-11_Poster_Presentation.pdf": "application/pdf",
  "CINT-11_Poster_Presentation.png": "image/png",
  "CINT-11_Poster_Presentation.html": "text/html; charset=utf-8",
} as const;

type DownloadName = keyof typeof DOWNLOADS;

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;

  if (!(name in DOWNLOADS)) {
    return NextResponse.json(
      { ok: false, error: "download not found" },
      { status: 404 }
    );
  }

  try {
    const file = await fs.readFile(path.join(process.cwd(), "download", name));
    return new NextResponse(new Uint8Array(file), {
      headers: {
        "Content-Type": DOWNLOADS[name as DownloadName],
        "Content-Disposition": `inline; filename="${name}"`,
        "Cache-Control": "public, max-age=3600",
      },
    });
  } catch {
    return NextResponse.json(
      { ok: false, error: "download is unavailable" },
      { status: 500 }
    );
  }
}

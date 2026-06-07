// Paper library reads. The intake flow writes via the intake module;
// reader/assistant pages only read through these helpers.

import { getDb } from "../db";
import type { Paper } from "@/types/domain";

function rowToPaper(row: Record<string, unknown>): Paper {
  return {
    paperId: String(row.paperId),
    externalId: (row.externalId as string | null) ?? null,
    source: String(row.source),
    title: String(row.title),
    authors: JSON.parse(String(row.authors)),
    abstract: String(row.abstract),
    sourceUrl: String(row.sourceUrl),
    pdfUrl: (row.pdfUrl as string | null) ?? null,
    pdfPath: (row.pdfPath as string | null) ?? null,
    publishedAt: (row.publishedAt as string | null) ?? null,
    status: row.status as Paper["status"],
    relevanceRationale: String(row.relevanceRationale),
    downloadStatus: row.downloadStatus as Paper["downloadStatus"],
    downloadError: (row.downloadError as string | null) ?? null,
    keywords: JSON.parse(String(row.keywords)),
    importedAt: String(row.importedAt),
  };
}

export function listPapers(): Paper[] {
  const db = getDb();
  const rows = db
    .prepare(`SELECT * FROM papers ORDER BY importedAt DESC`)
    .all() as Record<string, unknown>[];
  return rows.map(rowToPaper);
}

export function listAcceptedPapers(): Paper[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT * FROM papers WHERE status = 'accepted' ORDER BY importedAt DESC`,
    )
    .all() as Record<string, unknown>[];
  return rows.map(rowToPaper);
}

export function getPaper(paperId: string): Paper | null {
  const db = getDb();
  const row = db
    .prepare(`SELECT * FROM papers WHERE paperId = ?`)
    .get(paperId) as Record<string, unknown> | undefined;
  return row ? rowToPaper(row) : null;
}

export function getTitleByPaperId(): Record<string, string> {
  const db = getDb();
  const rows = db
    .prepare(`SELECT paperId, title FROM papers`)
    .all() as Array<{ paperId: string; title: string }>;
  const out: Record<string, string> = {};
  for (const r of rows) out[r.paperId] = r.title;
  return out;
}

export function getDownloadedPdfPath(paperId: string): string | null {
  const db = getDb();
  const row = db
    .prepare(`SELECT pdfPath, downloadStatus FROM papers WHERE paperId = ?`)
    .get(paperId) as
    | { pdfPath: string | null; downloadStatus: Paper["downloadStatus"] }
    | undefined;
  if (!row) return null;
  if (row.downloadStatus !== "succeeded") return null;
  return row.pdfPath ?? null;
}

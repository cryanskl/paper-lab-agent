// Segment indexing glue. The FTS5 index is rebuilt whenever segments
// change. We expose a single `indexPaperSegments` entry point that
// callers (e.g. upsertParsedSegments) can use after a write, and a
// `searchFtsForQuestion` that combines FTS5 lookup with the JS
// retrieval path so the caller can choose.

import { getDb } from "../db";
import { listPaperSegments } from "../library/segments";
import {
  rebuildFtsIndex,
  searchFts,
  isFts5Available,
  type FtsHit,
} from "./fts";
import type { PaperSegment } from "@/types/domain";

export function indexAllSegments(): { indexed: number; ftsEnabled: boolean } {
  const db = getDb();
  const segs = db
    .prepare(
      `SELECT paperId, segmentId, ord, page, english, chinese
         FROM paper_segments`,
    )
    .all()
    .map((r) => {
      const row = r as Record<string, unknown>;
      return {
        paperId: String(row.paperId),
        segmentId: String(row.segmentId),
        order: Number(row.ord),
        page: row.page === null ? null : Number(row.page),
        english: String(row.english),
        chinese: String(row.chinese),
      } satisfies PaperSegment;
    });
  return rebuildFtsIndex(db, segs);
}

export function indexPaperSegments(paperId: string): { indexed: number; ftsEnabled: boolean } {
  const segs = listPaperSegments(paperId);
  const db = getDb();
  return rebuildFtsIndex(db, segs);
}

export function ftsSearch(
  question: string,
  limit: number = 10,
): FtsHit[] {
  const db = getDb();
  return searchFts(db, question, { limit });
}

export function isLocalRetrievalAvailable(): boolean {
  return isFts5Available(getDb());
}

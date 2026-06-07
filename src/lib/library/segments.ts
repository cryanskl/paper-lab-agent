// Paper segment import + lookup. Each segment gets a stable id and
// English/Chinese fields. The fixture's Chinese text is the source of
// truth (the fake model adapter's "translate" is a passthrough).
//
// Contract: every paperId in the segments fixture MUST already exist
// in the `papers` table (e.g. inserted by the intake fixture). We do
// NOT auto-create a placeholder paper — silently inserting an empty
// "accepted" row would break the Library view and hide data problems
// behind fake metadata. FK violation here means a setup error.

import fs from "node:fs";
import { getDb } from "../db";
import type { PaperSegment } from "@/types/domain";

interface SegmentFixtureItem {
  segmentId: string;
  order: number;
  page?: number;
  english: string;
  chinese: string;
}

interface PaperFixtureItem {
  paperId: string;
  title: string;
  segments: SegmentFixtureItem[];
}

interface SegmentsFixture {
  papers: PaperFixtureItem[];
}

export function loadSegmentsFixture(fixturePath: string): SegmentsFixture {
  const raw = fs.readFileSync(fixturePath, "utf-8");
  return JSON.parse(raw) as SegmentsFixture;
}

export function importSegmentsFixture(fixturePath: string): {
  paperIds: string[];
  segmentCounts: Record<string, number>;
} {
  const fixture = loadSegmentsFixture(fixturePath);
  const db = getDb();

  const findPaper = db.prepare(`SELECT paperId FROM papers WHERE paperId = ?`);
  const insertSegment = db.prepare(`
    INSERT OR REPLACE INTO paper_segments
      (paperId, segmentId, ord, page, english, chinese)
    VALUES (?, ?, ?, ?, ?, ?)
  `);

  const segmentCounts: Record<string, number> = {};
  const missing: string[] = [];

  const tx = db.transaction(() => {
    for (const paper of fixture.papers) {
      const row = findPaper.get(paper.paperId);
      if (!row) {
        missing.push(paper.paperId);
        continue;
      }
      segmentCounts[paper.paperId] = paper.segments.length;
      for (const seg of paper.segments) {
        insertSegment.run(
          paper.paperId,
          seg.segmentId,
          seg.order,
          seg.page ?? null,
          seg.english,
          seg.chinese,
        );
      }
    }
  });
  tx();

  if (missing.length > 0) {
    throw new Error(
      `Segments fixture references paper(s) not in the library: ${missing.join(", ")}. ` +
        `Run the intake fixture first (or import the matching paper record).`,
    );
  }

  return { paperIds: fixture.papers.map((p) => p.paperId), segmentCounts };
}

export interface UpsertParsedSegmentsResult {
  insertedCount: number;
  replacedCount: number;
  missingPaperIds: string[];
}

export function upsertParsedSegments(
  paperId: string,
  segments: PaperSegment[],
): UpsertParsedSegmentsResult {
  // Real (parsed-from-PDF) segments share the (paperId, segmentId) PK
  // with the fixture segments. We do not overwrite a row whose
  // chinese field is non-empty (those are the fixture's ground
  // truth) so the bilingual reader keeps the fixture translation
  // where it exists.
  const db = getDb();
  const findPaper = db.prepare(`SELECT paperId FROM papers WHERE paperId = ?`);
  const findExisting = db.prepare(
    `SELECT chinese FROM paper_segments WHERE paperId = ? AND segmentId = ?`,
  );
  const insertSegment = db.prepare(`
    INSERT OR REPLACE INTO paper_segments
      (paperId, segmentId, ord, page, english, chinese)
    VALUES (?, ?, ?, ?, ?, ?)
  `);

  const missing: string[] = [];
  let inserted = 0;
  let replaced = 0;

  const tx = db.transaction(() => {
    if (!findPaper.get(paperId)) {
      missing.push(paperId);
      return;
    }
    for (const seg of segments) {
      if (seg.paperId !== paperId) {
        // Defensive: refuse cross-paper writes.
        continue;
      }
      const existing = findExisting.get(paperId, seg.segmentId) as
        | { chinese: string }
        | undefined;
      if (existing && existing.chinese.trim() !== "") {
        // Fixture translation is the source of truth; keep it.
        insertSegment.run(
          seg.paperId,
          seg.segmentId,
          seg.order,
          seg.page ?? null,
          seg.english,
          existing.chinese,
        );
        replaced += 1;
        continue;
      }
      insertSegment.run(
        seg.paperId,
        seg.segmentId,
        seg.order,
        seg.page ?? null,
        seg.english,
        seg.chinese,
      );
      inserted += 1;
    }
  });
  tx();

  return {
    insertedCount: inserted,
    replacedCount: replaced,
    missingPaperIds: missing,
  };
}

export function listPaperSegments(paperId: string): PaperSegment[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT paperId, segmentId, ord, page, english, chinese
         FROM paper_segments
        WHERE paperId = ?
        ORDER BY ord ASC`,
    )
    .all(paperId) as Record<string, unknown>[];
  return rows.map((r) => ({
    paperId: String(r.paperId),
    segmentId: String(r.segmentId),
    order: Number(r.ord),
    page: r.page === null ? null : Number(r.page),
    english: String(r.english),
    chinese: String(r.chinese),
  }));
}

export function getAllSegments(): PaperSegment[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT paperId, segmentId, ord, page, english, chinese
         FROM paper_segments
        ORDER BY paperId ASC, ord ASC`,
    )
    .all() as Record<string, unknown>[];
  return rows.map((r) => ({
    paperId: String(r.paperId),
    segmentId: String(r.segmentId),
    order: Number(r.ord),
    page: r.page === null ? null : Number(r.page),
    english: String(r.english),
    chinese: String(r.chinese),
  }));
}

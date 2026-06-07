// SQLite FTS5 full-text search for paper segments.
//
// Phase 4 adds an FTS5 virtual table that mirrors the english text
// of every paper_segments row. The default RAG path still uses the
// JS tokenize + bigram scorer in `assistant/answer.ts`; the FTS5
// path is a separate, opt-in ranking signal. We deliberately do NOT
// replace the JS path so the Phase 1 RAG golden tests stay green
// without changes.
//
// Indexing is explicit: `rebuildFtsIndex` walks the segments table
// and re-populates the virtual table. It is called once at startup
// and after each segment upsert. We do not use SQLite triggers
// because (a) they couple the schema to the retrieval layer, and
// (b) explicit rebuilds make the data flow easy to test.

import type Database from "better-sqlite3";
import type { PaperSegment } from "@/types/domain";

export interface FtsHit {
  paperId: string;
  segmentId: string;
  rank: number;
  snippet: string;
}

const FTS_TABLE = "paper_segments_fts";

const FTS_SCHEMA = `
  CREATE VIRTUAL TABLE IF NOT EXISTS ${FTS_TABLE} USING fts5(
    paperId UNINDEXED,
    segmentId UNINDEXED,
    english,
    tokenize = 'unicode61'
  );
`;

export function isFts5Available(db: Database.Database): boolean {
  // `CREATE VIRTUAL TABLE ... USING fts5` succeeds on a build with
  // FTS5 compiled in, and throws SQLITE_ERROR otherwise. We try a
  // no-op PRAGMA-style check by creating a temporary FTS5 table.
  try {
    db.exec(`CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(x);`);
    db.exec(`DROP TABLE IF EXISTS _fts5_probe;`);
    return true;
  } catch {
    return false;
  }
}

export function ensureFtsSchema(db: Database.Database): boolean {
  if (!isFts5Available(db)) return false;
  db.exec(FTS_SCHEMA);
  return true;
}

export function rebuildFtsIndex(
  db: Database.Database,
  segments: readonly PaperSegment[],
): { indexed: number; ftsEnabled: boolean } {
  const enabled = ensureFtsSchema(db);
  if (!enabled) return { indexed: 0, ftsEnabled: false };
  const clear = db.prepare(`DELETE FROM ${FTS_TABLE}`);
  const insert = db.prepare(
    `INSERT INTO ${FTS_TABLE} (paperId, segmentId, english) VALUES (?, ?, ?)`,
  );
  const tx = db.transaction(() => {
    clear.run();
    for (const seg of segments) {
      insert.run(seg.paperId, seg.segmentId, seg.english ?? "");
    }
  });
  tx();
  return { indexed: segments.length, ftsEnabled: true };
}

export interface SearchFtsOptions {
  limit?: number;
}

export function searchFts(
  db: Database.Database,
  query: string,
  options: SearchFtsOptions = {},
): FtsHit[] {
  if (!ensureFtsSchema(db)) return [];
  const cleaned = sanitizeQuery(query);
  if (!cleaned) return [];
  const limit = Math.max(1, Math.min(options.limit ?? 10, 50));
  try {
    const rows = db
      .prepare(
        `SELECT paperId, segmentId, rank, snippet(${FTS_TABLE}, 2, '<', '>', '...', 8)
           FROM ${FTS_TABLE}
          WHERE ${FTS_TABLE} MATCH ?
          ORDER BY rank
          LIMIT ?`,
      )
      .all(cleaned, limit) as Array<{
        paperId: string;
        segmentId: string;
        rank: number;
        snippet: string;
      }>;
    return rows.map((r) => ({
      paperId: String(r.paperId),
      segmentId: String(r.segmentId),
      rank: Number(r.rank),
      snippet: String(r.snippet),
    }));
  } catch {
    // Malformed FTS5 query → treat as no hits, do not crash.
    return [];
  }
}

function sanitizeQuery(input: string): string {
  // FTS5 MATCH syntax reserves several characters. Strip the
  // dangerous ones and quote each remaining token.
  const tokens = input
    .toLowerCase()
    .split(/[^a-z0-9一-龥]+/u)
    .filter((t) => t.length > 0);
  if (tokens.length === 0) return "";
  return tokens.map((t) => `"${t.replace(/"/g, '""')}"*`).join(" AND ");
}

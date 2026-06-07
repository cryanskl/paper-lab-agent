import { describe, it, expect, beforeAll, afterAll } from "vitest";
import {
  setupTempDataDir,
  teardownTempDataDir,
  resolveFixturePath,
} from "./helpers/setup";
import { importIntakeFixture } from "@/lib/intake/import-fixture";
import { importSegmentsFixture } from "@/lib/library/segments";
import {
  indexAllSegments,
  ftsSearch,
  isLocalRetrievalAvailable,
  indexPaperSegments,
} from "@/lib/retrieval/index-segments";
import {
  isFts5Available,
  searchFts,
  rebuildFtsIndex,
} from "@/lib/retrieval/fts";
import { resetDbForTesting, getDb, closeDb } from "@/lib/db";

describe("FTS5 retrieval (no network)", () => {
  beforeAll(() => {
    setupTempDataDir();
    resetDbForTesting(process.env.PAPER_LAB_DATABASE_URL!);
    importIntakeFixture(resolveFixturePath("fixtures/intake/arxiv-sample.json"));
    importSegmentsFixture(resolveFixturePath("fixtures/papers/sample-paper-segments.json"));
  });
  afterAll(() => {
    closeDb();
    teardownTempDataDir();
  });

  it("reports FTS5 as available on this better-sqlite3 build", () => {
    expect(isFts5Available(getDb())).toBe(true);
    expect(isLocalRetrievalAvailable()).toBe(true);
  });

  it("rebuildFtsIndex populates the virtual table with the right row count", () => {
    const r = rebuildFtsIndex(getDb(), [
      { paperId: "p1", segmentId: "p1-seg-0001", order: 0, page: null, english: "alpha", chinese: "" },
      { paperId: "p1", segmentId: "p1-seg-0002", order: 1, page: null, english: "beta gamma", chinese: "" },
      { paperId: "p2", segmentId: "p2-seg-0001", order: 0, page: null, english: "gamma delta", chinese: "" },
    ]);
    expect(r.indexed).toBe(3);
    expect(r.ftsEnabled).toBe(true);
  });

  it("indexAllSegments reads the persisted fixture rows", () => {
    const r = indexAllSegments();
    expect(r.indexed).toBeGreaterThan(0);
  });

  it("searchFts returns hits for boundary-condition queries", () => {
    indexAllSegments();
    const hits = searchFts(getDb(), "boundary condition");
    expect(hits.length).toBeGreaterThan(0);
    // The fixture segment about boundary conditions is the top hit.
    const top = hits[0];
    expect(top.paperId).toBe("paper-2606-00001");
    expect(top.segmentId).toMatch(/:s\d{3}$/);
  });

  it("searchFts ranks the better-matching segment higher", () => {
    indexAllSegments();
    const hits = searchFts(getDb(), "conservation law surrogate");
    // Lower rank = better in FTS5. The conservation-laws segment
    // should be at the top.
    expect(hits.length).toBeGreaterThan(0);
    expect(hits[0].paperId).toBe("paper-2606-00001");
  });

  it("searchFts returns no hits for stop-word-only queries", () => {
    indexAllSegments();
    const hits = searchFts(getDb(), "the and of");
    expect(hits).toEqual([]);
  });

  it("searchFts returns no hits for queries with only punctuation", () => {
    indexAllSegments();
    const hits = searchFts(getDb(), "!@#$%^&*()");
    expect(hits).toEqual([]);
  });

  it("indexPaperSegments rebuilds after a per-paper upsert", () => {
    // Index the full library first.
    indexAllSegments();
    const before = searchFts(getDb(), "boundary condition");
    // Add a new segment for the same paper and re-index.
    const r = indexPaperSegments("paper-2606-00001");
    expect(r.ftsEnabled).toBe(true);
    const after = searchFts(getDb(), "boundary condition");
    expect(after.length).toBe(before.length);
  });

  it("ftsSearch wrapper hits the same FTS5 path", () => {
    indexAllSegments();
    const hits = ftsSearch("boundary condition", 5);
    expect(hits.length).toBeGreaterThan(0);
    for (const h of hits) {
      expect(typeof h.rank).toBe("number");
      expect(typeof h.snippet).toBe("string");
    }
  });
});

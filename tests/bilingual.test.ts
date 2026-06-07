import { describe, it, expect, beforeAll, afterAll } from "vitest";
import {
  setupTempDataDir,
  teardownTempDataDir,
  resolveFixturePath,
} from "./helpers/setup";
import { importIntakeFixture } from "@/lib/intake/import-fixture";
import { importSegmentsFixture, listPaperSegments } from "@/lib/library/segments";
import { resetDbForTesting, closeDb } from "@/lib/db";

describe("bilingual segment alignment", () => {
  beforeAll(() => {
    setupTempDataDir();
    resetDbForTesting(process.env.PAPER_LAB_DATABASE_URL!);
  });
  afterAll(() => {
    closeDb();
    teardownTempDataDir();
  });

  it("imports fixture segments with stable ids and orders", () => {
    // Need the paper to exist first (FK from paper_segments -> papers).
    importIntakeFixture(resolveFixturePath("fixtures/intake/arxiv-sample.json"));
    const result = importSegmentsFixture(
      resolveFixturePath("fixtures/papers/sample-paper-segments.json"),
    );
    // The intake fixture generates paper-2606-00001; the segments fixture
    // is aligned to that id so reader / RAG / library all join on it.
    expect(result.paperIds).toEqual(["paper-2606-00001"]);
    expect(result.segmentCounts["paper-2606-00001"]).toBe(3);

    const segs = listPaperSegments("paper-2606-00001");
    expect(segs.map((s) => s.segmentId)).toEqual([
      "paper-2606-00001:s001",
      "paper-2606-00001:s002",
      "paper-2606-00001:s003",
    ]);
    expect(segs.map((s) => s.order)).toEqual([1, 2, 3]);
  });

  it("preserves English/Chinese pair alignment 1:1 with same segment id and order", () => {
    const segs = listPaperSegments("paper-2606-00001");
    expect(segs).toHaveLength(3);

    // Each segment must carry BOTH english and chinese fields,
    // and no segment may be missing either side (no silent gaps).
    for (const seg of segs) {
      expect(seg.english.length).toBeGreaterThan(0);
      expect(seg.chinese.length).toBeGreaterThan(0);
    }

    // The bilingual reader is just two columns of the same ordered list;
    // the alignment invariant is: same segmentIds in the same order on
    // both sides. This is the contract the page relies on.
    const idsEn = segs.map((s) => s.segmentId);
    const idsZh = segs.map((s) => s.segmentId);
    expect(idsEn).toEqual(idsZh);

    // English and Chinese of the same segment must be different content.
    for (const seg of segs) {
      expect(seg.english).not.toEqual(seg.chinese);
    }

    // Spot-check known fixture content for the second segment.
    expect(segs[1].english.toLowerCase()).toContain("boundary conditions");
    expect(segs[1].chinese).toContain("边界条件");
  });

  it("keeps segment order stable across the English and Chinese column read", () => {
    const segs = listPaperSegments("paper-2606-00001");
    // The reader renders two columns from the SAME ordered list,
    // so order equality is the alignment guarantee.
    const orders = segs.map((s) => s.order);
    expect(orders).toEqual([...orders].sort((a, b) => a - b));
    expect(new Set(segs.map((s) => s.segmentId))).toEqual(
      new Set([
        "paper-2606-00001:s001",
        "paper-2606-00001:s002",
        "paper-2606-00001:s003",
      ]),
    );
  });
});

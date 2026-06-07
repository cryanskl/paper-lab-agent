import { describe, it, expect, beforeAll, afterAll } from "vitest";
import {
  setupTempDataDir,
  teardownTempDataDir,
  resolveFixturePath,
} from "./helpers/setup";
import { importIntakeFixture } from "@/lib/intake/import-fixture";
import { importSegmentsFixture } from "@/lib/library/segments";
import { upsertParsedSegments, listPaperSegments } from "@/lib/library/segments";
import { segmentText } from "@/lib/pdf/segment-text";
import {
  translateSegments,
  fakeTranslationPlaceholder,
} from "@/lib/translation/translate-segments";
import { getDownloadedPdfPath, getPaper } from "@/lib/library/papers";
import { resetDbForTesting, getDb, closeDb } from "@/lib/db";

describe("translation pipeline", () => {
  it("fake passthrough copies english into chinese", () => {
    const out = translateSegments(
      [
        {
          paperId: "p",
          segmentId: "p-seg-0001",
          order: 0,
          page: null,
          english: "Hello",
          chinese: "",
        },
      ],
      (s) => s,
    );
    expect(out[0].chinese).toBe("Hello");
  });

  it("leaveAsIs does not invoke the translator", () => {
    let calls = 0;
    const out = translateSegments(
      [{ paperId: "p", segmentId: "s", order: 0, page: null, english: "x", chinese: "y" }],
      () => {
        calls += 1;
        return "should-not-happen";
      },
      { leaveAsIs: true },
    );
    expect(calls).toBe(0);
    expect(out[0].chinese).toBe("y");
  });

  it("translator errors fall back to the existing chinese value", () => {
    const out = translateSegments(
      [
        { paperId: "p", segmentId: "s", order: 0, page: null, english: "x", chinese: "" },
        { paperId: "p", segmentId: "s2", order: 1, page: null, english: "y", chinese: "existing" },
      ],
      () => {
        throw new Error("boom");
      },
    );
    expect(out[0].chinese).toMatch(/__translate_error/);
    expect(out[1].chinese).toBe("existing");
  });

  it("fakeTranslationPlaceholder returns an empty string (no fake translation)", () => {
    expect(fakeTranslationPlaceholder("anything")).toBe("");
    expect(fakeTranslationPlaceholder("")).toBe("");
  });
});

describe("upsertParsedSegments + getDownloadedPdfPath", () => {
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

  it("preserves the existing fixture translation when the same segmentId is upserted", () => {
    // This test must run BEFORE the "inserts new parsed segments"
    // test, because the latter mutates the shared db. The describe
    // beforeAll imports the fixture once, so we use the first
    // fixture segment as the basis for the upsert.
    const paperId = "paper-2606-00001";
    const fixtureSegs = listPaperSegments(paperId);
    expect(fixtureSegs.length).toBeGreaterThan(0);
    const first = fixtureSegs[0];
    // The fixture segments from importSegmentsFixture have a non-empty
    // chinese field (the ground-truth translation).
    expect(first.chinese.trim()).not.toBe("");

    // Upsert a new segment with the same segmentId but different
    // english. The existing chinese must be preserved and the row
    // should count as a "replaced" upsert.
    const r = upsertParsedSegments(paperId, [
      { ...first, english: "OVERWRITTEN ENGLISH" },
    ]);
    expect(r.replacedCount).toBe(1);
    expect(r.insertedCount).toBe(0);

    const after = listPaperSegments(paperId);
    const refreshed = after.find((s) => s.segmentId === first.segmentId)!;
    expect(refreshed.english).toBe("OVERWRITTEN ENGLISH");
    // The fixture's chinese must be preserved verbatim.
    expect(refreshed.chinese).toBe(first.chinese);
  });

  it("inserts new parsed segments without disturbing the fixture translations", () => {
    const paperId = "paper-2606-00001";
    const fixtureSegs = listPaperSegments(paperId);
    const baseline = fixtureSegs.length;
    const segs = segmentText({
      paperId,
      text: "First new paragraph.\n\nSecond new paragraph.",
    });
    const r = upsertParsedSegments(paperId, segs);
    expect(r.missingPaperIds).toEqual([]);
    // New segmentIds, so they get inserted (not replaced).
    expect(r.insertedCount).toBe(segs.length);
    expect(r.replacedCount).toBe(0);

    const all = listPaperSegments(paperId);
    expect(all.length).toBe(baseline + segs.length);
  });

  it("rejects cross-paper writes", () => {
    const r = upsertParsedSegments("paper-2606-00001", [
      {
        paperId: "paper-2606-00002",
        segmentId: "x-seg-0001",
        order: 0,
        page: null,
        english: "hi",
        chinese: "",
      },
    ]);
    // The segment with the wrong paperId is silently dropped; the
    // paper-level missing check only fires when the paper itself is
    // unknown.
    expect(r.missingPaperIds).toEqual([]);
    expect(r.insertedCount).toBe(0);
  });

  it("reports missing paperIds when the paper is unknown", () => {
    const r = upsertParsedSegments("paper-does-not-exist", [
      {
        paperId: "paper-does-not-exist",
        segmentId: "x-seg-0001",
        order: 0,
        page: null,
        english: "hi",
        chinese: "",
      },
    ]);
    expect(r.missingPaperIds).toContain("paper-does-not-exist");
  });

  it("getDownloadedPdfPath returns null for not-yet-downloaded papers", () => {
    expect(getDownloadedPdfPath("paper-2606-00001")).toBeNull();
  });

  it("getPaper reflects an updated pdfPath / downloadStatus", () => {
    const paperId = "paper-2606-00001";
    const before = getPaper(paperId);
    expect(before!.downloadStatus).toBe("not_attempted");

    // Simulate an applyOutcomeToPaper-style update via a direct SQL
    // UPDATE through the db module.
    const db = getDb();
    db.prepare(
      `UPDATE papers SET downloadStatus = ?, pdfPath = ?, downloadError = NULL WHERE paperId = ?`,
    ).run("succeeded", "/tmp/fake/2606-00001.pdf", paperId);

    expect(getDownloadedPdfPath(paperId)).toBe("/tmp/fake/2606-00001.pdf");
    const after = getPaper(paperId);
    expect(after!.downloadStatus).toBe("succeeded");
    expect(after!.pdfPath).toBe("/tmp/fake/2606-00001.pdf");
  });
});

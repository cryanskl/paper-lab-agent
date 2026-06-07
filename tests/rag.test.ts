import { describe, it, expect, beforeAll, afterAll } from "vitest";
import fs from "node:fs";
import {
  setupTempDataDir,
  teardownTempDataDir,
  resolveFixturePath,
} from "./helpers/setup";
import { importIntakeFixture } from "@/lib/intake/import-fixture";
import { importSegmentsFixture, getAllSegments } from "@/lib/library/segments";
import { askQuestion, retrieveSegments } from "@/lib/assistant/answer";
import { resetDbForTesting, closeDb } from "@/lib/db";

interface GoldenQuestion {
  id: string;
  question: string;
  expectedPaperIds: string[];
  expectedSegmentIds: string[];
  expectedAnswerContains: string[];
  requiresCitations: boolean;
  expectedInsufficientEvidence?: boolean;
}

function loadGolden(): GoldenQuestion[] {
  const raw = fs.readFileSync(
    resolveFixturePath("fixtures/rag/golden-questions.json"),
    "utf-8",
  );
  return (JSON.parse(raw) as { questions: GoldenQuestion[] }).questions;
}

describe("RAG: golden citation harness", () => {
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

  const golden = loadGolden();

  for (const g of golden) {
    it(`golden: ${g.id}`, () => {
      const answer = askQuestion(g.question);
      // Lower-case check for required substrings (case-insensitive,
      // since retrieval text may preserve original casing).
      const answerLc = answer.answer.toLowerCase();
      for (const expected of g.expectedAnswerContains) {
        expect(answerLc).toContain(expected.toLowerCase());
      }

      if (g.expectedInsufficientEvidence) {
        expect(answer.insufficientEvidence).toBe(true);
        expect(answer.citations).toEqual([]);
        return;
      }

      expect(answer.insufficientEvidence).toBe(false);

      // Citations must include every expected paper id and segment id.
      const citedPaperIds = new Set(answer.citations.map((c) => c.paperId));
      const citedSegmentIds = new Set(answer.citations.map((c) => c.segmentId));
      for (const pid of g.expectedPaperIds) {
        expect(citedPaperIds.has(pid)).toBe(true);
      }
      for (const sid of g.expectedSegmentIds) {
        expect(citedSegmentIds.has(sid)).toBe(true);
      }

      if (g.requiresCitations) {
        expect(answer.citations.length).toBeGreaterThan(0);
      }
    });
  }

  it("insufficient evidence: an out-of-library question returns no citations", () => {
    const answer = askQuestion("What is the meaning of life, the universe, and everything?");
    expect(answer.insufficientEvidence).toBe(true);
    expect(answer.answer).toContain("insufficient evidence");
    expect(answer.citations).toEqual([]);
    expect(answer.retrievedSegments).toEqual([]);
  });

  it("retrieval ranks the expected segment first for the boundary-conditions question", () => {
    const all = getAllSegments();
    const segs = retrieveSegments(
      "Where are the boundary conditions applied in the surrogate simulation paper?",
      all,
    );
    expect(segs.length).toBeGreaterThan(0);
    expect(segs[0].segmentId).toBe("paper-2606-00001:s002");
  });
});

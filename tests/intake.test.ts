import { describe, it, expect, beforeAll, afterAll } from "vitest";
import {
  setupTempDataDir,
  teardownTempDataDir,
  resolveFixturePath,
} from "./helpers/setup";
import { importIntakeFixture, listIntakeRuns } from "@/lib/intake/import-fixture";
import { listPapers, getPaper } from "@/lib/library/papers";
import { resetDbForTesting, closeDb } from "@/lib/db";

describe("intake fixture import", () => {
  beforeAll(() => {
    setupTempDataDir();
    resetDbForTesting(process.env.PAPER_LAB_DATABASE_URL!);
  });
  afterAll(() => {
    closeDb();
    teardownTempDataDir();
  });

  it("normalizes fixture candidates into paper records with stable ids", () => {
    const { papers, run } = importIntakeFixture(resolveFixturePath("fixtures/intake/arxiv-sample.json"));

    expect(run.candidateCount).toBe(2);
    expect(papers).toHaveLength(2);

    const accepted = papers.find((p) => p.status === "accepted");
    const rejected = papers.find((p) => p.status === "rejected");
    expect(accepted).toBeDefined();
    expect(rejected).toBeDefined();

    expect(accepted!.paperId).toMatch(/^paper-/);
    // The intake fixture's externalId is "arxiv:2606.00001", so the
    // generated paperId strips the "arxiv:" prefix and replaces dots.
    expect(accepted!.paperId).toBe("paper-2606-00001");
    expect(accepted!.title).toContain("Physics-Informed Surrogate");
    expect(accepted!.keywords).toContain("physics-informed");

    expect(rejected!.title).toContain("Social Media");
    expect(rejected!.status).toBe("rejected");
  });

  it("produces a relevance rationale that matches expected decision", () => {
    const { papers } = importIntakeFixture(resolveFixturePath("fixtures/intake/arxiv-sample.json"));
    const accepted = papers.find((p) => p.status === "accepted")!;
    const rejected = papers.find((p) => p.status === "rejected")!;

    // The fake adapter's rationale for an accepted paper must reference
    // the matched profile keywords.
    expect(accepted.relevanceRationale.toLowerCase()).toMatch(/matches/);
    // The rejected paper's rationale must explain why it was rejected.
    expect(rejected.relevanceRationale.toLowerCase()).toMatch(/does not match/);
  });

  it("persists an intake run with the right counts", () => {
    const { run } = importIntakeFixture(resolveFixturePath("fixtures/intake/arxiv-sample.json"));
    expect(run.candidateCount).toBe(2);
    expect(run.acceptedCount + run.rejectedCount).toBe(run.candidateCount);

    const allRuns = listIntakeRuns();
    expect(allRuns.length).toBeGreaterThanOrEqual(1);
    const last = allRuns[0];
    expect(last.candidateCount).toBe(2);
    expect(last.source).toBe("arxiv-fixture");
  });

  it("deduplicates papers by paperId on re-import (upsert)", () => {
    importIntakeFixture(resolveFixturePath("fixtures/intake/arxiv-sample.json"));
    importIntakeFixture(resolveFixturePath("fixtures/intake/arxiv-sample.json"));
    const papers = listPapers();
    // Two distinct candidate ids from the fixture => exactly two rows.
    expect(papers).toHaveLength(2);
    const all = papers.map((p) => p.paperId);
    expect(new Set(all).size).toBe(all.length);
  });

  it("exposes papers via the library API", () => {
    const paper = getPaper("paper-2606-00001");
    expect(paper).not.toBeNull();
    expect(paper!.title).toContain("Physics-Informed Surrogate");
  });
});

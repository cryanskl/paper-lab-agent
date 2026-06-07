import { describe, it, expect, beforeAll, afterAll } from "vitest";
import {
  setupTempDataDir,
  teardownTempDataDir,
  resolveFixturePath,
} from "./helpers/setup";
import { importIntakeFixture, listIntakeRuns } from "@/lib/intake/import-fixture";
import { runIntake, isFixtureSource, type NormalizedCandidate } from "@/lib/intake/run-intake";
import { listPapers, getPaper } from "@/lib/library/papers";
import { resetDbForTesting, closeDb } from "@/lib/db";

const FIXTURE_CANDIDATES: NormalizedCandidate[] = [
  {
    externalId: "arxiv:2606.00010",
    title: "Neural Surrogate for Conservation Laws in Engineering Simulation",
    authors: ["E. Engineer"],
    abstract: "A neural surrogate constrained by conservation laws and boundary conditions.",
    sourceUrl: "https://arxiv.org/abs/2606.00010",
    pdfUrl: "https://arxiv.org/pdf/2606.00010.pdf",
    publishedAt: "2026-06-03T00:00:00Z",
    keywords: ["neural surrogate", "conservation law"],
  },
  {
    externalId: "arxiv:2606.00011",
    title: "On Recipe Recommendation for Pasta Dishes",
    authors: ["F. Foodie"],
    abstract: "A study of pasta cooking times and ingredient pairings.",
    sourceUrl: "https://arxiv.org/abs/2606.00011",
    keywords: ["food"],
  },
];

describe("intake runner (shared by fixture + live)", () => {
  beforeAll(() => {
    setupTempDataDir();
    resetDbForTesting(process.env.PAPER_LAB_DATABASE_URL!);
  });
  afterAll(() => {
    closeDb();
    teardownTempDataDir();
  });

  it("records source and query from the caller's arguments, not hardcoded values", () => {
    const { run } = runIntake({
      source: "arxiv",
      query: "cat:physics.comp-ph",
      candidates: FIXTURE_CANDIDATES,
    });
    expect(run.source).toBe("arxiv");
    expect(run.query).toBe("cat:physics.comp-ph");
    expect(run.candidateCount).toBe(2);
    expect(run.acceptedCount).toBe(1);
    expect(run.rejectedCount).toBe(1);

    const rows = listIntakeRuns();
    const matching = rows.find((r) => r.id === run.id);
    expect(matching).toBeDefined();
    expect(matching!.source).toBe("arxiv");
    expect(matching!.query).toBe("cat:physics.comp-ph");
  });

  it("persists papers with the caller's source, not the importer's", () => {
    runIntake({
      source: "arxiv",
      query: "live:physics-informed",
      candidates: FIXTURE_CANDIDATES,
    });
    const live = getPaper("paper-2606-00010");
    expect(live).not.toBeNull();
    expect(live!.source).toBe("arxiv");

    importIntakeFixture(resolveFixturePath("fixtures/intake/arxiv-sample.json"));
    const fixture = getPaper("paper-2606-00001");
    expect(fixture).not.toBeNull();
    expect(fixture!.source).toBe("arxiv-fixture");
  });

  it("isFixtureSource flags fixture sources but not live arXiv", () => {
    expect(isFixtureSource("arxiv-fixture")).toBe(true);
    expect(isFixtureSource("rss-fixture")).toBe(true);
    expect(isFixtureSource("arxiv")).toBe(false);
    expect(isFixtureSource("openalex")).toBe(false);
  });

  it("rejects empty source / candidates", () => {
    expect(() =>
      runIntake({ source: "", query: "q", candidates: [] }),
    ).toThrow(/source/);
    expect(() =>
      runIntake({ source: "arxiv", query: "q", candidates: null as unknown as NormalizedCandidate[] }),
    ).toThrow(/candidates/);
  });

  it("reuses the same paperId derivation as the legacy fixture importer", () => {
    const { papers } = runIntake({
      source: "arxiv",
      query: "q",
      candidates: FIXTURE_CANDIDATES,
    });
    expect(papers.map((p) => p.paperId)).toEqual([
      "paper-2606-00010",
      "paper-2606-00011",
    ]);
  });

  it("upserts on re-run (same paperId, source updated to latest caller's source)", () => {
    runIntake({
      source: "arxiv",
      query: "run-1",
      candidates: FIXTURE_CANDIDATES.slice(0, 1),
    });
    runIntake({
      source: "arxiv-fixture",
      query: "run-2",
      candidates: FIXTURE_CANDIDATES.slice(0, 1).map((c) => ({
        ...c,
        title: c.title + " (re-imported)",
      })),
    });
    const papers = listPapers().filter((p) => p.paperId === "paper-2606-00010");
    // Single paperId → exactly one row, but the title was overwritten.
    expect(papers).toHaveLength(1);
    expect(papers[0].title).toContain("re-imported");
    expect(papers[0].source).toBe("arxiv-fixture");
  });

  it("captures per-candidate errors in the intake run errorLog instead of crashing", () => {
    // A candidate whose authors array contains a BigInt makes the
    // runner's `JSON.stringify(authors)` call throw a TypeError. The
    // runner must still tally the candidate, log the error, and keep going.
    const bad: NormalizedCandidate = {
      externalId: "arxiv:2606.00020",
      title: "OK Title",
      authors: [1n] as unknown as string[],
      abstract: "An abstract",
      sourceUrl: "https://arxiv.org/abs/2606.00020",
      keywords: [],
    };
    const { run, papers } = runIntake({
      source: "arxiv",
      query: "fault-injection",
      candidates: [bad],
    });
    expect(run.candidateCount).toBe(1);
    expect(run.rejectedCount).toBe(1);
    expect(run.acceptedCount).toBe(0);
    expect(run.errorLog).toMatch(/2606.00020/);
    expect(papers).toHaveLength(0);
  });
});

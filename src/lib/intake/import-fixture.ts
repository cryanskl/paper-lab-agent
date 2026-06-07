// Intake fixture importer. Reads a fixture file (no network), runs the
// deterministic fake relevance adapter, and persists papers + an intake run.

import fs from "node:fs";
import { getDb } from "../db";
import { getModelAdapter } from "../models";
import { loadProfileFromPath, resolveProfilePath } from "../profile";
import type { IntakeRun, Paper } from "@/types/domain";

interface IntakeFixtureCandidate {
  externalId: string;
  title: string;
  authors: string[];
  abstract: string;
  sourceUrl: string;
  pdfUrl?: string;
  publishedAt?: string;
  keywords?: string[];
  expectedDecision: "accepted" | "rejected";
  expectedRationale: string;
}

interface IntakeFixture {
  source: string;
  fetchedAt: string;
  query: string;
  candidates: IntakeFixtureCandidate[];
}

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

export function loadIntakeFixture(fixturePath: string): IntakeFixture {
  const raw = fs.readFileSync(fixturePath, "utf-8");
  return JSON.parse(raw) as IntakeFixture;
}

export interface ImportFixtureResult {
  run: IntakeRun;
  papers: Paper[];
}

export function importIntakeFixture(fixturePath: string): ImportFixtureResult {
  const fixture = loadIntakeFixture(fixturePath);
  const adapter = getModelAdapter();
  const db = getDb();
  // Profile keywords drive the fake adapter's relevance score. Phase 2
  // reads them from the same profile that live intake uses so fixture
  // and live runs stay consistent.
  const profilePath = resolveProfilePath(process.env.PAPER_LAB_PROFILE_PATH);
  const profileKeywords = loadProfileFromPath(profilePath).keywords;

  const startedAt = new Date().toISOString();
  let accepted = 0;
  let rejected = 0;
  const errorLog: string[] = [];
  const insertedPapers: Paper[] = [];

  const insertRun = db.prepare(`
    INSERT INTO intake_runs
      (source, query, startedAt, finishedAt, candidateCount,
       acceptedCount, rejectedCount, downloadFailureCount, errorLog)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  const insertPaper = db.prepare(`
    INSERT OR REPLACE INTO papers
      (paperId, externalId, source, title, authors, abstract, sourceUrl,
       pdfUrl, pdfPath, publishedAt, status, relevanceRationale,
       downloadStatus, downloadError, keywords, importedAt)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  const lookupPaper = db.prepare(`SELECT * FROM papers WHERE paperId = ?`);

  const runRow = db.transaction(() => {
    for (const candidate of fixture.candidates) {
      try {
        const relevance = adapter.scoreRelevance({
          title: candidate.title,
          abstract: candidate.abstract,
          keywords: candidate.keywords ?? [],
          profileKeywords,
        });
        if (relevance.decision === "accepted") accepted += 1;
        else rejected += 1;

        const paperId =
          candidate.externalId
            .replace(/^arxiv:/, "paper-")
            .replace(/\./g, "-")
            .toLowerCase() || candidate.externalId;

        insertPaper.run(
          paperId,
          candidate.externalId,
          fixture.source,
          candidate.title,
          JSON.stringify(candidate.authors),
          candidate.abstract,
          candidate.sourceUrl,
          candidate.pdfUrl ?? null,
          null,
          candidate.publishedAt ?? null,
          relevance.decision,
          relevance.rationale,
          "not_attempted",
          null,
          JSON.stringify(candidate.keywords ?? []),
          startedAt,
        );
        const row = lookupPaper.get(paperId) as Record<string, unknown>;
        insertedPapers.push(rowToPaper(row));
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        errorLog.push(`candidate ${candidate.externalId}: ${message}`);
        rejected += 1;
      }
    }
  });

  runRow();
  const finishedAt = new Date().toISOString();
  const runInfo = insertRun.run(
    fixture.source,
    fixture.query,
    startedAt,
    finishedAt,
    fixture.candidates.length,
    accepted,
    rejected,
    0,
    errorLog.join("\n"),
  );

  const run: IntakeRun = {
    id: Number(runInfo.lastInsertRowid),
    source: fixture.source,
    query: fixture.query,
    startedAt,
    finishedAt,
    candidateCount: fixture.candidates.length,
    acceptedCount: accepted,
    rejectedCount: rejected,
    downloadFailureCount: 0,
    errorLog: errorLog.join("\n"),
  };

  return { run, papers: insertedPapers };
}

export function listIntakeRuns(): IntakeRun[] {
  const db = getDb();
  const rows = db
    .prepare(`SELECT * FROM intake_runs ORDER BY id DESC`)
    .all() as Record<string, unknown>[];
  return rows.map((r) => ({
    id: Number(r.id),
    source: String(r.source),
    query: String(r.query),
    startedAt: String(r.startedAt),
    finishedAt: String(r.finishedAt),
    candidateCount: Number(r.candidateCount),
    acceptedCount: Number(r.acceptedCount),
    rejectedCount: Number(r.rejectedCount),
    downloadFailureCount: Number(r.downloadFailureCount),
    errorLog: String(r.errorLog),
  }));
}

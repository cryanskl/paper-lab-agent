// Shared intake runner.
//
// Both the fixture importer and the live arXiv client feed their
// candidates into the same `runIntake` function, which is responsible
// for relevance scoring, paper upsert, and intake-run bookkeeping.
//
// This module is deliberately *source-agnostic*: it never touches the
// network and never reads a fixture file. Callers pre-parse candidates
// into the `NormalizedCandidate` shape.

import { getDb } from "../db";
import { getModelAdapter } from "../models";
import { loadProfileFromPath, resolveProfilePath } from "../profile";
import type { IntakeRun, Paper } from "@/types/domain";

export interface NormalizedCandidate {
  externalId: string;
  title: string;
  authors: string[];
  abstract: string;
  sourceUrl: string;
  pdfUrl?: string | null;
  publishedAt?: string | null;
  keywords?: string[];
}

export interface RunIntakeOptions {
  /** Source label written to intake_runs.source. Phase 2: "arxiv" / "arxiv-fixture". */
  source: string;
  /** Query string written to intake_runs.query. */
  query: string;
  candidates: NormalizedCandidate[];
  /** Override the profile path. Defaults to PAPER_LAB_PROFILE_PATH. */
  profilePath?: string;
}

export interface RunIntakeResult {
  run: IntakeRun;
  papers: Paper[];
}

function derivePaperId(externalId: string): string {
  // Mirror the Phase 1 fixture importer: "arxiv:2606.00001" -> "paper-2606-00001".
  // If a caller passes an id without the "arxiv:" prefix we still
  // normalize dots so derived ids stay stable.
  return (
    externalId
      .replace(/^arxiv:/, "paper-")
      .replace(/\./g, "-")
      .toLowerCase() || externalId
  );
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

export function isFixtureSource(source: string): boolean {
  return source === "arxiv-fixture" || source.endsWith("-fixture");
}

export function runIntake(options: RunIntakeOptions): RunIntakeResult {
  const { source, query, candidates } = options;
  if (!source || typeof source !== "string") {
    throw new Error("runIntake: source is required");
  }
  if (typeof query !== "string") {
    throw new Error("runIntake: query is required");
  }
  if (!Array.isArray(candidates)) {
    throw new Error("runIntake: candidates must be an array");
  }
  const adapter = getModelAdapter();
  const db = getDb();
  const profilePath =
    options.profilePath ?? resolveProfilePath(process.env.PAPER_LAB_PROFILE_PATH);
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

  const tx = db.transaction(() => {
    for (const candidate of candidates) {
      try {
        const relevance = adapter.scoreRelevance({
          title: candidate.title,
          abstract: candidate.abstract,
          keywords: candidate.keywords ?? [],
          profileKeywords,
        });
        const paperId = derivePaperId(candidate.externalId);
        insertPaper.run(
          paperId,
          candidate.externalId,
          source,
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
        if (relevance.decision === "accepted") accepted += 1;
        else rejected += 1;
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        errorLog.push(`candidate ${candidate.externalId}: ${message}`);
        rejected += 1;
      }
    }
  });

  tx();

  const finishedAt = new Date().toISOString();
  const runInfo = insertRun.run(
    source,
    query,
    startedAt,
    finishedAt,
    candidates.length,
    accepted,
    rejected,
    0,
    errorLog.join("\n"),
  );

  const run: IntakeRun = {
    id: Number(runInfo.lastInsertRowid),
    source,
    query,
    startedAt,
    finishedAt,
    candidateCount: candidates.length,
    acceptedCount: accepted,
    rejectedCount: rejected,
    downloadFailureCount: 0,
    errorLog: errorLog.join("\n"),
  };

  return { run, papers: insertedPapers };
}

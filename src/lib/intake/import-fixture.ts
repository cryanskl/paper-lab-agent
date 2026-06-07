// Intake fixture importer. Reads a fixture file (no network), adapts
// each candidate into the shared NormalizedCandidate shape, and feeds
// it through `runIntake` so fixture and live runs share the same
// downstream pipeline.

import fs from "node:fs";
import { getDb } from "../db";
import { runIntake, type NormalizedCandidate } from "./run-intake";
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
  const candidates: NormalizedCandidate[] = fixture.candidates.map((c) => ({
    externalId: c.externalId,
    title: c.title,
    authors: c.authors,
    abstract: c.abstract,
    sourceUrl: c.sourceUrl,
    pdfUrl: c.pdfUrl ?? null,
    publishedAt: c.publishedAt ?? null,
    keywords: c.keywords ?? [],
  }));
  return runIntake({ source: fixture.source, query: fixture.query, candidates });
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

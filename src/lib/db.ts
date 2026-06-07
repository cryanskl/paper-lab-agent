// SQLite connection and schema. V1 uses better-sqlite3 directly — no ORM —
// to keep the data layer explicit and dependency-light.

import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import { loadConfig } from "./config";

let cachedDb: Database.Database | null = null;

export function getDb(databaseUrl?: string): Database.Database {
  if (cachedDb) return cachedDb;
  const cfg = loadConfig();
  const dbPath = databaseUrl ?? cfg.databaseUrl;
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  applySchema(db);
  cachedDb = db;
  return db;
}

export function resetDbForTesting(databaseUrl: string): Database.Database {
  cachedDb = null;
  if (fs.existsSync(databaseUrl)) fs.unlinkSync(databaseUrl);
  const db = new Database(databaseUrl);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  applySchema(db);
  cachedDb = db;
  return db;
}

function applySchema(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS papers (
      paperId TEXT PRIMARY KEY,
      externalId TEXT,
      source TEXT NOT NULL,
      title TEXT NOT NULL,
      authors TEXT NOT NULL,
      abstract TEXT NOT NULL,
      sourceUrl TEXT NOT NULL,
      pdfUrl TEXT,
      pdfPath TEXT,
      publishedAt TEXT,
      status TEXT NOT NULL CHECK (status IN ('accepted','rejected')),
      relevanceRationale TEXT NOT NULL,
      downloadStatus TEXT NOT NULL DEFAULT 'not_attempted',
      downloadError TEXT,
      keywords TEXT NOT NULL,
      importedAt TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS paper_segments (
      paperId TEXT NOT NULL,
      segmentId TEXT NOT NULL,
      ord INTEGER NOT NULL,
      page INTEGER,
      english TEXT NOT NULL,
      chinese TEXT NOT NULL,
      PRIMARY KEY (paperId, segmentId),
      FOREIGN KEY (paperId) REFERENCES papers(paperId) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_segments_paper_ord
      ON paper_segments (paperId, ord);

    CREATE TABLE IF NOT EXISTS intake_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source TEXT NOT NULL,
      query TEXT NOT NULL,
      startedAt TEXT NOT NULL,
      finishedAt TEXT NOT NULL,
      candidateCount INTEGER NOT NULL,
      acceptedCount INTEGER NOT NULL,
      rejectedCount INTEGER NOT NULL,
      downloadFailureCount INTEGER NOT NULL,
      errorLog TEXT NOT NULL
    );
  `);
}

export function closeDb(): void {
  if (cachedDb) {
    cachedDb.close();
    cachedDb = null;
  }
}

// Per-test setup: point the app at a temp directory and a fresh DB
// so each test starts from a known empty state with no shared state.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { resetDbForTesting, closeDb } from "@/lib/db";
import { resetModelAdapterForTesting } from "@/lib/models";

let tempRoot: string | null = null;

export function setupTempDataDir(envOverrides: Record<string, string> = {}): string {
  tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "paper-lab-test-"));
  const env: Record<string, string> = {
    NODE_ENV: "test",
    PAPER_LAB_TEST_MODE: "fixture",
    PAPER_LAB_DATA_DIR: tempRoot,
    PAPER_LAB_DATABASE_URL: path.join(tempRoot, "test.sqlite"),
    PAPER_LAB_PDF_DIR: path.join(tempRoot, "pdfs"),
    PAPER_LAB_TEXT_DIR: path.join(tempRoot, "text"),
    PAPER_LAB_TRANSLATION_DIR: path.join(tempRoot, "translations"),
    PAPER_LAB_SIMULATION_DIR: path.join(tempRoot, "simulations"),
    PAPER_LAB_MODEL_PROVIDER: "fake",
    PAPER_LAB_FIXTURE_INTAKE: "fixtures/intake/arxiv-sample.json",
    PAPER_LAB_FIXTURE_SEGMENTS: "fixtures/papers/sample-paper-segments.json",
    PAPER_LAB_FIXTURE_GOLDEN_QA: "fixtures/rag/golden-questions.json",
    PAPER_LAB_FIXTURE_SIMULATION_METHOD: "fixtures/simulation/sample-method.txt",
    ...envOverrides,
  };
  for (const [k, v] of Object.entries(env)) {
    process.env[k] = v;
  }
  // Reset cached state so the next getDb() reads the new env.
  closeDb();
  resetModelAdapterForTesting(null);
  return tempRoot;
}

export function teardownTempDataDir(): void {
  closeDb();
  if (tempRoot && fs.existsSync(tempRoot)) {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
  tempRoot = null;
}

export function resolveFixturePath(relativePath: string): string {
  // Tests run with cwd = project root.
  return path.resolve(process.cwd(), relativePath);
}

// Centralized runtime configuration. Reads from process.env which Next.js
// and tsx load from .env / .env.local. Tests override via setEnv before import.

import path from "node:path";

function envString(name: string, fallback: string): string {
  const value = process.env[name];
  if (value === undefined || value === "") return fallback;
  return value;
}

function envBool(name: string, fallback: boolean): boolean {
  const value = process.env[name];
  if (value === undefined || value === "") return fallback;
  return value === "true" || value === "1";
}

function resolveRelativeToProject(p: string): string {
  if (path.isAbsolute(p)) return p;
  return path.resolve(process.cwd(), p);
}

export interface AppConfig {
  testMode: "fixture" | "live";
  dataDir: string;
  databaseUrl: string;
  pdfDir: string;
  textDir: string;
  translationDir: string;
  simulationDir: string;
  modelProvider: "fake" | "ollama" | string;
  defaultSource: string;
  arxivQuery: string;
  maxCandidatesPerRun: number;
  downloadAllowlist: string[];
  disableAuthenticatedDownloads: boolean;
  fixtures: {
    intake: string;
    segments: string;
    goldenQa: string;
    simulationMethod: string;
  };
}

export function loadConfig(): AppConfig {
  const projectRoot = process.cwd();
  const dataDir = resolveRelativeToProject(envString("PAPER_LAB_DATA_DIR", "./data"));
  return {
    testMode: envString("PAPER_LAB_TEST_MODE", "fixture") === "live" ? "live" : "fixture",
    dataDir,
    databaseUrl: resolveRelativeToProject(
      envString("PAPER_LAB_DATABASE_URL", path.join(dataDir, "paper-lab-agent.sqlite")),
    ),
    pdfDir: resolveRelativeToProject(envString("PAPER_LAB_PDF_DIR", path.join(dataDir, "pdfs"))),
    textDir: resolveRelativeToProject(envString("PAPER_LAB_TEXT_DIR", path.join(dataDir, "text"))),
    translationDir: resolveRelativeToProject(
      envString("PAPER_LAB_TRANSLATION_DIR", path.join(dataDir, "translations")),
    ),
    simulationDir: resolveRelativeToProject(
      envString("PAPER_LAB_SIMULATION_DIR", path.join(dataDir, "simulations")),
    ),
    modelProvider: envString("PAPER_LAB_MODEL_PROVIDER", "fake"),
    defaultSource: envString("PAPER_LAB_DEFAULT_SOURCE", "arxiv"),
    arxivQuery: envString("PAPER_LAB_ARXIV_QUERY", "cat:cs.AI"),
    maxCandidatesPerRun: Number(envString("PAPER_LAB_MAX_CANDIDATES_PER_RUN", "25")),
    downloadAllowlist: envString("PAPER_LAB_DOWNLOAD_ALLOWLIST", "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    disableAuthenticatedDownloads: envBool(
      "PAPER_LAB_DISABLE_AUTHENTICATED_DOWNLOADS",
      true,
    ),
    fixtures: {
      intake: resolveRelativeToProject(
        envString("PAPER_LAB_FIXTURE_INTAKE", "fixtures/intake/arxiv-sample.json"),
      ),
      segments: resolveRelativeToProject(
        envString("PAPER_LAB_FIXTURE_SEGMENTS", "fixtures/papers/sample-paper-segments.json"),
      ),
      goldenQa: resolveRelativeToProject(
        envString("PAPER_LAB_FIXTURE_GOLDEN_QA", "fixtures/rag/golden-questions.json"),
      ),
      simulationMethod: resolveRelativeToProject(
        envString(
          "PAPER_LAB_FIXTURE_SIMULATION_METHOD",
          "fixtures/simulation/sample-method.txt",
        ),
      ),
    },
  };
  // Reference projectRoot so consumers can debug where config is loaded from.
  void projectRoot;
}

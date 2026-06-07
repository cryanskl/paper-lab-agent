// Research profile persistence.
//
// The profile is a small JSON document stored under the configured
// `PAPER_LAB_PROFILE_PATH` (default: `data/profile.json`). It carries the
// keywords, seed references, and arXiv query that drive intake. The file
// lives under the local data dir and is gitignored.
//
// We deliberately keep this module dependency-free (Node `fs` + `path`)
// so tests can run against a temp directory without bringing in the rest
// of the app.

import fs from "node:fs";
import path from "node:path";

export interface ResearchProfile {
  /** Free-form research keywords used by relevance scoring. */
  keywords: string[];
  /** Optional arXiv category / search query applied to live intake. */
  arxivQuery: string;
  /** Max candidates to keep per intake run. */
  maxCandidates: number;
  /** Which source to run next. Phase 2 supports "arxiv" and "arxiv-fixture". */
  source: "arxiv" | "arxiv-fixture" | string;
  /** Optional seed paper ids the user already knows about. */
  seedPaperIds: string[];
}

export const DEFAULT_PROFILE: ResearchProfile = {
  keywords: [
    "physics-informed",
    "surrogate model",
    "engineering simulation",
    "neural surrogate",
    "boundary condition",
    "conservation law",
  ],
  arxivQuery: "cat:cs.AI",
  maxCandidates: 25,
  source: "arxiv-fixture",
  seedPaperIds: [],
};

export class ProfileValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ProfileValidationError";
  }
}

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function validateProfile(input: unknown): ResearchProfile {
  if (!isObject(input)) {
    throw new ProfileValidationError("profile root must be a JSON object");
  }
  const keywords = input.keywords;
  if (!Array.isArray(keywords) || keywords.some((k) => typeof k !== "string")) {
    throw new ProfileValidationError("profile.keywords must be a string[]");
  }
  const arxivQuery = input.arxivQuery;
  if (typeof arxivQuery !== "string" || arxivQuery.trim() === "") {
    throw new ProfileValidationError("profile.arxivQuery must be a non-empty string");
  }
  const maxCandidates = input.maxCandidates;
  if (typeof maxCandidates !== "number" || !Number.isFinite(maxCandidates) || maxCandidates <= 0) {
    throw new ProfileValidationError("profile.maxCandidates must be a positive number");
  }
  const source = input.source;
  if (typeof source !== "string" || source.trim() === "") {
    throw new ProfileValidationError("profile.source must be a non-empty string");
  }
  const seedPaperIds = input.seedPaperIds;
  if (!Array.isArray(seedPaperIds) || seedPaperIds.some((s) => typeof s !== "string")) {
    throw new ProfileValidationError("profile.seedPaperIds must be a string[]");
  }
  return {
    keywords: keywords.map((k) => k.trim()).filter(Boolean),
    arxivQuery: arxivQuery.trim(),
    maxCandidates: Math.floor(maxCandidates),
    source,
    seedPaperIds,
  };
}

export function loadProfileFromPath(profilePath: string): ResearchProfile {
  if (!fs.existsSync(profilePath)) {
    return { ...DEFAULT_PROFILE };
  }
  const raw = fs.readFileSync(profilePath, "utf-8");
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new ProfileValidationError(
      `failed to parse profile JSON at ${profilePath}: ${message}`,
    );
  }
  return validateProfile(parsed);
}

export function saveProfileToPath(profilePath: string, profile: ResearchProfile): void {
  // Validate first so we never write a corrupted document.
  const valid = validateProfile(profile);
  fs.mkdirSync(path.dirname(profilePath), { recursive: true });
  // Atomic write: write to a sibling tmp file then rename, so a crash
  // mid-write cannot leave the user with a half-written profile.
  const tmp = `${profilePath}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(valid, null, 2) + "\n", "utf-8");
  fs.renameSync(tmp, profilePath);
}

export function resolveProfilePath(envValue: string | undefined): string {
  const raw = envValue && envValue.trim() !== ""
    ? envValue
    : "data/profile.json";
  return path.isAbsolute(raw) ? raw : path.resolve(process.cwd(), raw);
}

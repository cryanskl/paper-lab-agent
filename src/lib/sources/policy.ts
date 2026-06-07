// Pure policy helpers for the Sources & Profile page. These are
// extracted so the Server Actions and the unit tests can share the
// same opt-in / source-classification logic without pulling in
// Next.js context.

import {
  DEFAULT_PROFILE,
  loadProfileFromPath,
  saveProfileToPath,
  type ResearchProfile,
} from "../profile";
import { isFixtureSource } from "../intake/run-intake";

export function isLiveIntakeOptedIn(envValue: string | undefined): boolean {
  return envValue === "true";
}

export function currentModelProviderName(envValue: string | undefined): string {
  return envValue && envValue.trim() !== "" ? envValue : "fake";
}

export function isOllamaLiveOptedIn(envValue: string | undefined): boolean {
  return envValue === "true";
}

export function describeModelSelection(provider: string, optIn: boolean): string {
  if (provider === "fake") return "fake (deterministic default)";
  if (provider === "ollama") {
    return optIn
      ? "ollama (live local model)"
      : "ollama configured, but PAPER_LAB_LIVE_MODEL_OPT_IN is not 'true' — refusing to start";
  }
  return `${provider} (unsupported — V1 only knows fake / ollama)`;
}

export interface ProfileFormInput {
  keywords: string;
  arxivQuery: string;
  maxCandidates: string;
  source: string;
  seedPaperIds: string;
}

export function parseProfileForm(
  input: ProfileFormInput,
  current: ResearchProfile = DEFAULT_PROFILE,
): ResearchProfile {
  const keywords = input.keywords
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);
  const arxivQuery = input.arxivQuery.trim() || current.arxivQuery;
  const maxCandidates = Math.max(
    1,
    Math.min(100, Number(input.maxCandidates) || current.maxCandidates),
  );
  const source = (input.source || current.source || "arxiv-fixture").trim();
  const seedPaperIds = input.seedPaperIds
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);
  return { keywords, arxivQuery, maxCandidates, source, seedPaperIds };
}

export function persistProfileFromForm(
  profilePath: string,
  input: ProfileFormInput,
): ResearchProfile {
  const current = loadProfileFromPath(profilePath);
  const next = parseProfileForm(input, current);
  saveProfileToPath(profilePath, next);
  return next;
}

export function classifyRunMode(source: string): "fixture" | "live" {
  return isFixtureSource(source) ? "fixture" : "live";
}

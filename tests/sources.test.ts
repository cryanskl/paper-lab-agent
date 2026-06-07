import { describe, it, expect, beforeAll, afterAll } from "vitest";
import path from "node:path";
import fs from "node:fs";
import {
  setupTempDataDir,
  teardownTempDataDir,
} from "./helpers/setup";
import {
  isLiveIntakeOptedIn,
  parseProfileForm,
  persistProfileFromForm,
  classifyRunMode,
  currentModelProviderName,
  isOllamaLiveOptedIn,
  describeModelSelection,
} from "@/lib/sources/policy";
import { DEFAULT_PROFILE, loadProfileFromPath } from "@/lib/profile";

describe("sources & profile policy", () => {
  beforeAll(() => {
    setupTempDataDir();
  });
  afterAll(() => {
    teardownTempDataDir();
  });

  it("isLiveIntakeOptedIn only accepts the literal string 'true'", () => {
    expect(isLiveIntakeOptedIn("true")).toBe(true);
    expect(isLiveIntakeOptedIn("TRUE")).toBe(false);
    expect(isLiveIntakeOptedIn("1")).toBe(false);
    expect(isLiveIntakeOptedIn("yes")).toBe(false);
    expect(isLiveIntakeOptedIn(undefined)).toBe(false);
    expect(isLiveIntakeOptedIn("")).toBe(false);
  });

  it("parseProfileForm normalizes comma and newline separators", () => {
    const next = parseProfileForm({
      keywords: "physics-informed, neural surrogate\nconservation law",
      arxivQuery: "cat:cs.AI",
      maxCandidates: "12",
      source: "arxiv",
      seedPaperIds: "paper-2606-00001\npaper-2606-00002",
    });
    expect(next.keywords).toEqual([
      "physics-informed",
      "neural surrogate",
      "conservation law",
    ]);
    expect(next.arxivQuery).toBe("cat:cs.AI");
    expect(next.maxCandidates).toBe(12);
    expect(next.source).toBe("arxiv");
    expect(next.seedPaperIds).toEqual([
      "paper-2606-00001",
      "paper-2606-00002",
    ]);
  });

  it("parseProfileForm falls back to current values when the user leaves fields blank", () => {
    const current = { ...DEFAULT_PROFILE, arxivQuery: "all:physics" };
    const next = parseProfileForm(
      {
        keywords: "",
        arxivQuery: "",
        maxCandidates: "",
        source: "",
        seedPaperIds: "",
      },
      current,
    );
    // Blank keywords intentionally yield no keywords (user cleared
    // them) — this is not silently restored from current. arxivQuery
    // and source should fall back.
    expect(next.keywords).toEqual([]);
    expect(next.arxivQuery).toBe("all:physics");
    expect(next.source).toBe(current.source);
  });

  it("parseProfileForm clamps maxCandidates to a sane range", () => {
    const a = parseProfileForm({
      keywords: "k",
      arxivQuery: "q",
      maxCandidates: "9999",
      source: "arxiv",
      seedPaperIds: "",
    });
    expect(a.maxCandidates).toBeLessThanOrEqual(100);
    const b = parseProfileForm({
      keywords: "k",
      arxivQuery: "q",
      maxCandidates: "0",
      source: "arxiv",
      seedPaperIds: "",
    });
    expect(b.maxCandidates).toBeGreaterThanOrEqual(1);
  });

  it("persistProfileFromForm writes the parsed profile to disk and reloads it", () => {
    const profilePath = path.join(process.env.PAPER_LAB_DATA_DIR!, "profile-from-form.json");
    const next = persistProfileFromForm(profilePath, {
      keywords: "a, b, c",
      arxivQuery: "q",
      maxCandidates: "5",
      source: "arxiv",
      seedPaperIds: "",
    });
    expect(fs.existsSync(profilePath)).toBe(true);
    const reloaded = loadProfileFromPath(profilePath);
    expect(reloaded).toEqual(next);
  });

  it("classifyRunMode maps fixture and live sources correctly", () => {
    expect(classifyRunMode("arxiv-fixture")).toBe("fixture");
    expect(classifyRunMode("rss-fixture")).toBe("fixture");
    expect(classifyRunMode("arxiv")).toBe("live");
    expect(classifyRunMode("openalex")).toBe("live");
  });

  it("currentModelProviderName defaults to 'fake' on undefined / empty", () => {
    expect(currentModelProviderName(undefined)).toBe("fake");
    expect(currentModelProviderName("")).toBe("fake");
    expect(currentModelProviderName("ollama")).toBe("ollama");
  });

  it("isOllamaLiveOptedIn only accepts 'true'", () => {
    expect(isOllamaLiveOptedIn("true")).toBe(true);
    expect(isOllamaLiveOptedIn("1")).toBe(false);
    expect(isOllamaLiveOptedIn(undefined)).toBe(false);
  });

  it("describeModelSelection gives a clear label for each state", () => {
    expect(describeModelSelection("fake", false)).toMatch(/deterministic default/);
    expect(describeModelSelection("ollama", true)).toMatch(/live local model/);
    expect(describeModelSelection("ollama", false)).toMatch(/refusing to start/);
    expect(describeModelSelection("openai", false)).toMatch(/unsupported/);
  });
});

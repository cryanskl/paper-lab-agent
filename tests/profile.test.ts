import { describe, it, expect, beforeAll, afterAll } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { setupTempDataDir, teardownTempDataDir } from "./helpers/setup";
import {
  DEFAULT_PROFILE,
  loadProfileFromPath,
  saveProfileToPath,
  resolveProfilePath,
  ProfileValidationError,
} from "@/lib/profile";

describe("research profile", () => {
  beforeAll(() => {
    setupTempDataDir();
  });
  afterAll(() => {
    teardownTempDataDir();
  });

  it("returns the default profile when the file is missing", () => {
    const profilePath = path.join(process.env.PAPER_LAB_DATA_DIR!, "profile.json");
    expect(fs.existsSync(profilePath)).toBe(false);
    const profile = loadProfileFromPath(profilePath);
    expect(profile).toEqual(DEFAULT_PROFILE);
    // The defaults are the same keywords Phase 1 used inline, so the
    // intake fixture test's accepted paper must still match.
    expect(profile.keywords).toContain("physics-informed");
  });

  it("persists the profile to disk and reloads it", () => {
    const profilePath = path.join(process.env.PAPER_LAB_DATA_DIR!, "profile-persisted.json");
    const next = {
      ...DEFAULT_PROFILE,
      keywords: ["machine learning", "fluid dynamics"],
      arxivQuery: "cat:physics.comp-ph",
      maxCandidates: 7,
      source: "arxiv",
      seedPaperIds: ["paper-2606-00001"],
    };
    saveProfileToPath(profilePath, next);
    expect(fs.existsSync(profilePath)).toBe(true);

    const reloaded = loadProfileFromPath(profilePath);
    expect(reloaded).toEqual(next);
  });

  it("rejects malformed JSON with a typed error", () => {
    const profilePath = path.join(process.env.PAPER_LAB_DATA_DIR!, "profile-bad.json");
    fs.writeFileSync(profilePath, "{ not valid json", "utf-8");
    expect(() => loadProfileFromPath(profilePath)).toThrow(ProfileValidationError);
  });

  it("rejects a profile that is missing required fields", () => {
    const profilePath = path.join(process.env.PAPER_LAB_DATA_DIR!, "profile-shape.json");
    fs.writeFileSync(profilePath, JSON.stringify({ keywords: "not-an-array" }), "utf-8");
    expect(() => loadProfileFromPath(profilePath)).toThrow(/keywords/);
  });

  it("rejects a profile that is not an object", () => {
    const profilePath = path.join(process.env.PAPER_LAB_DATA_DIR!, "profile-root.json");
    fs.writeFileSync(profilePath, JSON.stringify(["just", "an", "array"]), "utf-8");
    expect(() => loadProfileFromPath(profilePath)).toThrow(/root/);
  });

  it("writes the profile atomically via a tmp file and rename", () => {
    const profilePath = path.join(process.env.PAPER_LAB_DATA_DIR!, "profile-atomic.json");
    saveProfileToPath(profilePath, { ...DEFAULT_PROFILE, maxCandidates: 9 });
    // After the rename the final file should exist and contain the value.
    const reloaded = loadProfileFromPath(profilePath);
    expect(reloaded.maxCandidates).toBe(9);
    // And there should be no stray .tmp file left behind.
    const stray = fs.readdirSync(process.env.PAPER_LAB_DATA_DIR!).find((f) =>
      f.includes("profile-atomic.json") && f.endsWith(".tmp"),
    );
    expect(stray).toBeUndefined();
  });

  it("resolveProfilePath honors an absolute path and falls back to data/profile.json", () => {
    const abs = path.join(process.env.PAPER_LAB_DATA_DIR!, "abs.json");
    expect(resolveProfilePath(abs)).toBe(abs);
    const rel = resolveProfilePath("relative/profile.json");
    expect(rel).toBe(path.resolve(process.cwd(), "relative/profile.json"));
    expect(resolveProfilePath(undefined)).toBe(
      path.resolve(process.cwd(), "data/profile.json"),
    );
    expect(resolveProfilePath("")).toBe(path.resolve(process.cwd(), "data/profile.json"));
  });
});

"use server";

// Server actions for the Sources & Profile page. These are the only
// entry points that touch the profile file and the live arXiv network.
// Live intake is explicitly gated on PAPER_LAB_LIVE_INTAKE_OPT_IN.
//
// The page itself reads profile + intake_runs on every render, so after
// a successful action we revalidate and redirect back to /sources. The
// page will then show the new state without any flash banner.

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import {
  loadProfileFromPath,
  resolveProfilePath,
  type ResearchProfile,
} from "@/lib/profile";
import { importIntakeFixture, listIntakeRuns } from "@/lib/intake/import-fixture";
import { fetchArxivCandidates } from "@/lib/intake/arxiv-client";
import { runIntake, type NormalizedCandidate } from "@/lib/intake/run-intake";
import { loadConfig } from "@/lib/config";
import { isLiveIntakeOptedIn, persistProfileFromForm } from "@/lib/sources/policy";
import {
  runDownloadForAcceptedPapers,
  summarizeDownloadResult,
  isLiveDownloadOptedIn,
} from "@/lib/download/run-download";

function envOptedIn(): boolean {
  return isLiveIntakeOptedIn(process.env.PAPER_LAB_LIVE_INTAKE_OPT_IN);
}

function readProfileSafe(): ResearchProfile {
  const profilePath = resolveProfilePath(process.env.PAPER_LAB_PROFILE_PATH);
  return loadProfileFromPath(profilePath);
}

export async function saveProfileAction(formData: FormData): Promise<void> {
  try {
    const profilePath = resolveProfilePath(process.env.PAPER_LAB_PROFILE_PATH);
    persistProfileFromForm(profilePath, {
      keywords: String(formData.get("keywords") ?? ""),
      arxivQuery: String(formData.get("arxivQuery") ?? ""),
      maxCandidates: String(formData.get("maxCandidates") ?? "25"),
      source: String(formData.get("source") ?? "arxiv-fixture"),
      seedPaperIds: String(formData.get("seedPaperIds") ?? ""),
    });
  } catch (err) {
    // Profile validation errors are surface-able to the operator via
    // the server logs. The redirect below still lands on /sources so
    // the user can fix the form without losing their input.
    console.error("saveProfileAction failed:", err);
  }
  revalidatePath("/sources");
  redirect("/sources");
}

export async function runFixtureIntakeAction(): Promise<void> {
  try {
    const cfg = loadConfig();
    importIntakeFixture(cfg.fixtures.intake);
  } catch (err) {
    console.error("runFixtureIntakeAction failed:", err);
  }
  revalidatePath("/sources");
  revalidatePath("/library");
  revalidatePath("/");
  redirect("/sources");
}

export async function runLiveArxivIntakeAction(): Promise<void> {
  // The action is wired to the live button, but the button is also
  // rendered disabled in the UI when opt-in is off. We double-check
  // here so a direct POST cannot bypass the gate.
  if (!envOptedIn()) {
    console.warn("runLiveArxivIntakeAction called without PAPER_LAB_LIVE_INTAKE_OPT_IN");
    redirect("/sources?live=blocked");
    return;
  }
  try {
    const profile = readProfileSafe();
    const maxResults = Math.max(1, Math.min(50, profile.maxCandidates));
    const candidatesRaw = await fetchArxivCandidates(profile.arxivQuery, {
      allowNetwork: true,
      maxResults,
    });
    const candidates: NormalizedCandidate[] = candidatesRaw.map((c) => ({
      externalId: `arxiv:${c.arxivId}`,
      title: c.title,
      authors: c.authors,
      abstract: c.abstract,
      sourceUrl: c.sourceUrl,
      pdfUrl: c.pdfUrl,
      publishedAt: c.publishedAt,
      keywords: c.rawKeywords,
    }));
    runIntake({
      source: "arxiv",
      query: profile.arxivQuery,
      candidates,
    });
  } catch (err) {
    console.error("runLiveArxivIntakeAction failed:", err);
  }
  revalidatePath("/sources");
  revalidatePath("/library");
  revalidatePath("/");
  redirect("/sources?live=ok");
}

export async function listIntakeRunsForUi(): Promise<ReturnType<typeof listIntakeRuns>> {
  return listIntakeRuns();
}

export async function runDownloadAllAction(): Promise<void> {
  try {
    const cfg = loadConfig();
    const result = await runDownloadForAcceptedPapers({
      pdfDir: cfg.pdfDir,
      allowList: cfg.downloadAllowlist,
      disableAuthenticated: cfg.disableAuthenticatedDownloads,
      liveNetwork: isLiveDownloadOptedIn(process.env.PAPER_LAB_DOWNLOAD_LIVE_OPT_IN),
    });
    console.info("runDownloadAllAction:", summarizeDownloadResult(result));
  } catch (err) {
    console.error("runDownloadAllAction failed:", err);
  }
  revalidatePath("/sources");
  revalidatePath("/library");
  redirect("/sources?download=done");
}

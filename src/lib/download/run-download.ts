// Server-side orchestration for the "Download PDFs for accepted
// papers" action. This module is a pure async function (no Next.js
// imports) so the unit tests can drive it without booting a server.
//
// Default behavior is no-network: the `fetchImpl` argument must be
// passed in (the test suite uses a stub; the action uses a global
// fetch only when PAPER_LAB_DOWNLOAD_LIVE_OPT_IN is set).

import { listAcceptedPapers, getPaper } from "../library/papers";
import { upsertParsedSegments } from "../library/segments";
import { getDb } from "../db";
import { parsePdfFromText, PdfParseError } from "../pdf/parse-pdf";
import { segmentText } from "../pdf/segment-text";
import {
  downloadPdf,
  applyOutcomeToPaper,
  type DownloadOutcome,
} from "./pdf-downloader";

export interface RunDownloadOptions {
  pdfDir: string;
  allowList: readonly string[];
  disableAuthenticated: boolean;
  fetchImpl?: typeof fetch;
  /** When false (default), only the local fetch stub is used. The
   *  Server Action sets this to true only when
   *  PAPER_LAB_DOWNLOAD_LIVE_OPT_IN is enabled. */
  liveNetwork?: boolean;
}

export interface PerPaperDownload {
  paperId: string;
  outcome: DownloadOutcome;
  segmentsInserted: number;
  segmentsPreserved: number;
  parseError: string | null;
}

export interface RunDownloadResult {
  attempted: number;
  succeeded: number;
  failed: number;
  totalSegments: number;
  perPaper: PerPaperDownload[];
}

function updatePaperRow(paperId: string, outcome: DownloadOutcome): void {
  const db = getDb();
  const patch = applyOutcomeToPaper({ paper: getPaper(paperId)!, outcome });
  db.prepare(
    `UPDATE papers
        SET downloadStatus = ?, downloadError = ?, pdfPath = ?
      WHERE paperId = ?`,
  ).run(patch.downloadStatus, patch.downloadError, patch.pdfPath, paperId);
}

function readPaperBytes(pdfPath: string): Buffer | null {
  // Lazy import fs to keep this module small in the no-network
  // default tests, which never reach this code path.
  const fs = require("node:fs") as typeof import("node:fs");
  try {
    return fs.readFileSync(pdfPath);
  } catch {
    return null;
  }
}

export async function runDownloadForAcceptedPapers(
  options: RunDownloadOptions,
): Promise<RunDownloadResult> {
  const accepted = listAcceptedPapers();
  const perPaper: PerPaperDownload[] = [];
  let totalSegments = 0;
  let succeeded = 0;
  let failed = 0;

  for (const paper of accepted) {
    const outcome = await downloadPdf({
      paper,
      pdfDir: options.pdfDir,
      allowList: options.allowList,
      disableAuthenticated: options.disableAuthenticated,
      ...(options.fetchImpl ? { fetchImpl: options.fetchImpl } : {}),
    });
    updatePaperRow(paper.paperId, outcome);

    let segmentsInserted = 0;
    let segmentsPreserved = 0;
    let parseError: string | null = null;

    if (outcome.ok && outcome.localPath) {
      const buf = readPaperBytes(outcome.localPath);
      if (buf) {
        let text: string;
        try {
          text = parsePdfFromText(buf);
        } catch (err) {
          parseError = err instanceof PdfParseError
            ? err.message
            : err instanceof Error
              ? err.message
              : String(err);
          text = "";
        }
        if (text) {
          const segs = segmentText({ paperId: paper.paperId, text });
          const r = upsertParsedSegments(paper.paperId, segs);
          segmentsInserted = r.insertedCount;
          segmentsPreserved = r.replacedCount;
          totalSegments += segs.length;
        }
      } else {
        parseError = "local-pdf-unreadable";
      }
    }

    perPaper.push({
      paperId: paper.paperId,
      outcome,
      segmentsInserted,
      segmentsPreserved,
      parseError,
    });

    if (outcome.ok) succeeded += 1;
    else failed += 1;
  }

  return {
    attempted: accepted.length,
    succeeded,
    failed,
    totalSegments,
    perPaper,
  };
}

export function summarizeDownloadResult(r: RunDownloadResult): string {
  if (r.attempted === 0) return "No accepted papers to download.";
  const segInfo = r.totalSegments > 0
    ? ` ${r.totalSegments} segment(s) upserted.`
    : "";
  return `Downloaded ${r.succeeded}/${r.attempted} (failed=${r.failed}).${segInfo}`;
}

export function isLiveDownloadOptedIn(envValue: string | undefined): boolean {
  return envValue === "true";
}

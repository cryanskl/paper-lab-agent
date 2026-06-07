// Open-PDF downloader. Side-effect aware (it writes to the local
// `data/pdfs/` dir) but never makes a real network call when given
// a stubbed `fetchImpl`. The default `fetchImpl` is `globalThis.fetch`
// gated behind the policy layer; tests always pass a stub.

import fs from "node:fs";
import path from "node:path";
import { canDownloadPdf, derivePdfLocalPath, type DownloadPolicyDecision } from "./policy";
import type { Paper } from "@/types/domain";

export type DownloadOutcomeStatus = "succeeded" | "download_failed";

export interface DownloadOutcome {
  ok: boolean;
  status: DownloadOutcomeStatus;
  reason: string;
  localPath: string | null;
  bytes: number;
  contentType: string | null;
}

export interface DownloadPdfOptions {
  paper: Paper;
  pdfDir: string;
  allowList: readonly string[];
  disableAuthenticated: boolean;
  fetchImpl?: typeof fetch;
  /** Override the timeout in ms; defaults to 30000. */
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 30_000;

function reasonFromPolicy(policy: DownloadPolicyDecision, fallback: string): string {
  return policy.allowed ? fallback : policy.reason;
}

export async function downloadPdf(options: DownloadPdfOptions): Promise<DownloadOutcome> {
  const policy = canDownloadPdf({
    pdfUrl: options.paper.pdfUrl,
    source: options.paper.source,
    allowList: options.allowList,
    disableAuthenticated: options.disableAuthenticated,
  });

  const localPath = derivePdfLocalPath(options.pdfDir, options.paper.paperId);

  if (!policy.allowed) {
    return {
      ok: false,
      status: "download_failed",
      reason: policy.reason,
      localPath: null,
      bytes: 0,
      contentType: null,
    };
  }

  const fetchImpl = options.fetchImpl ?? globalThis.fetch;
  if (typeof fetchImpl !== "function") {
    return {
      ok: false,
      status: "download_failed",
      reason: "fetch-unavailable",
      localPath: null,
      bytes: 0,
      contentType: null,
    };
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  try {
    const res = await fetchImpl(options.paper.pdfUrl as string, {
      signal: controller.signal,
      headers: { "user-agent": "paper-lab-agent/0.1 (local research assistant)" },
    });
    if (!res.ok) {
      return {
        ok: false,
        status: "download_failed",
        reason: reasonFromPolicy(policy, `http-${res.status}`),
        localPath: null,
        bytes: 0,
        contentType: res.headers.get("content-type"),
      };
    }
    const contentType = res.headers.get("content-type");
    // arXiv PDFs come back as application/pdf, but be lenient: also
    // accept application/octet-stream which some mirrors use.
    if (
      contentType &&
      !/application\/(pdf|octet-stream)/i.test(contentType)
    ) {
      return {
        ok: false,
        status: "download_failed",
        reason: `unexpected-content-type:${contentType}`,
        localPath: null,
        bytes: 0,
        contentType,
      };
    }
    const buf = Buffer.from(await res.arrayBuffer());
    if (buf.length === 0) {
      return {
        ok: false,
        status: "download_failed",
        reason: "empty-body",
        localPath: null,
        bytes: 0,
        contentType,
      };
    }
    fs.mkdirSync(path.dirname(localPath), { recursive: true });
    // Atomic write so a crash mid-write never leaves a half-PDF.
    const tmp = `${localPath}.${process.pid}.tmp`;
    fs.writeFileSync(tmp, buf);
    fs.renameSync(tmp, localPath);
    return {
      ok: true,
      status: "succeeded",
      reason: "ok",
      localPath,
      bytes: buf.length,
      contentType,
    };
  } catch (err) {
    const reason =
      err instanceof Error
        ? `fetch-error:${err.name || "Error"}:${err.message}`
        : "fetch-error:unknown";
    return {
      ok: false,
      status: "download_failed",
      reason: reasonFromPolicy(policy, reason),
      localPath: null,
      bytes: 0,
      contentType: null,
    };
  } finally {
    clearTimeout(timer);
  }
}

export interface ApplyOutcomeToPaperInput {
  paper: Paper;
  outcome: DownloadOutcome;
}

/** Returns a new Paper-like partial suitable for an UPDATE statement. */
export function applyOutcomeToPaper(input: ApplyOutcomeToPaperInput): {
  downloadStatus: Paper["downloadStatus"];
  downloadError: string | null;
  pdfPath: string | null;
} {
  return {
    downloadStatus: input.outcome.status,
    downloadError: input.outcome.ok ? null : input.outcome.reason,
    pdfPath: input.outcome.localPath,
  };
}

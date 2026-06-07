// Download policy for the open-PDF intake path.
//
// This module is intentionally side-effect free: it never touches the
// network, never opens a file, and never imports Node fs. It returns
// structured decisions that the downloader and the UI both consume.
//
// Phase 3 only ever downloads *directly accessible* PDFs (per
// docs/source-and-download-policy.md). Authenticated downloads are
// rejected by default. The allowlist is the user-controlled list of
// trusted domains; arXiv is the canonical example.

export interface DownloadPolicyInput {
  pdfUrl: string | null;
  source: string;
  allowList: readonly string[];
  disableAuthenticated: boolean;
}

export interface DownloadPolicyDecision {
  allowed: boolean;
  reason: string;
}

const ALLOW_RE = /^https?:\/\//i;

export function canDownloadPdf(input: DownloadPolicyInput): DownloadPolicyDecision {
  if (!input.pdfUrl) {
    return { allowed: false, reason: "missing-pdf-url" };
  }
  if (!ALLOW_RE.test(input.pdfUrl)) {
    return { allowed: false, reason: "pdf-url-not-http" };
  }
  if (input.disableAuthenticated && /:\/\/[^/]*@/.test(input.pdfUrl)) {
    return { allowed: false, reason: "authenticated-url-rejected" };
  }
  let host: string;
  try {
    host = new URL(input.pdfUrl).host.toLowerCase();
  } catch {
    return { allowed: false, reason: "pdf-url-malformed" };
  }
  if (input.allowList.length === 0) {
    return { allowed: false, reason: "no-allowlist-configured" };
  }
  const normalized = input.allowList.map((d) => d.toLowerCase());
  const matched = normalized.some(
    (allowed) => host === allowed || host.endsWith(`.${allowed}`),
  );
  if (!matched) {
    return { allowed: false, reason: `host-not-allowlisted:${host}` };
  }
  return { allowed: true, reason: "ok" };
}

export function derivePdfLocalPath(pdfDir: string, paperId: string): string {
  // Sanitize the paperId so a hostile value cannot escape the pdf dir.
  const safe = paperId.replace(/[^a-zA-Z0-9._-]/g, "_");
  return `${pdfDir.replace(/\/+$/, "")}/${safe}.pdf`;
}

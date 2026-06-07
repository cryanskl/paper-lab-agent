import { describe, it, expect, beforeAll, afterAll } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { setupTempDataDir, teardownTempDataDir } from "./helpers/setup";
import { canDownloadPdf, derivePdfLocalPath } from "@/lib/download/policy";
import { downloadPdf, applyOutcomeToPaper } from "@/lib/download/pdf-downloader";
import { loadConfig } from "@/lib/config";
import type { Paper } from "@/types/domain";

function makePaper(overrides: Partial<Paper> = {}): Paper {
  return {
    paperId: "paper-2606-00010",
    externalId: "arxiv:2606.00010",
    source: "arxiv",
    title: "Sample Physics-Informed Surrogate",
    authors: ["E. Engineer"],
    abstract: "An abstract",
    sourceUrl: "https://arxiv.org/abs/2606.00010",
    pdfUrl: "https://arxiv.org/pdf/2606.00010.pdf",
    pdfPath: null,
    publishedAt: "2026-06-03T00:00:00Z",
    status: "accepted",
    relevanceRationale: "matches",
    downloadStatus: "not_attempted",
    downloadError: null,
    keywords: ["neural surrogate"],
    importedAt: "2026-06-03T00:00:00Z",
    ...overrides,
  };
}

describe("download policy", () => {
  it("allows arXiv URLs when arxiv.org is in the allowlist", () => {
    const r = canDownloadPdf({
      pdfUrl: "https://arxiv.org/pdf/2606.00010.pdf",
      source: "arxiv",
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
    });
    expect(r.allowed).toBe(true);
    expect(r.reason).toBe("ok");
  });

  it("rejects when pdfUrl is missing", () => {
    const r = canDownloadPdf({
      pdfUrl: null,
      source: "arxiv",
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
    });
    expect(r.allowed).toBe(false);
    expect(r.reason).toBe("missing-pdf-url");
  });

  it("rejects non-http(s) URLs", () => {
    const r = canDownloadPdf({
      pdfUrl: "file:///etc/passwd",
      source: "arxiv",
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
    });
    expect(r.allowed).toBe(false);
    expect(r.reason).toBe("pdf-url-not-http");
  });

  it("rejects authenticated URLs when disableAuthenticated is true", () => {
    const r = canDownloadPdf({
      pdfUrl: "https://user:pass@arxiv.org/pdf/1.pdf",
      source: "arxiv",
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
    });
    expect(r.allowed).toBe(false);
    expect(r.reason).toBe("authenticated-url-rejected");
  });

  it("rejects hosts that are not in the allowlist", () => {
    const r = canDownloadPdf({
      pdfUrl: "https://example.com/paper.pdf",
      source: "arxiv",
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
    });
    expect(r.allowed).toBe(false);
    expect(r.reason).toMatch(/host-not-allowlisted/);
  });

  it("accepts subdomains of allowlist entries", () => {
    const r = canDownloadPdf({
      pdfUrl: "https://export.arxiv.org/pdf/1.pdf",
      source: "arxiv",
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
    });
    expect(r.allowed).toBe(true);
  });

  it("rejects when the allowlist is empty", () => {
    const r = canDownloadPdf({
      pdfUrl: "https://arxiv.org/pdf/1.pdf",
      source: "arxiv",
      allowList: [],
      disableAuthenticated: true,
    });
    expect(r.allowed).toBe(false);
    expect(r.reason).toBe("no-allowlist-configured");
  });

  it("rejects malformed URLs", () => {
    const r = canDownloadPdf({
      pdfUrl: "not a url",
      source: "arxiv",
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
    });
    expect(r.allowed).toBe(false);
    // "not a url" has no http(s):// prefix, so the policy trips on
    // the http-shape check before it tries to construct a URL.
    expect(r.reason).toBe("pdf-url-not-http");
  });

  it("derives a safe local path from paperId", () => {
    const p = derivePdfLocalPath("/tmp/pdfs", "../etc/passwd");
    expect(p).toBe("/tmp/pdfs/.._etc_passwd.pdf");
    expect(p).toMatch(/\.pdf$/);
  });
});

describe("PDF downloader (no real network)", () => {
  beforeAll(() => {
    setupTempDataDir();
  });
  afterAll(() => {
    teardownTempDataDir();
  });

  it("returns a missing-pdf-url failure without ever calling fetch", async () => {
    const calls: string[] = [];
    const stubFetch = (async (url: string) => {
      calls.push(url);
      throw new Error("fetch should not be called for missing pdfUrl");
    }) as unknown as typeof fetch;
    const out = await downloadPdf({
      paper: makePaper({ pdfUrl: null }),
      pdfDir: process.env.PAPER_LAB_PDF_DIR!,
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
      fetchImpl: stubFetch,
    });
    expect(calls).toHaveLength(0);
    expect(out.ok).toBe(false);
    expect(out.status).toBe("download_failed");
    expect(out.reason).toBe("missing-pdf-url");
  });

  it("writes the PDF to disk on a successful fetch and reports bytes", async () => {
    const stubFetch = (async () =>
      new Response("%PDF-1.4 fake bytes", {
        status: 200,
        headers: { "content-type": "application/pdf" },
      })) as unknown as typeof fetch;
    const out = await downloadPdf({
      paper: makePaper({ paperId: "paper-pdf-ok" }),
      pdfDir: process.env.PAPER_LAB_PDF_DIR!,
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
      fetchImpl: stubFetch,
    });
    expect(out.ok).toBe(true);
    expect(out.status).toBe("succeeded");
    expect(out.localPath).toMatch(/paper-pdf-ok\.pdf$/);
    expect(out.bytes).toBeGreaterThan(0);
    expect(fs.existsSync(out.localPath!)).toBe(true);
  });

  it("records a download_failed outcome with non-2xx status", async () => {
    const stubFetch = (async () =>
      new Response("forbidden", {
        status: 403,
        headers: { "content-type": "text/plain" },
      })) as unknown as typeof fetch;
    const out = await downloadPdf({
      paper: makePaper({ paperId: "paper-pdf-403" }),
      pdfDir: process.env.PAPER_LAB_PDF_DIR!,
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
      fetchImpl: stubFetch,
    });
    expect(out.ok).toBe(false);
    expect(out.reason).toBe("http-403");
  });

  it("rejects unexpected content types", async () => {
    const stubFetch = (async () =>
      new Response("<html>nope</html>", {
        status: 200,
        headers: { "content-type": "text/html" },
      })) as unknown as typeof fetch;
    const out = await downloadPdf({
      paper: makePaper({ paperId: "paper-pdf-html" }),
      pdfDir: process.env.PAPER_LAB_PDF_DIR!,
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
      fetchImpl: stubFetch,
    });
    expect(out.ok).toBe(false);
    expect(out.reason).toMatch(/unexpected-content-type/);
  });

  it("rejects an empty body", async () => {
    const stubFetch = (async () =>
      new Response("", {
        status: 200,
        headers: { "content-type": "application/pdf" },
      })) as unknown as typeof fetch;
    const out = await downloadPdf({
      paper: makePaper({ paperId: "paper-pdf-empty" }),
      pdfDir: process.env.PAPER_LAB_PDF_DIR!,
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
      fetchImpl: stubFetch,
    });
    expect(out.ok).toBe(false);
    expect(out.reason).toBe("empty-body");
  });

  it("records a fetch error when the network call throws", async () => {
    const stubFetch = (async () => {
      throw new Error("ECONNREFUSED");
    }) as unknown as typeof fetch;
    const out = await downloadPdf({
      paper: makePaper({ paperId: "paper-pdf-throw" }),
      pdfDir: process.env.PAPER_LAB_PDF_DIR!,
      allowList: ["arxiv.org"],
      disableAuthenticated: true,
      fetchImpl: stubFetch,
    });
    expect(out.ok).toBe(false);
    expect(out.reason).toMatch(/fetch-error/);
  });

  it("applyOutcomeToPaper maps the outcome onto the Paper shape", () => {
    const paper = makePaper();
    const succeeded = applyOutcomeToPaper({
      paper,
      outcome: {
        ok: true,
        status: "succeeded",
        reason: "ok",
        localPath: "/data/pdfs/x.pdf",
        bytes: 42,
        contentType: "application/pdf",
      },
    });
    expect(succeeded.downloadStatus).toBe("succeeded");
    expect(succeeded.downloadError).toBeNull();
    expect(succeeded.pdfPath).toBe("/data/pdfs/x.pdf");
    const failed = applyOutcomeToPaper({
      paper,
      outcome: {
        ok: false,
        status: "download_failed",
        reason: "host-not-allowlisted:example.com",
        localPath: null,
        bytes: 0,
        contentType: null,
      },
    });
    expect(failed.downloadStatus).toBe("download_failed");
    expect(failed.downloadError).toBe("host-not-allowlisted:example.com");
    expect(failed.pdfPath).toBeNull();
  });
});

describe("download layer respects config defaults", () => {
  beforeAll(() => {
    setupTempDataDir();
  });
  afterAll(() => {
    teardownTempDataDir();
  });

  it("loads PAPER_LAB_PDF_DIR from config", () => {
    const cfg = loadConfig();
    expect(cfg.pdfDir).toBe(process.env.PAPER_LAB_PDF_DIR);
    expect(path.basename(cfg.pdfDir)).toBe("pdfs");
  });
});

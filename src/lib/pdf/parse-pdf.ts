// PDF text extraction. Phase 3 ships two paths:
//
//   1. The default path: parsePdfFromText(text) is a pure function
//      that returns the input as-is. This is what the no-network
//      tests use, and it lets the rest of the pipeline be exercised
//      against a recorded text fixture.
//
//   2. An optional real-PDF path: extractPdfFromBuffer(buffer) uses
//      `pdf-parse` (a popular pure-JS PDF reader) via a dynamic
//      import. It is never invoked by the default test suite. If
//      the dependency is missing or the PDF is unreadable, it
//      throws a typed error and the caller can fall back to the
//      text-only path.

export class PdfParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PdfParseError";
  }
}

export function parsePdfFromText(input: string | Buffer): string {
  if (typeof input === "string") return input;
  // For a string-only pipeline we still accept Buffers and decode
  // them as UTF-8; this is useful when the caller already read a
  // text-style fixture from disk.
  try {
    return Buffer.isBuffer(input) ? input.toString("utf-8") : String(input);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new PdfParseError(`failed to decode PDF text input: ${message}`);
  }
}

export interface PdfExtractionResult {
  text: string;
  pages: number;
  source: "text" | "pdf-parse";
}

export async function extractPdfFromBuffer(buffer: Buffer): Promise<PdfExtractionResult> {
  // Dynamic import: `pdf-parse` is an optional dep so the default
  // install does not pay the (small) JS cost of loading it. If the
  // package is not installed, we surface a typed error and the
  // caller decides whether to fall back to the text path.
  let mod: { default?: (b: Buffer) => Promise<{ text: string; numpages: number }> };
  try {
    // `pdf-parse` is an optional dependency. It is loaded only when
    // a real PDF buffer is being parsed; the default test suite
    // never reaches this code path. If the package is missing, the
    // catch block below raises a typed PdfParseError and the caller
    // can fall back to the text-only path.
    // @ts-expect-error optional dep, only present when pdf-parse is installed
    mod = (await import("pdf-parse")) as typeof mod;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new PdfParseError(`pdf-parse is not installed: ${message}`);
  }
  const fn = mod.default ?? (mod as unknown as (b: Buffer) => Promise<{ text: string; numpages: number }>);
  if (typeof fn !== "function") {
    throw new PdfParseError("pdf-parse module did not export a function");
  }
  try {
    const out = await fn(buffer);
    return {
      text: typeof out.text === "string" ? out.text : "",
      pages: Number(out.numpages) || 0,
      source: "pdf-parse",
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new PdfParseError(`pdf-parse failed: ${message}`);
  }
}

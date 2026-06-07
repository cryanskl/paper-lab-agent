import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { parsePdfFromText, PdfParseError } from "@/lib/pdf/parse-pdf";
import { segmentText, segmentTextFromString } from "@/lib/pdf/segment-text";

const FIXTURE_PATH = path.resolve(process.cwd(), "fixtures/pdf/sample-paper.txt");

describe("parsePdfFromText (text-only path)", () => {
  it("returns string input unchanged", () => {
    const text = "hello\nworld\n";
    expect(parsePdfFromText(text)).toBe(text);
  });

  it("decodes Buffer input as utf-8", () => {
    const out = parsePdfFromText(Buffer.from("héllo", "utf-8"));
    expect(out).toBe("héllo");
  });

  it("wraps decoder errors in PdfParseError", () => {
    // A non-string, non-buffer input should still produce a typed error
    // rather than silently coercing.
    const weird = { toString: () => { throw new Error("boom"); } } as unknown as Buffer;
    expect(() => parsePdfFromText(weird)).toThrow(PdfParseError);
  });
});

describe("segmentText (no real network)", () => {
  it("reads the recorded text fixture and segments it", () => {
    const text = fs.readFileSync(FIXTURE_PATH, "utf-8");
    const segments = segmentText({ paperId: "paper-pdf-001", text });
    expect(segments.length).toBeGreaterThan(0);
    // First segment is a title-like single-line paragraph.
    expect(segments[0].english).toMatch(/Physics-Informed Surrogate/);
    // Segments are 0-indexed in `order` and 1-indexed in `segmentId`.
    expect(segments[0].order).toBe(0);
    expect(segments[0].segmentId).toBe("paper-pdf-001-seg-0001");
    expect(segments[1].order).toBe(1);
    expect(segments[1].segmentId).toBe("paper-pdf-001-seg-0002");
  });

  it("splits on blank lines and skips empty paragraphs", () => {
    const segs = segmentTextFromString("p", "Para A\n\n\n\n\nPara B\n\n   \nPara C");
    expect(segs.map((s) => s.english)).toEqual(["Para A", "Para B", "Para C"]);
  });

  it("collapses soft line breaks inside a paragraph into single spaces", () => {
    const segs = segmentTextFromString("p", "first line\nsecond line\nthird line\n\nNew paragraph");
    expect(segs[0].english).toBe("first line second line third line");
    expect(segs[1].english).toBe("New paragraph");
  });

  it("produces stable segmentIds across runs (deterministic)", () => {
    const text = "alpha\n\nbeta\n\ngamma";
    const a = segmentTextFromString("paper-stable", text);
    const b = segmentTextFromString("paper-stable", text);
    expect(a.map((s) => s.segmentId)).toEqual(b.map((s) => s.segmentId));
  });

  it("sanitizes hostile paperIds", () => {
    const segs = segmentTextFromString("../etc/passwd", "hello");
    expect(segs[0].paperId).toBe(".._etc_passwd");
    expect(segs[0].segmentId).toMatch(/^\.\._etc_passwd-seg-0001$/);
  });

  it("chunks long paragraphs when maxCharsPerSegment is set", () => {
    const long = "Sentence one. Sentence two. Sentence three. Sentence four.";
    const segs = segmentTextFromString("p", long, { maxCharsPerSegment: 25 });
    expect(segs.length).toBeGreaterThan(1);
    for (const s of segs) {
      expect(s.english.length).toBeLessThanOrEqual(60);
    }
  });

  it("returns an empty array for empty or whitespace-only input", () => {
    expect(segmentTextFromString("p", "")).toEqual([]);
    expect(segmentTextFromString("p", "   \n\n   \n")).toEqual([]);
  });

  it("zero maxCharsPerSegment disables the cap", () => {
    const long = "a. b. c. d. e.";
    const segs = segmentTextFromString("p", long, { maxCharsPerSegment: 0 });
    expect(segs).toHaveLength(1);
  });
});

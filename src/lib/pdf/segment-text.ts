// Paragraph segmentation. Phase 3 turns a chunk of extracted PDF text
// into ordered PaperSegment records with stable segmentIds.
//
// Heuristics (best-effort, not layout-perfect — per the Phase 3 spec):
//   - Split on double newlines.
//   - Within a paragraph, collapse internal whitespace and soft line
//     breaks into single spaces.
//   - Drop empty or whitespace-only segments.
//   - The first segment order is 0; segmentId is "<paperId>-seg-NNNN"
//     where NNNN is the 1-indexed order (so the first segment is
//     "-seg-0001", matching the existing fixture convention).

import type { PaperSegment } from "@/types/domain";

export interface SegmentTextInput {
  paperId: string;
  text: string;
}

export interface SegmentTextOptions {
  /** Maximum characters per segment. Default 4000 — long enough to
   *  keep most paragraphs intact, short enough to keep RAG retrieval
   *  focused. Set to 0 to disable the cap. */
  maxCharsPerSegment?: number;
}

function pad4(n: number): string {
  return n.toString().padStart(4, "0");
}

function sanitizePaperId(paperId: string): string {
  // Defensive: paperIds from derivePaperId are already lower-case
  // kebab-ish, but we trim whitespace and strip path separators.
  return paperId.trim().replace(/[^a-zA-Z0-9._-]/g, "_");
}

function splitOnBlankLines(text: string): string[] {
  // \r\n or \n. We split on a blank-line boundary, which means
  // "one or more lines that contain only whitespace".
  return text
    .split(/\r?\n/)
    .reduce<string[]>((acc, line) => {
      if (line.trim() === "") {
        acc.push("__BLANK__");
      } else {
        acc.push(line);
      }
      return acc;
    }, [])
    .join("\n")
    .split("__BLANK__")
    .map((s) => s.replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

function chunkLong(paragraph: string, maxChars: number): string[] {
  if (maxChars <= 0 || paragraph.length <= maxChars) return [paragraph];
  const out: string[] = [];
  const sentences = paragraph.split(/(?<=[.!?])\s+/);
  let buffer = "";
  for (const s of sentences) {
    if ((buffer + " " + s).trim().length > maxChars && buffer) {
      out.push(buffer.trim());
      buffer = s;
    } else {
      buffer = (buffer + " " + s).trim();
    }
  }
  if (buffer) out.push(buffer.trim());
  return out;
}

export function segmentText(
  input: SegmentTextInput,
  options: SegmentTextOptions = {},
): PaperSegment[] {
  const safePaperId = sanitizePaperId(input.paperId);
  const maxChars = options.maxCharsPerSegment ?? 4000;
  const paragraphs = splitOnBlankLines(input.text ?? "");
  const out: PaperSegment[] = [];
  let order = 0;
  for (const paragraph of paragraphs) {
    for (const chunk of chunkLong(paragraph, maxChars)) {
      out.push({
        paperId: safePaperId,
        segmentId: `${safePaperId}-seg-${pad4(order + 1)}`,
        order,
        page: null,
        english: chunk,
        chinese: "",
      });
      order += 1;
    }
  }
  return out;
}

export function segmentTextFromString(
  paperId: string,
  text: string,
  options?: SegmentTextOptions,
): PaperSegment[] {
  return segmentText({ paperId, text }, options);
}

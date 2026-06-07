// RAG retrieval + answer. The fake model is deterministic and refuses
// to invent content: with no retrieved segments it always answers
// "insufficient evidence" and cites nothing.

import { getAllSegments } from "../library/segments";
import { getTitleByPaperId } from "../library/papers";
import { getModelAdapter } from "../models";
import type { AssistantAnswer, PaperSegment } from "@/types/domain";

// A small English stop-word set. The V1 harness is English + a few
// CJK bigrams; we don't try to be clever about Chinese tokenization
// (no jieba in V1) — CJK substrings still match via `.includes`.
const EN_STOP_WORDS = new Set([
  "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
  "has", "have", "in", "is", "it", "its", "of", "on", "or", "that",
  "the", "this", "to", "was", "were", "will", "with", "what", "when",
  "where", "which", "who", "why", "how", "do", "does", "did", "any",
  "some", "all", "anybody", "anyone", "anything",
]);

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9一-龥\s]+/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .filter((tok) => {
      // Drop single-character English stop words. Keep CJK characters
      // (a single CJK char is still meaningful as a substring).
      if (/^[a-z]+$/.test(tok)) {
        return !EN_STOP_WORDS.has(tok) && tok.length > 1;
      }
      return tok.length > 0;
    });
}

// Exposed for debugging / future tooling; tests import from the module
// surface rather than poking at internals.
export const _debugTokenize = tokenize;

export function retrieveSegments(
  question: string,
  segments: PaperSegment[],
  topK: number = 3,
): PaperSegment[] {
  const questionTokens = Array.from(new Set(tokenize(question)));
  if (questionTokens.length === 0) return [];

  // Build adjacent 2-token phrases from the question so a phrase like
  // "boundary conditions" outranks an unrelated segment that happens
  // to match a single one of the words.
  const questionBigrams: string[] = [];
  for (let i = 0; i < questionTokens.length - 1; i += 1) {
    questionBigrams.push(`${questionTokens[i]} ${questionTokens[i + 1]}`);
  }

  const scored = segments
    .map((seg) => {
      const haystack = (seg.english + " " + seg.chinese).toLowerCase();
      let score = 0;
      for (const tok of questionTokens) {
        if (haystack.includes(tok)) score += 1;
      }
      for (const bg of questionBigrams) {
        if (haystack.includes(bg)) score += 3; // phrase match outranks single tokens
      }
      return { seg, score };
    })
    .filter((x) => x.score > 0);

  // Primary key: retrieval score (descending). Secondary key: document
  // order (paperId asc, order asc) — preserves alignment with the
  // bilingual reader when scores are tied.
  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    if (a.seg.paperId !== b.seg.paperId) return a.seg.paperId.localeCompare(b.seg.paperId);
    return a.seg.order - b.seg.order;
  });

  return scored.slice(0, topK).map((x) => x.seg);
}

export function askQuestion(question: string, topK: number = 3): AssistantAnswer {
  const segments = getAllSegments();
  const retrieved = retrieveSegments(question, segments, topK);
  const titles = getTitleByPaperId();
  return getModelAdapter().generateAnswer(question, retrieved, titles);
}

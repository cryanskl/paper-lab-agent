// Citation policy for RAG answers.
//
// The model adapter (fake or any real provider) returns an
// `AssistantAnswer` that may or may not include the right
// citations. This module enforces the project-wide policy
// regardless of the provider:
//
//   1. If no segments were retrieved, the answer must report
//      "insufficient evidence" and carry zero citations.
//   2. If segments were retrieved, every retrieved segment must
//      appear in `citations` (paperId + segmentId). The Chinese
//      paper title is filled in from the lookup when missing.
//   3. The answer text must mention at least one paperId or
//      segmentId so a downstream reader can trace the claim back
//      to its source.
//
// The policy is intentionally tolerant: it only *adds* missing
// citations and never strips existing ones, so providers that
// already produce well-cited answers (like the fake adapter)
// are unaffected.

import type {
  AssistantAnswer,
  Citation,
  PaperSegment,
} from "@/types/domain";

export const INSUFFICIENT_EVIDENCE_MARKER = "insufficient evidence";

export interface EnforceCitationPolicyInput {
  answer: AssistantAnswer;
  retrievedSegments: readonly PaperSegment[];
  paperTitleByPaperId: Record<string, string>;
}

export function enforceCitationPolicy(
  input: EnforceCitationPolicyInput,
): AssistantAnswer {
  const { answer, retrievedSegments, paperTitleByPaperId } = input;

  // Branch 1: insufficient evidence.
  if (answer.insufficientEvidence || retrievedSegments.length === 0) {
    return {
      question: answer.question,
      retrievedSegments: [],
      answer: INSUFFICIENT_EVIDENCE_MARKER,
      citations: [],
      insufficientEvidence: true,
    };
  }

  // Branch 2: build a complete citation set keyed by (paperId, segmentId).
  // Citations the adapter already produced come first and are preserved
  // (titles, etc. are not overwritten). For any retrieved segment that
  // the adapter failed to cite, we append a fallback citation so the
  // citation set is provably complete.
  const seen = new Set<string>();
  const citations: Citation[] = [];
  for (const c of answer.citations) {
    const key = `${c.paperId}::${c.segmentId}`;
    if (seen.has(key)) continue;
    seen.add(key);
    citations.push(c);
  }
  for (const seg of retrievedSegments) {
    const key = `${seg.paperId}::${seg.segmentId}`;
    if (seen.has(key)) continue;
    seen.add(key);
    citations.push({
      paperId: seg.paperId,
      segmentId: seg.segmentId,
      paperTitle: paperTitleByPaperId[seg.paperId] ?? seg.paperId,
    });
  }

  // Branch 3: the answer text must reference at least one source.
  let finalAnswer = answer.answer;
  if (citations.length > 0 && !mentionsAnyCitation(finalAnswer, citations)) {
    const first = citations[0];
    finalAnswer = `${finalAnswer} (Source: ${first.paperId} / ${first.segmentId})`;
  }

  return {
    question: answer.question,
    retrievedSegments: [...retrievedSegments],
    answer: finalAnswer,
    citations,
    insufficientEvidence: false,
  };
}

function mentionsAnyCitation(text: string, citations: readonly Citation[]): boolean {
  if (typeof text !== "string" || text.length === 0) return false;
  return citations.some((c) =>
    text.includes(c.paperId) || text.includes(c.segmentId),
  );
}

export function hasAtLeastOneCitation(answer: AssistantAnswer): boolean {
  return answer.citations.length > 0;
}

export function isInsufficientEvidence(answer: AssistantAnswer): boolean {
  return (
    answer.insufficientEvidence === true ||
    answer.citations.length === 0 ||
    /insufficient evidence/i.test(answer.answer ?? "")
  );
}

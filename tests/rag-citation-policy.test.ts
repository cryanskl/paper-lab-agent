import { describe, it, expect } from "vitest";
import {
  enforceCitationPolicy,
  hasAtLeastOneCitation,
  isInsufficientEvidence,
  INSUFFICIENT_EVIDENCE_MARKER,
} from "@/lib/assistant/citation-policy";
import type {
  AssistantAnswer,
  Citation,
  PaperSegment,
} from "@/types/domain";

const SEG_A: PaperSegment = {
  paperId: "paper-2606-00001",
  segmentId: "paper-2606-00001:s001",
  order: 1,
  page: 1,
  english: "The method approximates a high-fidelity engineering simulator with a neural surrogate.",
  chinese: "该方法使用受守恒定律约束的神经代理模型来近似高保真工程仿真器。",
};
const SEG_B: PaperSegment = {
  paperId: "paper-2606-00001",
  segmentId: "paper-2606-00001:s002",
  order: 2,
  page: 2,
  english: "Boundary conditions are imposed at the inlet and outlet.",
  chinese: "边界条件施加在入口和出口。",
};

const TITLE_BY_PAPERID = {
  "paper-2606-00001": "Physics-Informed Surrogate Models",
};

describe("enforceCitationPolicy", () => {
  it("returns insufficient-evidence when retrievedSegments is empty", () => {
    const r = enforceCitationPolicy({
      answer: {
        question: "q",
        retrievedSegments: [],
        answer: "I don't know",
        citations: [],
        insufficientEvidence: false,
      },
      retrievedSegments: [],
      paperTitleByPaperId: TITLE_BY_PAPERID,
    });
    expect(r.insufficientEvidence).toBe(true);
    expect(r.answer).toBe(INSUFFICIENT_EVIDENCE_MARKER);
    expect(r.citations).toEqual([]);
  });

  it("drops citations when the adapter lies about insufficientEvidence but retrieved is empty", () => {
    const r = enforceCitationPolicy({
      answer: {
        question: "q",
        retrievedSegments: [],
        answer: "no idea",
        citations: [{ paperId: "x", segmentId: "y", paperTitle: "x" }],
        insufficientEvidence: false,
      },
      retrievedSegments: [],
      paperTitleByPaperId: {},
    });
    expect(r.citations).toEqual([]);
    expect(r.insufficientEvidence).toBe(true);
  });

  it("builds a citation for every retrieved segment when the adapter forgot them", () => {
    const r = enforceCitationPolicy({
      answer: {
        question: "q",
        retrievedSegments: [SEG_A, SEG_B],
        answer: "The method uses a neural surrogate. Boundary conditions are imposed at the inlet.",
        citations: [],
        insufficientEvidence: false,
      },
      retrievedSegments: [SEG_A, SEG_B],
      paperTitleByPaperId: TITLE_BY_PAPERID,
    });
    expect(r.citations).toHaveLength(2);
    expect(r.citations[0].paperId).toBe("paper-2606-00001");
    expect(r.citations[0].paperTitle).toBe("Physics-Informed Surrogate Models");
    expect(r.citations[0].segmentId).toBe("paper-2606-00001:s001");
  });

  it("appends a source suffix when the answer text mentions no paperId or segmentId", () => {
    const r = enforceCitationPolicy({
      answer: {
        question: "q",
        retrievedSegments: [SEG_A],
        answer: "Some generic text that mentions no source at all.",
        citations: [],
        insufficientEvidence: false,
      },
      retrievedSegments: [SEG_A],
      paperTitleByPaperId: TITLE_BY_PAPERID,
    });
    expect(r.answer).toMatch(/Source: paper-2606-00001/);
  });

  it("does not double-add citations the adapter already produced", () => {
    const existing: Citation = {
      paperId: SEG_A.paperId,
      segmentId: SEG_A.segmentId,
      paperTitle: "Adapters own title",
    };
    const r = enforceCitationPolicy({
      answer: {
        question: "q",
        retrievedSegments: [SEG_A],
        answer: "answer referencing paper-2606-00001:s001 already",
        citations: [existing],
        insufficientEvidence: false,
      },
      retrievedSegments: [SEG_A],
      paperTitleByPaperId: TITLE_BY_PAPERID,
    });
    expect(r.citations).toHaveLength(1);
    // The adapter's own title is preserved, not overwritten.
    expect(r.citations[0].paperTitle).toBe("Adapters own title");
  });

  it("falls back to paperId as paperTitle when the lookup is empty", () => {
    const r = enforceCitationPolicy({
      answer: {
        question: "q",
        retrievedSegments: [SEG_A],
        answer: "answer referencing paper-2606-00001:s001",
        citations: [],
        insufficientEvidence: false,
      },
      retrievedSegments: [SEG_A],
      paperTitleByPaperId: {},
    });
    expect(r.citations[0].paperTitle).toBe("paper-2606-00001");
  });

  it("hasAtLeastOneCitation and isInsufficientEvidence are cheap predicates", () => {
    const good: AssistantAnswer = {
      question: "q",
      retrievedSegments: [SEG_A],
      answer: "x",
      citations: [{ paperId: SEG_A.paperId, segmentId: SEG_A.segmentId, paperTitle: "t" }],
      insufficientEvidence: false,
    };
    expect(hasAtLeastOneCitation(good)).toBe(true);
    expect(isInsufficientEvidence(good)).toBe(false);
    const bad: AssistantAnswer = {
      question: "q",
      retrievedSegments: [],
      answer: "I don't know",
      citations: [],
      insufficientEvidence: true,
    };
    expect(hasAtLeastOneCitation(bad)).toBe(false);
    expect(isInsufficientEvidence(bad)).toBe(true);
  });

  it("detects insufficient evidence from the answer text even when the flag is false", () => {
    const a: AssistantAnswer = {
      question: "q",
      retrievedSegments: [],
      answer: "Insufficient evidence for that.",
      citations: [],
      insufficientEvidence: false,
    };
    expect(isInsufficientEvidence(a)).toBe(true);
  });
});

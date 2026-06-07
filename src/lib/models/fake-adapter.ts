// Deterministic fake model adapter. The same input must always produce the
// same output. Translation returns the Chinese text supplied by the segment
// (the fixture's translations are the "ground truth"); relevance uses a
// simple keyword heuristic; RAG answers concatenate retrieved segments
// with required citation markers; simulation specs are derived from
// fixed-shape evidence tokens.

import type {
  AssistantAnswer,
  Citation,
  PaperSegment,
  RelevanceInput,
  RelevanceResult,
  SimulationSpec,
} from "@/types/domain";
import type { ModelAdapter } from "./adapter";

const INSUFFICIENT_EVIDENCE_MARKER = "insufficient evidence";

export class FakeModelAdapter implements ModelAdapter {
  readonly name = "fake";

  scoreRelevance(input: RelevanceInput): RelevanceResult {
    const haystack = [
      input.title,
      input.abstract,
      ...input.keywords,
    ]
      .join(" ")
      .toLowerCase();

    const profileKeywords = input.profileKeywords.map((k) => k.toLowerCase());
    const matchedKeywords = profileKeywords.filter((k) => haystack.includes(k));

    if (matchedKeywords.length > 0) {
      return {
        decision: "accepted",
        rationale: `Matches research profile keyword(s): ${matchedKeywords.join(", ")}.`,
        matchedKeywords,
      };
    }
    return {
      decision: "rejected",
      rationale: "Does not match paper-lab-agent research profile keywords.",
      matchedKeywords,
    };
  }

  // The fake translator just echoes the input. The harness tests assert
  // that the translation written by the segment-import flow is preserved
  // verbatim, not that the adapter invents Chinese text. This is the
  // safest default per the harness rules: no hidden LLM behavior.
  translate(english: string): string {
    return english;
  }

  generateAnswer(
    question: string,
    retrievedSegments: PaperSegment[],
    paperTitleByPaperId: Record<string, string>,
  ): AssistantAnswer {
    if (retrievedSegments.length === 0) {
      return {
        question,
        retrievedSegments: [],
        answer: INSUFFICIENT_EVIDENCE_MARKER,
        citations: [],
        insufficientEvidence: true,
      };
    }

    const citations: Citation[] = retrievedSegments.map((s) => ({
      paperId: s.paperId,
      segmentId: s.segmentId,
      paperTitle: paperTitleByPaperId[s.paperId] ?? s.paperId,
    }));

    // Build a deterministic answer that quotes retrieved segment English text
    // in segment-order. Tests assert the citations and the must-contain
    // substrings; we deliberately avoid paraphrasing so that no unstated
    // model behavior enters the harness.
    const answerParts = retrievedSegments.map(
      (s) => `From ${s.segmentId}: ${s.english}`,
    );
    const answer = answerParts.join(" ");

    return {
      question,
      retrievedSegments,
      answer,
      citations,
      insufficientEvidence: false,
    };
  }

  generateSimulationSpec(
    methodText: string,
    sourcePaperId: string | null,
  ): SimulationSpec {
    const sourceEvidence = sourcePaperId
      ? `${sourcePaperId} method section: ${methodText.slice(0, 120)}`
      : `method evidence: ${methodText.slice(0, 120)}`;

    return {
      sourceEvidence,
      assumptions: [
        "The method approximates a high-fidelity engineering simulator with a neural surrogate constrained by conservation laws.",
        "Loss function includes residual terms for the governing equations.",
        "Inlet and outlet boundary conditions are imposed as hard constraints.",
      ],
      parameters: [
        {
          name: "reynoldsNumber",
          value: 100,
          unit: "dimensionless",
          description: "Reynolds number characterizing the flow regime.",
        },
        {
          name: "domainLength",
          value: 1.0,
          unit: "m",
          description: "Length of the 2D flow domain along the streamwise direction.",
        },
        {
          name: "domainHeight",
          value: 0.2,
          unit: "m",
          description: "Height of the 2D flow domain along the wall-normal direction.",
        },
      ],
      units: ["m", "s", "Pa", "dimensionless"],
      boundaryConditions: [
        "Inlet: prescribed velocity profile at x = 0.",
        "Outlet: zero-gradient pressure at x = L.",
        "Walls: no-slip velocity on top and bottom boundaries.",
      ],
      runSteps: [
        "Initialize the 2D flow field on a uniform grid.",
        "Apply inlet and outlet boundary conditions.",
        "Evaluate the surrogate model prediction.",
        "Compute the residual-based loss for the governing equations.",
        "Record prediction error over the parameter sweep.",
      ],
      artifactPaths: [
        "data/simulations/spec.json",
        "data/simulations/run_simulation.py",
        "data/simulations/results/chart.png",
      ],
    };
  }
}

export const INSUFFICIENT_EVIDENCE = INSUFFICIENT_EVIDENCE_MARKER;

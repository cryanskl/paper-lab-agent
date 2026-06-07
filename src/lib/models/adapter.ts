// Narrow interface every model adapter must implement.
// V1 only ships the fake adapter; Ollama / other local runtimes come later.

import type {
  PaperSegment,
  AssistantAnswer,
  SimulationSpec,
  RelevanceInput,
  RelevanceResult,
} from "@/types/domain";

export interface ModelAdapter {
  readonly name: string;

  scoreRelevance(input: RelevanceInput): RelevanceResult;

  translate(english: string): string;

  generateAnswer(
    question: string,
    retrievedSegments: PaperSegment[],
    paperTitleByPaperId: Record<string, string>,
  ): AssistantAnswer;

  generateSimulationSpec(
    methodText: string,
    sourcePaperId: string | null,
  ): SimulationSpec;
}

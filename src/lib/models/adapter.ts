// Narrow interface every model adapter must implement.
// The fake adapter ships today; Ollama / other local runtimes are
// added in Phase 4. All methods may return either a sync value or
// a Promise so adapters that need a network round-trip (Ollama)
// can be expressed without breaking the existing sync fake adapter.

import type {
  PaperSegment,
  AssistantAnswer,
  SimulationSpec,
  RelevanceInput,
  RelevanceResult,
} from "@/types/domain";

export type MaybePromise<T> = T | Promise<T>;

export interface ModelAdapter {
  readonly name: string;

  scoreRelevance(input: RelevanceInput): MaybePromise<RelevanceResult>;

  translate(english: string): MaybePromise<string>;

  generateAnswer(
    question: string,
    retrievedSegments: PaperSegment[],
    paperTitleByPaperId: Record<string, string>,
  ): MaybePromise<AssistantAnswer>;

  generateSimulationSpec(
    methodText: string,
    sourcePaperId: string | null,
  ): MaybePromise<SimulationSpec>;
}

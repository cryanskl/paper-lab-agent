// Ollama-compatible local model adapter.
//
// Ollama exposes a JSON HTTP API on http://localhost:11434 by
// default. The adapter implements the same `ModelAdapter` surface
// as the fake adapter but routes each call through a prompt to
// the local model. Network access is gated through a stubbable
// `fetchImpl` so the default test suite never hits the network.
//
// The factory (`models/index.ts`) only constructs an
// `OllamaAdapter` when the configured provider is "ollama" AND
// the operator has explicitly opted in via the env flag.

import type {
  AssistantAnswer,
  Citation,
  PaperSegment,
  RelevanceInput,
  RelevanceResult,
  SimulationSpec,
} from "@/types/domain";
import type { ModelAdapter } from "./adapter";

export class OllamaUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "OllamaUnavailableError";
  }
}

export interface OllamaAdapterOptions {
  endpoint: string;
  model: string;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

interface OllamaTagsResponse {
  models?: Array<{ name: string }>;
}

const DEFAULT_TIMEOUT_MS = 30_000;

function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max) + "…" : text;
}

function buildRelevancePrompt(input: RelevanceInput): string {
  const profileKw = input.profileKeywords.join(", ");
  return [
    "You score whether a paper matches a research profile.",
    `Profile keywords: ${profileKw}.`,
    "",
    "Title: " + input.title,
    "Abstract: " + truncate(input.abstract, 600),
    "Keywords: " + (input.keywords ?? []).join(", "),
    "",
    'Reply with one line: either "ACCEPT" or "REJECT" followed by a brief rationale.',
  ].join("\n");
}

function buildTranslatePrompt(english: string): string {
  return [
    "Translate the following English paragraph to Simplified Chinese.",
    "Output only the translation, no commentary.",
    "",
    english,
  ].join("\n");
}

function buildAnswerPrompt(
  question: string,
  retrieved: readonly PaperSegment[],
  paperTitleByPaperId: Record<string, string>,
): string {
  const evidence = retrieved
    .map((s) => {
      const title = paperTitleByPaperId[s.paperId] ?? s.paperId;
      return `[${s.paperId} / ${s.segmentId} — ${title}]\n${truncate(s.english, 800)}`;
    })
    .join("\n\n");
  return [
    "You are a research assistant. Use ONLY the supplied evidence.",
    "If the evidence is empty or insufficient, reply with the literal text:",
    '"insufficient evidence".',
    "Otherwise, answer the question in one or two sentences and end with a",
    "line that begins with the literal text: \"Source: <paperId> / <segmentId>\".",
    "",
    "Question: " + question,
    "",
    "Evidence:",
    evidence || "(none)",
  ].join("\n");
}

function buildSimulationPrompt(methodText: string, sourcePaperId: string | null): string {
  return [
    "Produce a toy simulation spec for the following method section.",
    sourcePaperId ? `Source paper: ${sourcePaperId}.` : "Source: not provided.",
    "",
    "Method:",
    truncate(methodText, 1200),
    "",
    "Reply with a JSON object that has exactly these keys:",
    "sourceEvidence, assumptions, parameters, units, boundaryConditions,",
    "runSteps, artifactPaths. parameters is an array of {name,value,unit,description}.",
  ].join("\n");
}

function jsonBetween<T>(raw: string, key: string): T | null {
  // Ollama returns the model output as a free-form string. When we
  // ask for JSON, the model usually wraps it in fences. We try to
  // extract the most likely JSON object; if parsing fails we return
  // null and the caller falls back to a sensible default.
  const fence = raw.match(/```(?:json)?\s*([\s\S]+?)```/i);
  const candidate = fence ? fence[1] : raw;
  try {
    return JSON.parse(candidate) as T;
  } catch {
    const idx = candidate.indexOf("{");
    const end = candidate.lastIndexOf("}");
    if (idx === -1 || end === -1 || end <= idx) return null;
    try {
      return JSON.parse(candidate.slice(idx, end + 1)) as T;
    } catch {
      return null;
    }
  }
}

export class OllamaAdapter implements ModelAdapter {
  readonly name = "ollama";

  private readonly endpoint: string;
  private readonly model: string;
  private readonly fetchImpl: typeof fetch;
  private readonly timeoutMs: number;

  constructor(options: OllamaAdapterOptions) {
    this.endpoint = options.endpoint.replace(/\/+$/, "");
    this.model = options.model;
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch;
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  private async generate(prompt: string): Promise<string> {
    if (typeof this.fetchImpl !== "function") {
      throw new OllamaUnavailableError("global fetch is not available in this runtime");
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const res = await this.fetchImpl(`${this.endpoint}/api/generate`, {
        method: "POST",
        signal: controller.signal,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ model: this.model, prompt, stream: false }),
      });
      if (!res.ok) {
        throw new OllamaUnavailableError(
          `ollama responded ${res.status} ${res.statusText}`,
        );
      }
      const json = (await res.json()) as { response?: string };
      return typeof json.response === "string" ? json.response : "";
    } finally {
      clearTimeout(timer);
    }
  }

  async scoreRelevance(input: RelevanceInput): Promise<RelevanceResult> {
    const raw = await this.generate(buildRelevancePrompt(input));
    const accepted = /^accept\b/i.test(raw.trim());
    return {
      decision: accepted ? "accepted" : "rejected",
      rationale: raw.trim().slice(0, 200) || "ollama produced no rationale",
      matchedKeywords: accepted ? input.profileKeywords : [],
    };
  }

  async translate(english: string): Promise<string> {
    if (english.trim() === "") return "";
    return await this.generate(buildTranslatePrompt(english));
  }

  async generateAnswer(
    question: string,
    retrievedSegments: PaperSegment[],
    paperTitleByPaperId: Record<string, string>,
  ): Promise<AssistantAnswer> {
    if (retrievedSegments.length === 0) {
      return {
        question,
        retrievedSegments: [],
        answer: "insufficient evidence",
        citations: [],
        insufficientEvidence: true,
      };
    }
    const raw = await this.generate(
      buildAnswerPrompt(question, retrievedSegments, paperTitleByPaperId),
    );
    const citations: Citation[] = retrievedSegments.map((s) => ({
      paperId: s.paperId,
      segmentId: s.segmentId,
      paperTitle: paperTitleByPaperId[s.paperId] ?? s.paperId,
    }));
    return {
      question,
      retrievedSegments,
      answer: raw.trim(),
      citations,
      insufficientEvidence: false,
    };
  }

  async generateSimulationSpec(
    methodText: string,
    sourcePaperId: string | null,
  ): Promise<SimulationSpec> {
    const raw = await this.generate(buildSimulationPrompt(methodText, sourcePaperId));
    const parsed = jsonBetween<Record<string, unknown>>(raw, "spec");
    if (parsed && Array.isArray(parsed.assumptions) && Array.isArray(parsed.runSteps)) {
      return {
        sourceEvidence: String(parsed.sourceEvidence ?? ""),
        assumptions: parsed.assumptions.map((a) => String(a)),
        parameters: Array.isArray(parsed.parameters)
          ? (parsed.parameters as Array<Record<string, unknown>>).map((p) => ({
              name: String(p.name ?? ""),
              value: Number(p.value ?? 0),
              unit: String(p.unit ?? ""),
              description: String(p.description ?? ""),
            }))
          : [],
        units: Array.isArray(parsed.units) ? parsed.units.map((u) => String(u)) : [],
        boundaryConditions: Array.isArray(parsed.boundaryConditions)
          ? parsed.boundaryConditions.map((b) => String(b))
          : [],
        runSteps: parsed.runSteps.map((s) => String(s)),
        artifactPaths: Array.isArray(parsed.artifactPaths)
          ? parsed.artifactPaths.map((a) => String(a))
          : [],
      };
    }
    // Fallback: hand back a deterministic placeholder so the rest
    // of the pipeline still produces a valid SimulationSpec.
    return {
      sourceEvidence: `ollama output could not be parsed: ${raw.slice(0, 80)}`,
      assumptions: ["ollama output did not match the expected JSON shape."],
      parameters: [],
      units: [],
      boundaryConditions: [],
      runSteps: ["Fall back to fake adapter output for the simulation spec."],
      artifactPaths: ["data/simulations/spec.json"],
    };
  }
}

// Model provider health checks. The default no-network test suite
// stubs the fetchImpl so it can verify the policy behavior without
// ever hitting the real local model.

import { OllamaAdapter, OllamaUnavailableError } from "./ollama-adapter";

interface OllamaTagsResponse {
  models?: Array<{ name: string }>;
}

export type ProviderName = "fake" | "ollama" | string;

export interface HealthCheckInput {
  provider: ProviderName;
  endpoint?: string;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

export interface HealthCheckResult {
  ok: boolean;
  message: string;
  model: string | null;
}

const DEFAULT_MODEL = "llama3";

export async function checkProviderHealth(
  input: HealthCheckInput,
): Promise<HealthCheckResult> {
  if (input.provider === "fake") {
    return { ok: true, message: "fake provider is always available", model: "fake" };
  }
  if (input.provider === "ollama") {
    return checkOllamaHealth(input);
  }
  return {
    ok: false,
    message: `unknown provider: ${input.provider}. V1 supports "fake" or "ollama".`,
    model: null,
  };
}

async function checkOllamaHealth(
  input: HealthCheckInput,
): Promise<HealthCheckResult> {
  const fetchImpl = input.fetchImpl ?? globalThis.fetch;
  if (typeof fetchImpl !== "function") {
    return {
      ok: false,
      message: "global fetch is not available in this runtime",
      model: null,
    };
  }
  const endpoint = (input.endpoint ?? "http://localhost:11434").replace(/\/+$/, "");
  try {
    const res = await fetchImpl(`${endpoint}/api/tags`, {
      headers: { "user-agent": "paper-lab-agent/0.1 (local research assistant)" },
      signal: AbortSignal.timeout(input.timeoutMs ?? 5000),
    });
    if (!res.ok) {
      return {
        ok: false,
        message: `ollama responded ${res.status} ${res.statusText}`,
        model: null,
      };
    }
    const json = (await res.json()) as OllamaTagsResponse;
    const models = (json.models ?? []).map((m) => m.name);
    if (!models.includes(DEFAULT_MODEL) && models.length === 0) {
      return {
        ok: false,
        message: "ollama is reachable but no models are installed; run `ollama pull llama3`",
        model: null,
      };
    }
    return {
      ok: true,
      message: `ollama is reachable; models: ${models.join(", ") || "(none)"}`,
      model: models[0] ?? DEFAULT_MODEL,
    };
  } catch (err) {
    const reason =
      err instanceof OllamaUnavailableError
        ? err.message
        : err instanceof Error
          ? `${err.name || "Error"}: ${err.message}`
          : String(err);
    return {
      ok: false,
      message: `ollama is not reachable: ${reason}`,
      model: null,
    };
  }
}

void OllamaAdapter;

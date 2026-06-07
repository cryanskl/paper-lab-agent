// Adapter factory. V1 supports the deterministic fake adapter and an
// opt-in Ollama-compatible local model. The fake adapter is always
// the default. Ollama is only constructed when the operator has
// explicitly set PAPER_LAB_MODEL_PROVIDER=ollama AND
// PAPER_LAB_LIVE_MODEL_OPT_IN=true. This double gate prevents a
// stray env file from silently changing which model backs the app.

import { loadConfig } from "../config";
import { FakeModelAdapter } from "./fake-adapter";
import { OllamaAdapter } from "./ollama-adapter";
import type { ModelAdapter } from "./adapter";

let cached: ModelAdapter | null = null;

export function isOllamaOptIn(envValue: string | undefined): boolean {
  return envValue === "true";
}

export function getModelAdapter(): ModelAdapter {
  if (cached) return cached;
  const cfg = loadConfig();
  if (cfg.modelProvider === "fake") {
    cached = new FakeModelAdapter();
    return cached;
  }
  if (cfg.modelProvider === "ollama") {
    if (!isOllamaOptIn(process.env.PAPER_LAB_LIVE_MODEL_OPT_IN)) {
      throw new Error(
        "PAPER_LAB_MODEL_PROVIDER=ollama requires PAPER_LAB_LIVE_MODEL_OPT_IN=true. " +
          "V1 falls back to refusing rather than silently changing the provider.",
      );
    }
    const endpoint = process.env.PAPER_LAB_OLLAMA_URL || "http://localhost:11434";
    const model = process.env.PAPER_LAB_OLLAMA_MODEL || "llama3";
    cached = new OllamaAdapter({ endpoint, model });
    return cached;
  }
  throw new Error(
    `Unknown PAPER_LAB_MODEL_PROVIDER: ${cfg.modelProvider}. V1 supports "fake" or "ollama".`,
  );
}

export function resetModelAdapterForTesting(adapter: ModelAdapter | null): void {
  cached = adapter;
}

export type { ModelAdapter } from "./adapter";

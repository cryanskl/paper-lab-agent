// Adapter factory. V1 only resolves to the fake adapter.
// Future: if (config.modelProvider === "ollama") { return new OllamaAdapter(); }

import { loadConfig } from "../config";
import { FakeModelAdapter } from "./fake-adapter";
import type { ModelAdapter } from "./adapter";

let cached: ModelAdapter | null = null;

export function getModelAdapter(): ModelAdapter {
  if (cached) return cached;
  const cfg = loadConfig();
  if (cfg.modelProvider === "fake") {
    cached = new FakeModelAdapter();
    return cached;
  }
  // V1 only ships the fake adapter. We refuse to fall back silently.
  throw new Error(
    `Unknown PAPER_LAB_MODEL_PROVIDER: ${cfg.modelProvider}. V1 only supports "fake".`,
  );
}

export function resetModelAdapterForTesting(adapter: ModelAdapter | null): void {
  cached = adapter;
}

export type { ModelAdapter } from "./adapter";

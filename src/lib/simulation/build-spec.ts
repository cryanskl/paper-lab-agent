// Simulation spec builder. Reads the method fixture text and feeds it
// to the fake model adapter. The adapter always returns a fixed-shape
// spec with the required fields; tests assert that shape.
//
// Phase 4 keeps this function sync-only. If the active adapter
// returns a Promise (Ollama), we surface a typed error rather than
// silently changing the API shape. Use `buildSimulationSpecAsync`
// for the async path.

import fs from "node:fs";
import path from "node:path";
import { getModelAdapter } from "../models";
import { getDataLayout, ensureDataDirs } from "../files";
import type { SimulationSpec } from "@/types/domain";

export class SimulationProviderNotSyncError extends Error {
  constructor() {
    super(
      "buildSimulationSpec is sync-only. The active adapter returns a " +
        "Promise; use buildSimulationSpecAsync instead. This typically " +
        "happens when the Ollama adapter is selected at runtime.",
    );
    this.name = "SimulationProviderNotSyncError";
  }
}

export function loadMethodFixture(fixturePath: string): string {
  return fs.readFileSync(fixturePath, "utf-8");
}

export function buildSimulationSpec(
  methodText: string,
  sourcePaperId: string | null,
): SimulationSpec {
  const out = getModelAdapter().generateSimulationSpec(methodText, sourcePaperId);
  if (out instanceof Promise) {
    throw new SimulationProviderNotSyncError();
  }
  return out;
}

export async function buildSimulationSpecAsync(
  methodText: string,
  sourcePaperId: string | null,
): Promise<SimulationSpec> {
  return await getModelAdapter().generateSimulationSpec(methodText, sourcePaperId);
}

export function writeSimulationArtifact(
  spec: SimulationSpec,
  sourcePaperId: string | null,
): string {
  const layout = ensureDataDirs();
  const target = sourcePaperId
    ? path.join(layout.simulationDir, sourcePaperId, "spec.json")
    : path.join(layout.simulationDir, "spec.json");
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, JSON.stringify(spec, null, 2), "utf-8");
  return target;
}

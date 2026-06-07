// Simulation spec builder. Reads the method fixture text and feeds it
// to the fake model adapter. The adapter always returns a fixed-shape
// spec with the required fields; tests assert that shape.

import fs from "node:fs";
import path from "node:path";
import { getModelAdapter } from "../models";
import { getDataLayout, ensureDataDirs } from "../files";
import type { SimulationSpec } from "@/types/domain";

export function loadMethodFixture(fixturePath: string): string {
  return fs.readFileSync(fixturePath, "utf-8");
}

export function buildSimulationSpec(
  methodText: string,
  sourcePaperId: string | null,
): SimulationSpec {
  return getModelAdapter().generateSimulationSpec(methodText, sourcePaperId);
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

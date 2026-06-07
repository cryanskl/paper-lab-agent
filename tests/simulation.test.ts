import { describe, it, expect, beforeAll, afterAll } from "vitest";
import {
  setupTempDataDir,
  teardownTempDataDir,
  resolveFixturePath,
} from "./helpers/setup";
import { buildSimulationSpec, loadMethodFixture } from "@/lib/simulation/build-spec";
import { resetDbForTesting, closeDb } from "@/lib/db";

describe("simulation spec harness", () => {
  beforeAll(() => {
    setupTempDataDir();
    resetDbForTesting(process.env.PAPER_LAB_DATABASE_URL!);
  });
  afterAll(() => {
    closeDb();
    teardownTempDataDir();
  });

  it("loads the method fixture without network", () => {
    const text = loadMethodFixture(
      resolveFixturePath("fixtures/simulation/sample-method.txt"),
    );
    expect(text.length).toBeGreaterThan(0);
    expect(text.toLowerCase()).toContain("boundary condition");
  });

  it("builds a spec with all required fields", () => {
    const text = loadMethodFixture(
      resolveFixturePath("fixtures/simulation/sample-method.txt"),
    );
    const spec = buildSimulationSpec(text, "paper-2606-00001");

    // Source evidence is required and must reference the paper id.
    expect(spec.sourceEvidence).toContain("paper-2606-00001");

    // Assumptions, parameters, units, boundary conditions, run steps,
    // artifact paths — all required, all non-empty.
    expect(Array.isArray(spec.assumptions)).toBe(true);
    expect(spec.assumptions.length).toBeGreaterThan(0);

    expect(Array.isArray(spec.parameters)).toBe(true);
    expect(spec.parameters.length).toBeGreaterThan(0);
    for (const p of spec.parameters) {
      expect(typeof p.name).toBe("string");
      expect(p.name.length).toBeGreaterThan(0);
      expect(typeof p.value).toBe("number");
      expect(typeof p.unit).toBe("string");
      expect(p.unit.length).toBeGreaterThan(0);
      expect(typeof p.description).toBe("string");
    }

    expect(Array.isArray(spec.units)).toBe(true);
    expect(spec.units.length).toBeGreaterThan(0);
    for (const u of spec.units) {
      expect(typeof u).toBe("string");
    }

    expect(Array.isArray(spec.boundaryConditions)).toBe(true);
    expect(spec.boundaryConditions.length).toBeGreaterThan(0);

    expect(Array.isArray(spec.runSteps)).toBe(true);
    expect(spec.runSteps.length).toBeGreaterThan(0);

    expect(Array.isArray(spec.artifactPaths)).toBe(true);
    expect(spec.artifactPaths.length).toBeGreaterThan(0);
  });

  it("artifact paths must be under the configured data/simulations directory", () => {
    const text = loadMethodFixture(
      resolveFixturePath("fixtures/simulation/sample-method.txt"),
    );
    const spec = buildSimulationSpec(text, "paper-2606-00001");
    for (const a of spec.artifactPaths) {
      // The V1 spec is conservative: every artifact path lives under
      // the local data dir, never outside it.
      expect(a).toMatch(/^data\/simulations\//);
    }
  });
});

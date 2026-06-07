import { buildSimulationSpec, loadMethodFixture } from "@/lib/simulation/build-spec";
import { loadConfig } from "@/lib/config";
import fs from "node:fs";
import path from "node:path";

export const dynamic = "force-dynamic";

export default function SimulationPage() {
  const cfg = loadConfig();

  let methodText: string | null = null;
  let loadError: string | null = null;
  try {
    if (fs.existsSync(cfg.fixtures.simulationMethod)) {
      methodText = loadMethodFixture(cfg.fixtures.simulationMethod);
    } else {
      loadError = `Missing fixture: ${cfg.fixtures.simulationMethod}`;
    }
  } catch (err) {
    loadError = err instanceof Error ? err.message : String(err);
  }

  if (loadError) {
    return (
      <div>
        <h1>Simulation Spec</h1>
        <div className="warn-box">{loadError}</div>
      </div>
    );
  }

  const spec = buildSimulationSpec(methodText ?? "", null);
  const artifactDir = path.relative(process.cwd(), cfg.simulationDir);

  return (
    <div>
      <h1>Simulation Spec</h1>
      <p className="muted">
        Generated from <span className="code">{path.relative(process.cwd(), cfg.fixtures.simulationMethod)}</span>{" "}
        using the deterministic fake model adapter. The spec includes the
        required fields: assumptions, parameters, units, boundary conditions,
        run steps, and artifact paths.
      </p>

      <div className="card">
        <h2>Source evidence</h2>
        <p>{spec.sourceEvidence}</p>

        <h2>Assumptions</h2>
        <ul className="spec-list">
          {spec.assumptions.map((a) => <li key={a}>{a}</li>)}
        </ul>

        <h2>Parameters</h2>
        <dl className="spec-grid">
          {spec.parameters.map((p) => (
            <div key={p.name} style={{ display: "contents" }}>
              <dt><span className="code">{p.name}</span></dt>
              <dd>
                value <strong>{p.value}</strong> {p.unit} — {p.description}
              </dd>
            </div>
          ))}
        </dl>

        <h2>Units</h2>
        <p>{spec.units.map((u) => <span className="badge" key={u}>{u}</span>)}</p>

        <h2>Boundary conditions</h2>
        <ul className="spec-list">
          {spec.boundaryConditions.map((b) => <li key={b}>{b}</li>)}
        </ul>

        <h2>Run steps</h2>
        <ol className="spec-list">
          {spec.runSteps.map((s) => <li key={s}>{s}</li>)}
        </ol>

        <h2>Artifact paths</h2>
        <ul className="spec-list">
          {spec.artifactPaths.map((a) => <li key={a}><span className="code">{a}</span></li>)}
        </ul>

        <p className="muted">
          All artifacts will be written under <span className="code">{artifactDir}</span>.
        </p>
      </div>
    </div>
  );
}

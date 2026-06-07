# Phase 5: Experiment Lab Artifacts

## Goal

Turn simulation specs into small runnable research artifacts: Python scripts, notebooks, charts, and lightweight visual explanations for physics/engineering toy simulations.

## Scope

Phase 5 includes:

- Artifact generator from `SimulationSpec`.
- Runnable Python script for a toy simulation.
- Optional notebook export.
- Chart or animation artifact under `data/simulations/`.
- Experiment Lab UI for viewing spec, parameters, run steps, and generated artifact paths.
- Tests that validate artifact structure and local-path boundaries.

Phase 5 excludes:

- Full reproduction of paper benchmarks.
- Claims of numerical equivalence to original papers.
- Heavy domain solvers unless explicitly approved.
- Cloud execution.
- Long-running simulations by default.

## Implementation Boundaries

- Toy simulations must be small, deterministic, and runnable locally.
- Generated files must stay under `data/simulations/`.
- Every artifact must trace back to a paper id and source evidence.
- Parameter units and boundary conditions must be explicit.
- If the system cannot produce a meaningful artifact, it must report limitations instead of fabricating scientific validity.

## Suggested Files

- `src/lib/simulation/artifact-generator.ts`: script/notebook/chart artifact generation.
- `src/lib/simulation/run-artifact.ts`: controlled local run helper.
- `src/app/simulation/[paperId]/page.tsx`: paper-specific experiment view.
- `tests/simulation-artifacts.test.ts`: file shape and path-boundary tests.
- `fixtures/simulation/expected-spec.json`: expected artifact input.

## Harness Requirements

- Tests must run without network and without a real model.
- Artifact tests should use temp directories.
- Generated artifact paths must be verified to stay under the configured simulation directory.
- If Python execution is introduced, add a fast smoke test and a skip condition for missing Python runtime.

## Acceptance Criteria

- User can generate simulation artifacts for a selected paper.
- At least one runnable script or notebook is written locally.
- A chart or animation placeholder is produced from deterministic toy data.
- UI shows assumptions, parameters, units, boundary conditions, run steps, and artifact paths.
- The app clearly labels the result as a toy simulation, not a full paper reproduction.

## Required Verification

```bash
pnpm typecheck
pnpm test
pnpm build
```

If Python artifact execution is added, run its explicit smoke command and document the runtime requirement.

# Evaluation

## Purpose

`paper-lab-agent` should be evaluated by whether it preserves research evidence, keeps outputs traceable, and supports a repeatable local workflow.

The default evaluation path must be fixture-backed, deterministic, and no-network.

## Intake Quality

An intake run passes when:

- Fixture candidates are normalized into stable paper records.
- Duplicate candidates are not inserted twice.
- Accepted and rejected papers include relevance rationale.
- Download attempts produce explicit success or failure status.
- Run logs include source, candidate count, accepted count, rejected count, and errors.

## Relevance Quality

Relevance evaluation should check:

- Keyword hits are reflected in the rationale.
- Seed-paper similarity signals are reflected in the rationale when available.
- Negative examples remain rejected.
- The fake model adapter returns stable decisions for identical inputs.

## Bilingual Reader Quality

Reader evaluation passes when:

- English and Chinese segment counts match.
- Segment ids match between original and translation.
- Segment order is stable.
- Missing translation is shown as an explicit missing state, not silently shifted.

## RAG Quality

RAG evaluation passes when:

- Golden questions retrieve the expected paper id and segment id.
- Answers include citations for every factual claim derived from papers.
- Unsupported questions return an insufficient-evidence result.
- Tests do not require a real LLM or network.

## Simulation Quality

A simulation spec passes when it contains:

- Source paper or method evidence.
- Assumptions.
- Parameters.
- Units.
- Boundary conditions.
- Run steps.
- Artifact paths for code, data, chart, or animation output.

V1 simulation evaluation checks structure and traceability. It does not claim full experimental reproduction.

## Release Gates

Before claiming a feature is complete:

- Documentation must match the current implemented behavior.
- Fixture-backed harness tests must pass.
- Any real network/model behavior must be marked as integration-only.
- RAG answers must remain cited and evidence-bound.

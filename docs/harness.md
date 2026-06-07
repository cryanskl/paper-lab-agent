# Harness

## Purpose

The harness keeps `paper-lab-agent` testable before real models, real PDFs, or real network sources are connected. Default harness behavior must be deterministic and no-network.

## Fake Model Harness

The fake model adapter should provide stable responses for:

- Relevance review.
- English-to-Chinese paragraph translation.
- RAG answer generation.
- Simulation spec generation.

The same input must always produce the same output. Tests should assert output shape, citations, and required fields rather than model creativity.

## Intake Fixture Harness

Use `fixtures/intake/arxiv-sample.json` to test:

- Source metadata normalization.
- Candidate deduplication.
- Keyword relevance rationale.
- Accepted/rejected state transitions.

No intake fixture test should call the live arXiv API.

## Paper Segment Harness

Use `fixtures/papers/sample-paper-segments.json` to test:

- Stable paper ids and segment ids.
- Paragraph order.
- English/Chinese alignment.
- Retrieval input records for RAG tests.

## RAG Citation Harness

Use `fixtures/rag/golden-questions.json` to test:

- A question maps to expected paper ids and segment ids.
- Answers include citations.
- Unsupported questions return insufficient evidence.

The harness should fail if an answer contains paper-derived facts without citations.

## Simulation Spec Harness

Use `fixtures/simulation/sample-method.txt` to test generation of a toy physics/engineering simulation spec. A passing spec includes assumptions, parameters, units, boundary conditions, run steps, and artifact paths.

## Future Automation

When the codebase is initialized, convert this harness into automated tests:

- Unit tests for fake model outputs.
- Unit tests for fixture normalization and segment alignment.
- Golden tests for RAG citations.
- Shape tests for simulation specs.
- Integration tests for real sources, marked separately from default test runs.

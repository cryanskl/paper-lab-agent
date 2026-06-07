# Phase 4: Local Model RAG

## Goal

Add an optional local model path for retrieval-augmented Q&A while preserving fake adapter determinism and citation requirements.

## Scope

Phase 4 includes:

- Local model adapter interface implementation, recommended first target: Ollama-compatible HTTP API.
- Configurable model provider selection.
- Retrieval improvements using SQLite FTS5 or a local embedding index.
- Answer generation that cites retrieved paper segments.
- Model health check and clear error messages when the local model is unavailable.
- Evaluation set for cited answers and insufficient-evidence behavior.

Phase 4 excludes:

- Cloud model as the default.
- Uncited model answers.
- Automatic upload of paper contents to external APIs.
- Fine-tuning.
- Multi-agent autonomous research workflows.

## Implementation Boundaries

- `fake` remains the default provider for tests.
- Real local model tests must be opt-in integration tests.
- RAG output must never omit citations for paper-derived claims.
- If retrieval evidence is weak or empty, answer must report insufficient evidence.
- Local model failures must not corrupt stored papers or segments.

## Suggested Files

- `src/lib/models/ollama-adapter.ts`: local model adapter.
- `src/lib/models/health.ts`: provider health checks.
- `src/lib/retrieval/fts.ts`: SQLite FTS5 index and search.
- `src/lib/retrieval/index-segments.ts`: segment indexing.
- `tests/retrieval.test.ts`: FTS retrieval behavior with fixtures.
- `tests/model-fake-regression.test.ts`: fake provider remains deterministic.
- `tests/rag-citation-policy.test.ts`: citation policy independent of provider.

## Harness Requirements

- Keep `pnpm test` no-network and provider=`fake`.
- Add opt-in local model check, for example:

```bash
PAPER_LAB_MODEL_PROVIDER=ollama pnpm test:integration:model
```

- The golden RAG fixture must still pass under fake mode.
- Add retrieval tests that verify ranking and insufficient-evidence behavior without a real model.

## Acceptance Criteria

- User can configure `PAPER_LAB_MODEL_PROVIDER=fake` or a local provider.
- App clearly reports local model unavailable when the provider cannot be reached.
- Retrieval is segment-based and citation-preserving.
- Fake adapter tests remain stable.
- Local provider does not become required for build or default tests.

## Required Verification

```bash
pnpm typecheck
pnpm test
pnpm build
```

Run local model integration only when the local provider is installed and intentionally enabled.

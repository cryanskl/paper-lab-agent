# Phase 4 Implementation Report

> Records the Phase 4 "Local Model RAG" delivery on `paper-lab-agent`.
> Phase 4 adds an optional Ollama-compatible local model path,
> a citation policy that is enforced regardless of the active
> provider, and a SQLite FTS5 ranking signal for retrieval.

## 1. Goal Recap

Add an opt-in local-model path for RAG without changing the
default behavior of the app or weakening the citation
requirements. Keep:

- The fake adapter as the default and provider=`fake` in tests.
- The Phase 1 RAG golden tests stable.
- The harness rule that default tests are no-network and
  provider-agnostic.

## 2. Feature Breakdown

| # | Feature | Commit | Files |
|---|---------|--------|-------|
| 4.1 | SQLite FTS5 full-text index for paper segments | `0f40690` | `src/lib/retrieval/{fts,index-segments}.ts`, `tests/retrieval.test.ts` |
| 4.2 | Citation policy enforced on every RAG answer | `ac93da4` | `src/lib/assistant/citation-policy.ts`, `src/lib/assistant/answer.ts`, `tests/rag-citation-policy.test.ts` |
| 4.3 | Ollama local model adapter + health check + factory gating | `c941ec5` | `src/lib/models/{ollama-adapter,health}.ts`, `src/lib/models/{adapter,index}.ts`, `tests/model-fake-regression.test.ts`, sync-vs-async split in `assistant/answer.ts`, `simulation/build-spec.ts`, `intake/run-intake.ts` |
| 4.4 | Sources UI surfaces model selection + opt-in health probe | `dd84484` | `src/app/sources/{page,actions}.ts`, `src/lib/sources/policy.ts`, `tests/sources.test.ts` |

Each commit was pushed to `phase/4-local-model-rag` and merged
into `main` via a single `--no-ff` merge commit.

## 3. Architecture Notes

### FTS5

- `src/lib/retrieval/fts.ts` ships:
  - `isFts5Available(db)`: probes the SQLite build via a
    throw-away virtual table; returns false on a build without
    FTS5 compiled in.
  - `ensureFtsSchema(db)`: idempotently creates
    `paper_segments_fts(paperId UNINDEXED, segmentId UNINDEXED,
    english, tokenize='unicode61')`.
  - `rebuildFtsIndex(db, segments)`: explicit rebuild (no
    triggers), so the indexing strategy is testable and easy to
    invalidate.
  - `searchFts(db, query, { limit })`: sanitizes the query into
    a quoted FTS5 MATCH expression, returns `{ paperId,
    segmentId, rank, snippet }` rows.
- `src/lib/retrieval/index-segments.ts` exposes
  `indexAllSegments` / `indexPaperSegments` / `ftsSearch` /
  `isLocalRetrievalAvailable` so the rest of the app does not
  need to know about the virtual table.

The default RAG path in `assistant/answer.ts` is deliberately
**unchanged**: FTS5 is an additional ranking signal so the
Phase 1 RAG golden tests stay green without any modifications.

### Citation Policy

- `enforceCitationPolicy({ answer, retrievedSegments, paperTitleByPaperId })`
  is a pure function that runs after the model adapter returns.
- Branch 1 — `retrievedSegments.length === 0`:
  - The answer is forced to `"insufficient evidence"`.
  - Citations are cleared.
  - `insufficientEvidence` is forced to `true`.
- Branch 2 — segments were retrieved:
  - Citations already present in the adapter's output are
    preserved (the adapter's title is not overwritten).
  - For any retrieved segment not already cited, a fallback
    citation is appended with `paperTitle` looked up from the
    `paperTitleByPaperId` map.
  - The answer text is checked: if it mentions none of the
    paperId / segmentId values, a `(Source: ...)` suffix is
    appended so a downstream reader can always trace the claim
    back to its source.
- `hasAtLeastOneCitation` / `isInsufficientEvidence` are
  cheap predicates for tests and future UI badges.

### Adapter Interface

- The `ModelAdapter` interface now allows `MaybePromise<T>` return
  values. The fake adapter (still sync) automatically satisfies
  the Promise branch, so no behavior change.
- `askQuestion` / `runIntake` / `buildSimulationSpec` are
  **sync** (matching the Phase 1 RAG golden tests) and detect a
  Promise return with a typed error. The corresponding
  `askQuestionAsync` / `buildSimulationSpecAsync` helpers expose
  the async path for callers that explicitly want a real model.

### Ollama Adapter

- `OllamaAdapter` posts to `${endpoint}/api/generate` with
  `{ model, prompt, stream: false }` and returns the
  `response` field.
- All four adapter methods are implemented as prompts:
  - `scoreRelevance` asks for `ACCEPT` / `REJECT` + rationale.
  - `translate` sends the English paragraph and reads the
    response.
  - `generateAnswer` builds a context block with `[paperId /
    segmentId — title]` markers and asks the model to cite at
    least one of them.
  - `generateSimulationSpec` requests a JSON object; the
    adapter falls back to a deterministic placeholder spec if
    the parse fails.
- `OllamaUnavailableError` is the typed error for non-2xx
  responses and connection issues.

### Health Check

- `checkProviderHealth` returns a structured `{ ok, message,
  model }` result.
  - `fake` -> always `{ ok: true, model: "fake" }`.
  - `ollama` -> `GET /api/tags`; success reports the model
    list; failure surfaces a clear `ollama is not reachable:
    ECONNREFUSED` (or similar) message.
  - Unknown provider -> `{ ok: false, message: "unknown
    provider: ..." }`.

### Factory

- The factory at `src/lib/models/index.ts` still defaults to the
  fake adapter. It constructs an `OllamaAdapter` only when
  `PAPER_LAB_MODEL_PROVIDER=ollama` AND
  `PAPER_LAB_LIVE_MODEL_OPT_IN=true` is set; this double gate
  prevents a stray env file from silently changing which model
  backs the app. Unknown providers throw a typed error.

## 4. Verification

All gates run after the merge into `main`:

```text
pnpm typecheck    # tsc --noEmit        → clean
pnpm test         # vitest run          → 14 files, 127 / 127 pass
pnpm build        # next build          → 6 routes, no warnings
```

Phase 1's 16 baseline tests, Phase 2's 45 tests, and Phase 3's
29 tests all pass without changes. Phase 4 adds 37 new tests:

- `tests/retrieval.test.ts` (9)
- `tests/rag-citation-policy.test.ts` (8)
- `tests/model-fake-regression.test.ts` (17)
- `tests/sources.test.ts` (3 new, 9 total)

`pnpm test` was confirmed to be **no-network** in
`model-fake-regression.test.ts`: every Ollama call takes a
stubbable `fetchImpl` and the default tests pass a stub.

A `curl` smoke test against `pnpm start` returned HTTP 200 for
`/sources` and rendered the new section:

```text
Local model · Active provider: fake — fake (deterministic default).
health probe is only available when the provider is ollama AND
PAPER_LAB_LIVE_MODEL_OPT_IN=true is set.
```

## 5. Scope / Excludes Check

- ✅ Local model adapter interface implementation
  (Ollama-compatible).
- ✅ Configurable model provider selection
  (`PAPER_LAB_MODEL_PROVIDER`).
- ✅ Retrieval improvements using SQLite FTS5
  (default RAG path is unchanged; FTS5 is opt-in ranking).
- ✅ Answer generation that cites retrieved paper segments
  (citation policy enforced regardless of provider).
- ✅ Model health check and clear error messages when the local
  model is unavailable.
- ✅ Evaluation set for cited answers and insufficient-evidence
  behavior (`rag-citation-policy.test.ts` + `retrieval.test.ts`).

Excludes (not done, deferred):

- ❌ Cloud model as the default.
- ❌ Uncited model answers.
- ❌ Automatic upload of paper contents to external APIs.
- ❌ Fine-tuning.
- ❌ Multi-agent autonomous research workflows.

## 6. Local-Data / Safety Boundaries

- The fake adapter remains the default; the only path to a real
  model is `PAPER_LAB_MODEL_PROVIDER=ollama` +
  `PAPER_LAB_LIVE_MODEL_OPT_IN=true`. Both must be set.
- The default `pnpm test` does not require Ollama; the
  `OllamaAdapter` is exercised via a stubbed `fetchImpl`.
- `enforceCitationPolicy` is the safety net: even if a real
  model adapter forgets to include citations, the policy layer
  fills them in from the retrieved segments.
- Local model failures (network, parse, non-2xx) surface as
  typed errors (`OllamaUnavailableError`) and never corrupt
  stored papers or segments.

## 7. Known Limitations / Follow-ups

- The FTS5 index is rebuilt explicitly; for very large libraries
  this becomes O(N) per upsert. A real-world optimization
  (delta indexing) is a Phase 6+ concern.
- `askQuestion` / `runIntake` / `buildSimulationSpec` are sync
  and surface a typed error when the active adapter is async.
  Callers wanting the Ollama path should switch to
  `askQuestionAsync` / `buildSimulationSpecAsync` (and a
  future `runIntakeAsync`).
- The Ollama adapter does not currently support streaming;
  `stream: false` is the only mode.
- We do not yet test against a real Ollama instance; the
  `tests/integration/ollama.test.ts` is a follow-up under the
  opt-in `pnpm test:integration:arxiv` style.

## 8. Operating the App

```bash
cd /Users/zenith/Desktop/paper-lab-agent
pnpm install
pnpm seed
pnpm dev
# Open /sources to see the active model provider.
# To enable the local Ollama path:
#   export PAPER_LAB_MODEL_PROVIDER=ollama
#   export PAPER_LAB_LIVE_MODEL_OPT_IN=true
#   export PAPER_LAB_OLLAMA_URL=http://localhost:11434
#   export PAPER_LAB_OLLAMA_MODEL=llama3
#   pnpm dev
# The "Check local model health" button will appear under the
# "Local model" section on /sources.
```

To verify the Phase 4 loop deterministically:

```bash
pnpm typecheck
pnpm test
pnpm build
```

## 9. Git State

- Phase branch: `phase/4-local-model-rag`
- Pushed feature commits: `0f40690`, `ac93da4`, `c941ec5`, `dd84484`
- Merge commit: produced by the `git merge --no-ff` step above
- All gates passed before and after the merge.

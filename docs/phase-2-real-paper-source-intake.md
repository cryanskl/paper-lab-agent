# Phase 2: Real Paper Source Intake

## Goal

Replace fixture-only candidate discovery with live arXiv metadata intake while preserving deterministic fixture mode and the existing no-network test harness.

## Scope

Phase 2 includes:

- Research Profile persistence for keywords, seed paper references, arXiv query, max candidates, and mode selection.
- Sources & Profile page for viewing and editing the local research profile.
- Manual Run Intake page or action.
- Live arXiv metadata fetch for paper candidates.
- Fixture/live mode separation.
- Intake run logs that show source, query, candidate count, accepted count, rejected count, and errors.
- Integration script or test for live arXiv that runs only when explicitly invoked.

Phase 2 excludes:

- PDF download.
- PDF parsing.
- Full paper text extraction.
- Real model provider integration.
- Embedding search.
- Automated daily scheduling.
- Login/authenticated download.

## Implementation Boundaries

- Keep fixture mode as the default development and test mode.
- Live arXiv intake must write the same `Paper` shape used by Phase 1.
- Relevance scoring still uses the fake adapter and profile keywords.
- Live intake errors must be visible in `intake_runs` and must not crash the app shell.
- Do not introduce background workers yet; manual trigger is enough.

## Suggested Files

- `src/lib/profile/`: profile load/save helpers.
- `src/lib/intake/arxiv-client.ts`: arXiv metadata fetch and normalization.
- `src/lib/intake/run-intake.ts`: shared intake runner for fixture and live sources.
- `src/app/sources/page.tsx`: Sources & Profile UI.
- `src/app/intake/page.tsx`: manual intake run UI if separated from sources.
- `tests/profile.test.ts`: profile persistence.
- `tests/intake-arxiv-normalization.test.ts`: no-network normalization from recorded arXiv fixture.

## Harness Requirements

- Add a recorded arXiv response fixture under `fixtures/intake/`.
- Unit tests must parse the recorded fixture, not call live arXiv.
- Live arXiv verification must be a separate explicit command such as:

```bash
pnpm test:integration:arxiv
```

or:

```bash
pnpm intake:live -- --source arxiv
```

The default `pnpm test` must remain no-network.

## Acceptance Criteria

- User can view and edit local research profile values.
- User can run fixture intake exactly as before.
- User can manually run live arXiv metadata intake.
- Live arXiv papers appear in Paper Library with metadata and relevance rationale.
- Intake run logs distinguish fixture and live runs.
- Existing Phase 1 reader/RAG/simulation fixture behavior does not regress.

## Required Verification

```bash
pnpm typecheck
pnpm test
pnpm build
pnpm seed
```

Then run the explicit live arXiv check only when the network is intentionally allowed.

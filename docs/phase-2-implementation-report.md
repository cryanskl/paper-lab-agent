# Phase 2 Implementation Report

> Records the Phase 2 "Real Paper Source Intake" delivery on
> `paper-lab-agent`. Phase 2 ships a local research profile, an
> opt-in arXiv metadata client, a shared intake runner, and a
> Sources & Profile page — all without regressing the Phase 1
> fixture-only loop.

## 1. Goal Recap

Replace fixture-only candidate discovery with **live arXiv metadata
intake** while preserving:

- Deterministic fixture mode and the no-network test harness.
- The fake `ModelAdapter` and the existing `Paper` shape.
- The harness rules in `docs/harness.md` (no LLM, no network in
  default tests).

## 2. Feature Breakdown

| # | Feature | Commit | Files |
|---|---------|--------|-------|
| 2.1 | Research profile persistence (`data/profile.json`) | `20a3df2` | `src/lib/profile/index.ts`, `tests/profile.test.ts`, config + helper updates |
| 2.2 | arXiv metadata client + recorded XML fixture | `d3fa324` | `src/lib/intake/arxiv-client.ts`, `fixtures/intake/arxiv-live-sample.xml`, `tests/intake-arxiv-normalization.test.ts`, vitest + package script updates |
| 2.3 | Shared `runIntake` runner | `43bfb83` | `src/lib/intake/run-intake.ts`, refactored `src/lib/intake/import-fixture.ts`, `tests/intake-runner.test.ts` |
| 2.4 | Sources & Profile UI with live opt-in gate | `c366e36` | `src/app/sources/{page,actions}.ts`, `src/lib/sources/policy.ts`, `tests/sources.test.ts`, layout + globals updates |

Each commit was pushed to `phase/2-real-paper-source-intake` and
merged into `main` via a single `--no-ff` merge commit (`02049f6`).

## 3. Architecture Notes

### Profile

- A small JSON document at `data/profile.json` (overridable via
  `PAPER_LAB_PROFILE_PATH`) carrying keywords, arXiv query, max
  candidates, source, and seed paper ids.
- `saveProfileToPath` writes atomically via a sibling tmp file +
  `fs.renameSync`, so a mid-write crash cannot leave a half-written
  profile.
- `validateProfile` rejects malformed input with a typed
  `ProfileValidationError` so the UI / CLI get a readable error.

### arXiv Client

- Atom XML parser (`parseArxivAtom`) is a pure function: it strips
  the URL prefix and version suffix, decodes common HTML entities,
  and resolves the PDF link by scanning **all** `<link>` tags (so
  attribute order in arXiv responses does not matter).
- `fetchArxivCandidates` only ever fetches metadata; the `pdfUrl`
  field is recorded but never downloaded in Phase 2.
- Network access is gated by `allowNetwork: true`. The function
  throws `ArxivAccessError("network disabled ...")` otherwise, so
  the default test mode never hits the network.

### Shared Runner

- `runIntake({ source, query, candidates })` is the single source
  of truth for relevance scoring, paper upsert, and `intake_runs`
  bookkeeping. Both `importIntakeFixture` and the live arXiv action
  feed the same `NormalizedCandidate[]` shape into it.
- `source` and `query` are always the caller's values, so
  `intake_runs` rows distinguish fixture runs (`arxiv-fixture`)
  from live runs (`arxiv`) by the column values themselves.
- A per-candidate `try/catch` records the candidate's `externalId`
  in `errorLog` and increments `rejectedCount` exactly once
  (regression-pinned by the fault-injection test). Without this
  fix, the Phase 1 code double-counted `rejected` on a per-row
  failure.

### Sources UI

- `/sources` is the only page added in Phase 2; it is reachable
  from the new `Sources` link in the site nav.
- The page renders a profile form, two run-control buttons
  (fixture always enabled, live disabled by default), and a
  table of the 10 most recent intake runs.
- Live intake is gated in **three** places:
  1. UI: button rendered `disabled` with a tooltip until
     `PAPER_LAB_LIVE_INTAKE_OPT_IN=true` is set.
  2. Server Action: `runLiveArxivIntakeAction` checks
     `envOptedIn()` and redirects to `/sources?live=blocked`
     otherwise.
  3. arXiv Client: `fetchArxivCandidates` throws when
     `allowNetwork` is false (defense in depth).
- Pure form/parse logic lives in `src/lib/sources/policy.ts` so
  the action and unit tests share the same implementation.

## 4. Verification

All gates run after the merge into `main`:

```text
pnpm typecheck    # tsc --noEmit        → clean
pnpm test         # vitest run          → 8 files, 45 / 45 pass
pnpm build        # next build          → 6 routes, no warnings
```

Phase 1's 16 baseline tests still pass unchanged:

- `tests/intake.test.ts` (5/5)
- `tests/bilingual.test.ts` (3/3)
- `tests/rag.test.ts` (5/5)
- `tests/simulation.test.ts` (3/3)

Phase 2 added:

- `tests/profile.test.ts` (7/7)
- `tests/intake-arxiv-normalization.test.ts` (9/9)
- `tests/intake-runner.test.ts` (7/7)
- `tests/sources.test.ts` (6/6)

`pnpm test` was confirmed to be **no-network** in the
`parseArxivAtom` and `fetchArxivCandidates` tests — the network
gate rejects any live call when `allowNetwork` is false, and the
recorded XML fixture is the only thing the suite reads.

A `curl` smoke test against `pnpm start` returned HTTP 200 for
`/sources` and rendered the expected UI labels ("Run fixture
intake", "Live arXiv disabled", "PAPER_LAB_LIVE_INTAKE_OPT_IN",
"Recent intake runs", "Research profile").

## 5. Scope / Excludes Check

- ✅ Research Profile persistence for keywords, query, max, mode,
  seeds.
- ✅ Sources & Profile page for view + edit + manual run.
- ✅ Live arXiv metadata fetch (Atom XML, no PDF).
- ✅ Fixture/live mode separation (`source` column + UI badge).
- ✅ Intake run logs distinguish fixture vs live runs.
- ✅ Integration-style live arXiv command surface:
  `pnpm test:integration:arxiv`, `pnpm intake:live` script entries.

Excludes (not done, deferred):

- ❌ PDF download (Phase 3).
- ❌ PDF parsing (Phase 3).
- ❌ Real model provider integration (Phase 4).
- ❌ Embedding search (Phase 4).
- ❌ Automated daily scheduling (Phase 6).
- ❌ Login / authenticated download (out of V1).

## 6. Local-Data / Safety Boundaries

- `data/profile.json` lives under the configured `PAPER_LAB_DATA_DIR`
  and is covered by `.gitignore` (`data/`).
- No PDFs are written; the `pdfUrl` field is recorded in the DB
  but no HTTP GET to a PDF URL is issued.
- The live arXiv metadata fetch honors the
  `source-and-download-policy.md` rules: arXiv is a stable, open
  metadata source with no auth.
- The Phase 1 default tests still run on a fresh temp DB and never
  call the network; this is enforced by:
  - `vitest.config.ts` excluding `tests/integration/**`,
  - the arXiv client throwing when `allowNetwork` is false,
  - the runner having no `fetch` import (live fetch is only
    reachable via the gated Server Action).

## 7. Known Limitations / Follow-ups

- The Sources page does not yet show a flash banner for action
  results. After the action returns, the page re-reads
  `listIntakeRuns` and the new run appears at the top of the
  table; this is sufficient for V1, but a flash banner is a
  reasonable Phase 6 polish.
- Live arXiv is intentionally not exercised by the default test
  suite. `tests/integration/arxiv.test.ts` is a follow-up and is
  not yet authored (the `test:integration:arxiv` script entry
  points at the future file).
- The profile `source` field is free-form; Phase 6 can enforce a
  closed set if needed.

## 8. Operating the App

```bash
cd /Users/zenith/Desktop/paper-lab-agent
pnpm install
pnpm seed               # load Phase 1 fixtures
pnpm dev                # http://localhost:3000
# Open /sources to view / edit the local profile.
# Set PAPER_LAB_LIVE_INTAKE_OPT_IN=true in .env, restart,
# then the "Run live arXiv intake" button becomes active.
```

To verify the Phase 2 loop deterministically:

```bash
pnpm typecheck
pnpm test
pnpm build
```

## 9. Git State

- Phase branch: `phase/2-real-paper-source-intake`
- Merge commit: `02049f6` (no-ff merge into `main`)
- Pushed feature commits: `20a3df2`, `d3fa324`, `43bfb83`, `c366e36`
- All gates passed before and after the merge.

# Phase 1: Fixture-Based Minimal Loop

## Status

Completed locally. This phase establishes the smallest runnable research loop without network access and without a real model provider.

## Goal

Prove that `paper-lab-agent` can ingest paper-like fixture data, store it in SQLite, render bilingual paper segments, answer cited questions, and generate a simulation spec with deterministic fake model behavior.

## Scope

Phase 1 includes:

- Next.js + TypeScript + pnpm project initialization.
- SQLite metadata storage and local `data/` directory convention.
- Deterministic fake model adapter.
- Fixture-backed paper intake from `fixtures/intake/arxiv-sample.json`.
- Fixture-backed paper segments from `fixtures/papers/sample-paper-segments.json`.
- Minimal Paper Library page.
- Minimal Bilingual Reader page.
- Minimal Ask Papers page with citations and insufficient-evidence behavior.
- Minimal Simulation Spec page.
- No-network, no-LLM Vitest harness.

Phase 1 excludes:

- Live arXiv/RSS/API fetching.
- PDF download.
- PDF parsing.
- Real translation.
- Real OpenAI/Ollama/local model integration.
- Scheduled automation.
- Login/authenticated download.
- Complete experiment reproduction.

## Key Invariants

- Fixture intake, fixture segments, RAG golden questions, and simulation artifact must reference the same accepted paper id: `paper-2606-00001`.
- Default tests must not call the network or a real model.
- RAG answers must include `paperId` and `segmentId` citations.
- Unsupported questions must return `insufficient evidence`.
- Generated local runtime state must stay under `data/` and must not be committed.

## Required Verification

Run from the project root:

```bash
pnpm typecheck
pnpm test
pnpm build
pnpm seed
```

Then verify seeded data:

```bash
node - <<'NODE'
const Database = require('better-sqlite3');
const db = new Database('data/paper-lab-agent.sqlite');
console.log(db.prepare('select paperId,status from papers order by paperId').all());
console.log(db.prepare('select paperId,count(*) as count from paper_segments group by paperId').all());
NODE
```

Expected seeded invariant:

- `paper-2606-00001` exists and is `accepted`.
- `paper-2606-00001` has 3 segments.
- No placeholder `paper-surrogate-sim-001` paper exists.

## Completion Notes

The implementation report is stored in `docs/phase-1-implementation-report.md`. Keep that report as historical evidence; future fixes should update this phase plan only when Phase 1 invariants change.

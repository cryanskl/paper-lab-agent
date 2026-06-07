# paper-lab-agent Architecture

## Architecture Style

V1 uses a modular monolith: one local Next.js application with clear module boundaries. The deployment should be simple, but the code should still separate paper intake, filtering, storage, reading, RAG, simulation, and model adapters.

## Planned Stack

- Next.js and TypeScript for UI, API routes, and local workflow entry points.
- SQLite for metadata, task state, and retrieval-friendly segment records.
- Local `data/` file store for PDFs, parsed text, translations, indexes, and simulation artifacts.
- Deterministic fake model adapter first.
- Optional future local model adapter such as Ollama after the harness and product flow are stable.

## Module Boundaries

### Intake

Fetch candidate papers from stable sources such as arXiv, RSS, APIs, and journal endpoints. Intake owns source configuration, candidate normalization, deduplication, run logs, and raw metadata capture.

Intake must not decide final relevance alone and must not bypass download restrictions.

### Relevance

Score candidate papers against the research profile. V1 combines keyword/seed-paper signals with fake model output. Every accepted or rejected paper needs a human-readable relevance rationale.

### Library

Own persistent paper metadata, processing status, file paths, segment records, and task logs. Other modules should use library APIs instead of directly rewriting storage state.

### Reader

Render paragraph-level bilingual reading. Reader depends on stable `PaperSegment` ids and must preserve English/Chinese order and alignment.

### Assistant

Retrieve evidence across ingested paper segments and generate cited answers. Assistant must return citations and must expose insufficient evidence when retrieval does not support an answer.

### Simulation

Generate physics/engineering toy simulation specs and artifacts from selected paper evidence. Simulation output must include assumptions, parameters, units, boundary conditions, run steps, and artifact paths.

### Model Adapters

Provide a narrow interface for relevance, translation, Q&A, and simulation spec generation. The default adapter is fake and deterministic. Real local model adapters must be optional and must not be required for core tests.

## Data Flow

```text
ResearchProfile
  -> IntakeRun
  -> Candidate Paper
  -> Relevance result
  -> Accepted Paper
  -> Download attempt
  -> PDF/Text extraction
  -> PaperSegment records
  -> Bilingual Reader
  -> RAG Assistant
  -> Simulation Lab
```

## Operational Rules

- Default local test mode should avoid network and real model calls.
- Real network source checks belong in integration tests.
- Authenticated download support must be explicit, allowlisted, and failure-aware.
- The schedule entry should call the same intake pipeline used by manual runs.

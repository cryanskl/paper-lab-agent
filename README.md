# paper-lab-agent

`paper-lab-agent` is a local-first research assistant for paper discovery, bilingual reading, RAG Q&A, and simulation-oriented experiment support.

The project is designed for a single researcher first. V1 should make the full loop work on a local machine: discover relevant papers, store and parse them, read them in English/Chinese side-by-side, ask cited questions across the paper library, and generate small physics/engineering simulation artifacts from paper methods.

## V1 Scope

- Paper intake from stable sources such as arXiv, RSS feeds, APIs, and journal search endpoints.
- Relevance filtering from a research profile that combines keywords and seed papers.
- Local paper library using SQLite metadata and a local file store for PDFs, parsed text, translations, and experiment artifacts.
- Bilingual reader with paragraph-level English/Chinese alignment.
- RAG Q&A across all ingested papers, with required paper and segment citations.
- Experiment Lab for physics/engineering toy simulations with assumptions, parameters, units, boundary conditions, runnable artifacts, and visual explanations.
- Deterministic fake model adapter first; local model integration comes after the product flow is stable.

## Non-Goals For V1

- No cloud sync, account system, team collaboration, or hosted multi-user deployment.
- No promise of full benchmark reproduction from papers.
- No bypassing paywalls, CAPTCHA, access controls, robots restrictions, or site terms.
- No real model dependency in the core harness; tests must run without network and without an LLM.

## Planned Stack

- Next.js + TypeScript + pnpm for the local web app.
- SQLite for metadata and task state.
- Local `data/` directory for PDFs, parsed text, translations, indexes, and simulation outputs.
- Fake model adapter for deterministic translation, relevance, Q&A, and simulation spec outputs.
- Later optional model adapters for Ollama or another local model runtime.

## Repository Layout

```text
docs/
  research-assistant-v1-plan.md
  product-spec.md
  architecture.md
  source-and-download-policy.md
  evaluation.md
  harness.md
fixtures/
  intake/
  papers/
  rag/
  simulation/
```

## Development Status

This repository currently contains product and engineering constraints plus fixture seeds. It has not yet been initialized as a Next.js application.

## Quick Start

For now, review the planning documents:

```bash
ls docs
cat docs/product-spec.md
cat docs/architecture.md
cat docs/harness.md
```

When code is added, core tests should default to fixture-backed no-network mode.

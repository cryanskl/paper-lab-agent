# paper-lab-agent Product Spec

## Product Intent

`paper-lab-agent` is a local-first research assistant for a single researcher. It should help with daily paper discovery, relevance filtering, bilingual reading, cited RAG Q&A, and physics/engineering simulation-oriented experiment support.

V1 should prove the complete research loop on a local machine before adding real model providers, cloud deployment, or complex automation.

## V1 Capabilities

- Discover candidate papers from stable sources such as arXiv, RSS feeds, APIs, and journal search endpoints.
- Filter candidates with a research profile built from keywords and seed papers.
- Store accepted papers in SQLite and save PDFs, parsed text, translations, indexes, and experiment outputs in a local file store.
- Render a paragraph-level bilingual reader with English on the left and Chinese translation on the right.
- Answer questions across all ingested papers using retrieved evidence and required citations.
- Generate physics/engineering toy simulation specs from paper method sections.
- Provide deterministic fake model behavior for relevance, translation, Q&A, and simulation specs until a real local model adapter is added.

## Core Data Objects

- `ResearchProfile`: sources, keywords, seed papers, download allowlist, and schedule entry configuration.
- `Paper`: title, authors, abstract, source, URL, PDF path, processing status, and relevance rationale.
- `PaperSegment`: paper id, segment id, paragraph order, English text, Chinese translation, page or location, and retrieval index fields.
- `IntakeRun`: run time, source, candidate count, accepted count, rejected count, download failures, and error log.
- `AssistantAnswer`: question, retrieved segments, answer text, citations, and insufficient-evidence marker.
- `SimulationSpec`: source paper/method, assumptions, parameters, units, boundary conditions, run steps, and artifact paths.

## V1 Workflow

1. The user configures sources, keywords, seed papers, and download allowlist.
2. The user manually triggers intake, or later uses the stable schedule entry command.
3. The system fetches candidates, deduplicates them, and records intake state.
4. Relevance filtering runs with keyword/seed-paper signals and a deterministic fake model adapter.
5. Accepted papers attempt PDF download according to the download policy.
6. Downloaded PDFs are parsed into paragraph segments.
7. English segments and Chinese translations are stored with stable segment ids.
8. The reader shows paragraph-level English/Chinese alignment.
9. The assistant retrieves across all ingested papers and answers with citations.
10. The lab generates a toy simulation spec and artifact outline from selected method evidence.

## Explicit Non-Goals

- No cloud sync, login system, hosted multi-user service, or team collaboration in V1.
- No full benchmark reproduction promise.
- No automatic bypass of restricted access.
- No default dependency on network or real LLMs in the harness.

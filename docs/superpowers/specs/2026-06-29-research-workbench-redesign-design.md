# Research workbench frontend redesign

## Summary

Redesign the Streamlit frontend from module-based tabs into a three-column research workbench for simulation engineers.

The current frontend exposes backend modules directly: search, config, documents, RAG, chemistry. The redesigned frontend should match the user's actual workflow:

1. Put papers and PDFs into the local knowledge base.
2. Analyze PDFs into sections, translations, chunks, and extracted chemistry assets.
3. Ask the whole knowledge base by default.
4. Review, summarize, and export the chemistry library produced during PDF analysis.

This is a frontend information architecture and layout redesign. It should reuse the existing FastAPI contract and helper functions in `app/frontend_api.py`.

## Goals

- Make the first screen understandable to a simulation engineer without knowing backend modules.
- Treat RAG as knowledge-base Q&A, not single-paper Q&A.
- Present chemistry extraction as part of PDF analysis and knowledge deposition, not as an isolated final step.
- Keep maintenance, raw JSON, API docs, release readiness, journals, and categories available but visually secondary.
- Preserve existing functionality and API behavior.

## Non-goals

- Do not add user accounts, cloud sync, permissions, or collaboration.
- Do not change API paths, database schema, or response contracts.
- Do not introduce a new frontend framework.
- Do not make automatic background refresh the default behavior.
- Do not hide failure details needed for debugging; move them into maintenance or expandable diagnostics.

## User

Primary user: simulation engineer preparing low-temperature plasma literature and chemistry data for modeling.

Primary job: find and ingest relevant papers, analyze PDFs, ask across the accumulated knowledge base, then review and export reaction data.

Secondary users:

- Researcher reading and comparing papers.
- Maintainer configuring journals, categories, external capabilities, and release readiness.

## Information architecture

### Top status strip

The top of the page should provide compact operational context:

- Knowledge base counts: papers, PDFs/documents, chunks.
- PDF analysis counts: parsed, indexed, chemistry extracted, failed.
- Chemistry library counts: reaction sets, pending/unverified reactions, export-ready sets when available from current data.
- System health: API status, release ready state, config warning count, GROBID live state when checked.

This replaces the large always-visible sidebar. Detailed system state moves into an expandable maintenance area.

### Left column: Library intake

Purpose: show what data exists and help users add more.

Content:

- Paper search with compact filters: keyword, journal, category, year range, OA only, sort.
- Search result cards that show title, journal/date, OA state, categories, DOI/dedupe metadata in a compact secondary line, and OA/Landing links.
- Actions on papers: classify, resolve OA, manual category override in an expander.
- PDF upload associated with an existing paper search result or no paper.
- Document queue with statuses for parse, index, translation, and chemistry extraction.
- Crawl task creation and recent crawl diagnostics in an expander.
- Configuration maintenance in a collapsed section: journals and categories.

The left column is the source-of-truth selector for the rest of the workbench. Selecting a document here should drive the article analysis preview in the middle column and the chemistry context in the right column.

### Middle column: Knowledge base Q&A and article analysis

Purpose: make the knowledge base useful after ingestion.

Default mode:

- Ask the whole knowledge base. The RAG request should send `document_ids: []` unless the user explicitly scopes the query.
- Scope controls are optional and secondary: all knowledge base, selected document, selected category, selected paper when available.
- Answers show citations immediately below the answer: paper title, document id, section title/type, chunk id, score, and source excerpt.

Selected document mode:

- Show document analysis status and next useful action.
- Group the existing operations as PDF analysis:
  - Parse sections.
  - Index into the knowledge base.
  - Generate translation preview.
  - Extract chemistry assets.
- Keep operations explicit. A combined "continue analysis" button may be added only if it calls existing steps in a predictable sequence and still surfaces each step's result.
- Show section preview, translation preview, and chunk/source preview in tabs or compact expanders inside the middle column.
- Show failures inline with plain messages and raw payload in an expander.

Important behavior:

- Q&A is not framed as "ask one paper." It is "ask the knowledge base" with optional scoping.
- The selected document is a reading context, not the default RAG boundary.

### Right column: Chemistry deposition and delivery

Purpose: show what the analyzed PDFs have contributed to the chemistry library.

Content:

- Reaction sets grouped by selected document when one is selected; otherwise show recent/pending reaction sets when available through existing data paths.
- Pending/unverified reactions first.
- Each reaction card should show:
  - Reaction expression.
  - Reaction type and rate type.
  - Rate value.
  - Threshold eV.
  - Cross-section URL / LXCat evidence.
  - Source section and source excerpt.
  - Confidence.
  - Verification fields.
- Audit log remains accessible in an expander.
- Export controls appear at the reaction-set level and are disabled until the set is export-ready.
- Export formats stay JSON, TXT, and BOLSIG.
- A short deposition summary should explain which document/paper produced the current reaction set and how many items still need review.

Important behavior:

- Chemistry data is presented as produced during PDF analysis.
- Review and export are downstream quality gates, not the moment where chemistry "appears."

### Maintenance area

Place the following in a bottom or sidebar expander named "System and maintenance":

- Release readiness details.
- Demo data state.
- External capabilities and config warnings.
- Storage health.
- Status distributions.
- API docs links.
- Full journal/category CRUD if it does not fit in the left column.
- Raw JSON diagnostics.

The maintenance area must remain accessible because this project is still in release hardening, but it should not dominate the first screen.

## Component boundaries

Refactor `streamlit_app.py` into small rendering functions before changing layout. Suggested boundaries:

- `load_system_status()`
- `render_status_strip(status)`
- `render_library_intake(...)`
- `render_paper_search(...)`
- `render_document_queue(...)`
- `render_knowledge_qa(...)`
- `render_document_analysis(...)`
- `render_chemistry_delivery(...)`
- `render_system_maintenance(status)`

Keep API transformation and defensive payload handling in `app/frontend_api.py`. Add frontend helper functions there only when data normalization is reusable and testable.

## Data flow

1. Load health and system status once near the top of the page.
2. Load paper search data in the left column from `/papers`, `/journals`, and `/categories`.
3. Load documents from `/documents` and let the selected document id become shared page state.
4. Middle column:
   - RAG uses `/rag/query`.
   - Default `document_ids` is `[]`.
   - Selected document only scopes the query when the user explicitly chooses scoped mode.
   - Document analysis uses `/documents/{id}`, `/sections`, `/chunks`, and `/translation`.
5. Right column:
   - For selected document, load `/documents/{id}/reaction-sets`.
   - Load selected set through `/reaction-sets/{id}`.
   - Save reviews through `/reactions/{id}/verify`.
   - Export through `/reaction-sets/{id}/export?format=...`.

## Error handling

- API connection failure should stop the page with a clear API error.
- Per-panel failures should not collapse the whole workbench unless the shared health call failed.
- Show concise user-facing errors first.
- Keep raw payloads in expanders named "Diagnostics" or "Raw API response."
- Empty states should tell the user the next action:
  - No papers: import fixtures, run crawl, or adjust search.
  - No PDFs: upload a PDF.
  - No chunks: parse and index the PDF.
  - No reactions: run PDF chemistry analysis or inspect extraction failure.
  - No exports: verify all reactions first.

## Visual direction

- Keep the interface quiet, dense, and work-focused.
- Avoid marketing-style hero sections and decorative cards.
- Use a wide layout with three persistent columns:
  - Left: about 28%.
  - Middle: about 44%.
  - Right: about 28%.
- Use compact section headers, small status badges, and tables only where comparison matters.
- Prefer containers for repeated items and avoid nesting cards inside cards.
- Move raw JSON and low-frequency controls behind expanders.

## Testing and verification

Minimum verification after implementation:

- `python scripts/validate_docs_links.py`
- `git diff --check`
- `python -m pytest tests/test_frontend_api.py -q`
- `python -m pytest tests/test_api.py -q`
- `DEV_EXIT_AFTER_READY=true START_OPEN_BROWSER=false ./start.sh`
- `python scripts/health_check.py --require-frontend`

For final release-hardening closure, run:

- `bash scripts/release_check.sh`

Manual UI checks:

- First screen shows the three-column workbench.
- RAG question defaults to whole knowledge base when no scope is selected.
- Selecting a document updates article analysis and chemistry context.
- PDF analysis controls expose parse, index, translation, and chemistry extraction together.
- Reaction review and export still work.
- Maintenance diagnostics are still accessible.

## Implementation notes

- The existing backend already supports whole-knowledge-base RAG because `document_ids` can be empty.
- The existing PDF analysis capabilities are separate endpoints. The redesign groups them in the UI without changing their API contract.
- Streamlit's layout constraints mean narrow screens may stack columns. The primary target for this workbench is desktop use.

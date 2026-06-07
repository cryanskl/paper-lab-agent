# Phase 3: PDF Download, Parsing, and Bilingual Reading

## Goal

Turn accepted open-access paper metadata into local paper content: PDF files, parsed text, paragraph segments, and paragraph-level bilingual reading.

## Scope

Phase 3 includes:

- Open PDF download for directly accessible URLs.
- Download status transitions: `not_attempted`, `succeeded`, `download_failed`.
- Local PDF storage under the configured `data/pdfs/` directory.
- PDF text extraction for downloaded PDFs.
- Paragraph segmentation with stable segment ids.
- Translation pipeline interface with fake adapter output by default.
- Reader support for real parsed segments, not only fixture segments.
- Failure records for missing PDF URL, inaccessible PDF, parse failure, and empty extraction.

Phase 3 excludes:

- Paywall bypass.
- CAPTCHA bypass.
- Login/authenticated download.
- Real translation provider as the default.
- Perfect PDF layout reconstruction.
- OCR for scanned PDFs.

## Implementation Boundaries

- Follow `docs/source-and-download-policy.md`.
- Automatically download only directly accessible PDFs.
- Do not store credentials.
- Do not attempt browser login state.
- Treat PDF parsing as best-effort text extraction, not layout-perfect reproduction.
- Keep fake translation deterministic until a real model phase is approved.

## Suggested Files

- `src/lib/download/pdf-downloader.ts`: open PDF download and status update.
- `src/lib/pdf/parse-pdf.ts`: PDF text extraction.
- `src/lib/pdf/segment-text.ts`: paragraph segmentation and stable segment id generation.
- `src/lib/translation/translate-segments.ts`: fake translation pipeline wrapper.
- `tests/download-policy.test.ts`: policy and status behavior.
- `tests/pdf-segmentation.test.ts`: segment id and paragraph output.
- `fixtures/pdf/`: tiny synthetic PDF fixture or recorded extracted text fixture.

## Harness Requirements

- Default tests must not download from the network.
- Use a tiny local PDF fixture or extracted-text fixture for parser tests.
- Add tests for failed download states without real external calls.
- Add reader tests that assert real parsed segments align English and Chinese fields.

## Acceptance Criteria

- Accepted paper with open `pdfUrl` can be downloaded to `data/pdfs/`.
- Download failures are recorded without crashing intake.
- Parsed text produces ordered `PaperSegment` records for the same paper id.
- Reader displays real parsed segments with left English and right Chinese.
- Existing fixture-based reader and RAG tests still pass.

## Required Verification

```bash
pnpm typecheck
pnpm test
pnpm build
```

If a live open-PDF smoke script is added, run it separately and document that it uses network access.

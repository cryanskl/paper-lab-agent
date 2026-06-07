# Phase 3 Implementation Report

> Records the Phase 3 "PDF Download, Parsing, and Bilingual Reading"
> delivery on `paper-lab-agent`. Phase 3 turns accepted open-access
> paper metadata into local paper content: PDF files, parsed text,
> paragraph segments, and a reader that distinguishes fixture and
> real parsed rows.

## 1. Goal Recap

Take the accepted open-PDF metadata that Phase 2 produced and turn
it into local paper content under `data/`, while keeping:

- The fake `ModelAdapter` and the no-network test harness.
- The fixture-based reader path (Phase 1) intact.
- The harness rules in `docs/harness.md` (no LLM, no network in
  default tests).

## 2. Feature Breakdown

| # | Feature | Commit | Files |
|---|---------|--------|-------|
| 3.1 | PDF download policy + downloader with status state machine | `76440fb` | `src/lib/download/{policy,pdf-downloader}.ts`, `tests/download-policy.test.ts` |
| 3.2 | PDF text extraction + paragraph segmentation with stable ids | `0df514c` | `src/lib/pdf/{parse-pdf,segment-text}.ts`, `fixtures/pdf/sample-paper.txt`, `tests/pdf-segmentation.test.ts` |
| 3.3 | Translation pipeline + parsed-segment upsert + pdf path lookup | `99400b0` | `src/lib/translation/translate-segments.ts`, `src/lib/library/segments.ts` (extended), `src/lib/library/papers.ts` (extended), `tests/translation-segments.test.ts` |
| 3.4 | Reader surfaces download state and untranslated rows | `4923f44` | `src/app/library/[paperId]/page.tsx` (extended) |
| 3.5 | Open-PDF download orchestrator + Sources UI control | `9831845` | `src/lib/download/run-download.ts`, `src/app/sources/{page,actions}.ts` (extended), `tests/download-policy.test.ts` (extended) |

Each commit was pushed to `phase/3-pdf-download-parsing-bilingual-reading`
and merged into `main` via a single `--no-ff` merge commit.

## 3. Architecture Notes

### Policy

- `src/lib/download/policy.ts` is a pure function. It never touches
  the network, the filesystem, or the DB. It returns a structured
  `DownloadPolicyDecision` (`missing-pdf-url`, `pdf-url-not-http`,
  `authenticated-url-rejected`, `pdf-url-malformed`,
  `no-allowlist-configured`, `host-not-allowlisted:<host>`, or `ok`).
- `derivePdfLocalPath` sanitizes the paperId so a hostile value
  cannot escape the configured `pdfDir`.

### Downloader

- `src/lib/download/pdf-downloader.ts` is the side-effecting layer.
  It accepts a `fetchImpl` override so the default tests never hit
  the network. Successful downloads are written atomically via
  `tmp + rename`, content-type is validated, and the outcome is
  mapped onto the `Paper` shape via `applyOutcomeToPaper`.

### PDF Parse + Segment

- `parsePdfFromText` is the text-only default path: it accepts a
  string or a Buffer (decoded as UTF-8) and is what the default
  test suite uses.
- `extractPdfFromBuffer` is the optional real-PDF path. It uses a
  dynamic `import("pdf-parse")` and is intentionally a `@ts-expect-error`
  site so the package can be missing without breaking the build. A
  typed `PdfParseError` is thrown when the dependency is missing
  or the PDF is unreadable, allowing the caller to fall back.
- `segmentText` splits on blank lines, collapses soft breaks into
  single spaces, and produces `paperId-scoped` segmentIds of the
  form `<paperId>-seg-NNNN` with a 0-indexed `order`. A
  `maxCharsPerSegment` chunker (default 4000 chars) keeps
  retrieval focused.

### Translation

- `translateSegments` is a pure wrapper. Default behavior is the
  fake passthrough; `leaveAsIs: true` skips translation entirely;
  a translator that throws falls back to the existing `chinese`
  field rather than corrupting the pipeline.
- `fakeTranslationPlaceholder(english) => ""` is the honest
  placeholder. We do not invent Chinese text in Phase 3; the
  reader surfaces the row as "(中文待翻译)" so users are not
  misled.

### Library

- `upsertParsedSegments` writes the new (parsed) segments without
  overwriting the existing fixture translation: when a `(paperId,
  segmentId)` row already has a non-empty `chinese` field, the
  fixture's translation is preserved verbatim.
- `getDownloadedPdfPath` returns the local path only when
  `downloadStatus === "succeeded"`, so the reader does not show
  phantom links for failed downloads.

### Reader UI

- The reader now shows a "Download state" card with three branches:
  `downloaded` (local path), `download failed` (warn-box with
  reason), and `not downloaded` (muted hint).
- The right column of the bilingual grid renders `(中文待翻译)`
  for any parsed segment whose `chinese` field is empty. Fixture
  segments keep their ground-truth translations.

### Sources UI

- A new "Download open PDFs" section exposes
  `runDownloadAllAction`. The button is rendered `disabled` until
  `PAPER_LAB_DOWNLOAD_LIVE_OPT_IN=true` is set in the env, so a
  direct POST cannot bypass the gate.
- `runDownloadForAcceptedPapers` is the only call site that ties
  the downloader, the parser, the segmenter, and the segment
  upsert together. Rejected papers are filtered out at the
  intake level (`listAcceptedPapers`).

## 4. Verification

All gates run after the merge into `main`:

```text
pnpm typecheck    # tsc --noEmit        → clean
pnpm test         # vitest run          → 11 files, 90 / 90 pass
pnpm build        # next build          → 6 routes, no warnings
```

Phase 1's 16 baseline tests, Phase 2's 45 tests, and Phase 3's
29 new tests all pass. The `download-policy.test.ts` suite alone
covers 24 cases (policy branches, fetch stubs, write-back,
rejected-paper skip, segment insertion, fetch-call counting).

`pnpm test` was confirmed to be **no-network**: the runner takes
a `fetchImpl` and the default tests always pass a stub.

Two `curl` smoke tests against `pnpm start` returned HTTP 200 for
the changed pages and rendered the expected UI labels:

- `/library/paper-2606-00001`: "Download state", "not downloaded",
  "parsed PDF", "中文待翻译", "back to Library".
- `/sources`: "Run fixture intake", "Live arXiv disabled", "Recent
  intake runs", "Download open PDFs", "Download disabled",
  "PAPER_LAB_DOWNLOAD_LIVE_OPT_IN".

## 5. Scope / Excludes Check

- ✅ Open PDF download for directly accessible URLs.
- ✅ Download status transitions:
  `not_attempted` → `succeeded` / `download_failed`.
- ✅ Local PDF storage under `data/pdfs/`.
- ✅ PDF text extraction for downloaded PDFs (text path always;
  pdf-parse dynamic import is opt-in).
- ✅ Paragraph segmentation with stable segment ids.
- ✅ Translation pipeline interface with fake adapter output by
  default.
- ✅ Reader support for real parsed segments alongside fixture
  segments.
- ✅ Failure records for missing PDF URL, inaccessible PDF,
  unexpected content type, empty body, and parse failure.

Excludes (not done, deferred):

- ❌ Paywall bypass.
- ❌ CAPTCHA bypass.
- ❌ Login / authenticated download.
- ❌ Real translation provider as the default.
- ❌ Perfect PDF layout reconstruction.
- ❌ OCR for scanned PDFs.

## 6. Local-Data / Safety Boundaries

- All downloaded PDFs are written under `PAPER_LAB_PDF_DIR`
  (default `data/pdfs/`), covered by `.gitignore`.
- The default `pnpm test` is no-network: every fetch site takes a
  stub. The real `pdf-parse` import is a `@ts-expect-error`
  dynamic import, so the package can be missing without breaking
  the build.
- `disableAuthenticatedDownloads` defaults to `true`, and the
  policy layer rejects any URL containing a `user:pass@` prefix.
- The Sources page renders the download button as `disabled` until
  `PAPER_LAB_DOWNLOAD_LIVE_OPT_IN=true` is set, and the underlying
  Server Action checks the same flag. The action also redirects
  back to `/sources?download=done` so a direct POST cannot bypass
  the gate.

## 7. Known Limitations / Follow-ups

- The real-PDF parser (`pdf-parse`) is loaded only when the
  dependency is installed. The test suite does not exercise this
  path; a follow-up integration test can be added under
  `tests/integration/`. The text-only path always works.
- The reader does not yet let the user click a row to see its
  `page` number for parsed rows (we set `page: null` in the
  segmenter; the PDF page boundary detection is a Phase 6 polish).
- The `downloadStatus` badge in the Library list does not yet
  surface the failure reason inline; users need to open the
  reader to see it. A small card-level hover tooltip is a
  reasonable Phase 6 enhancement.

## 8. Operating the App

```bash
cd /Users/zenith/Desktop/paper-lab-agent
pnpm install
pnpm seed
pnpm dev                # http://localhost:3000
# Open /library/paper-2606-00001 to see the bilingual reader.
# Open /sources, optionally set PAPER_LAB_DOWNLOAD_LIVE_OPT_IN=true
# in .env, restart, and click "Download PDFs for accepted papers".
```

To verify the Phase 3 loop deterministically:

```bash
pnpm typecheck
pnpm test
pnpm build
```

## 9. Git State

- Phase branch: `phase/3-pdf-download-parsing-bilingual-reading`
- Pushed feature commits: `76440fb`, `0df514c`, `99400b0`,
  `4923f44`, `9831845`
- Merge commit: produced by the `git merge --no-ff` step above
- All gates passed before and after the merge.

# AGENTS.md

## Project Rule

Use Chinese for user-facing explanations unless the user asks otherwise.

Classify each task before starting:

- **小修复**：single-file, small copy/config/type/style adjustments.
- **功能/重构**：new features, cross-file changes, architecture changes, or harness work.

For non-trivial work, inspect the real project state before changing files. Prefer narrow implementation over broad refactors.

## Product Boundaries

- Keep `paper-lab-agent` local-first for V1.
- Use the existing product plan in `docs/research-assistant-v1-plan.md` and the formal spec in `docs/product-spec.md` as source of truth.
- Do not add account systems, cloud sync, team features, default categorization, automatic refresh, or unrelated recommendation features unless explicitly requested.
- Treat Experiment Lab as toy simulation and explanation support. Do not claim full reproduction of paper benchmarks unless explicitly implemented and verified.

## Download And Access Policy

- Automatically download only directly accessible PDFs or allowlisted sources with user-authorized access.
- Do not bypass paywalls, CAPTCHA, access controls, robots restrictions, or site terms.
- Do not store user passwords.
- If a source requires login and the authorized session is unavailable, record the failure reason and preserve the metadata link.
- Keep download behavior consistent with `docs/source-and-download-policy.md`.

## RAG And Answering Rules

- RAG answers must cite paper title or paper id plus segment id.
- If retrieved evidence is insufficient, say evidence is insufficient instead of guessing.
- Core RAG tests must run against fixture data before using real papers.
- Do not let generated answers depend on unstated model behavior in tests.

## Harness Rules

- Keep default tests deterministic and no-network.
- Use fake model adapters for relevance, translation, Q&A, and simulation spec behavior until a real local model adapter is explicitly added.
- Fixture-backed tests should cover intake, bilingual alignment, RAG citations, and simulation spec shape.
- Real network and real model checks must be separate integration tests.

## Verification

- After documentation-only changes, list created files and verify key documents use `paper-lab-agent` consistently.
- After code is added, run the project typecheck/build command before reporting completion.
- For UI changes, run browser verification against the local app.

## Git Safety

- Before committing, run:

```bash
git branch --show-current
git rev-parse --show-toplevel
```

- Do not run destructive git commands without explicit approval in the current user message.
- Do not initialize git, commit, or push unless explicitly requested.

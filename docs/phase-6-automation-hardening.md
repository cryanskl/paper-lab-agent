# Phase 6: Automation and Hardening

## Goal

Make the local research assistant reliable for repeated daily use: scheduled intake, task logs, retries, backup-friendly storage, UI polish, and operational safety.

## Scope

Phase 6 includes:

- Stable command or route for scheduled intake.
- macOS `launchd` or cron documentation for local daily runs.
- Task status page for recent intake, download, parsing, indexing, and simulation jobs.
- Retry and failure visibility for recoverable tasks.
- Data backup/export guidance.
- Database migration discipline.
- Browser smoke tests for core pages.
- Performance checks for larger local libraries.

Phase 6 excludes:

- Hosted SaaS deployment.
- Team accounts.
- Multi-user permissions.
- Background automation that bypasses download policy.
- Automatic authenticated download by default.

## Implementation Boundaries

- Scheduling must call the same intake runner used by manual actions.
- Automation must preserve no-network default tests.
- Download and parsing failures must be visible and recoverable.
- No destructive cleanup of user data without explicit confirmation.
- Backups should be file-system friendly: SQLite plus `data/` directory.

## Suggested Files

- `src/lib/tasks/`: task runner and task status helpers.
- `src/app/tasks/page.tsx`: task log and failure visibility.
- `scripts/run-scheduled-intake.ts`: stable scheduled entry point.
- `docs/operations.md`: scheduling, backup, restore, and troubleshooting.
- `tests/tasks.test.ts`: task state transitions and retry behavior.
- `tests/smoke-pages.test.ts`: browser or HTTP smoke coverage for `/`, `/library`, `/ask`, `/simulation`.

## Harness Requirements

- Default tests must not require a real scheduler.
- Task tests should use fixture mode and temp data directories.
- Browser smoke tests may run against a local dev or production server, but must not depend on live paper sources.
- Migration tests should verify existing Phase 1-5 fixture data remains readable.

## Acceptance Criteria

- User can manually run the same command that a scheduler would call.
- Documentation explains local scheduling and how to disable it.
- Task logs show success/failure counts and actionable error messages.
- Core pages have smoke coverage.
- Backup and restore instructions are documented.
- Existing Phase 1-5 behavior remains intact.

## Required Verification

```bash
pnpm typecheck
pnpm test
pnpm build
```

If scheduler documentation or scripts are added, run the scheduled command manually once in fixture mode and confirm it writes an intake run.

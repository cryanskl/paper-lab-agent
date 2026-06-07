# Source And Download Policy

## Purpose

This policy defines what `paper-lab-agent` may fetch automatically and how it should behave when access is restricted.

The goal is useful paper intake without bypassing access controls, site restrictions, or user trust boundaries.

## Supported Sources

V1 should prioritize stable sources:

- arXiv APIs or feeds.
- RSS feeds from journals, conferences, labs, or search services.
- Public APIs from publishers or indexes.
- Journal search endpoints where automated access is allowed.

Custom webpage scraping should be added only when a source is important, stable enough, and consistent with the site's terms.

## Automatic Download Rules

The system may automatically download a PDF when:

- The PDF is directly accessible without login or access controls.
- The source clearly provides an open PDF link.
- The source domain is explicitly allowlisted by the user for authenticated download attempts.

The system must record download status and failure reason for every accepted paper.

## Authenticated Download Rules

Authenticated download is a controlled adapter, not the default path.

- Only attempt authenticated downloads for allowlisted domains.
- Do not store user passwords.
- Do not bypass CAPTCHA, MFA, paywalls, access controls, robots restrictions, or site terms.
- If the authenticated session is missing, expired, or blocked, mark the paper as `download_failed` and preserve the source link.
- If the site requires manual action, record that manual download/import is needed.

## Restricted Access Handling

When a paper is behind a paywall, login wall, CAPTCHA, or disallowed automated access:

- Save metadata and source URL.
- Do not attempt circumvention.
- Record a clear failure reason.
- Keep the paper visible for manual follow-up if it is relevant.

## User Data Boundary

Local PDFs, parsed text, translations, indexes, and simulation outputs should stay under the configured local data directory. Do not upload paper contents or credentials to external services unless the user explicitly enables a provider that requires it.

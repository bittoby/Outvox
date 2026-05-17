# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project uses Semantic
Versioning.

## [0.1.0] - 2026-05-17

### Added

- Initial open-source release posture for Outvox.
- FastAPI backend for outbound voice, SMS campaigns, lead management, call
  results, settings, phone numbers, and analytics.
- React/Vite frontend dashboard.
- Apache-2.0 license, security policy, disclaimer, contribution guide, code of
  conduct, issue templates, PR template, and CI.
- Backend smoke tests for DNC detection, phone validation, and SMS template
  rendering.
- SQL Server-first runtime configuration, plus an asyncpg/Postgres schema
  initialization path for migration work.
- Credential-free demo compose with Postgres, mock OpenAI, mock Twilio, mock
  API, and demo UI.
- Twilio HTTP webhook signature validation.
- Signed Media Stream WebSocket tokens to prevent direct URL spoofing.
- Atomic SQL Server reservation for SMS Twilio number selection.

### Changed

- SQL Server is documented as the supported `v0.1.x` runtime backend.
- Frontend dependency lockfile refreshed with `npm audit fix`.
- Voice-agent call state is hydrated from signed WebSocket query parameters
  instead of module globals.
- SMS campaign sends reserve a phone number before calling Twilio so concurrent
  workers do not select the same number from stale capacity data.

### Known Gaps

- The repository query layer still contains SQL Server-specific SQL and pyodbc
  call sites. Postgres schema initialization exists, but full runtime
  repository compatibility is not complete.
- Several production hardening items remain open; see `SECURITY.md`.

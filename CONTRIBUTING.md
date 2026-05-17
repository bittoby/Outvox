# Contributing to Outvox

Thanks for your interest in Outvox. This document covers the practical bits
of working on the codebase. The short version:

- **Open an issue first** for anything non-trivial — bug, feature, refactor.
  Drive-by 1,000-line PRs are hard to land cold.
- **Run `pytest`** before submitting. CI runs the same.
- **Follow the existing layout**: routers → services → repositories → DB.
- **Never reintroduce hard-coded tenant data.** All customer-facing strings
  must flow through `config.brand` env vars.
- **Don't bypass `core/auth.py`.** If a new route should be public, add it to
  `AUTH_EXEMPT_PREFIXES`, don't disable the middleware.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
**Security issues** go through the private channel in
[`SECURITY.md`](SECURITY.md), not public GitHub issues.

---

## Ways to help

You don't have to write code. Useful contributions include:

- Reporting bugs with clear reproduction steps.
- Filling in documentation gaps (especially "how do I deploy this against
  X?").
- Sharing real-world configurations (carrier setups, prompt variations,
  store-routing strategies) as examples.
- Reviewing open pull requests.
- Improving test coverage — see [Testing](#testing) below.
- Raising compliance/security concerns through the
  [`SECURITY.md`](SECURITY.md) channel.

---

## Development setup

```bash
git clone https://github.com/bittoby/Outvox.git
cd Outvox

# Backend
cd BE
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r ../tests/requirements.txt
cp env.example .env                  # edit credentials

# Frontend
cd ../FE
cp env.example .env
npm install
```

Then in three terminals:

```bash
# 1. Database service
cd BE && source .venv/bin/activate && python db_service.py

# 2. A single voice agent
cd BE && source .venv/bin/activate && AGENT_ID=OUT1 PORT=5001 python outbound_main.py

# 3. Dashboard
cd FE && npm run dev
```

For development against Twilio webhooks, point your `NGROK_HOST` at a tunnel
that forwards to the local voice agent's port.

---

## Code style

### Python (backend)

- **Python 3.11+.** Use modern syntax (`X | None`, `list[str]`) where it
  reads cleanly.
- **Layering:**
  - **Routers** (`BE/routers/`) handle HTTP only — parse input, call a
    service, return a response. No SQL, no business logic.
  - **Services** (`BE/services/`) implement business rules. They depend on
    repositories, not other services where possible.
  - **Repositories** (`BE/repositories/`) contain SQL and return plain
    dicts/lists. No business logic. The legacy runtime path still uses
    SQL Server/pyodbc in places. SQL Server is the supported runtime for
    `v0.1.x`; new portable database work should move toward the
    Postgres/asyncpg path without breaking the SQL Server path.
  - **Models** (`BE/models/`) are Pydantic schemas — split request and
    response shapes where they diverge.
  - **Utils** (`BE/utils/`) are pure helpers; no DB, no Twilio, no OpenAI.
- **No raw SQL in services or routers.** If you need a new query, add it to
  the relevant repository.
- **Parameterise SQL.** Never string-format user input into a query.
- **Validate at the boundary, trust internally.** Pydantic models handle
  validation at the router edge. Inside services, assume your inputs are
  well-formed.
- **Logging:** the standard library `logging` module is configured at
  process start. Use `logger = logging.getLogger(__name__)` at the top of
  each module. Don't `print()` in library code (workers and CLI scripts may
  print).

### TypeScript (frontend)

- **TypeScript strict mode is on.** Don't widen types to `any` to make a
  warning go away.
- **No new axios instances.** All HTTP goes through the default axios that
  `authBootstrap.ts` has decorated with `X-API-Key`.
- **Keep `pages/` thin.** Move shared widgets into `components/`. Move
  per-feature API calls into `services/api/`.
- **Match backend types.** When you change a Pydantic model, update the
  corresponding TS type in `FE/src/types/`.

### Brand / tenant strings

Anything a customer might read or hear — company name, agent persona, SMS
copy, prompt text — must come from `config.brand`. Hard-coded brand strings
are blocked at code review.

- Prompts (`BE/prompts/*`) use `{company_name}`, `{agent_name}`,
  `{company_short_name}`, `{company_tagline}`, `{company_offering}`. The
  prompt loader substitutes them at load time.
- Services that emit SMS or speech read from `config.brand.COMPANY_NAME`.
- SMS templates seeded by `scripts/setup_templates.py` interpolate the
  company name at seed time so the stored template is brand-resolved.

---

## Testing

Test deps are in `tests/requirements.txt`, separate from production
requirements:

```bash
pip install -r tests/requirements.txt
pytest                    # all tests
pytest tests/test_x.py    # one file
pytest -k phone_validator # by keyword
pytest -x                 # stop on first failure
```

The current suite is intentionally small — smoke coverage on detectors,
validators, the prompt loader, and the template renderer. Contributions that
extend it are high-leverage. Suggested next coverage areas, roughly in
order of value:

1. `services/lead_service.py` — duplicate-detection, bulk import, consent
   state machine.
2. `services/sms_campaign_manager.py` — batch creation, rate-limit math,
   pause/resume semantics.
3. `utils/dnc_detector.py` — adversarial transcripts; current heuristics
   under-detect single explicit opt-outs.
4. `repositories/*.py` — integration tests against local SQL Server for the
   supported runtime, plus Postgres coverage for migration work where behavior
   differs.
5. The `outbound_main.py` WebSocket handler — needs decomposition first.

We do **not** ship FE unit tests yet. CI runs `tsc` and `vite build`, which
catches type and build errors.

---

## Commit and PR conventions

- **One logical change per PR.** Refactors and feature work go in separate
  PRs.
- **Imperative subject line, ≤72 chars.** "Fix N+1 in bulk_create_leads"
  beats "Fixed the N+1 problem with bulk lead creation".
- **Body explains the why**, not the what. The diff shows the what.
- **Link the issue**: `Closes #123` or `Refs #123`.
- **Sign-off optional, DCO not currently enforced.** May change pre-1.0.

For the PR description, fill in the template in
`.github/pull_request_template.md`:

- What does this change and why?
- How did you test it?
- Any breaking-change notes, migration steps, or security impact?

---

## What gets rejected

These are common patterns we will ask you to change before merging:

- Hard-coded company/agent/store names instead of `config.brand` values.
- New routes that bypass `core/auth.py`'s API-key check without a documented
  reason (and an exemption added to `AUTH_EXEMPT_PREFIXES`).
- SQL constructed by string concatenation. Use parameterised queries.
- Bare `except:` and `except Exception:` blocks that swallow errors without
  logging.
- `print()` for diagnostics in library code. Use the logger.
- Synchronous blocking work in an `async def` route. Wrap with
  `asyncio.to_thread()` if needed.
- Test files committed to the working tree without corresponding test code
  (e.g., test fixtures that are actually production data).
- Real customer data in test fixtures, sample CSVs, or prompts. All sample
  data must be obviously fake (`+15555550101`, `100 Main St, Anytown`).

---

## Where to ask

- **Questions / discussion:** GitHub Discussions on the repo (when enabled).
- **Bugs / feature requests:** GitHub Issues — please use the templates in
  `.github/ISSUE_TEMPLATE/`.
- **Security:** see [`SECURITY.md`](SECURITY.md).

Thanks for helping make Outvox better.

# Outvox

**Outbound voice + SMS campaign fleet, powered by OpenAI Realtime and Twilio.**
Licensed under **Apache-2.0**.

> ⚠️ **Read [`DISCLAIMER.md`](DISCLAIMER.md) and [`SECURITY.md`](SECURITY.md) before
> placing real calls.** This software automates outbound voice calls and SMS;
> TCPA, FCC, state-level mini-TCPAs, CTIA, and carrier rules all apply. The
> maintainers make **no claim of compliance**. You are the operator and you
> carry the legal risk.

Outvox is **early-stage software**. It works end-to-end, but there are known
security, operational, and compliance hardening items documented in
`SECURITY.md`. Do not deploy to the public internet without working through
that file's hardening checklist.

---

## Contents

1. [What it does](#what-it-does)
2. [Architecture](#architecture)
3. [Project layout](#project-layout)
4. [Quick start](#quick-start)
5. [Configuration](#configuration)
6. [Running in Docker](#running-in-docker)
7. [Credential-free demo](#credential-free-demo)
8. [Command-line tooling](#command-line-tooling)
9. [Testing](#testing)
10. [Contributing](#contributing)
11. [License](#license)

---

## What it does

Outvox places automated outbound calls and SMS messages on behalf of an
operator — for example, a business reaching out to leads who have previously
opted in. It bridges Twilio's Programmable Voice / Messaging with OpenAI's
Realtime API so that each call is a live, two-way conversation rather than
prerecorded audio.

Headline capabilities:

- **AI voice calls** via OpenAI Realtime, streamed through Twilio Media
  Streams.
- **SMS campaigns** with template management, batch scheduling, rate limiting,
  and YES/STOP reply tracking.
- **Lead management**: CSV import/export, store routing, DNC flagging, SMS
  consent state machine.
- **Fleet model**: ten voice-agent containers behind an Nginx load balancer for
  concurrent outbound calling.
- **Operator dashboard**: React + TypeScript SPA for monitoring agents,
  campaigns, conversations, and call results.

Everything customer-facing — company name, agent persona, products mentioned,
locations — is driven by environment variables. The repository ships
deliberately generic defaults; see [Configuration](#configuration).

---

## Architecture

```mermaid
flowchart TD
    FE[React frontend<br/>Vite :3000] -->|HTTPS + X-API-Key| DB[FastAPI database service<br/>:8000]
    DB -->|pyodbc| MSSQL[(SQL Server runtime)]
    DB -. experimental schema path .-> PG[(Postgres)]
    DB --> Workers[Background workers]
    DB --> WS[WebSocket fan-out]
    Twilio[Twilio webhooks] --> Nginx[Nginx load balancer<br/>:5100]
    Nginx --> A1[Voice agent 1]
    Nginx --> A2[Voice agent 2]
    Nginx --> A3[Voice agent ...]
    Nginx --> A10[Voice agent 10]
    A1 -->|HTTP| DB
    A2 -->|HTTP| DB
    A3 -->|HTTP| DB
    A10 -->|HTTP| DB
    A1 <-->|Realtime media| OpenAI[OpenAI Realtime]
    A2 <-->|Realtime media| OpenAI
    A3 <-->|Realtime media| OpenAI
    A10 <-->|Realtime media| OpenAI
```

The voice-agent containers do **not** talk to the database directly. They call
the central `db_service` over HTTP, so the database driver is only loaded in
one place.

SQL Server is the supported runtime backend for `v0.1.x`. A Postgres schema
bootstrap path exists for migration work, but the repository query layer still
contains SQL Server-specific SQL in places. Treat full Postgres runtime
compatibility as active migration work, not complete.

---

## Project layout

```
Outvox/
├── BE/                                Backend (FastAPI, Python 3.11+)
│   ├── core/                          Cross-cutting infrastructure
│   │   ├── auth.py                    API-key middleware
│   │   ├── error_handler.py           Global exception handlers
│   │   ├── exceptions.py              Custom HTTP exception types
│   │   ├── logging_config.py          Logging setup
│   │   ├── responses.py               JSON response helpers
│   │   └── schema.py                  Postgres + SQL Server table creation
│   ├── models/                        Pydantic request/response models
│   ├── repositories/                  Data-access layer
│   ├── services/                      Business logic
│   ├── routers/                       FastAPI routers (HTTP + WebSocket)
│   ├── utils/                         Detectors, parsers, prompt loader,
│   │                                  location mapper, phone validator
│   ├── workers/                       Background jobs (batch executor,
│   │                                  daily reporter, phone-stats reset,
│   │                                  safe-call popup creator)
│   ├── prompts/                       AI prompt fixtures (use {company_name}
│   │                                  and {agent_name} placeholders)
│   ├── scripts/                       Operator scripts (setup, cleanup, CLI)
│   │   ├── call_manager.py
│   │   ├── setup_outbound.py
│   │   ├── setup_stores.py
│   │   ├── setup_templates.py
│   │   ├── delete_all_tables.py
│   │   └── logs.bat
│   ├── config.py                      Centralised configuration
│   ├── db_service.py                  Database service entry point (:8000)
│   ├── outbound_main.py               Voice-agent entry point (:5001)
│   ├── requirements.txt               Python dependencies (pinned)
│   ├── env.example                    Example env file — copy to .env
│   ├── docker-compose.yml             10 agents + Nginx
│   ├── Dockerfile
│   └── nginx.conf
│
├── FE/                                Frontend (React 18 + TypeScript + Vite)
│   ├── src/
│   │   ├── pages/                     Dashboard, Leads, Campaigns, SMS, etc.
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── routes/
│   │   ├── services/
│   │   │   ├── api/                   Axios-based REST clients
│   │   │   ├── websocket/             WS client
│   │   │   └── authBootstrap.ts       Installs X-API-Key on axios
│   │   └── types/                     Shared TS types
│   ├── env.example
│   ├── package.json
│   └── vite.config.ts
│
├── tests/                             Pytest test suite (BE)
├── LICENSE                            Apache-2.0
├── NOTICE
├── DISCLAIMER.md                      Legal / TCPA / operator responsibilities
├── SECURITY.md                        Disclosure channel + hardening checklist
├── CONTRIBUTING.md                    How to contribute
├── CODE_OF_CONDUCT.md                 Contributor Covenant
└── README.md                          You are here
```

---

## Quick start

### Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- Microsoft SQL Server 2019 or newer
- Microsoft ODBC Driver 18 for SQL Server and `unixodbc-dev` on Linux
- Postgres 16 or newer only if you are working on the experimental migration
- Docker (only if you want to run the multi-agent fleet)
- A Twilio account with a Voice/SMS-capable phone number
- An OpenAI API key with Realtime API access
- For inbound Twilio webhooks: a public tunnel such as ngrok

### 1. Clone and install

```bash
git clone https://github.com/bittoby/Outvox.git
cd Outvox

# Backend
cd BE
cp env.example .env                  # edit with your credentials, see below
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../FE
cp env.example .env                  # edit if backend isn't on localhost
npm install
```

### 2. Bring up SQL Server

Outvox creates its own tables on first start; you just need a reachable
SQL Server database that the configured user can write to. For local
development with Docker:

```bash
docker run --name outvox-sqlserver \
  -e ACCEPT_EULA=Y \
  -e MSSQL_SA_PASSWORD='YourStrong!Passw0rd' \
  -p 1433:1433 \
  -d mcr.microsoft.com/mssql/server:2022-latest

docker exec outvox-sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P 'YourStrong!Passw0rd' -C \
  -Q "CREATE DATABASE outvox"
```

Create an `outvox` database, then set these values in `BE/.env`:

```env
DATABASE_BACKEND=sqlserver
SQLServer=localhost,1433
SQLDatabase=outvox
SQLUser=sa
SQLPassword=YourStrong!Passw0rd
```

> The Postgres schema path is asyncpg-based and experimental. Several
> repository queries still use SQL Server syntax. Use
> `DATABASE_BACKEND=sqlserver` for the complete runtime path today.

### 3. Start the services

In three terminals, with `BE/.venv` activated in the first two:

```bash
# Terminal 1 — database service (port 8000)
cd BE
python db_service.py

# Terminal 2 — a single voice agent (port 5001)
cd BE
AGENT_ID=OUT1 PORT=5001 python outbound_main.py

# Terminal 3 — frontend (port 3000)
cd FE
npm run dev
```

For the production fleet (10 agents + Nginx), see
[Running in Docker](#running-in-docker).

### 4. Seed sample data (optional)

```bash
cd BE
python scripts/setup_stores.py        # creates three sample stores
python scripts/setup_templates.py     # creates 15 carrier-safe SMS templates
python scripts/setup_outbound.py      # edit the script to register your
                                       # Twilio numbers before running
```

### 5. Open the dashboard

- Dashboard: <http://localhost:3000>
- Database API + Swagger: <http://localhost:8000/docs>
- Voice load balancer (when Docker fleet is up): <http://localhost:5100>

If your backend has `API_KEY` set, the dashboard will be rejected with 401s
until you either set `VITE_API_KEY` in `FE/.env` and rebuild, or run
`setApiKey("…")` from the browser console (the key is persisted in
`localStorage` under `outvox.api_key`).

---

## Configuration

All backend configuration lives in `BE/config.py` and is loaded from
environment variables (`.env`). The full inventory is in `BE/env.example` —
the highlights:

```env
# ── Authentication ──────────────────────────────────────────────
# Random shared secret used to gate mutating routes. Generate with:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
# If unset, services log a warning and accept all requests. DO NOT
# leave unset on any internet-reachable deployment.
API_KEY=

# ── Brand / tenant strings (every customer-facing word) ─────────
COMPANY_NAME=Acme Pawn
COMPANY_SHORT_NAME=Acme
AGENT_NAME=Alex
COMPANY_TAGLINE=Trusted local pawn loans and appraisals.
COMPANY_OFFERING=pawn loans and quick cash for gold, jewelry, watches, and electronics

# ── OpenAI Realtime ─────────────────────────────────────────────
OPENAI_API_KEY=sk-...
REALTIME_MODEL=gpt-realtime-2025-08-28
VOICE_SELECTION=sage

# ── Twilio ──────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=
NGROK_HOST=your-subdomain.ngrok.app
PUBLIC_WEBHOOK_BASE_URL=https://your-subdomain.ngrok.app
TWILIO_VALIDATE_SIGNATURE=true
MEDIA_STREAM_VALIDATE_TOKEN=true

# ── Database ────────────────────────────────────────────────────
DATABASE_BACKEND=sqlserver
SQLServer=localhost,1433
SQLDatabase=outvox
SQLUser=sa
SQLPassword=YourStrongPassword

# Experimental Postgres migration path:
# DATABASE_BACKEND=postgres
# DATABASE_URL=postgresql://outvox:outvox@localhost:5432/outvox

# ── Agent identity ──────────────────────────────────────────────
AGENT_ID=OUT1
PORT=5001
```

The frontend reads the same API key from `FE/.env` as `VITE_API_KEY`. See
[`SECURITY.md`](SECURITY.md) for the full hardening checklist and
[`DISCLAIMER.md`](DISCLAIMER.md) for compliance gaps you must close.

---

## Running in Docker

```bash
cd BE
docker compose up -d --build
```

This brings up ten voice-agent containers (`outvox-agent1` through
`outvox-agent10`) on ports `5101`–`5110`, behind an Nginx load balancer on
`:5100`. The compose file does **not** start `db_service` — run it on the
host (or add a service of your own). The agents reach the host via
`host.docker.internal:8000`.

Logs:

```bash
docker compose logs -f                 # everything
docker compose logs -f outvox-agent1   # one agent
docker logs outvox-nginx -f            # load balancer
```

Stop:

```bash
docker compose down
```

---

## Credential-free demo

You can boot a local demo stack without real Twilio or OpenAI credentials:

```bash
docker compose -f docker-compose.demo.yml up --build
```

It starts:

- Postgres on `localhost:5432`
- Mock API on <http://localhost:8000>
- Fake OpenAI endpoint on <http://localhost:8081>
- Fake Twilio endpoint on <http://localhost:8082>
- Demo UI on <http://localhost:3000>

This stack proves first-run wiring and documentation, but it does not place
real calls or exercise every production route.

---

## Command-line tooling

The `BE/scripts/call_manager.py` script is a small operator CLI that hits the
running services.

```bash
cd BE
python scripts/call_manager.py stats           # daily call statistics
python scripts/call_manager.py health          # health of all agents + LB
python scripts/call_manager.py single-call     # place one call
python scripts/call_manager.py campaign 100    # parallel campaign of 100
python scripts/call_manager.py add-lead +15551234567 "Jane Doe"
python scripts/call_manager.py mark-dnc +15551234567
python scripts/call_manager.py send-consent <lead_id> [--force]
python scripts/call_manager.py consent-batch [limit] [--force]
```

The SMS batch worker can run as a daemon:

```bash
cd BE
python workers/batch_executor.py --daemon    # continuous polling
python workers/batch_executor.py             # one-shot run
```

The worker is normally started automatically by `db_service.py` on boot via
`services/worker_manager.py`; you only need to run it standalone when
debugging.

---

## Testing

Test dependencies are not in `requirements.txt`; install them separately:

```bash
pip install -r BE/requirements.txt
pip install -r tests/requirements.txt
PYTHONPATH=BE pytest
```

The test suite is intentionally small for now — smoke coverage on the
detectors, validators, prompt loader, and template renderer. Contributions
that fill in service-level and integration tests are very welcome.

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). In short: open an issue first for
anything non-trivial, run `pytest` before submitting, follow the existing 3-
layer pattern (routers → services → repositories), and never reintroduce
hard-coded tenant data.

By participating you agree to the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

Security reports go through the channel in [`SECURITY.md`](SECURITY.md), not
public issues.

---

## License

Outvox is released under the Apache License, Version 2.0. See
[`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

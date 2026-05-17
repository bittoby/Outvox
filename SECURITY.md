# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Outvox, **please do not open a
public GitHub issue**. Instead, report it privately so we can investigate before
the details become public.

- **Preferred:** open a private GitHub security advisory at
  `https://github.com/bittoby/Outvox/security/advisories/new`.
- If you run a public fork, configure a maintainer-controlled private security
  address before announcing it.

Please include:

- A clear description of the issue and its impact.
- Step-by-step reproduction details.
- The version, commit SHA, or branch you tested against.
- Any proof-of-concept code, redacted of real PII.

We aim to acknowledge reports within **3 business days** and to triage within
**10 business days**. Coordinated disclosure timelines will be negotiated on a
case-by-case basis.

## Supported versions

Outvox has not yet shipped a stable release. Until version 1.0.0, only the
`main` branch is supported for security fixes.

| Version | Supported       |
| ------- | --------------- |
| main    | :white_check_mark: |
| < 1.0   | :x:             |

---

## Current security posture — READ BEFORE DEPLOYING

Outvox is **early-stage software**. There are known security limitations that
operators must mitigate before any non-development deployment. Treating this list
as exhaustive is a mistake: complete your own threat model before going live.

### 1. Endpoint authentication

Out of the box, the FastAPI services (`BE/db_service.py` on port 8000 and
`BE/outbound_main.py` on ports 5101–5110 behind Nginx on 5100) require an
API key on all non-exempt routes when the `API_KEY` environment variable is
set. However:

- **Webhook routes are exempt from the API key** because Twilio cannot send the
  shared Outvox key. They must remain protected by Twilio request-signature
  validation.
- **WebSocket endpoints** (`/media-stream`) cannot use Twilio's HTTP signature
  header. Generated TwiML includes an HMAC `stream_token`; keep
  `MEDIA_STREAM_VALIDATE_TOKEN=true` outside local demos.
- If `API_KEY` is **not** set, the middleware logs a loud warning at startup and
  allows all requests. **Do not run without `API_KEY` set unless behind another
  trust boundary.**

**Mitigation:** put Outvox behind a reverse proxy or VPN, set `API_KEY`,
keep Twilio request-signature validation enabled, keep media-stream token
validation enabled, and restrict the database service to an internal network.

### 2. CORS

`db_service` and `outbound_main` set `allow_origins=["*"]`. Tighten this to the
exact origin(s) of your frontend before exposing to the internet.

### 3. Concurrency / state correctness

SMS number reservation uses SQL Server update locks so competing workers cannot
claim the same Twilio number before counters move. Keep this path covered by
integration tests before changing the repository SQL, because carrier rate
limits are compliance-sensitive.

### 4. Webhook signature validation

Twilio HTTP webhooks are validated with `X-Twilio-Signature` by default. Keep
`TWILIO_VALIDATE_SIGNATURE=true` outside local mock/demo traffic, and set
`PUBLIC_WEBHOOK_BASE_URL` to the exact public scheme and host Twilio calls
when the app sits behind ngrok, Nginx, or another reverse proxy.

**Mitigation:** keep webhook validation enabled, use TLS, avoid logging full
webhook bodies containing customer data, and put the webhook surface behind a
long, unguessable URL prefix.

### 5. Secrets

- The OpenAI API key is passed in a WebSocket request header at connect time.
  An unhandled exception in that codepath could log the key into a traceback.
- `.env` files must never be committed. The repository's `.gitignore` excludes
  them, but operators should also enable secret-scanning on their fork.
- `env.example` files in this repository are placeholders only. If you fork,
  verify that no real credential has been added to those files.

### 6. SQL injection

Database access is parameterized through pyodbc and is not vulnerable to SQL
injection on known paths. However, dynamic `SET`/`WHERE` clauses are built from
whitelisted column names in repository code; **any change to those whitelists
must be carefully reviewed**.

### 7. Input validation

User-supplied content (lead names, SMS template variables) is substituted into
SMS templates with simple `str.replace`. Untrusted lead names that themselves
contain placeholder tokens (e.g., a lead named `{store_name}`) could cause
unexpected substitutions. Sanitize lead input at ingress.

### 8. Recording disclosure

Two-party-consent recording laws apply in several U.S. states and elsewhere.
The system can be configured to record calls (`ENABLE_CALL_RECORDING`), but the
prompt and the operator are responsible for disclosing recording before it
begins.

### 9. Data retention

The schema retains call transcripts and recording URLs indefinitely. Operators
should implement retention policies appropriate to their legal jurisdiction
and the consents they obtained.

### 10. Compliance gaps

See [DISCLAIMER.md](DISCLAIMER.md) for a list of compliance-relevant
limitations that affect operator risk in addition to the security items above.

---

## Hardening checklist before going live

- [ ] Set a strong, random `API_KEY` (32+ bytes from a CSPRNG).
- [ ] Restrict CORS `allow_origins` to your frontend's exact origin(s).
- [ ] Put both FastAPI services behind a reverse proxy with TLS.
- [ ] Keep `TWILIO_VALIDATE_SIGNATURE=true` and configure
      `PUBLIC_WEBHOOK_BASE_URL`.
- [ ] Keep `MEDIA_STREAM_VALIDATE_TOKEN=true` and configure a strong
      `MEDIA_STREAM_TOKEN_SECRET` if you do not want to reuse the Twilio auth
      token.
- [ ] Restrict the database service to an internal network or VPN.
- [ ] Rotate OpenAI, Twilio, Trestle, and ElevenLabs credentials regularly.
- [ ] Enable secret-scanning on your repository fork.
- [ ] Review and tighten the bundled DNC heuristics for your risk tolerance.
- [ ] Establish data-retention and deletion procedures for call recordings,
      transcripts, and SMS history.
- [ ] Subscribe to security advisories on dependencies (FastAPI, Twilio SDK,
      pyodbc, websockets, React, etc.).

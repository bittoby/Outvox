# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Outvox, **please do not open a
public GitHub issue**. Instead, report it privately so we can investigate before
the details become public.

- **Preferred:** open a private GitHub security advisory at
  `https://github.com/<your-org>/<your-repo>/security/advisories/new`.
- **Alternative:** email the maintainers at `security@example.com`
  (replace with the maintainer-controlled address after forking).

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
`BE/outbound_main.py` on ports 5101–5110 behind Nginx on 5100) require an API
key on **mutating** routes when the `API_KEY` environment variable is set.
However:

- **Read-only routes are not authenticated.** Anyone who can reach the service
  can list leads, campaigns, call results, and other potentially sensitive data.
- **WebSocket endpoints** (`/media-stream`) are not authenticated and rely on
  Twilio's webhook signature, which this software does **not** currently verify.
  See limitation #5 below.
- If `API_KEY` is **not** set, the middleware logs a loud warning at startup and
  allows all requests. **Do not run without `API_KEY` set unless behind another
  trust boundary.**

**Mitigation:** put Outvox behind a reverse proxy or VPN, set `API_KEY`,
front any public webhook surface with Twilio request-signature validation, and
restrict the database service to an internal network.

### 2. CORS

`db_service` and `outbound_main` set `allow_origins=["*"]`. Tighten this to the
exact origin(s) of your frontend before exposing to the internet.

### 3. Concurrency / state correctness

`BE/outbound_main.py` uses module-level globals (`temp_lead_id`,
`temp_twilio_number`) to thread state between a Twilio webhook and a WebSocket
handler. Two concurrent calls can cross-contaminate, causing the wrong customer
data to be loaded for a call. This is a correctness defect with security and
compliance implications.

Similarly, `BE/utils/phone_pool_manager.py` does not lock the number-selection
critical section, so two campaigns may claim the same Twilio number and exceed
carrier rate limits.

### 4. Webhook signature validation

Twilio webhooks are accepted without validating `X-Twilio-Signature`. Anyone who
guesses the public webhook URL can spoof inbound call events, trigger SMS
processing for arbitrary phone numbers, or replay call results.

**Mitigation:** validate `X-Twilio-Signature` on every Twilio-originating
endpoint using the official Twilio SDK helpers, and put the webhook surface
behind a long, unguessable URL prefix.

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
- [ ] Validate `X-Twilio-Signature` on all Twilio-originating routes.
- [ ] Restrict the database service to an internal network or VPN.
- [ ] Rotate OpenAI, Twilio, Trestle, and ElevenLabs credentials regularly.
- [ ] Enable secret-scanning on your repository fork.
- [ ] Review and tighten the bundled DNC heuristics for your risk tolerance.
- [ ] Implement Twilio webhook signature validation and replay protection.
- [ ] Establish data-retention and deletion procedures for call recordings,
      transcripts, and SMS history.
- [ ] Subscribe to security advisories on dependencies (FastAPI, Twilio SDK,
      pyodbc, websockets, React, etc.).

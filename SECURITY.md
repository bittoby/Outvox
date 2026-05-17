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

Out of the box, the FastAPI services require an API key on all non-exempt
routes whenever the `API_KEY` environment variable is set.

| Service | Port (default) |
| --- | --- |
| `BE/db_service.py` | `8000` |
| `BE/outbound_main.py` (single agent) | `5001` |
| `BE/outbound_main.py` (Docker fleet) | `5101–5110`, behind Nginx on `5100` |

Authentication notes:

- **The dashboard sends the API key as `X-API-Key`** (axios default, installed
  by `FE/src/services/authBootstrap.ts`). Server-to-server callers may use
  `Authorization: Bearer <key>` instead.
- **Twilio webhook routes are exempt from the API key** because Twilio cannot
  send our shared secret. Default exempt paths: `/twilio-voice`, `/twilio-sms`
  (voice agent), `/sms/twilio-sms`, `/api/sms/twilio-sms` (db_service). They
  remain protected by Twilio's `X-Twilio-Signature` HMAC, validated in
  `BE/core/twilio_validation.py`.
- **The media-stream WebSocket** (`/media-stream`) cannot use Twilio's HTTP
  signature header. Generated TwiML includes an HMAC `stream_token`. Keep
  `MEDIA_STREAM_VALIDATE_TOKEN=true` outside local demos.
- **If `API_KEY` is unset, the middleware logs a loud warning at startup and
  allows all requests.** Do not run without `API_KEY` set unless the services
  sit behind another trust boundary (VPN, mTLS, etc.).
- **Override the exempt list with `AUTH_EXEMPT_PREFIXES`** if you front the
  service with a different webhook surface.

**Mitigation:** put Outvox behind a reverse proxy or VPN, set `API_KEY`, keep
both Twilio signature validation and media-stream token validation enabled, and
restrict the database service to an internal network.

### 2. CORS

Both services configure CORS through the `CORS_ALLOWED_ORIGINS` environment
variable (comma-separated). If unset (or `*`), they default to
`allow_origins=["*"]` for local development convenience.

**Before exposing to the internet,** set `CORS_ALLOWED_ORIGINS` to the exact
origin(s) of your dashboard, e.g.:

```env
CORS_ALLOWED_ORIGINS=https://dashboard.example.com,https://admin.example.com
```

`allow_credentials=True` is set by the apps, so a `*` origin combined with
credentialed requests would be rejected by browsers anyway — but make this
explicit before going live.

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

> **Known gap.** The voice agent's `/twilio-sms` handler forwards the form body
> to `db_service`'s `/api/sms/twilio-sms` *without* re-attaching the
> `X-Twilio-Signature` header. If you set `TWILIO_VALIDATE_SIGNATURE=true` on
> the `db_service` process, the proxied call will fail signature validation. In
> practice, point Twilio at the voice agent's endpoint (which does validate)
> and consider the `db_service` SMS endpoint an internal-only API. If you also
> want signature validation on `db_service`, either disable it there
> (`TWILIO_VALIDATE_SIGNATURE=false` for the db_service process only), or
> patch the proxy to forward the header — note that the signature is computed
> over the original URL, so re-validation at the inner hop only works if the
> validator uses the original public URL.

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
begins. The default voice prompts do **not** include a recording disclosure.

### 9. Calling-hour windows

`BE/workers/batch_executor.py` enforces a **hardcoded** SMS execution window of
**9 AM – 6 PM in the server's local time zone**. It is not configurable and is
not based on the recipient's time zone.

The U.S. federal TCPA default is 8 AM – 9 PM in the **recipient's** local time
zone, and many states are stricter. Outvox does not implement per-recipient
time-zone resolution. Voice calls have no time-window check at all — they fire
whenever the operator triggers them.

**Mitigation:** treat the built-in window as a coarse safety net only. Operate
within a recipient-time-zone-aware scheduler, or restrict campaign launches to
calling hours operationally.

### 10. Data retention

The schema retains call transcripts and recording URLs indefinitely. Operators
should implement retention policies appropriate to their legal jurisdiction
and the consents they obtained.

### 11. Compliance gaps

See [DISCLAIMER.md](DISCLAIMER.md) for a list of compliance-relevant
limitations that affect operator risk in addition to the security items above.

---

## Hardening checklist before going live

- [ ] Set a strong, random `API_KEY` (32+ bytes from a CSPRNG). Generate one
      with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- [ ] Mirror that value into the dashboard's `VITE_API_KEY` at build time.
- [ ] Set `CORS_ALLOWED_ORIGINS` to the exact origin(s) of your dashboard —
      never leave the default `*` in production.
- [ ] Put both FastAPI services behind a reverse proxy with TLS termination.
- [ ] Keep `TWILIO_VALIDATE_SIGNATURE=true` and set `PUBLIC_WEBHOOK_BASE_URL`
      to the exact public scheme + host Twilio calls.
- [ ] Keep `MEDIA_STREAM_VALIDATE_TOKEN=true` and configure a dedicated
      `MEDIA_STREAM_TOKEN_SECRET` instead of reusing the Twilio auth token.
- [ ] Review the default `AUTH_EXEMPT_PREFIXES`. If you do not actually expose
      `db_service` to Twilio directly, drop `/api/sms/twilio-sms` and
      `/sms/twilio-sms` from the list to shrink the public surface.
- [ ] Restrict the `db_service` port (`8000`) to an internal network or VPN.
      The dashboard is the only legitimate external client.
- [ ] Rotate OpenAI, Twilio, Trestle, and ElevenLabs credentials regularly.
- [ ] Enable secret-scanning on your repository fork.
- [ ] Review and tighten the bundled DNC heuristics for your risk tolerance.
- [ ] Add a recording disclosure to the AI voice prompt before enabling
      `ENABLE_CALL_RECORDING=true` in any two-party-consent jurisdiction.
- [ ] Wrap campaign launches with your own calling-hour scheduler that
      respects the **recipient's** time zone — the built-in 9 AM–6 PM
      server-local window is a coarse safety net, not a compliance control.
- [ ] Establish data-retention and deletion procedures for call recordings,
      transcripts, and SMS history.
- [ ] Subscribe to security advisories on dependencies (FastAPI, Twilio SDK,
      pyodbc, websockets, React, etc.).

# Disclaimer

Outvox is software that places automated outbound voice calls and SMS messages
on behalf of the operator. Operating this software exposes you to a substantial body
of telecommunications, consumer-protection, and privacy law. **By using this software
you accept full responsibility for compliance with all applicable laws and regulations
in every jurisdiction in which calls or messages are placed or received.**

The maintainers and contributors of Outvox provide this software "AS IS",
**make no claim of regulatory compliance**, and accept no responsibility for losses,
penalties, fines, or damages resulting from its use. This includes but is not limited
to:

- **U.S. Telephone Consumer Protection Act (TCPA)**, 47 U.S.C. § 227
- **FCC rules**, including 47 C.F.R. § 64.1200 (Do Not Call, prior express written
  consent for autodialed/prerecorded calls, opt-out handling)
- **State-level mini-TCPAs** (e.g., Florida FTSA, Washington WACPA, Oklahoma TCPA)
- **CAN-SPAM Act** and state SMS marketing laws
- **CTIA Messaging Principles and Best Practices**
- **Carrier rules** (10DLC registration, A2P consent requirements, etc.)
- **Call recording disclosure laws** (two-party-consent states)
- **GDPR / UK GDPR** for any EU/UK contact data
- **CCPA / CPRA** for California consumer data
- **Canadian CRTC rules** including the National DNCL
- All other applicable federal, state, provincial, and local statutes

## Operator responsibilities

Before using Outvox in production, you are responsible for:

1. **Obtaining prior express written consent** from every contact you call or text,
   where required, before any automated outreach occurs.
2. **Honoring opt-out requests** ("STOP", "remove me", "do not call", etc.)
   immediately and recording them durably. Federal rules require cessation within
   reasonable time periods that this software does not on its own guarantee.
3. **Scrubbing the National Do Not Call Registry** and any applicable state
   Do Not Call lists on your own cadence. This software does not perform DNC
   registry scrubs.
4. **Respecting calling-hour restrictions** in the recipient's local time zone
   (federal default: 8:00 a.m. to 9:00 p.m.). State rules may be narrower.
5. **Disclosing call recording** where required by state law before recording begins.
6. **Registering 10DLC or toll-free SMS sender campaigns** with carriers as required.
7. **Disclosing the identity of the caller** as required by FCC rules.
8. **Maintaining records** of consent and opt-outs for the periods required by law.
9. **Implementing your own audit, monitoring, and incident-response procedures.**

## Known limitations

Outvox has several known compliance-relevant limitations that you must
mitigate before production use. The current list includes, but is not limited
to:

- **Heuristic DNC detection.** The bundled Do Not Call detector uses sentiment
  thresholds and a keyword list. A single explicit opt-out phrase may not be
  registered as DNC. Operators should layer stricter detection and manual review
  on top.
- **No 24-hour STOP-honoring window in code.** The system marks a lead as
  opted-out when a STOP reply is classified, but it does not enforce a maximum
  time-to-honor in the SMS pipeline. Federal rules require cessation within
  reasonable time periods that this software does not on its own guarantee.
- **No 30-day quiet-period suppression after a STOP.** Re-engagement gating is
  the operator's responsibility.
- **Calling-hour window is hardcoded, SMS-only, and server-local.** The SMS
  batch executor at `BE/workers/batch_executor.py` skips execution outside
  **9 AM – 6 PM in the server's local time zone**. It is **not configurable**
  by env var, **not based on the recipient's time zone**, and **does not apply
  to voice calls** — voice calls fire whenever the operator triggers them. The
  federal TCPA default is 8 AM – 9 PM in the recipient's local time zone, and
  many states are stricter. Outvox does not implement per-recipient time-zone
  resolution.
- **No consent metadata validation.** The system does not validate consent
  timestamps, channel of consent, or audit-trail retention.
- **No DNC registry scrubs.** The system does not query the federal or any
  state Do Not Call registry. Scrubbing is entirely the operator's
  responsibility.
- **No recording disclosure prompt.** When `ENABLE_CALL_RECORDING=true`, calls
  are recorded but the bundled voice prompts do not announce recording. Add a
  disclosure to your prompt before recording in two-party-consent
  jurisdictions.
- **Indefinite retention.** Call transcripts, recordings (URLs), and SMS
  conversations are retained indefinitely in the schema. Implement a retention
  policy appropriate to your jurisdiction and the consents you obtained.

## Not legal advice

Nothing in this repository, including documentation, comments, code, or sample
prompts, constitutes legal advice. **Consult qualified telecommunications counsel
before placing calls or sending messages with this software.**

## Trademarks

Outvox is a generic placeholder name. The bundled sample prompts, store data,
and SMS templates are example fixtures only and do not represent any real business.
Configure `COMPANY_NAME`, `AGENT_NAME`, and related environment variables (see
`BE/env.example`) before any non-development use.

## Trial / development use

For development, integration testing, or evaluation:

- Use Twilio test credentials (`Test SID` / `Test Token`) and test phone numbers
  (e.g., `+15005550006`) to exercise the call and SMS paths without placing
  real-world calls.
- Use the OpenAI Realtime API in a development project.
- Keep all `.env` files out of version control.

## Reporting compliance issues

If you discover behavior in this software that creates a compliance risk, please
open an issue and (where appropriate) coordinate disclosure with the maintainers
before publicizing details. See `SECURITY.md` for the disclosure channel.

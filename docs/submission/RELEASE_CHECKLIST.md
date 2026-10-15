# Friday — current submission readiness

Updated 15 October 2026 for version 0.24.0. This replaces stale owner-only
access and older test counts. Dated release reports retain their historical
evidence; see [reports index](../REPORTS_INDEX.md).

## Implemented and verified

- Statement-first Home → upload → review → spending → optional coaching path.
- Verified Google account display; live Vertex PDF extraction and aggregate
  coaching; transactional statement storage/replay; reversible exclusions;
  hosted artificial CSV preview without polluting owner history.
- Current test counts and exact deployed sources: [CURRENT_RELEASE](../CURRENT_RELEASE.json).
- Still pending: independent bank-format/accuracy and usefulness evaluation,
  dedicated outstanding-loan/APR extraction, human eligibility/deadline checks
  and final submission artifacts. No production-bank readiness guarantee.

- Google-sign-in Cloud Run website, isolated visitor workspaces and private API.
- Live Gemini/Vertex conversation, document facts, quoted risk reasoning and typed
  restricted plans. Document AI OCR anchors are not issuer authentication.
- Private document reconciliation, unsent verification drafts and selected-obligation
  preparation with fresh evidence checks. Preparation cannot pay.
- Separate signed artificial-payment tasks, exact confirmation, reserve/permission
  gates, idempotency and independent recorded-outcome checks.
- Transactional Firestore in cloud and SQLite/Docker development; server-held
  credentials, explicit context consent and request limits.
- Low-rate keyless Cloud Tasks journal-only recovery with historical actual
  callback acceptance. No blind financial retry or continuous bank intake.
- Private buddy preferences/follow-ups, manual cleanup and in-flight cancellation.
- Money Runway: exact dated INR assumptions, spending caps, delayed-income chart,
  optional latest-plan memory and separately consented Gemini explanation.
- Native 526 tests: 525 passed, one optional skip. Docker 526: 503 passed,
  twenty-three optional skips. Twenty-four tooling checks passed; published Money
  Runway GitHub checks also passed on Python 3.11/3.12 and Docker.
- Corrected real Vertex/Firestore runway acceptance verified exact rupee caps,
  save/readback/cleanup, unchanged rules and no money movement. The initial
  zero-traffic unit error is documented, not hidden.
- [Deployment manifest](../CURRENT_RELEASE.json) records actual source commits,
  immutable images, build IDs and historical/current acceptance scopes.

## Required before claiming the submission is complete

1. Confirm exact cutoff/timezone, eligibility and roster in the dashboard. The
   [official timeline](https://aibuildercup.com/) checked 14 October lists team
   formation by 14 October and submission by 18 October 2026. Dashboard-specific
   completion is not verified by this documentation pass.
2. Test the app with a second person's Google account. Visitor enrollment is not
   owner-only, but managed accounts may be restricted. Never expose the API to
   solve a login issue. Source access needs an invitation to this private GitHub
   repository or an organiser-approved source-delivery method; a link is not access.
3. Complete held-out usefulness/risk tests; report misses, false warnings, latency
   and cost. Unit counts/developer cases are not real-world fraud accuracy. Preserve
   the paired comparison; do not invent superiority over plain Gemini.
4. Finish/confirm deck as PDF, public approximately three-minute video, English
   submission fields and checked links. This file does not submit the entry.
5. Keep a labelled outage fallback and verify trial/billing availability through
   evaluation. Budget alerts and app quotas are not guaranteed spending/uptime caps.

## Production work, not claimed as hackathon implementation

Authorised independent bank/utility integration, real settlement/refunds, automatic
bank/SMS/email intake, external notifications, native voice, account-erasure and
regulatory/security review, independent large-scale validation and trusted-reference
retrieval remain future work. Do not claim unrestricted financial Jarvis, perfect
safety, trained fraud classification or autonomous production patching.

# Financial Friday 0.18.0 — hardening boundaries

This release closes concrete code gaps. It does not certify real banking,
fraud-detection accuracy, legal compliance or full production readiness.

## Implemented

1. **Complete bounded financial evidence:** the recent UI may show 50 records;
   safety checks read all stored entries up to 1,000 and fail closed beyond that
   bound. Old conflicts and receipts no longer disappear just because new inputs
   arrived. This is a conservative tenant-wide snapshot, not an unlimited graph.
2. **Atomic evidence gate:** SQLite rehashes the safety snapshot inside its payment
   transaction. Firestore reads the evidence epoch inside its payment transaction;
   admitted review writes/imports/cleanup increment that epoch atomically. A late
   change holds a new debit. An earlier signature does not bypass this check.
3. **Durable lifecycle:** a separate signed execution journal binds task/tenant,
   lease, status and run reference. Completed tasks are independently replayed on
   readback. Expired leases mean outcome unknown. A reconciliation endpoint reads
   the existing payment journal without initiating a retry or calling Gemini.
4. **Privacy:** manual cleanup age and explicit review/draft deletion controls.
   Comparison history is removed; financial receipts/idempotency are retained to
   prevent repeating recorded effects. Cleanup cancels in-flight saves through a
   privacy generation check. No automatic retention deletion is enabled by default.
5. **Rotation support:** an operator-provisioned public verification keyring can
   preserve old signed records after replacing the active private key. Key IDs
   must match public-key fingerprints. Unknown/misattributed keys fail closed.
   No live private key was changed by this release.
6. **Independent OCR adapter:** exact Document AI processor resource, bounded
   pages/text, OCR anchors, field-value support and readability checks. When the
   processor is not configured, image/PDF extraction remains explicitly ungrounded
   and cannot silently act as independently verified payment evidence. OCR does
   not authenticate issuer, recipient ownership, fraud or settlement.
7. **Evaluation:** a frozen-corpus paired live-model runner, external label
   provenance, errors/false warnings/missed risks/latency and an independent review
   protocol. Bundled probes are developer-authored, not an independent benchmark.
   There is no executor in the evaluation runner and no invented fraud score.
8. **Observability:** timing, available actual token counts and exception type;
   no prompts/replies/tenant identifiers in model telemetry. SDK retries are limited
   so explicit application retry bounds are not multiplied invisibly.

## Cloud activation still requires authorization

Historical 0.18 activation status below is superseded by
[the 0.19 cloud extensions](CLOUD_EXTENSIONS_0190.md). Basic Mumbai OCR is now
active and verified; automatic Tasks dispatch still requires dedicated identity
approval. The current adapter accepts US/EU/Mumbai processors, not only US/EU.

- Set `FRIDAY_DOCUMENT_AI_PROCESSOR` to an exact approved processor only after
  enabling the API, choosing its processing region and granting the API service
  narrowly scoped processing access. The current adapter admits US/EU processors;
  do not claim Indian processing residency. Trial eligibility/pricing must be checked.
- `FRIDAY_VERIFICATION_KEYS_PATH` optionally points to a server-mounted JSON map
  of public key fingerprint to base64 raw Ed25519 public key. It contains no private
  key. Keep the active private key in Secret Manager; rotate only through a reviewed
  operator procedure with historical receipt replay tests.
- Cloud Tasks automatic scheduling is **not active**. Durable execution recording
  and read-only recovery work without it, but this release does not claim a worker
  automatically resumes after a Cloud Run crash. Queue/service permissions and a
  background dispatcher remain a distinct approved deployment step.
- Independent human labels and held-out cases are still required for a credible
  AI-quality claim. Engineering tests cannot manufacture that independence.
- Real provider/bank access and external correction/refund submission remain
  unavailable. No application code may silently turn a draft into a sent complaint.

## Migration and verification

Existing uploaded reviews are not deleted during release. Old image quotations
remain marked ungrounded in safety snapshots. Existing prepared tasks must be
regenerated because they lack the new evidence binding; old receipts remain
readable under trusted signing keys. Model outages are visible; no canned answer
or accuracy result is substituted.

Tests cover late SQLite/Firestore evidence changes, older-than-window conflicts,
coverage overflow, leases, completed task readback, journal-only reconciliation,
privacy isolation/confirmation/in-flight cancellation and public-key rotation.
See README for the final verified counts and the latest deployment release record.

The live Vertex/Firestore release probe used a fresh disposable synthetic visitor:
preparation without debit, semantic refund hold, one confirmed artificial payment,
completed-task replay without another debit, signed lifecycle readback, journal-only
reconciliation and synthetic draft cleanup preserving the receipt all passed.
The Developer API paired-risk smoke comparison was stopped after repeated server
errors; no independent accuracy number is available. Runtime identities are in
[CURRENT_RELEASE](CURRENT_RELEASE.json).

## Outcome-focused follow-up, 13 October

The obligation inbox now joins complete bounded document claims, exact artificial
supplier/reference provider matches, reserve/limit planning and journal outcomes.
Selected Gemini preparation includes relevant facts and saved rules, binds the
evidence version, and rejects bill substitution or excessive document context
before execution (oversized context is refused before a model call).

Seventeen new regression tests cover those boundaries. Native 422 ran (421 passed,
one skip), Docker 422 ran (403 passed, nineteen skips), and fifteen tooling checks
passed. A new synthetic bill was extracted live with Vertex AI, prepared as an
exact selected obligation, executed once and read back as recorded complete.
Read-only recorded-outcome lookup creates no new payment and calls no Gemini.
The source is `f1966f7`; GitHub CI passed for that commit.

Contradictions are not fraud verdicts. Missing providers lead to verification
assistance; uploaded receipts remain claims. Customer impact, adoption, real-bank
settlement and independent model-quality validation still require outside evidence.

# Financial Friday — Task and risk-gate release, 13 October 2026

Runtime source `a248997c6d6641ced7f906e74734a7117396b8fb`. Package version remains
`0.17.0`. Later documentation and verification-tool fixes do not alter runtime.

| Service | 100% traffic revision | Immutable image digest |
| --- | --- | --- |
| API | `financial-friday-api-tasksfinal1013` | `sha256:50535c7dd3ea6eb0df5c41641bb5ee457f9004cd4be601fbb350733d36122211` |
| Web | `financial-friday-web-tasksfinal1013` | `sha256:b57338d7862bc170e9893f68ab89dd3d5cf9ca6dfdffa5e5d260d1ee23e8f421` |

Builds: API `bb40ca58-6e39-45fc-b382-acf3da67f723`; web
`f8120a52-1219-45bf-b369-9f58c18ab742`, both successful. Clean Git archives excluded
unrelated local edits. Existing IAP, private API IAM, origins and secrets were
preserved; no new bank access, APIs, billing upgrade or Cloud SQL trial was added.

## Verified behavior

- Native: 384 tests, 383 passed/one optional skip.
- Docker: 384 tests, 366 passed/eighteen optional skips.
- Tooling: twelve tests passed.
- [Runtime-source GitHub CI](https://github.com/Santxsh27/financial-friday/actions/runs/38381981034): passed.
- Live `gemini-3.5-flash-lite` on Vertex AI selected a new synthetic bill task.
- Request-only refund/send contradiction produced quoted risk findings and HOLD
  without reading saved-workspace records.
- Signed Firestore task reopened with the same digest. Preparing did not debit.
- After explicit artificial confirmation, one INR 100 payment was recorded.
- Repeated confirmation produced no second debit; independent replay was VERIFIED.
- Canonical live website: a newly typed refund request, with saved-workspace
  consent off, rendered an actual Vertex risk hold, exact source quotation and
  unsent verification message. Browser console error/warning check returned empty.
- Synthetic run `ff_3556a9a3ebdf4a46af2709ccd5fe4c87` lives only in its isolated
  test visitor workspace; it is not a shared customer/judge payment.

The live verifier respects admission pacing; it does not weaken rate limits.
Only synthetic records and artificial funds were used, not user bank information.

## Issues discovered and fixed before promotion

An initial staged test prepared a payment using displayed default limits, but
the fresh Firestore workspace had not saved a mandate/account. The independent
executor correctly held it with `MANDATE_OR_ACCOUNT_MISSING` and no debit.
The final preparation gate now returns `SANDBOX_SETUP_REQUIRED` and the UI offers
My rules instead of claiming readiness. The test explicitly saves artificial
limits with automatic execution off. A verification-tool HTTP method mistake
was corrected to use PUT for rule updates and covered by a tooling test.

## Scope

These are working integrations and small functional probes, not a calibrated
fraud benchmark, real bank certification or proof that Gemini never misses a scam.
Only existing bounded artificial payments execute. Verification messages are
unsent. Real banking, refunds, account freezes, investment execution, provider
ownership verification, native voice and production code repair remain unavailable.
See [FRIDAY_TASKS](FRIDAY_TASKS.md) for exact context and transaction boundaries.

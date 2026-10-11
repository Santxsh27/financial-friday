# Friday 0.16.0 — a shorter path from bill to outcome

## Customer journey

Home → Open my bill plan → Select a bill → Check & handle in sandbox → Recorded
task result → Activity. Reading or selecting a plan never authorizes a payment.
The action button explicitly consents to artificial-money execution, within
current saved rules. It does not authorize a real payment.

The dark-jade Money Journey layout is the user's selected third direction,
refined with a real generated glass-orb asset. Companion states are derived from
request/run state: ready, working, held, attention or confirmed outcome. Animation
is cosmetic and can be disabled; it is not evidence of background monitoring.
Technical program/evidence details remain expandable.

## Mechanism

1. A read-only, exact deadline/Pareto dynamic program selects bills fitting the
   protected reserve and saved per-payment limit. This existing solver is tested
   against an exhaustive oracle, not claimed as a new mathematical discovery.
2. Each displayed provider record has a canonical digest. POST
   `/v1/friday/bills/handle` accepts only the reference, reviewed digest and strict
   execution consent; browser-supplied payment fields and unknown keys are rejected.
3. The service resolves that record in the authenticated tenant, recomputes
   eligibility, and asks the configured Gemini adapter to interpret it.
4. Independent checks require the same bill, amount, payee, INR currency and
   one-time request. Contradictions or unsupported instructions stop the action.
5. Ingestion must use the same reviewed record, then the existing restricted
   program planner/verifier/executor runs. Gemini has no signing key or direct
   bank API permission.
6. SQLite and Firestore commit gates recheck current records, permission and
   reserve. Firestore commits the artificial payment, balance, idempotency and run
   together. Prior valid receipts suppress another financial effect.
7. The gateway does not retry an uncertain POST. The UI directs uncertain outcomes
   to Activity before another action. The customer sees server-derived results.

The digest binds a displayed record; it is not independent proof that a merchant
is honest or a substitute for payment authority. Provider data is artificial.

## Verification

287 native application tests: 286 passed, one optional integration skipped.
Eleven tooling tests passed. This includes twelve reviewed-bill tests, two cloud
gateway/asset tests and Firestore current-limit/default-normalization tests. Tests use
local rules/fakes unless explicitly described as live Vertex checks.

Covered: changed reviewed fields, provider change during AI work and before
ingestion, switched model amount/payee/reference, recurring intent, consent
coercion, unexpected payment fields, cross-tenant lookup, replay, changed limits,
same-origin enforcement and protected exact-path PNG serving.

A live local Vertex run found a false provider-change hold on a legacy artificial
bill lacking newer optional fields. Provider comparison now validates both records
through the same strict schema before exact comparison. It only normalizes defined
defaults: real field changes, invalid values and unknown fields remain rejected.
SQLite and Firestore contract tests cover this compatibility repair.

The rebuilt local service then completed JUDGE-7430 with live Vertex Gemini:
one planning call, one INR 1,850 artificial payment, a saved receipt and no browser
console errors. Activity also retained the earlier held run and the successful
legacy-record recheck as separate outcomes. Docker ran all 287 tests with ten
optional-tool/integration skips and no failures.

Browser fidelity and responsive evidence are recorded in `../design-qa.md`.
Deployment identifiers and live checks will be appended only after verification.

## What is still outside the product

Real banking/payment integration, background cloud scheduling, native voice,
universal SMS monitoring, investment recommendations and bank-code patching are
not implemented. Judge enrollment, submission PDF/video and broader independent
evaluation still matter; no release or design can guarantee selection.

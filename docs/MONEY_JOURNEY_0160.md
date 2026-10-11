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
## Cloud deployment evidence

Clean source commit: `3ff5f41`. Cloud Build:
`b9a95013-82ba-45a5-ad67-8282f4e9ee4b`.
Image digest:
`sha256:5af1c5831213d06f555c18a597df804b95c52193273c919ec410ec9d4af8653b`.
API and web revisions `financial-friday-api-jade1011` and
`financial-friday-web-jade1011` were deployed without traffic, checked, then
promoted to 100%. Existing IAP, tenant enrollment and private API settings were
retained. The dirty, unrelated local `control_room_future.py` edit was excluded
from the commit and clean build archive.

Candidate and stable private API checks passed: version 0.16.0, transactional
Firestore, 13 artificial bill records, no payment authority on the plan,
unchanged balance, rejected unconfirmed execution (422), unavailable external
follow-through and rejected anonymous access. The candidate also used live Vertex
to interpret one artificial paid notice without a payment request or case.
Owner browser checks confirmed the protected orb asset loads and the redesigned
home/plan renders without console errors.

Full stable-site action also passed for artificial bill `FRIDAY-c33cf0f72952`:
run `ff_94d5ef6a4f634914af82f3d55c6f1894`. Gemini made three planning calls;
the checker rejected two proposals before an accepted restricted program recorded
one INR 2,479 payment to the enrolled artificial recipient. The cloud screen
showed a saved receipt, actual correction evidence and no browser errors. This
test intentionally changed the sandbox balance; the read-only candidate checks
above did not. It is task-plan correction, not production bank-code repair.

## What is still outside the product

Real banking/payment integration, background cloud scheduling, native voice,
universal SMS monitoring, investment recommendations and bank-code patching are
not implemented. Judge enrollment, submission PDF/video and broader independent
evaluation still matter; no release or design can guarantee selection.

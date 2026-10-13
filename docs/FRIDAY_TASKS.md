# Financial Friday — Evidence-bound AI tasks

Implemented 13 October 2026. This is a real integration between live Gemini task
preparation, private evidence, independent checking and the existing artificial
payment executor. It is not a newly trained fraud model or bank integration.

## What changed

- Free-text requests become one typed action, rather than only a conversational reply.
- Gemini identifies potential semantic risks with exact quotations and source IDs.
- Separate code rejects unavailable citations, recipient/amount/direction conflicts,
  claimed prior payments, ineligible bills and unsafe model proposals.
- Signed ten-minute task capsules bind one workspace, exact provider bill, rules
  and related evidence. Preparation never enters the auto-payment intake.
- Confirmation cannot override a HOLD. Fresh checks feed the existing typed-program
  verifier, artificial-money transaction and signed outcome replay.
- The reviewed-bill button also checks related document claims, preventing that
  customer path from ignoring a conflict held by task preparation.
- SQLite and Firestore support private saved task readback. Model text is rendered
  as text, never executable HTML, SQL, source code or a model-supplied URL.

## User flow

1. Start on Overview. Grant optional saved-workspace context.
2. Enter a request and choose **Prepare next step**.
3. Review the separate task page: exact bill fields, risk quotations, gate reasons
   and any unsent verification message.
4. If eligible, choose **Confirm artificial payment**. Only this explicit action
   enters execution; ask/read/prepare/refresh are not payment authority.
5. Read the actual signed outcome in the existing result screen. On a timeout,
   check Activity instead of assuming failure or blindly retrying.

An editable artificial bill must be published through Bills for the execution
demonstration. Uploaded invoices/receipts alone are not payable provider records.
For ordinary documents Friday can prepare a verification message without a bank.

## Model and deterministic boundaries

Gemini interprets intent, classifies potential contradictions, selects a bounded
next action and drafts a useful verification message. After explicit confirmation,
the existing Gemini interpreter/planner proposes the restricted financial program.
The independent verifier—not Gemini—checks identities, fields, ordering, reserve,
permission and idempotency. No arbitrary new tool can be generated.

Each risk quotation must occur in its supplied source; this proves provenance,
not that the model's interpretation is correct. All uploaded financial claims
remain unverified externally. No fake numeric confidence or calibrated fraud
accuracy is displayed. Fixed semantic categories do not constitute a trained ML
fraud classifier. A real classifier would require representative labels and a
held-out evaluation, including false positives.

## Limitations

- Context: twenty provider bills and ten reconciled cases; gate: latest fifty
  reviewed inputs with exact invoice identity. Coverage is visible.
- Review evidence and posting are separate bounded snapshots, not one transaction.
  A new claim arriving during final execution may not be included. Financial
  idempotency/balance/rule gates retain their existing atomic transaction boundary.
- Risk findings can miss scams and over-warn. They do not establish merchant/account
  authenticity or proof of fraud. No universal protection claim is made.
- Historical developer execution routes are not consumer task-preparation tools.
- No new independent provider, Gmail/SMS integration, real bank/payment rail, stock
  service, live voice, fund recovery or production-code patching was added.
- Saved task excerpts and messages share existing private retention limitations;
  raw questions and authentication secrets are not deliberately stored.

## Verification

`tests/test_friday_tasks.py` exercises preparation without financial effects,
standing-auto-authority separation, consent/auth, cross-user isolation, exact quote
and citation checks, hallucinated tool/bill rejection, conflict holds, stale
provider/rules/evidence, expiry, tamper, repeat-confirmation idempotency, unavailable
models, cloud storage selection and safe rendering. These tests mock inference;
they measure code behavior, not real-world fraud accuracy.

`tools/verify_tasks_cloud.py` separately tests real Vertex inference and Firestore
in a fresh synthetic visitor workspace. Its optional explicit execution flag uses
only artificial funds. Release evidence must distinguish mocked unit tests from
live model checks; deployment details are recorded after verification.

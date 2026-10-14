# Financial Friday — Current product and engineering contract

Updated **14 October 2026**. This document replaces the mixed historical product
specifications. Current code version is `0.22.0`. Actual deployed source and
image identities are recorded in [CURRENT_RELEASE](docs/CURRENT_RELEASE.json),
not inferred from documentation or a GitHub push. See [hardening](docs/HARDENING_0180.md).
For the detailed rationale, algorithms and trust boundaries, read
[ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md).

## 1. Product definition

Financial Friday helps users keep financial obligations on track with minimal
repeat input. Its obligation inbox joins saved document claims, exact artificial
provider identities, saved constraints and recorded outcomes. Gemini prepares the
next step; independent checks determine what can proceed. The intended outcome
is a completed allowed task or useful verification assistance, not just an alert.

The default consumer workflow is **read-only guidance and claim reconciliation**.
The execution workflow is **separate and explicitly artificial**. Neither is a
real-bank connector, investment adviser, SMS/Gmail agent or universal fraud shield.

### Primary customer journey

Input once → obligation inbox → explicit selected-context sharing → Gemini prepares
one exact obligation → signed task and independent gates → explicit artificial
confirmation if eligible → journal-backed result. No provider connection means
verification assistance only. No automatic external complaint, correction or refund.

`GET /v1/friday/obligations` reads complete bounded safety evidence and joins only
exact normalized supplier AND reference to a provider record. It does not call
Gemini or move funds. States are `READY_TO_PREPARE`, `RECORDED_COMPLETE`,
`DETAILS_CONFLICT`, `VERIFY_STATUS`, `NEEDS_DETAILS`, `VERIFY_PROVIDER`,
`REVIEW_RULES`. These are workflow states, not fraud classifications.

Selected preparation binds `obligation_id` and `expected_evidence_version` into
the signed task. The planner sees only the selected provider bill, selected case,
up to ten supporting document facts, saved rules and current instruction. Any
attempt to select another bill is rejected; excess selected-document context
is rejected before a model call. Full bounded evidence remains checked independently. Preparation
does not authorize payment, and evidence/provider/rules are rechecked at execution.

## 2. Supported workflows

### Money Runway (private what-if planning)

User-entered INR cash, chosen buffer, daily variable spending, dated expected
income and known bills produce an exact 1–90 day scenario. Integer minor-unit
calculations find the first buffer dip/negative cash, the largest daily cap
consistent with every prefix of the entered plan, and a delayed-income comparison.
Bills and discretionary spending are deducted before same-day income. Income is
not guaranteed, and known commitments can exceed the buffer even with zero
discretionary spending. Never classify a user as poor or promise future balances.

Calculation calls neither Gemini nor execution. Saving the latest snapshot is
optional, private and generation-protected against cleanup races in SQLite and
transactional Firestore. Review cleanup removes that snapshot; opening the page
does not create one. A separate unchecked chat consent sends only aggregate
calculator context to Gemini, not raw statements or individual events. Changes
clear stale conversation context. This memory is not model training. There is no
RAG corpus, fine-tuning job, live bank/SMS source or external notification service.
See [algorithm, privacy and dataset plan](docs/MONEY_RUNWAY_0220.md).

### Follow-up memory (separate from financial truth)

Saved obligations can be tracked, marked waiting for a provider reply, rechecked,
or closed as a follow-up. No message is sent and no payment is verified by these
actions. Closing never clears financial warnings or bypasses the execution gate.
New evidence for the same exact supplier/reference/currency group produces
`NEW_EVIDENCE`, including after closing; rechecking acknowledges the current
evidence, not merchant authenticity or settlement. Missing identities remain
separate instead of guessing relationships.

Updates require the current evidence version and tracking revision; simultaneous
or stale edits fail rather than overwrite another session. Tracking is private,
bounded to 100 entries, persists in SQLite locally/Firestore in cloud, and is
cleared during explicit review cleanup. Privacy-generation transactions prevent
in-flight updates from restoring removed tracking. Read-only inbox refresh uses
no model call. There is no scheduled reminder, provider monitoring or external send.

### A. Conversational assistance

The task planner separately prioritises a useful unsent verification draft when
risk is identified or the user asks for one; educational requests remain explanations.
Production and same-output evaluation share the exact source/quote admission
function. Duplicate source IDs are rejected. The live developer regression and
its pre-correction failures are recorded in `docs/EVIDENCE_EVALUATION_0211.md`;
it is not an independent fraud benchmark or permission to execute money movements.

User question -> validated tenant request -> optional bounded private context ->
Gemini response -> schema/citation/authority validation -> safely rendered text.

- Message/reply limit 1,600 characters; up to eight prior user/assistant turns.
- Context is opt-in and contains at most ten cases from the latest fifty review
  inputs, currency-separated totals and artificial balance/reserve information.
- No bank lookup, payment, code, SQL, shell, arbitrary URL or browsing tools.
- Suggestions navigate to allowlisted screens; model text is not task completion.
- Drafts remain unsent. History is page-memory only and clears when consent changes.
- Known credential patterns are scrubbed best-effort; users must not enter secrets.
- Model failure reports unavailable instead of substituting a pretend live answer.

### B. Document/transaction-claim review

User-supplied text/image/PDF -> Gemini typed facts -> exact checks -> tenant review
record -> related claims/conflicts -> verification message and evidence display.

- Default review cannot alter a mandate, payment journal or balance.
- Supported files are PNG/JPEG/WebP/PDF below the 8 MB bound; text is bounded to
  12,000 characters. File selection/example loading alone does not send data.
- Matching fields require supporting quotations. Text quotes are checked verbatim;
  configured Document AI independently anchors image/PDF quotations to OCR text
  and page/line evidence. Without that processor, they remain unverified.
  OCR does not verify the issuer or payment recipient's ownership.
- Exact decimal/minor-unit checks cover line arithmetic and supported precision.
- Currency is explicit; bare `$` remains unknown. No currency conversion/aggregation.
- Incoming credits do not satisfy outgoing bills. Invoice and payment references
  are separate. Exact supported identity groups, not fuzzy merchant authentication.
- Content hashes deduplicate per tenant. Raw uploads are discarded, but extracted
  facts, quoted evidence, provenance, filename and hash are retained privately.
- CSV claim import requires consent and is bounded to twenty INR rows/1 MB; it
  does not call AI. Statement spending analysis is a separate read-only operation.

Review states: `BILL_TO_VERIFY`, `RECEIPT_MATCHED_CLAIM`,
`RECORDED_PAYMENT_CLAIM`, `CONFLICT_REVIEW`, `INCOMPLETE_REVIEW`.
They do not prove fraud, a legitimate merchant, real ownership or settlement.

### C. Restricted artificial-money execution

Reviewed test-provider bill -> digest-bound interpretation -> immutable goal and
separate provider evidence -> typed Gemini program -> deterministic verifier ->
bounded plan repair/challenges -> current permission/state recheck -> atomic
artificial effect -> signed receipt -> independent replay.

Only an explicit sandbox action or previously granted automatic sandbox authority
can enter this workflow. New users default to automatic execution off. The original
execution-model intake is not a prepare-only conversation API. Chat/default
review never use it to create an executable task.

### D. Evidence-bound AI task preparation

Free-text request + optional explicit workspace consent -> Gemini typed task selection and
quoted semantic-risk findings -> independent related-claim/provider/reserve checks
-> signed ten-minute task -> exact customer confirmation -> existing restricted
executor -> signed outcome and independent replay.

The fixed model actions are `PREPARE_PAYMENT`, `PREPARE_VERIFICATION`, `EXPLAIN`.
Findings include refund/send contradiction, recipient switch, coercion, secret
requests, hidden recurring terms and prompt injection. Each finding needs a
verbatim quotation from an available source. These are potential risk indications,
not authenticated fraud verdicts or calibrated probabilities. Model misses and
false warnings remain possible; no fraud classifier has been trained.

Without workspace consent, only the current request is sent; no saved financial
records are read and no provider bill can be selected for payment. Risk checks
and unsent verification messages still work. Preparation never calls execution
intake, even if automatic authority is enabled.
A task binds tenant, canonical artificial bill, related claim snapshot and rule
digest. Confirmation checks signature, digest, expiry, tenant and fresh evidence;
the existing executor rechecks provider/rules and enforces atomic idempotency.
Related recipient/amount/direction conflicts or claimed prior payments cannot be
cleared by a favourable model answer. The reviewed-bill button uses that same
claim gate. Historical execution intake routes remain separate developer paths.

States: `READY_FOR_CONFIRMATION`, `HOLD`, `PREPARED_MESSAGE`, `GUIDANCE_ONLY`.
Only the first permits explicit artificial-money execution. Verification messages
are unsent drafts. Tasks persist privately in SQLite/Firestore; no raw question
is stored, though redacted finding excerpts and proposed messages can be retained.
Model context is bounded to twenty provider bills and ten review cases. Related
claim gates inspect the latest fifty review documents. This is a bounded snapshot,
not continuous surveillance; review reads and payment posting do not share an
atomic transaction. It cannot guarantee rejection of a new claim arriving during
the final execution window or detect scams outside the available context.

## 3. Contracts and algorithms

`FinancialGoal` binds goal/provider/payee, INR, total/fee ceilings, one-time cadence,
allowed data fields and an idempotency identity. `FinancialEvidence` contains the
server-owned test-provider record, options, observations and prior outcome.
`FinancialProgram` contains typed actions and an explanation, never generated code.

Normal action order:

```text
VERIFY_PROVIDER -> LOAD_OBLIGATION -> CREATE_ONE_TIME_PAYMENT -> CONFIRM_RESULT
```

Unknown prior outcome:

```text
RECONCILE_EXISTING -> CONFIRM_RESULT
```

The checker rejects changed identities, unobserved evidence, unauthenticated options,
wrong amount/fee/cadence, excessive disclosure, repeated financial actions and
unsafe ordering. A recurring verb exists in the schema for rejection tests; it is
not authorised by the one-time product contract. One bounded planning repair can
use safe validation error codes, never rewritten user permission.

Six normal-case mutations test amount, payee, disclosure, recurring obligation,
duplicate action and missing confirmation. The unknown-outcome path tests retry
before reconciliation. Mutation success is targeted robustness evidence, not an
exhaustive proof or model accuracy benchmark.

The reserve planner uses exact deadline-prioritised Pareto-frontier dynamic
programming: maximise bill count on earlier due dates, minimise spending for ties.
Bounds are 32 candidates/10,000 frontier states. Incomplete/ambiguous records and
limits fail closed. It previews artificial obligations; it neither reserves money
nor accounts for real external accounts, criticality or all personal-finance needs.

## 4. State, transactions and outcome assurance

- Local: SQLite, `SQLITE_LOCAL`; cloud: tenant-scoped Firestore,
  `FIRESTORE_TRANSACTIONAL`.
- State kinds: mandates, accounts, provider bills, signals, dynamic cases, runs,
  signed assistant tasks,
  payments, idempotency and reviews.
- New artificial balance ₹50,000; default reserve ₹10,000, automatic single-payment
  ceiling ₹5,000, zero fee, automatic execution disabled. Rules are not balance resets.
- Commit-time checks re-read relevant provider/mandate state. Preview is bounded
  and non-atomic; it cannot substitute for those checks.
- Atomic artificial commits bind balance, payment identity, signed receipt,
  idempotency and run outcome. Receipt-first replay consults the journal before
  requesting a new plan/payment, including during an AI outage.
- Ed25519 signatures and canonical hashes protect internal evidence integrity;
  reopening recomputes verifier/signature/journal checks rather than trusting
  stored pass flags. Legacy unsealed outcomes remain explicitly uncertified.
- These guarantees stop at the implemented transaction/trust boundary. A local
  rollback cannot undo an external transfer; signatures cannot prove a truthful bank.

Local follow-through checks a matching sandbox receipt and atomically stores a
signed acknowledgement. Cloud returns `UNAVAILABLE / CLOUD_CONNECTOR_NOT_IMPLEMENTED`.
Neither is an external biller update, settlement, refund or money recovery.
The separate bank/biller resolution kernel is tested proposal logic without an
authorised live correction adapter.

## 5. Identity, privacy and security

IAP authenticates the Google user. The Cloud Run gateway selects an owner mapping
or stable isolated visitor tenant from verified identity; browser-supplied tenant
headers are not authority. Domain-separated server HMACs derive visitor credentials.
The API is private and the web service uses an authorised service identity.
Secrets/signing keys stay server-side, with Secret Manager in the hosted setup.

Public visitor admission limits: twenty write/action requests per user/day, two
hundred globally, one thousand reads/user/day and ten thousand globally, plus
burst limits. Daily windows reset at midnight UTC. Counts include admitted requests
that fail downstream, and are not model-token or dollar spending caps.

Untrusted documents/history cannot redefine system permission. No model output
is executed as source code or SQL. Structured task inputs exclude credentials;
chat redaction is best-effort and arbitrary uploads are not guaranteed secret-free.
Users must redact inputs before transmission. Retention/deletion, stronger DLP,
external provider authentication and production operational review remain work.

## 6. Deployment and technology roles

| Component | Actual responsibility |
| --- | --- |
| Python/FastAPI/Uvicorn | API, bounded service orchestration and local/cloud web hosting. |
| HTML/CSS/JavaScript | Multi-page-like hash navigation, chat, uploads, evidence, rules and results. |
| Pydantic | Strict inputs, typed model outputs and contract validation. |
| Google Gen AI SDK / Gemini | Conversation, multimodal understanding, restricted planning and bounded repair. |
| Vertex AI | Authenticated hosted model inference; verified model `gemini-3.5-flash-lite`. |
| Firestore/SQLite | Cloud/local private records and implemented artificial transaction boundary. |
| cryptography / Ed25519 | Internal receipt/run integrity, not real-bank certification. |
| Cloud Run | Protected web gateway plus private API. |
| IAP/IAM/Secret Manager | Identity, service invocation and server-held credentials. |
| Cloud Build/Artifact Registry/Docker | Reproducible images and controlled revision deployment. |

Cloud Run/Firestore use the Mumbai deployment configuration; Gemini's model
location is configured as `global`, not a promise of universal Indian residency.
Local live development can use the Gemini Developer API. `LOCAL_RULES` is a labelled
baseline; multimodal review/chat do not masquerade as live AI in that mode.

Document AI supports an approved basic Mumbai processor, preflight one-to-three
page PDFs, and an app-wide 100-page daily admission limit. Deployment activation
and actual live evidence are recorded in `docs/CURRENT_RELEASE.json`.
Cloud Tasks journal-only recovery has an approved dedicated keyless identity and
low-rate queue. Actual deployment activation and callback evidence are recorded
in the release manifest. It cannot retry a payment.
Not implemented: native Gemini Live/Agora voice, ADK,
BigQuery, Vertex AI Search, Model Armor and Cloud KMS signing.
Bank of Anthos is retired from customer navigation/default configuration. Its
optional historical fixtures and compatibility identifiers remain recoverable.

## 7. Current experience and readiness

The financial-buddy surface adds tenant-isolated communication preferences and
a read-only overview of the user's saved claims. Default provider examples are
not personal obligations. The optional nickname stays out of model requests;
style/focus require saved and per-request consent. These choices never change a
mandate, reserve, verifier or execution authority. Animation and returned AI
provenance indicate actual requests, not background bank surveillance.

Overview has useful questions, document entry and editable guided examples, rather
than fake personal activity. Chat is compact with bounded scrolling, opt-in context
and privacy details. Home examples do not submit automatically. Theme, optional
sound and motion preferences affect presentation only. Evidence states reflect
actual results; insufficient information does not produce a universal safe badge.

Current hardening code: 405 native tests (404 pass/one skip), 405 Docker tests
(386 pass/nineteen skips), fifteen tooling tests. Earlier live Vertex/Firestore verified
preparation without debit, a quoted refund-risk hold, confirmed artificial payment,
repeat-confirmation idempotency and independent replay. Details are in
[the release record](docs/FRIDAY_TASK_RELEASE_1013.md). Remote CI for runtime source
`a248997` passed; later documentation CI must be checked separately.
Test passes do not measure fraud accuracy or certify every feature/device.

## 8. Priorities and non-goals

Before submission: confirm another human login/roster/deadline, evaluate the new
conversation-to-approved-task bridge on varied unseen inputs
and create required video/deck/materials. Preserve the existing safety boundary.
Implemented hardening includes durable task lifecycle, journal-only recovery,
complete bounded safety snapshots, atomic evidence-version checks and explicit
review/draft retention/deletion. Later: independently authorised providers,
automatic cloud workflow dispatch, complete account erasure and wider governance
operations and native voice. No autonomous real-money access, trading calls,
phone surveillance, production patching or guaranteed reimbursements.

Novelty/patentability and competition awards remain unproven. The BFSI submission
is a functional AI-assisted financial experience and bounded-execution prototype,
not a claimed replacement for banking infrastructure. Review the official
[requirements](https://aibuildercup.com/themes.html) and
[submission checklist](docs/submission/README.md).

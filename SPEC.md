# Financial Friday — Current product and engineering contract

Updated **17 October 2026**. This document replaces the mixed historical product
specifications. Release `0.32.0` is deployed in production consumer mode.
Actual deployed source and
image identities are recorded in [CURRENT_RELEASE](docs/CURRENT_RELEASE.json),
not inferred from documentation or a GitHub push. See [hardening](docs/HARDENING_0180.md).
For the detailed rationale, algorithms and trust boundaries, read
[ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md).

### Source extraction and reconciliation

Statement imports may contain literal-grounded source facts, running balances
and unit/page references. The server issues a tenant/generation-bound extraction
receipt, verifies immutable fields on save and recomputes all source checks.
Declared mismatches block save; unsupported or missing facts remain UNKNOWN.
User-reviewed meaning/category labels stay editable. Legacy imports never gain
a source-bound badge. The signature is Friday's extraction attestation, not bank
authentication. Minimal labelled fact excerpts are retained with normalized
history; raw files are not archived and excerpts/signatures are not chat context.
See [0.31.0 boundaries and measured baseline](docs/STATEMENT_RELIABILITY_0310.md).

### Consumer admission and release status

The consumer API and web proxy share an explicit route allowlist.
`FRIDAY_LEGACY_DEMO_ENABLED` defaults to `false` when loaded from the environment;
the deployed production setting is explicitly `false`. Earlier payment/preflight
demonstrations and new artificial execution routes require server opt-in.
Existing task/run inspection and authenticated journal-only recovery remain
available. This restricts route admission and OpenAPI exposure within the same
application; it does not create separate processes, storage or IAM identities.
Both services passed staged acceptance before promotion. See
[consumer assurance](docs/CONSUMER_ASSURANCE_0320.md) and
[CURRENT_RELEASE](docs/CURRENT_RELEASE.json).

## 1. Product definition

Financial Friday is a statement-first money buddy. The user imports supported
INR bank/card exports, reviews the proposed interpretation, sees exact categories
and monthly comparisons, then optionally shares aggregate context with Gemini.
The main interface is Home, Statements and My money, with Friday chat alongside
and Account at the top right. The existing
visual system is retained; earlier forms live under More tools rather than Home.
Its optional obligation inbox joins saved document claims, exact artificial
provider identities, saved constraints and recorded outcomes. Gemini prepares the
next step; independent checks determine what can proceed. The intended outcome
is a completed allowed task or useful verification assistance, not just an alert.

The default consumer workflow is **automatic statement checks, visual findings
and a prepared next step**. The server runs eight bounded checks on saved history:
repeated entries, regular payments, changed regular amounts, unusual expense
amounts, fees, unclear credits, exact spending-change attribution and the refund
evidence graph described below. Findings
retain source-file/row references and account type. `CHECKUP_2` uses finite,
complete UPI/NEFT/IMPS/RTGS narration layouts with explicit reference and payee
slots, with literal-description fallback. It preserves payee words, digits,
punctuation and non-ASCII distinctions, scopes matches by exact account
nickname/type, and reports match basis and uncertainty. Reliable explicit tokens
distinguish repeated-entry candidates; masked references cannot establish the
same transaction. They can support a weaker recurring payee candidate. Recurring
series still need at least three consecutive months, one occurrence per month
and 20–40 day gaps.
Amount increases require at least 15% and INR 100 above the prior median.
Outliers need six earlier account/category observations and must exceed the
maximum of three times median, median plus six median absolute deviations, and
median plus INR 1,000. These are review heuristics, not calibrated fraud scores.
Ambiguous recurring series are suppressed; duplicate candidates remain counted.
No thresholds were tuned against the existing 39-case authored corpus. Its
precision remains 14/21 = 66.67%, recall 14/19 = 73.68%, and case false-positive
rate 7/18 = 38.89%. These unreviewed agent-authored labels are not independent or
blind validation. The comparison report records no measured improvement or
regression; [the assurance note](docs/CONSUMER_ASSURANCE_0320.md) separates this
quality evidence from engineering regressions and AI smoke-test limitations.

The default workbench integrates refund evidence rather than requiring a Money
Shield tab. `ASSISTANT_WORK_1` derives a stable, source-bound batch of at most eight
open findings on each portfolio read/save. Repeated-entry comparisons and unclear
credit classification worksheets avoid turning those findings into unsupported
bank complaints. Other items use the existing unsent enquiry recipe. The response
states prepared/open/deferred counts, revision, generation, source fingerprint,
zero model calls, zero external actions and no money moved. Review advances the
queue; reopen/new evidence rebuilds it. This is deterministic preparation, not
autonomous resolution or model training.

An in-app guide reacts only to actual local workflow events. It is pauseable and
does not poll or monitor a financial account. The optional briefing route sends
only server-composed aggregate text (at most 50 words) to `gemini-2.5-flash-tts`
through the configured Vertex client. Explicit per-action consent, current
revision/generation and source recheck after generation are mandatory. Only
completed mono 16-bit 24 kHz PCM, bounded to 30 seconds, is wrapped as WAV in memory.
Audio is not persisted or auto-played; this is not a microphone/live voice agent.
Generated speech is not independently transcribed or certified for fidelity.

The server prepares unsent enquiries from current source evidence. A separate
revision/generation-bound acknowledgement stores only reviewed/open status.
No source transaction is changed. Gemini selects typed visuals or draft requests;
server code validates every selected finding against separately opted-in context.
Derived context excludes transaction descriptions, account nicknames and source
row/file identities. No personal model is trained. Monthly comparisons attribute
supplied amounts, not proven full-month behaviour. Financial planning is optional.

Typed Gemini goals feed a bounded integer
allocation engine; a separate arithmetic/constraint checker verifies its result.
Essentials and recorded loan repayments stay fixed. A selected source month,
category-cut caps and income-drop assumptions are shown rather than hidden in
AI prose. Infeasible goals report an unmet amount. Charts include exact tables.
See [0.26 planning contract](docs/VISUAL_MONEY_PLANS_0260.md).

Statement sharing is independent of the legacy financial-inbox permission.
General questions do not require records. Explicitly shared aggregate context
cannot grant financial actions. Ordinary settings open Privacy & data; legacy
payment rules remain a separate artificial execution concern, not onboarding.

### Money Shield

`REFUND_FLOW_1` groups EXPENSE purchases and REFUND credits by literal normalized
merchant, account nickname and type. Compatibility requires a purchase no later
than its refund, within 90 days. Integer max flow finds compatible capacity;
fixed-total min-cost flows minimize/maximize each purchase's allocation. A
separate primal check verifies compatible edges, capacities and conservation;
residual reduced-cost checks verify mathematical optimality. Bounds are tight
for this graph, not probabilities or bank-authenticated relationships. Bounds
for different purchases cannot be added as simultaneous maxima.

Groups with repeated rows, over eight purchases/refunds, or beyond 32 solved
groups are withheld. Missing merchant/history remains unlinked. Source rows
are not deleted or changed. Partial matches do not establish a refund obligation.
The UI displays linked evidence, ambiguity and a clarification path. Typed Gemini
action `MONEY_SHIELD` selects the view; `PREPARE_ENQUIRY` assembles current sources.
The server supplies their completion text, including when no personal check was
completed. Neither action can send a complaint, recover funds, alter a ledger or
grant bank access. No legal deadlines, tax entitlements, illegal-fee verdicts or
unused-subscription claims are inferred. [Full contract](docs/MONEY_SHIELD_0290.md).

### Financial rehearsals

The optional advanced decision workflow is **goal → explicit cash/buffer → review replay
assumptions → exact daily constraints → calculated alternatives → optional Gemini
explanation**. A single selected bank account prevents accidentally treating
several accounts as one cash pool. Each of up to six supplied months is replayed
separately by calendar day. Baseline and simultaneous delayed/reduced-income,
higher-essential-cost variants are tested. All bank-account debits count as cash
outflow, including card/loan repayments and transfers; only identified income is
projected. Same-day debits precede credits. Past income is not delayed forward
and counted a second time.

The engine computes an exact suffix-minimum one-off purchase envelope, earliest
later fitting date, and minimum uniform proportional flexible cut at 0.01
percentage-point precision within the chosen cap. An independent replay checks
daily conservation, protected costs and option feasibility. Infeasibility remains
visible. No probability, learned risk score, future guarantee or financial action
is implied. Full contract: [financial rehearsals](docs/FINANCIAL_REHEARSAL_0270.md).

The execution workflow is **separate and explicitly artificial**.
Neither is a
real-bank connector, investment adviser, SMS/Gmail agent or universal fraud shield.

### Primary customer journey

Statement upload → unsaved source-linked rows → explicit review/save → exact
spending/category/monthly dashboard → independently opted-in Gemini guidance.
Raw uploads are ephemeral. Same-source imports replay without duplicate rows;
different overlapping files are counted with a warning until a user excludes an
import. Exclusion is reversible, not deletion. Generic credits remain unclear;
borrowing/refunds/transfers are not identified earnings. Card repayments are not
new spending, but missing card purchases can understate spending. No inferred
assets, loan principal, complete net worth, or official financial-health score.

PDF support is bounded, not universal: INR, 4 MB, 1–6 pages, up to 200 proposed
rows, one model call. Text PDFs use locally extracted text with minimized
identifiers and source IDs. Scans need configured Document AI and existing page
admission limits. No bank password is accepted. CSV supports the documented
date/description/debit/credit schema, up to 1 MB/500 rows, without a model call.
At most 10 imports / 2,000 normalized rows / 800 KB per private workspace.
Proposals require user review; exact text matching does not prove correct column
interpretation, completeness or authenticity. A bank-layout benchmark is pending.

Optional separate protection journey: input once → obligation inbox → explicit selected-context sharing → Gemini prepares
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

### My money today (private user-reported diary)

Start with cash before new entries and a positive chosen buffer. Gemini can
propose up to five INR entries from one explicitly shared check-in, selecting
server-owned source IDs rather than writing quotations. Each literal amount
needs exact Decimal equivalence to its printed INR source and explicit direction. This is an
English-cue, today-only convenience path, not general statement parsing or date
inference. Unsupported currencies, future income and ambiguous dates need manual
entry or a future runway scenario. AI proposals never save themselves.

Confirmed writes use an operation identity, expected revision and privacy
generation. SQLite and Firestore transact updates atomically; a same-ID exact
retry cannot duplicate entries, changed-ID payload reuse and stale tabs fail.
Group Undo marks bookkeeping entries undone, never reverses a bank payment.
Exact integer arithmetic shows reported cash, money in/out, net change and
coverage of the user's buffer. Money in is not necessarily earnings or profit.
The meter is not a credit/financial-health score or future-safety guarantee.

Each diary admits 100 entries and 200 changes without silent eviction. Local
download exports all returned entries, including undone entries. Explicit private
input cleanup clears the diary and invalidates pending saves. Chat has independent
unchecked diary consent, shares aggregates without entry notes, and applies the
existing explicit-rupee response gate. No model training, bank feed, notification,
payment permission, borrowing or investment action is added.

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
calculator context as formatted INR strings to Gemini, not raw statements or
individual events. Explicit unsupported rupee figures in a model reply fail closed;
this is not a complete semantic-proof mechanism. Changes
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

Private-context replies check the privacy generation before loading context,
after generation, and after the last freshness read and response assembly.
Changed shared diary, forecast or inbox context rejects the reply; statement
context also checks revision/generation. Regression tests cover cleanup during
the final read even when it returns an older snapshot. General chat does not load
unshared private records. Reloading an unsaved statement preview shows an empty
state and a statement-selection action without changing saved history.

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

Release 0.32.0 test counts, successful CI, exact cloud revisions and live acceptance
are recorded in [CURRENT_RELEASE](docs/CURRENT_RELEASE.json). Historical test and
artificial-payment evidence remains in its dated reports. The original six-call production-path AI smoke run
records 0/6 strict passes, including two genuine extraction rejections and scorer
defects. After the numeric source-fact prompt clarification, both PDFs and all
six follow-up outputs were admitted. Strict original scoring still passes only
1/6; separately versioned finite factual checks pass 5/6. The revised protocol
was authored after observation, not independently held out. Engineering test
passes and these tiny smoke checks do not establish representative fraud/AI
accuracy or certify every feature/device.

## 8. Priorities and non-goals

Before submission: confirm another human login/roster/deadline, independently
review statement labels and evaluate varied unseen statement/chat inputs,
and create required video/deck/materials. Preserve the existing safety boundary.
Implemented hardening includes durable task lifecycle, journal-only recovery,
complete bounded safety snapshots, atomic evidence-version checks and explicit
review/draft retention/deletion. Later: independently authorised providers,
authorised source connectors, complete account erasure and wider governance
operations and native voice. No autonomous real-money access, trading calls,
phone surveillance, production patching or guaranteed reimbursements.

Novelty/patentability and competition awards remain unproven. The BFSI submission
is a functional AI-assisted financial experience and bounded-execution prototype,
not a claimed replacement for banking infrastructure. Review the official
[requirements](https://aibuildercup.com/themes.html) and
[submission checklist](docs/submission/README.md).

# Financial Friday — Architecture guide

Current technical reference: **15 October 2026**, version **0.27.0**. Project name: Financial Friday.
Read the trust boundaries before using execution-capable APIs.

### Primary decision layer

`friday_rehearsal.py` compiles at most six historical bank-account month templates
into baseline and adverse calendar-event scenarios. Integer-paise daily cash
floors feed a suffix-minimum purchase envelope and monotone search for the least
uniform flexible-cost reduction. The checker independently replays each returned
option; source revision/privacy generation bind every calculation. This is
classical finite-scenario robust constraint checking, not a new optimisation
theorem, trained forecasting model or bank authentication system.

Gemini has two separate bounded jobs: interpret a goal into strict fields and
explain server-recomputed result aggregates. Neither job supplies numerical truth
or receives payment tools. Explicit goal interpretation shares no statements;
explicit explanation shares no original descriptions or account aliases. Preview
never calls the model or persists a scenario. The existing statement/private
storage and artificial-payment trust boundaries remain separate. See
[the algorithm and verification report](docs/FINANCIAL_REHEARSAL_0270.md).

### Primary product spine: statement → review → spending picture → guidance

`friday_statements.py` uses strict CSV parsing or bounded PDF text extraction;
scans use the existing Document AI processor and admission budget. Gemini sees
minimized source units, returns row/source IDs and proposed labels; strict models
validate dates, directions, amounts and literal source values. It has no tools.
User review remains necessary: matching source text does not prove the right
column or all rows were read. Raw files/text are not persisted.

`FridayPortfolio` stores explicitly reviewed normalized rows in a tenant-scoped
SQLite record or one bounded Firestore document. Revision and privacy-generation
checks prevent stale writes/resurrection after cleanup. Same-source replay is
idempotent; overlapping different files are warned, not automatically deduplicated.
Reversible exclusions keep the source history but remove selected imports from
aggregates. Exact integer arithmetic separates spending, identified income,
transfers, borrowing/refunds and repayments. The diary and artificial ledger are
separate and never silently merged with statement history.

The primary UI has separate Upload, Review, Spending, Coach and Account views.
The gateway's profile response uses already verified IAP claims only; it never
returns tenant keys, OAuth tokens or unverified identity headers. An existing
Google session can be reused. Statement chat context is an independent opt-in:
only formatted aggregate rupees, coverage warnings and fixed evidence identity
are sent. Transaction descriptions/account nicknames are excluded from that
context. No weights are trained and no personal financial action is authorized.

See [statement-first scope and verification](docs/STATEMENTS_0240.md).

### Checked visual planning

Gemini returns `MoneyPlanDraft`, never executable chart code or money movements.
The server selects the tenant's explicitly shared aggregate snapshot and rejects
a changed revision/privacy generation. A requested amount must occur in the
current user message. The source-month engine minimizes a separable convex
quadratic cost over integer-paise reductions, subject to category caps and locked
essentials/loan repayments. Marginal-cost threshold search avoids per-paise loops;
an independent exchange-condition checker verifies exact totals, limits and
optimality for this mathematical objective, not financial desirability.

Chart.js renders only fixed server-computed series, with exact HTML tables and
no external CDN. Manual `POST /v1/friday/plans/preview` recalculation is private,
revision-bound, unsaved and makes no model call. No new payment or bank permission
is granted. No-income records cannot establish an income-stress conclusion.
See [algorithm, evaluation and limitations](docs/VISUAL_MONEY_PLANS_0260.md).

### Secondary protection spine: financial obligation → checked next step → outcome

The obligation projection joins complete bounded document evidence (up to 1,000
entries) to exact normalized supplier-and-reference artificial provider records.
It distinguishes missing details, conflicting claims, possible prior payment,
rule-constrained tasks, eligible preparation and verified artificial journal outcomes.
There is no fuzzy merchant authentication and no fraud probability.

Gemini receives selected-obligation context only after explicit consent, prepares
an explanation/verification draft or exact supported bill, and cannot substitute
another financial obligation. Saved rules and an evidence-version binding accompany
the signed task. Existing independent gates recheck full evidence, provider state,
permission and balance during execution. Recorded outcome lookup is read-only,
verifies the receipt against the current bill and signing key, and never calls
Gemini or retries a payment. Uploaded receipts cannot satisfy this check.

This is the central demonstrable benefit: less repeat input and a coherent next
step, with a checked outcome. Real provider integration, recipient ownership,
external settlement, customer adoption and independently measured accuracy remain
unproven. New connectors require independent authorisation—not new UI badges.

Do not describe every historical CARAPACE idea as part of today's product. This
repository evolved substantially; current documents take precedence over old pitches.

## 1. Links and what to read

- Repository: <https://github.com/Santxsh27/financial-friday>
- Live app: <https://financial-friday-web-171681243260.asia-south1.run.app/#home>
- Short tour: [START_HERE.md](START_HERE.md)
- Every control: [USER_GUIDE.md](USER_GUIDE.md)
- Current contract: [SPEC.md](SPEC.md)
- API inventory: [docs/API_MAP.md](docs/API_MAP.md)
- Setup/change process: [CONTRIBUTING.md](CONTRIBUTING.md)
- Current release/evidence: [docs/CURRENT_RELEASE.json](docs/CURRENT_RELEASE.json)
- All reports and historical scope: [docs/REPORTS_INDEX.md](docs/REPORTS_INDEX.md)
- Money Runway: [docs/MONEY_RUNWAY_0220.md](docs/MONEY_RUNWAY_0220.md)

The GitHub repository is private. Collaborators must be invited using their own
GitHub accounts; a link is not access permission. This does not change website
Google sign-in or authorise cloud administration. Do not share owner tokens.

Google sign-in does not link a bank. Each visitor gets an isolated workspace;
the owner's records are not the visitor's starting data. Some managed accounts
may be blocked by their organisation. A second real-human access test remains a
team acceptance task; do not claim all possible accounts were tested.

## 2. Why Google AI, and what the competition actually asks

The chosen theme concerns financial risk, fraud, useful financial experiences and
process automation. Friday addresses evidence discrepancies, safer delegation,
document intelligence and customer assistance rather than promising universal
fraud detection. The official requirements call for meaningful Google AI and a
working Google Cloud deployment, not every suggested service.

| Judging area | Weight | Evidence we should show |
| --- | ---: | --- |
| Technical and generative-AI execution | 40% | Real unfamiliar input, typed extraction/planning, functioning APIs and independent checks. |
| Relevance and impact | 25% | A person understands or resolves financial admin with fewer mistakes. Quantify actual benefit. |
| Originality and creativity | 25% | The evidence-to-constraint-to-outcome combination and a measured comparison, not a new name for a chatbot. |
| Usability and design | 10% | Clear starting tasks, visible states, useful next actions and accessible interaction. |

Sources: [official themes/requirements](https://aibuildercup.com/themes.html),
[public timeline/eligibility](https://aibuildercup.com/), checked 14 October.
The public dates say team formation by **14 October** and prototype submission by
**18 October 2026**, with finalists announced 7 November and the Singapore finale
4 December. Public eligibility lists 2–4 members, age 21+, JAPAC and working
professionals rather than students. Confirm the actual dashboard roster and cutoff;
we have not verified account-specific eligibility or submission status here.

The submission needs the functional cloud prototype, a proposal deck converted to
PDF, English materials and a public approximately three-minute demo video link.
The dashboard is the authority for its precise fields. Selection, awards and
patentability cannot be guaranteed by a specification or test count.

## 3. Product scope: three different trust levels

| Level | Evidence | Permitted outcome |
| --- | --- | --- |
| Conversation | General knowledge or opt-in bounded workspace snapshot | Explanation, checklist, unsent message and a suggested page. No execution. |
| Financial review | User-supplied documents/CSV | Compare claims, show conflicts and prepare a verification message. No payment. |
| Sandbox operator | Server-owned test-provider record + saved permission + exact goal | A restricted, verified artificial-money operation or a hold. Not a real-bank transaction. |

Matching a bill and receipt is useful, but two matching user claims can both be
false. The same-operator test provider is more structured than uploaded text,
yet is not an independently authenticated utility or bank. Never merge these
levels silently.

## 4. Complete architecture

```text
Google user
    |
    v
Identity-Aware Proxy (IAP)
    |
    v
Cloud Run web service: HTML/CSS/JS + authenticated proxy
    | derive tenant from verified identity; keep credentials server-side
    v
Private Cloud Run API: Python / FastAPI / Pydantic
    |
    +-- Chat -> bounded Gemini answer -> schema/citation checks -> safe text
              -> typed goal -> protected-first integer allocation
              -> independent constraint/optimality checks -> charts + exact tables
    |
    +-- Review -> Gemini facts -> exact reconciliation -> private evidence inbox
    |
    +-- Money Runway -> exact cash-flow scenario -> optional latest private memory
              -> separate chat consent -> formatted INR context -> Gemini explanation
              -> explicit-amount/citation gate; no payment or model training
    |
    +-- Explicit sandbox task -> immutable goal + provider evidence
              -> Gemini program -> verifier -> bounded repair/challenges
              -> permission/reserve recheck -> restricted atomic executor
              -> signed receipt -> independent outcome replay
    |
    +-- Firestore cloud state / SQLite local state

Cloud Build -> Artifact Registry -> Cloud Run revisions
Secret Manager + service identities -> server-held keys/credentials
```

Frontend is plain HTML/CSS/JavaScript composed in Python modules; there is no React,
Next.js or separate Node frontend build. Node is used for optional presentation
tests. Python supports 3.11+, the container runs 3.12. FastAPI/Uvicorn serve the API;
Pydantic performs validation; Google Gen AI SDK calls Gemini; `cryptography`
provides signing; Docker Compose gives a repeatable local environment.

Both Cloud Run services and Firestore are configured for the project's Mumbai
deployment. Gemini requests use the configured `global` model location; do not
claim every data-processing operation stays in India. We are India-oriented in
currency/examples, not certified as legally compliant in every financial setting.

## 5. Workflow A — useful chat without records

1. User clicks **Understand a charge**. Only the question field changes.
2. **Ask Friday** calls the web proxy, then `POST /v1/friday/chat`.
3. Server validates message length, history roles and strict context consent.
4. A bounded request goes to Gemini; there are no model tools or arbitrary URLs.
5. Output must contain a reply, valid available case citations and an allowlisted
   navigation suggestion. Extra authority fields/invalid references are rejected.
6. UI renders text, not model HTML. Requested drafts use placeholders and remain
   unsent. API reports `actions_executed: []` and no money moved.

Context is off by default. With consent it contains at most ten cases from the
latest fifty review inputs, separated currency totals and artificial balance/reserve.
It is not a complete bank statement. There is no Anthos database lookup in chat.
History is kept only in page memory, with at most eight previous turns in a request.
Changing consent clears that history. Google still processes the prompt under the
chosen service's policies; “not saved by Friday” is not “never processed elsewhere.”

Private communication preferences and saved cash-flow context have independent
strict consent flags. Cash-flow context contains aggregate calculator results,
not raw statements or individual dated events. Amounts arrive as formatted INR
strings; unsupported explicit rupee references fail closed. This reduces a real
unit-error shape, not every semantic mistake. Consent changes clear page history
and late responses cannot restore it. Context memory is not model tuning.

Limits: 1,600-character messages/replies, schema-validated output, one generation
per chat request. Recognisable secret patterns are scrubbed best-effort, not full DLP.
No current-news browsing, stock feed, trading recommendation or continuous monitoring.

## 6. Workflow B — bill, receipt and discrepancy review

1. User loads editable example text or explicitly uploads a redacted document.
2. Text review uses `/v1/friday/reviews`; files use `/reviews/documents`.
3. Gemini extracts document kind, money direction, issuer, invoice reference,
   transaction reference, totals, currency, payee, dates, line items and quotations.
4. Pydantic validates facts. Text quotations must occur in the original text.
   The configured basic Mumbai Document AI processor independently anchors
   image/PDF claims to OCR text and page/line evidence. One-to-three-page PDFs and
   a shared daily admission limit bound use. Missing/unsupported fields stay
   unverified; OCR does not authenticate an issuer or recipient.
5. Exact code checks decimal precision and printed arithmetic, groups supported
   identities and detects conflicting totals/payees/payment references.
6. Records are saved privately and the inbox shows evidence plus a verification
   draft. It does not submit that draft, a complaint, a refund or a payment.

PNG/JPEG/WebP/PDF inputs are bounded to 8 MB; review text to 12,000 characters.
Supported explicit currencies include INR/USD/EUR/GBP/AUD/SGD/JPY. A bare dollar
sign is ambiguous; currencies are not converted or combined. Reference and
transaction reference have different meanings. Incoming credits do not pay bills.
Normal artificial-example disclaimers are not themselves prompt injection.

Content hashes deduplicate within a tenant; raw uploads are not stored by Friday,
but extracted facts, quotations, filenames, hashes and provenance persist. Users
must redact secrets before uploading; no blanket promise of automated document
redaction is made. Retention/deletion governance needs further work.

Important states: `BILL_TO_VERIFY`, `RECEIPT_MATCHED_CLAIM`,
`RECORDED_PAYMENT_CLAIM`, `CONFLICT_REVIEW`, `INCOMPLETE_REVIEW`.
These are review outcomes, not fraud convictions or settlement confirmations.

The statement-import option requires explicit storage consent, accepts up to twenty
INR rows below 1 MB, parses claims deterministically and does not call Gemini.
Spending analysis is a distinct read-only flow; use its coverage limits rather
than assuming it represents all the customer's money.

## 7. Workflow C — bounded artificial-money execution

1. An operator/user publishes a fresh test-provider bill with a reference, payee,
   amount and date. Its record is not an actual utility balance.
2. User reviews the bill and saved mandate. Defaults protect ₹10,000, cap one
   automatic payment at ₹5,000, permit zero fees and disable automatic execution.
   A new artificial account starts with ₹50,000; saving rules must not reset it.
3. The reviewed bill digest binds what was displayed. Gemini interpretation must
   match the selected reference, amount, currency and recipient exactly.
4. An immutable `FinancialGoal` and separate `FinancialEvidence` bound the task.
5. Gemini emits a `FinancialProgram`, not executable source code.
6. The deterministic verifier checks the proposed financial effects. Invalid
   proposals receive safe error codes for one bounded plan-repair attempt.
7. Mutations probe the same guard, then current provider/rules/reserve are checked
   again before the transaction. An explicit action may execute in saved authority.
8. The executor atomically journals artificial balance, payment identity, receipt
   and run outcome. Repetition consults the original identity instead of paying again.
9. A read-only reopening recomputes safety checks, verifies signatures and checks
   the receipt against the journal. Stored green flags are not trusted as proof.

Home chat and default review never call this executor. The alternate original
artificial-payment mode and explicit handling/approval controls can. Do not call
an intake path that may automatically execute merely to create a conversational
draft. The new task preparation path respects this constraint; only its explicit
confirmation endpoint can enter the existing executor. See [FRIDAY_TASKS](docs/FRIDAY_TASKS.md).

## 8. Algorithms and what the “security” actually is

- **Restricted program language:** normal payment order is
  `VERIFY_PROVIDER -> LOAD_OBLIGATION -> CREATE_ONE_TIME_PAYMENT -> CONFIRM_RESULT`.
  An unknown prior outcome allows `RECONCILE_EXISTING -> CONFIRM_RESULT`, not a new
  payment. The schema includes a recurring verb for negative tests, but this
  one-time goal rejects it.
- **Independent verifier:** compares provider/payee, options, authenticated test
  evidence, exact total/fees, cadence, data fields, evidence IDs and action ordering.
  It checks bounded contracts, not a universal formal proof of financial safety.
- **Mutations:** alter amount, recipient, data disclosure, recurrence, repeated
  action and final confirmation. This is targeted robustness evidence, not a
  complete adversarial evaluation. The unknown-outcome branch has its own retry test.
- **Reserve planning:** exact Pareto-frontier dynamic programming prioritises bill
  counts on earlier deadlines, then lower spend. Bound: 32 candidates/10,000 frontier
  states; missing/truncated records and limits fail closed. It is not AI arithmetic
  or a proven globally optimal personal-finance strategy.
- **Receipts and replay:** Ed25519 signatures bind identity/evidence; canonical
  hashes bind snapshots; idempotency and atomic storage prevent duplicate effects
  inside the implemented boundary. Signatures alone do not prove a truthful bank.
- **Outcome uncertainty:** check the original operation before retrying. A local
  database rollback cannot undo an external provider payment.

The implementation combination is our differentiator. Schemas, signatures,
dynamic programming, idempotency and AI-plus-checker designs are known techniques.
World-first novelty or patent approval requires evidence we do not currently have.

## 9. Storage, identity and deployment

Cloud state is `FIRESTORE_TRANSACTIONAL`, local state `SQLITE_LOCAL`. Firestore
collections under each tenant store mandates, accounts, provider bills, signals,
dynamic cases, runs, payments, idempotency and reviews. Atomic payment commits
revalidate current permission/provider state. The workspace preview is bounded
and non-atomic; execution must not trust it as a reservation.
Buddy preferences, follow-up memory, privacy generations, prepared tasks and the
latest optional cash-flow snapshot are also tenant-scoped. Review cleanup clears
follow-ups and the saved runway plan; payment journals are retained.

IAP verifies Google identity. The web gateway derives stable visitor identities
and credentials using domain-separated HMACs from a server secret; browser headers
cannot choose another tenant. The API is private; the web service invokes it using
its service identity. Owner mappings and public visitor workspaces are distinct.
Signing/enrolment secrets are server-held; no bank password belongs in a model.

Public visitor quotas: 20 write/action requests per user/day and 200 globally;
1,000 reads/user/day and 10,000 globally, plus minute/burst limits. They count
admitted requests, not dollars or model tokens; failed downstream calls still use
admission. UTC daily reset is 5:30 AM India time. Budget alerts do not stop billing.

Actual deployed source, revisions and image digests are in
[CURRENT_RELEASE](docs/CURRENT_RELEASE.json). Code version `0.18.0` adds the
[hardening boundaries](docs/HARDENING_0180.md). Docs/CI commits do not automatically
change images. Local/cloud state is
separate. Do not copy owner credentials, private data or local SQLite into a pilot.

No auto-deployment from GitHub is configured by this handover. Cloud builds and
revision promotion are deliberate steps; preserve IAM, origin restrictions,
secrets and rollback revisions. Finite trial credits are not free hosting forever.

## 10. Implementation status and limitations

| Area | Status |
| --- | --- |
| Live cloud chat/document review | Implemented and observed with Gemini/Vertex. |
| Guided example and evidence inbox | Implemented; bill, matching claims and recipient conflict observed. |
| Artificial ledger/permission/verifier/replay | Implemented; unit/integration and recorded live checks. |
| Current UI | Compact assistant, task starters, separate pages, theme/sound/motion preferences. |
| Conversation-to-approved-task bridge | Implemented as a separate prepare/review/confirm workflow; plain chat remains guidance only. |
| Semantic financial-risk analysis | Live Gemini quoted findings; exact source checks and separate claim/provider holds. Not a trained/calibrated fraud classifier. |
| Cloud biller follow-through | Returns `UNAVAILABLE / CLOUD_CONNECTOR_NOT_IMPLEMENTED`. |
| Local acknowledgement | Signed local bookkeeping only; not external biller correction. |
| Bank/biller resolution kernel | Tested proposal logic; no live correction/refund provider connected. |
| Anthos | Removed from customer navigation; optional historical fixture only. |
| Background inbox | Local sample feed remains a demo. Cloud Tasks performs authenticated journal-only recovery; it is not continuous bank/bill intake. |
| Voice | Earlier browser/transcript experiments; no native Gemini Live/Agora voice product. |
| Real banking, wallets, utilities, Gmail/SMS | Not connected. Requires authorised APIs, consent and provider onboarding. |
| Independent OCR | Basic Mumbai Document AI processor is live and tested with independent text/page anchors. Unsupported fields remain unverified; OCR does not authenticate an issuer. |
| Durable task lifecycle | Signed leases, state/run reference and journal-only reconciliation implemented; not automatic cloud crash resumption. |
| Privacy / key rotation | Manual review/draft cleanup, in-flight cancellation and trusted historical public-key ring support. Payment journal retained. |
| Buddy preferences | Private communication choices, separately consented; never financial authority. Nickname stays out of model prompts. |
| Follow-up memory | Private tracking/waiting/recheck/close states; new evidence resurfaces a closed item. No external send or settlement claim. |
| Money Runway | Exact user-assumption forecast, daily cap and delayed-income comparison; optional private snapshot and separately consented AI explanation. No bank feed or external alerts. |
| Dataset learning | Personal context memory implemented; reference RAG and fine-tuning are not implemented or automatically authorised. |
| Cloud Tasks recovery | Approved keyless callback identity and low-rate queue; actual callback and no-repeat artificial debit verified. |
| ADK, BigQuery, Model Armor, Cloud KMS signing | Not implemented; add only for a specific demonstrable need. |

Never claim guaranteed fraud detection/reimbursement, safe merchants, all banks
supported, every fault repaired, production autonomous patching or legal compliance.
Protecting signing keys, external provider authentication, account deletion/retention,
operational resilience and regulatory review remain production concerns.

## 11. Verification and what it proves

Historical pre-statement checks: 526 native tests (525 pass/one skip), 526 Docker tests
(503 pass/twenty-three skips), 24 tooling tests. The extra optional skips are
Node-only motion runtime checks. GitHub Python 3.11/3.12 and Docker
checks passed for the Money Runway release. Twenty-two runway tests cover exact
caps, timing, opt-in privacy, tenant isolation, cleanup races and AI unit guards.
Real Vertex acceptance initially exposed a 100× unit error; that zero-traffic API
was not promoted. The corrected API passed Firestore save/readback/cleanup and
an explanation with exact INR caps; public browser calculation also passed.
See [Money Runway evidence](docs/MONEY_RUNWAY_0220.md) and the release manifest.

Earlier live tests used a fresh synthetic
visitor with saved artificial rules: Vertex prepared a task, held a refund
contradiction, moved artificial funds only after confirmation, prevented a second
debit and independently verified the outcome. See the
[release record](docs/FRIDAY_TASK_RELEASE_1013.md).

Tests include auth/tenant isolation, schemas, currency/arithmetic, tampered evidence,
reserve/permissions, concurrency/idempotency, signatures, replay, model outages,
review safety and JavaScript presentation. Mock tests are not live AI accuracy.
Earlier proposal corpora and 16-case evaluations are small engineering probes, not
a representative fraud benchmark or a measured comparison with plain Gemini.

The prior remote CI failure was the historical Anthos job, which did not start its
now-optional database. This handover retains core/container testing, adds the
standalone page check and makes that historical fixture manually selectable.
Check [Actions](https://github.com/Santxsh27/financial-friday/actions) for the actual
new run result rather than inferring a remote pass from local tests.

## 12. Engineering priorities and acceptance criteria

**Implemented task milestone:** a prepare-only conversation tool creates
an expiring tenant-bound task from an exact provider record and reviewed digest;
the customer confirms it through the existing gate; result readback uses the
existing signed journal. No text response or model-provided boolean is authority.
Cases to test: changed provider/rules, wrong tenant, expired draft, duplicate
confirmation, model injection/outage and external outcome uncertainty.

Other immediate tasks: second human sign-in, varied unseen-document evaluation,
latency/cost measurement, a short coherent demo and required submission artifacts.
Do not pivot the idea or add extra services merely to make the diagram larger.

Use a branch and reviewed changes in this repository. Never share cloud secrets
or grant owner-level access merely to review the application.

## 13. File map for a developer

| Responsibility | Main source |
| --- | --- |
| Typed program and guard | `src/carapace_core/financial_friday.py` |
| Mandate/provider/input schemas | `src/carapace_core/friday_live.py` |
| Bill optimisation | `src/carapace_core/friday_bill_plan.py` |
| Claim matching/arithmetic | `src/carapace_core/friday_review.py` |
| Statement analysis | `src/carapace_core/friday_statement.py` |
| Cash-flow calculation/private memory | `src/carapace_core/friday_cashflow.py`, `src/carapace_api/friday_cashflow.py` |
| Cash-flow UI | `src/carapace_integrations/friday_cashflow_ui.py` |
| Presentation-only interaction motion | `src/carapace_integrations/friday_soft_flow.py` |
| Signed outcome replay | `src/carapace_core/friday_assurance.py` |
| Gemini planner | `src/carapace_ai/financial_friday.py` |
| Gemini review/chat | `src/carapace_ai/friday_review.py`, `friday_chat.py` |
| API/execution service | `src/carapace_api/financial_friday.py`, `financial_friday_routes.py` |
| Review service/durable state | `src/carapace_api/friday_review.py`, `friday_durable.py` |
| Reviewed-bill gate | `src/carapace_api/friday_bill_handle.py` |
| Cloud identity/quotas | `src/carapace_integrations/friday_cloud_web.py`, `src/carapace_core/friday_access.py`, `src/carapace_api/friday_public_quota.py` |
| UI composition | `src/carapace_integrations/friday_experience.py`, `friday_everyday.py`, `friday_review_ui.py`, `friday_chat_ui.py` |
| Deployment/test configuration | `compose.yaml`, `Dockerfile`, `Dockerfile.web`, `cloudbuild*.yaml`, `.github/workflows/ci.yml` |

Preserve unrelated local edits; do not reset them. Historical
CARAPACE graph, release-passport and Anthos experiments are not the default Friday
customer workflow. See CONTRIBUTING for the safest starting commands.

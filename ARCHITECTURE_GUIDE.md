# Financial Friday — architecture guide

Current reference: 17 October 2026, goal/research expansion 0.35.0.
[SPEC](SPEC.md) defines the contract; [CURRENT_RELEASE](docs/CURRENT_RELEASE.json)
identifies the actual source commits, container digests, revisions and verification.
Earlier dated reports describe history, not additional current consumer features.

## Product boundary

Friday turns supplied INR bank/card statements into reviewed history, exact charts,
source-linked review candidates and optional Gemini guidance. Its main journey is
**Home → Add statement → Review → My money → Ask Friday**. Statements selects the
source set; Listen opens separately consented speech; the top-right account menu
shows the verified sign-in and privacy controls. Back returns from detail views.

There is no consumer bill inbox, real bank feed or payment execution. A repeated
row is a candidate for review, not a verified duplicate debit. Refund worksheets
do not establish entitlement or recover money. No personalised securities calls,
guaranteed savings, universal safety or bank authentication are claimed.

## Goal/research boundary

`friday_goals.py` is a pure shared-pool purchase-scenario calculator. Quote-bound
`friday_goal_intake.py` supplies reviewed proposals only. `friday_research.py`
uses explicit public Google Search grounding separately from private records and
ordinary chat. `friday_goals_ui.py` supplies goal cards, charts, tables and
sandboxed Search Suggestions. There is no server goal persistence or background
market polling. Details and limitations: [0.35 report](docs/GOALS_RESEARCH_0350.md).

## Runtime and deployment

```text
Browser — HTML / CSS / JavaScript, local Chart.js + accessible tables
  │
  ├─ Google sign-in / Identity-Aware Proxy
  │
Cloud Run web gateway — verified visitor identity and same-origin admission
  │ authenticated invocation; backend credentials never reach the browser
Private Cloud Run API — Python / FastAPI / Pydantic
  │
  ├─ CSV adapters ──────────────┐
  ├─ PDF text / Document AI OCR ── Gemini typed extraction
  │                            │
  ├─ Literal source checks + exact integer-paise reconciliation
  ├─ Signed extraction receipt + explicit user review/save
  ├─ Firestore private portfolio / source revision / privacy generation
  ├─ Deterministic summaries / checkup / refund bounds / checked plans
  └─ Consented Gemini conversation or speech → validated UI result

Cloud Build → Artifact Registry → staged Cloud Run revision → acceptance → traffic
IAM / IAP / Secret Manager → existing scoped identities and server-held secrets
```

The frontend is composed by Python integration modules, not React/Next.js. Python
supports 3.11+; Docker runs 3.12. Google Gen AI SDK calls Vertex; pypdf reads bounded
PDFs; cryptography supplies Ed25519 signing. Node enables presentation tests, not
a separate production frontend service. Local Docker uses SQLite and loopback
ports 8080/8090. The historical Compose name `anthos-demo` runs Friday's standalone
web process; Bank of Anthos is not a product dependency.

Cloud Run/Firestore use the existing Mumbai deployment. Gemini's configured model
location is global; OCR can use its configured non-India location. Do not claim
all processing stays in India. No ADK, BigQuery, Vertex AI Search, Agora, native
Gemini Live, Model Armor, Cloud KMS signing or fine-tuning is implemented.

## Statement ingestion and source truth

`friday_statement_csv.py` recognises finite supported tables, explicit debit/credit
headings, metadata preambles, encodings, date and INR amount forms. It rejects
ambiguous tables/rows without a partial save. The five artificial bank-format
samples test these adapters; they are not a universal bank-export guarantee.

`friday_statements.py` supplies bounded PDF source units to Gemini for typed rows
and literal references. Supported scans use Document AI OCR. Models have no bank
or execution tools. Strict validation rejects unsupported dates, amounts,
directions and references. Raw files/text are not archived; reviewed normalised
rows and minimal source-check evidence are saved only after confirmation.

`friday_statement_reconciliation.py` checks available printed totals, row counts,
page coverage, opening/closing equations and running balances with integer paise.
Printed facts and derived checks stay distinct. Missing facts remain unknown;
bank-account and credit-card balance semantics are not interchangeable. Matching
arithmetic does not prove document authenticity or completeness.

`friday_statement_receipt.py` domain-separates the existing Ed25519 signer. The
extraction receipt binds immutable row values, source, tenant and privacy
generation; user-reviewed meaning/category labels remain editable. Save verifies
the receipt and recalculates checks. This is Friday's signature, not the bank's.

## Portfolio, source selection and concurrency

`FridayPortfolio` holds a bounded tenant-scoped SQLite record locally or Firestore
document in cloud. All derived views use the same selected imports. Selection
submits the complete inclusion set with expected revision/generation. Atomic
transactions reject stale or unknown sources instead of silently overwriting.

Start a new review excludes earlier imports; it does not delete them. Restore
selects saved sources without re-upload. Same-source replay is idempotent, while
overlapping different exports require warnings/review, not guessed deduplication.
Privacy cleanup changes the generation. AI responses and derived artifacts are
freshness-checked so late work cannot restore an older private workspace.

Real synthetic Firestore acceptance exercised concurrent selections (409/200),
restoration and cleanup. Unit-injected transaction aborts and privacy races are
separate evidence; they are not claimed as forced live provider failures.

## Analysis and independently checked calculations

- `friday_checkup.py`: source-linked repeated-entry, recurring-pattern and change
  candidates using exact groups, bounded regularity and statistical/rule thresholds.
  These are explainable heuristics, not a trained fraud classifier.
- `friday_assistance.py`: up to eight source-bound private work items from the
  checkup; review/reopen changes acknowledgments, not source transactions.
  `friday_workbench_ui.py` presents one task and an actual category chart.
- `friday_refund_shield.py`: bounded bipartite max-flow/min-cost-flow allocation
  ranges, independently checked for capacity, conservation and residual conditions.
  Ambiguity remains visible; the calculation does not establish bank linkage.
- Checked visual planning: protected-first integer allocation, marginal-cost
  threshold search and independent constraints/exchange-condition checks. Optimal
  for the stated mathematical objective is not optimal financial advice.
- `friday_rehearsal.py`: finite source-month cash-floor scenarios, suffix-minimum
  envelopes and checked alternatives. Historical scenarios are not predictions.

Money uses integer paise throughout. Charts receive fixed server-computed series;
the model never supplies executable chart code, SQL or arbitrary tool calls.

## Conversation, speech and authority

`friday_chat.py` interprets a question and selects a strict supported visual,
explanation, checked plan or unsent enquiry. General questions require no private
context. With separate consent, the model receives bounded aggregate totals,
coverage warnings and permitted finding references—not transaction descriptions
or account nicknames. Amount/reference and destination allowlists are checked.
Conversation history stays in page memory; consent changes clear it.

Consumer admission rejects retired bill-inbox sharing before model/storage reads.
The server supplies statement-only system scope and normalises old typed
destinations to supported pages. A model reply never grants financial authority.

`friday_speech.py` generates an explicitly consented aggregate briefing through
Vertex with freshness checks, strict narration, PCM validation and a 30-second
cap. The UI provides transcript and manual Play; no live microphone, automatic
playback or saved audio is implied. Speech identity/fidelity is not independently
certified by unit tests.

## Security, operations and retained legacy code

IAP verifies Google identity. The web gateway derives an isolated workspace and
invokes the separately private API with its service identity. The current policy
admits authenticated Google users, but an organisational account can impose its
own restrictions. A second person's full login is still a human acceptance gate.
Private GitHub source requires invitation; the hosted walkthrough does not.

Same-origin guards, strict schemas, finite uploads/routes, tenant checks,
revision/generation checks and existing quotas remain in force. Opaque request
IDs correlate gateway, API, model and calculation events. Content-free logs record
bounded timings, model/version, available tokens and failure categories, never raw
statements, identifiers or prompts. Alert delivery, exact per-user billing and
continuous availability are not established.

`friday_surface.py` allowlists consumer HTTP admission. Legacy assurance,
artificial-payment and obligation modules remain for history/tests behind explicit
opt-in. They are not a separate process/IAM-isolated stack. Cloud Tasks retains a
narrow historical journal-recovery target; it was not redirected or expanded.
Do not describe old payment demonstrations as today's consumer functionality.

## Verification and remaining gates

Use [the release report](docs/SUBMISSION_READINESS_0340.md) for tests, skips,
synthetic live calls and deployment evidence. The authored 39-case candidate
benchmark still has false warnings/misses; it is not independently validated.
The small Gemini study preserves failed checks and follow-ups, not a universal
accuracy claim. [Validation handoff](docs/VALIDATION_HANDOFF.md) explains the
remaining independent work.

[The submission checklist](docs/submission/RELEASE_CHECKLIST.md) covers the
second-person access check, private source delivery, exact dashboard cutoff,
eligibility/roster, proposal PDF, public video and final form acknowledgment.
Technical checks do not guarantee an award or complete those human actions.

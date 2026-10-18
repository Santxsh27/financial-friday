# Financial Friday technical specification

Conversation-first roadmap 0.36.0 over the statement/research consumer foundation.
Deployment identity, source commits, verification and remaining gates are recorded
in [CURRENT_RELEASE](docs/CURRENT_RELEASE.json), not inferred from this document.

## 1. Product and authority

Financial Friday is an INR financial decision workspace: describe a purchase,
savings or reserve goal, confirm proposed facts, track a cash-only roadmap and optionally research
public information through Friday. Supplied bank/card statements provide a separate
reviewed spending picture. The two main journeys are **Home → Goals → Confirm →
Visual roadmap → Report savings**, and **Add statement → Review → My money → Ask Friday**.

It is not a payment processor, bank feed, settlement witness, investment adviser,
official credit score or continuously listening assistant. It cannot pay, reverse,
recover funds, cancel subscriptions, submit complaints, change bank records or
guarantee savings. A finding means review may be useful, not fraud was proved.
The separate bill/receipt inbox is not part of the consumer release.

## Saved priority roadmap (0.36.0)

The default Goals screen uses Friday's existing chat, starter intents, one missing
number at a time and graphical output. Purchase, savings and emergency-reserve
goals use one confirmed cash budget. Historical statement budget proposals are
local averages of supplied months, explicitly accepted, never current cash.
Potentially overlapping imports suppress these proposals. Year-only requests
propose a December date, disclosed before save. Horizons are bounded to 1–60 months.

Integer-paise calculation excludes the protected reserve for purchase/savings,
fills an underfunded reserve first, counts current liquid savings for a reserve
goal, and reports a monthly step, capacity gap, baseline/stress path and milestones.
No returns or future savings are assumed. Passing time cannot increase actual
progress. A reserve is not a complete assessment of financial stability.

One active priority avoids allocating one pot twice. Replacing it requires
confirmation; up to five previous snapshots are archived. Limits: 100 progress
reports and 200 changes. ADD is additional user-reported savings, not bank proof.
UNDO marks a specific report inactive. Every mutation requires tenant credentials,
strict confirmation, expected revision, privacy generation and an operation ID
bound to its payload. SQLite/Firestore transactions enclose changes. Cleanup
invalidates stale writers and clears goals and archives. Export preserves them.

Gemini intake receives only opted-in user text; numeric source quotes are checked,
but semantic correctness is not proved. Missing facts remain unknown. Goal coaching
uses a separate include_roadmap chat opt-in, with saved assumptions and exact
summary/milestones only. INR amounts, citations and context freshness are checked.
AI never writes goals or authorises money. No new IAM/queue/bank access is needed.

Routes: GET goals/roadmap, goals/export, goals/budget-hints; POST goals/conversation,
goals/roadmap-preview, goals/roadmap; existing POST chat. Existing quotas remain.

## Advanced calculator and public research (retained from 0.35.0)

The collapsed Advanced calculator offers one explicitly confirmed budget for up to three
purchase targets over 1–60 months. A pure integer-paise earliest-deadline-first
engine excludes/tops up the selected buffer, allocates savings once, estimates
monthly-rounded financing, checks peak overlapping repayments beyond purchase
deadlines and computes baseline/adverse scenarios. It is not
an optimal financial strategy, return forecast, investment selection or loan
approval. Fees, future recurring costs and prices are user assumptions, not
automatically researched inputs. These advanced scenarios remain in page memory,
separate from the saved priority roadmap; export is explicit.

Gemini goal intake receives only the supplied text after consent. Every proposed
number must bind to a literal quote, including supported lakh/crore conversion;
missing fields stay unknown and require review. No statement-derived income or
personal facts are inferred into a plan. Research is a separate consented public
question/topic, with no private portfolio/preferences/history reads. Provider
grounding sources and Google Search Suggestions are required. Output is sourced
model text, not an independently checked market feed or personalised investment
advice. Suggestions render unmodified in a script-disabled sandbox with an outer
new-tab base target. Other output uses text nodes, not model HTML.

Authenticated read-only endpoints: POST /v1/friday/goals/interpret,
/goals/preview and /research. Existing visitor method quotas apply. The separate
tools do not give ordinary chat browsing or payment authority. See
[the full extension report](docs/GOALS_RESEARCH_0350.md).

## 2. Statement inputs and extraction

Supported input: INR bank/card PDF or CSV, not a screenshot/image bill upload.
PDFs are limited to 4 MB, six pages and 200 proposed rows. CSVs are limited to
1 MB and 500 rows. The workspace holds at most ten imports and 2,000 saved rows,
including excluded sources. Larger exports need careful splitting.

CSV adapters identify one explicit transaction table, recognised headings and a
bounded known preamble. Comma/semicolon/tab layouts, UTF-8/BOM-marked UTF-16,
finite day-first four-digit-year dates and valid INR amount spellings are supported.
Separate debit/credit roles are required. Unknown financial headings, ambiguous
columns, unexplained rows, bad encodings or invalid directions reject the import;
no partial rows are saved. These finite adapters are not universal bank support.

PDF text is read with pypdf. Supported scans need configured Document AI OCR.
Gemini on Vertex AI proposes typed rows and literal source references. Amounts,
directions, dates, source units/pages and supplied facts are validated. Encrypted
PDFs must be unlocked locally; Friday never requests the password. Cloud processing
requires explicit consent and can fail. Raw uploads are not archived.

Every public sample is artificial and labelled. HDFC/Kotak illustrations inform
two layouts; ICICI is an explicitly unverified candidate. Generic stress cases
do not impersonate a bank. No searched customer records form a training corpus.
No model fine-tuning was performed.

## 3. Source facts and exact reconciliation

Money calculations use integer paise, not floating-point rupees. Source claims
remain separate from derived checks. A printed opening balance is not income.
Missing controls remain UNKNOWN; they are never replaced with convenient zeros.

Checks cover printed debit/credit totals, transaction count, physical/printed page
coverage, opening-to-closing arithmetic, running balances and detected dated-row
coverage. Balance arithmetic requires an explicit account-appropriate direction
and established ordering. Bank balance and card amount-due semantics are separate.
Extraction assertions alone do not prove that a statement is complete.

A domain-separated Ed25519 extraction receipt binds Friday's tenant, privacy
generation, source hash, parser/account type, minimal source facts and immutable
row fields. Reviewed category/meaning labels are deliberately editable. Save
verifies the receipt and recalculates checks. Changed source amounts/dates,
forged receipts, wrong tenants and old generations are rejected. Known source
mismatches block saving. Unknown coverage remains visibly qualified.

Friday's receipt is not bank authentication, payee ownership or settlement evidence.

## 4. Reviewed history and source selection

Stored imports contain source identity, user nickname/account type, normalised
rows, minimal evidence references, extraction status and reconciliation metadata.
Aliases are not account identifiers. Users review classifications before saving.
The library displays aliases/types, date ranges, row counts and short source hashes.

All derived views use one selected source set. Atomic selection requests contain
the full inclusion list plus expected revision and privacy generation. SQLite uses
a transaction; cloud uses the existing Firestore transaction callback. Stale or
unknown sources fail without silent overwrite. No-op selection does not advance
the revision. Confirmed re-import of an excluded identical source restores it only
against current state, without duplicating its rows.

Start a new review excludes all earlier sources atomically; it does not delete
them, reviews, diary records or financial journals. Imports remain available to
restore without re-upload. Actual privacy cleanup is separate and explicit.
Source changes invalidate derived plans, chat and speech freshness.

Same-source replay and overlapping exports are different problems. Friday must
not silently discard all similar rows: identical-looking transactions can be
legitimate. Warnings and review candidates remain visible and qualified.

## 5. Analysis and prepared work

Exact summaries separate proposed income, expenses, borrowing, transfers, refunds
and repayments. CSV classifications are local editable proposals, not a trained
model. A net-flow total is not a live bank balance, net worth or complete debt view.

CHECKUP_2 uses bounded literal UPI/NEFT/IMPS/RTGS narration grammars and documented
heuristics for repeated entries, regular payments, increases, outliers, fees and
changes. Account nickname/type scope every match. Unsupported narrations use
literal fallback; masked identifiers are not recovered. Findings retain evidence,
versioned identity, matching basis and uncertainty. Acknowledgements do not alter
banking records or retroactively prove a charge legitimate.

Refund analysis computes constrained candidate-link bounds with independent
arithmetic/flow checks. Ambiguity remains a range; matching is conditional on
supplied evidence and assumptions, not bank-confirmed linkage or entitlement.
Unsent enquiry worksheets are prepared from selected source evidence. No external
message is sent and no money is recovered.

Plans and purchase rehearsals use confirmed goals/assumptions, exact category/date
calculations, protection constraints and explicit infeasibility/stress results.
Gemini may interpret intent or explain recomputed output. These are conditional
history/scenario calculations, not predicted returns or automatic financial repair.

## 6. Gemini chat and speech

The assistant has no executor, arbitrary SQL, URL or banking tools. It receives
bounded text and separately consented statement, diary, cash-flow or style context.
Aggregate statement chat does not receive transaction descriptions, signing
material, source excerpts or account identifiers. General questions need no
financial sharing. Recognisable secrets are minimised, not guaranteed detected.

Typed outputs are schema-validated. Available citation/finding allowlists,
explicit rupee-amount support and workflow-consistency checks constrain responses.
These finite guards are not a proof that arbitrary prose is true. Unsupported
outputs fail explicitly rather than become canned live answers.

Consumer mode adds a statement-only instruction and normalises old document/inbox
destinations to supported statement destinations. Retired inbox permission is
rejected before storage/model access. Model navigation is a suggestion, not authority.
Visuals and plans remain in chat until the user elects to open them; no random
page jump accompanies a late result.

Responses are bound to privacy generation and selected statement revision. Changed
context or cleanup withholds stale answers; frontend epochs discard obsolete
plan/rehearsal results. Page chat history is not stored by Friday.

Optional speech uses a server-composed, revision-bound aggregate briefing with
separate consent, bounded generated audio, transcript and manual Play. No microphone,
autoplay, phone surveillance, external alert or always-on conversation is implied.
The normal on-screen review remains useful when voice is unavailable.

## 7. Interface contract

Home presents the purpose, a primary Add statement action, friendly companion,
right-side chat on wide screens and a visible sample walkthrough. Main navigation
is Home, Statements, My money, Ask Friday and Listen. Account identity, account
switch/sign-out guidance and privacy live in the top-right menu. Returning Google
sessions may sign in silently; profile makes that identity explicit.

Statement detail views have real history-aware Back behaviour and safe direct-link
parents. The source banner names the selected review. A fresh review is distinguishable
from unloaded history, failure and a successful empty result. Optional planning,
rehearsal, diary and runway tools stay outside the main journey.

The hosted walkthrough serves the labelled CSV/PDF samples and expected results
without requiring GitHub access. Loading a page or example never submits to a model
or grants permission. Appearance/sound/motion are presentation preferences only.
Reduced motion and keyboard/focus states must remain supported. No claim of
certified accessibility or every-device verification is made.

## 8. Cloud architecture and security

Frontend: HTML/CSS/JavaScript. Backend: Python/FastAPI/Pydantic and Google Gen AI SDK.
Local Docker uses Python 3.12 and SQLite. Cloud uses a Google-IAP-protected Cloud Run
web gateway, separately private Cloud Run API and tenant-scoped Firestore.
Vertex AI supplies Gemini; Document AI supplies configured OCR. Cloud Build and
Artifact Registry produce pinned release images. IAM, IAP and Secret Manager keep
credentials server-side. Current signing is Ed25519, not Cloud KMS.

The existing web access policy admits authenticated Google users; verified identity
derives a separate visitor tenant. Browser-supplied tenant identities are not trusted.
Mutating web requests must match the canonical origin. The API remains non-public.
This private GitHub repository requires separate invitations for source access.

Consumer route admission is explicit and defaults on. Bill/receipt inbox,
obligation follow-ups, provider enrollment, new payment tasks, preflight/contracts,
watch and execution demonstrations are excluded. Historical code/tests remain
behind explicit legacy opt-in. This is not a complete process/service-account split.
Existing signed journal inspection and the narrow authenticated Cloud Tasks
recovery target remain unchanged; recovery cannot initiate a new payment.

Logs correlate gateway/API/model/calculation work with opaque request IDs, bounded
route templates, timing, model/version, available token counts and fixed failure
categories. Chat and extraction use the privacy-safe model wrapper. Raw statements,
identifiers, filenames, prompts and replies are not included in this telemetry.
Operational alerting, exact cost attribution and uptime guarantees are not implied.

## 9. Verification and release gates

Engineering tests, synthetic live acceptance, authored finding quality and independent
financial usefulness are separate evidence. Count skips separately. Preserve failed
model runs and scorer revisions. Do not tune against inspected data and call it a
blind benchmark. The current 39-case authored corpus still contains false alerts and
misses and lacks independent label review.

Build from known commits; retain identities, signing keys, quotas, data and recovery
configuration. Stage at zero normal traffic, run bounded fresh artificial-tenant
checks, verify cleanup and only then promote matching API/web revisions. Record
separate source identities where a web-only or API-only follow-up differs.
GitHub push alone is not deployment. Keep local services and hosted trial availability
under explicit operational control; budget alerts are not hard cost/uptime guarantees.

A second-person login, independent fresh cases, broader bank/export/scanned
coverage and external usefulness/security review remain human/external acceptance
work. The official submission also needs dashboard eligibility/roster/deadline
confirmation, proposal deck/PDF, public short video and final form acknowledgement.
No novelty, patent, selection, prize or production certification is guaranteed.

See [release checklist](docs/submission/RELEASE_CHECKLIST.md),
[statement release evidence](docs/SUBMISSION_READINESS_0340.md),
[goal/research evidence](docs/GOALS_RESEARCH_0350.md) and
[independent review protocol](docs/VALIDATION_HANDOFF.md).

# Financial Friday

**One statement. Less admin. A clearer next step.**

### Friday prepares the work, not another report to read

**Add statement → review once → open your workbench.** Friday reads the supplied
history, runs eight exact checks and automatically prepares a private batch of
up to eight source-linked next steps. The default result is a spending chart and
**one priority item**, not five competing report tabs. Repeated entries get a
comparison worksheet; unidentified credits get a classification worksheet;
other candidates get a source-filled **unsent enquiry**. Download, review and
advance. Acknowledging an item never edits its transaction or proves legitimacy.

The in-app buddy responds to real reading, preview, saving and chat events.
It can be paused; it does not watch Google Pay, other apps or bank accounts.
**Hear my briefing** separately asks permission to send aggregate figures to
Gemini 2.5 Flash TTS through the existing Vertex client. Audio is temporary,
silent by default and has no microphone. Failure leaves the visual result usable.
Gemini chat still reasons over only the context you explicitly choose to share.

Use **Statements → Try with an example** for a labelled 35-row artificial history
through the same parser, processing consent and review/save flow as your file.
Account options and detailed evidence are folded away, not removed. The approved
Soft Studio palette is retained, with consistent dark native controls and logo.
See [the workbench implementation and verification report](docs/ASSISTANT_WORKBENCH_0300.md).

### Money Shield: follow refunds without inventing certainty

Friday builds a purchase/refund evidence graph automatically after statement
review. It handles split and partial returns, tests alternative allocations, and
shows simple visual ranges when one refund could fit several purchases. A refund
is never counted twice. Missing original purchases, repeated rows and analysis
limits stay visibly unresolved. Refund evidence is integrated into the priority
workbench item when clarification is needed. Its unsent enquiry is already
prepared; **Show source evidence** reveals the underlying rows. No complaint is
sent and no refund entitlement is asserted.

Underneath is bounded **integer min-cost maximum flow**, with a separate capacity/
conservation checker, residual optimality checks and per-purchase lower/upper
bounds over all maximum compatible allocations. This is established mathematics
applied to evidence ambiguity, not a claimed new theorem. Compatibility uses
literal merchant text, account nickname/type and a 90-day window; even fixed
purchase totals are **not bank-confirmed** or proof of unique refund links. Gemini on Vertex AI selects the visual or
enquiry using separately consented derived totals. The server, not model prose,
owns completion receipts for these actions, preventing a generated response from
announcing that it sent the enquiry or recovered funds.

The [historical artificial Money Shield CSV](examples/friday-money-shield-artificial.csv)
remains available; the upload page now offers one combined example. There are no precomputed answers: the
same parser and graph engine run on each upload. See the
[algorithm, demo and verification report](docs/MONEY_SHIELD_0290.md). This adds no
bank access, model training, legal/tax determination or autonomous financial action.

### Automatic statement checkup

Upload and review a supported statement once. Friday automatically checks repeated
entries, recurring payments, regular-amount increases, unusual expense amounts,
fees and unclear credits. It calculates exactly which categories explain the
change between consecutive supplied months. **My money** presents the result as
charts and a short review queue, not another questionnaire.

Friday also does the follow-through: open a finding to see its source rows and
prepare a downloadable, **unsent bank enquiry** with the dates and amounts already
filled in. Mark reviewed/reopen persists a reversible review status; it never
changes a transaction or declares it legitimate. Chat can select the appropriate
visual and prepare the same source-grounded draft. Gemini receives only separately
opted-in aggregates and derived findings, not transaction descriptions or account
aliases. No bank credentials or additional OAuth permissions are required.

The engine uses exact-description grouping, temporal regularity checks, a lower-median
and median-absolute-deviation outlier threshold, integer-paise attribution and
revision-bound evidence IDs. These are explainable review heuristics, **not a
trained fraud model, fraud probability or proof of novelty**. The test CSV is
[artificial three-month history](examples/friday-checkup-artificial.csv): it
produces five candidates and two regular-payment patterns without any precomputed
answer. Generalisation to real bank exports and false-warning rates still needs
independent validation.

See [the automatic-checkup workflow and verification report](docs/AUTOMATIC_CHECKUP_0280.md).

Financial Friday is a private, **statement-first financial buddy**. Instead of
entering every purchase, upload supported INR bank or credit-card statements.
Google Gemini proposes source-linked PDF interpretations; CSV reading uses exact
parsing and local interpretation rules. Exact code
calculates monthly spending, categories, identified income and repayments. Review
the interpretation, save the normalized rows, and optionally ask Friday for a
practical next step using aggregate context only. Raw PDFs/CSVs are not archived.

The main journey is **Add statement → Review/save → Automatic checkup → Visual result → Prepared next step**. The selected
Soft Studio interface puts a friendly, live-on-request Friday chat beside the
desktop workspace, with a dedicated chat page on phones. A top-right avatar
menu opens the account, spending and privacy pages. Example charts are labelled
illustrations, not seeded financial history; saved transactions are searchable.
Financial context sharing remains explicit and off by default. The avatar uses
initials; no additional Google profile-photo permission has been requested.
The selected design's handwritten underline, lavender note/arrow, accent marks
and grounded companion shadow are restored. For a first try, use the
[fictional two-month CSV](examples/friday-artificial-statement.csv) and
[its expected results](examples/FRIDAY_SAMPLE_STATEMENT.md); it is never
automatically added to your account.

### New: ask a goal, inspect a checked plan

Budget plans and daily financial rehearsals remain optional advanced tools, not
mandatory onboarding. The former **What if?** item and its large home-page form
invitation are removed from the primary navigation. Rehearsals still require an
explicit opening cash/buffer because statements do not establish a live balance.
See [the advanced rehearsal contract](docs/FINANCIAL_REHEARSAL_0270.md).

Share statement totals in the chat, then try: **“Help me reduce spending by INR
1000 per month. Protect transport and test 20% lower income.”** Gemini interprets
the instruction into a strict, non-executable proposal. An exact integer-paise
allocation engine finds bounded cuts, leaves essentials and loan repayments
unchanged, and independently checks the result. Friday opens before/after and
income-stress charts with exact figures and visible assumptions. An impossible
goal shows its unmet amount, not a fabricated success. Recalculate scenarios
without a new model call, saving a plan or moving money.

The old financial-inbox permission is **not** statement permission. Context
sharing is explicit and off by default; **Statements ready · tap to share** or
the labelled **Use my statement totals with Gemini & answer** action enables it
for the page conversation. Ordinary questions need no records. **Privacy & data**
replaces legacy payment rules in the normal account flow. Spending now includes
a category doughnut and monthly comparison, with accessible exact-value tables.
See [visual planning and its limits](docs/VISUAL_MONEY_PLANS_0260.md).

One month is
enough to begin; multiple supported exports can cover six months or more within
the demo limits. Salary is not confused with generic credits, borrowing or
refunds. Card repayments and identified own-account transfers are kept out of
new spending. Overlapping rows are flagged, never silently deleted. Imports can
be reversibly excluded/restored. **Account** shows the verified Google email;
returning users may already have a Google sign-in session. The account menu
explains how to clear Friday’s IAP sign-in; Google may automatically reuse its
browser session, so this is not advertised as signing out of all Google apps.

This is not a bank feed, a complete asset/debt statement, a credit score or a
guarantee of saving money. Missing accounts, partial periods and wrong labels
affect the conclusions. Bank statements alone do not establish outstanding loan
principal or net worth. See [statement scope and evidence](docs/STATEMENTS_0240.md).

Optional protection tools remain under **My account → More financial tools**. The **obligation inbox** lets you give Friday a
financial request once, see what is known versus missing,
prepare one evidence-bound next step, and follow its actual outcome. Supplier and
reference must match an artificial provider record before a document can join the
payment workflow. No connected provider means useful verification assistance,
not a fabricated payment. Matching uploaded receipts remain unconfirmed claims.

## Technical documentation

1. [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md): purpose, trust boundaries, complete
   technical architecture, algorithms, workflows, current gaps and review questions.
2. [START_HERE.md](START_HERE.md): a short live-demo tour.
3. [USER_GUIDE.md](USER_GUIDE.md): detailed controls and expected results.
4. [SPEC.md](SPEC.md), [API map](docs/API_MAP.md) and
   [CONTRIBUTING.md](CONTRIBUTING.md): engineering contract and development setup.
5. [Reports index](docs/REPORTS_INDEX.md): current release, test evidence,
   evaluation results, known gaps and clearly labelled historical reports.

Repository access is separate from website access. This repository is private:
share its link with an invited GitHub collaborator, not merely anyone with the
URL. Google login to the deployed demo does not grant source-code access.
Cloning requires your authorised GitHub login; never share owner tokens or cloud
credentials. Confirm organisers' required source-code access before judging.

[Open the live Google-sign-in demo](https://financial-friday-web-171681243260.asia-south1.run.app/#home).

## Using the interface

Start on **Home → Understand my statements**. Choose a file, an account nickname
(not an account number), and bank/card type. Confirm temporary processing, then
review the extracted totals and labels before saving. **Spending** shows category
and monthly charts. **Friday** answers questions; its separate **Share statement
totals** option sends aggregates, not transaction descriptions. **Account** shows
sign-in, communication preferences and access to privacy controls. **More tools**
contains the earlier diary, runway, document checks and artificial payment demo.

Blue means working or prepared—not paid. Amber means incomplete or needing
verification. Red means held/conflicting. Green is reserved for independently
confirmed artificial-money outcomes. Status text accompanies colour. Light/dark
themes, reduced motion, keyboard focus and phone-width navigation are supported.
Detailed quotes, model provenance and limits remain available in expandable panels.
Interaction polish adds soft card lift, bounded pointer depth, light click feedback,
short page/disclosure transitions and reading-aware chat scrolling. These are local
decorations, not financial progress. Device/app reduced-motion settings take priority;
loading feedback is tied to actual pending requests. See [soft flow](docs/SOFT_FLOW_0220.md).

## Problem and implemented solution

People have bank records but still struggle to understand their spending or see
whether a money goal fits their constraints. A generic chatbot can suggest a
plausible budget without calculating or checking it. Friday uses Google AI to
interpret reviewed records and explicit goals, then exact code computes bounded
scenarios, checks protected costs and shows both feasible reductions and gaps.
That turns “what should I do?” into inspectable options, not guaranteed advice.

**Main flow:** upload → review → exact spending charts → optionally share totals
→ Gemini interprets a goal → independent calculation/checks → editable visual
plan. It does not pay, change bank records or train on private statements.

The separate protection tools reconcile financial claims and restrict artificial
payment tasks. The model's confidence is never payment authority or settlement proof.

**Optional protection flow:** Overview → Financial inbox → choose one obligation →
confirm selected-context sharing → Prepare this bill / Prepare verification →
review a signed task → confirm an eligible artificial payment → recorded outcome.
No repeat upload or typed bill reference is needed for a saved item. Opening the
inbox is read-only and makes no Gemini call. The model cannot substitute another
obligation; changed evidence requires a fresh check. Corrections, partial payments,
fees and recipient changes are verification questions, not automatic fraud labels.

| Capability | What works and what it does not mean |
| --- | --- |
| My money today | Real private, versioned diary; Gemini proposes source-anchored entries, manual fallback, explicit save, group Undo, export and chosen-buffer coverage. No official score, bank balance, automatic tracking or payment. |
| Ask Friday | Live Gemini answers, explanations and unsent drafts. Optional private workspace context; no execution tools. |
| Make Friday yours | Private nickname, concise/step-by-step explanations and focus preferences. Opt-in presentation choices, never payment authority; nickname is not sent to Gemini. |
| Follow-up memory | Keep a saved obligation on your list, wait for a reply, recheck new evidence or close the follow-up. New evidence resurfaces closed items; closing never means paid or verified. No automatic messages or bank monitoring. |
| Visible AI companion | Animated request-driven presence, returned model/call provenance and a read-only saved-record overview. No invented background scanning or fake progress. |
| Prepare next step | Live Gemini task selection and quoted risk analysis; signed ten-minute draft; independent claim/rule gates; explicit artificial-payment confirmation. No payment during preparation. |
| Document intelligence | PNG/JPEG/WebP/PDF or text extraction, typed facts, quotations and exact arithmetic checks. Extracted facts are claims, not authenticity. |
| Financial inbox | Compares related amount/payee claims, separates currencies and prepares verification messages. A matching receipt is not bank settlement. |
| Obligation workflow | Complete bounded evidence joined to artificial provider records and journal outcomes; exact selected-item Gemini preparation, targeted verification questions and explicit outcome states. |
| Guided first use | Editable artificial bill/receipt/conflict examples. Clicking Load does not send or pay; explicit review produces actual model results. |
| Statement review | Consented INR CSV analysis; exact totals and bounded coverage, not a bank balance. |
| Money Runway | Exact income/bill/spending scenarios, first buffer dip, daily cap and delayed-income comparison. Optional private latest-plan memory and separately consented Gemini explanation; no live bank feed or guaranteed forecast. |
| Bill planning | Exact reserve-aware deadline prioritisation over test-provider bills. Preview does not authorise or reserve money. |
| Sandbox execution | Typed Gemini program, independent safety checks, bounded repair, adversarial mutations and atomic artificial-money posting. |
| Outcome assurance | Signed receipts, idempotency, receipt-first replay and independent journal checks. Not external banking proof. |
| Cloud access | Google authentication, private API, isolated visitor workspaces, request limits and persistent Firestore state. |
| Evidence hardening | Recent inbox is separate from complete bounded safety evidence; late changes are checked inside the financial commit. |
| Task recovery | Signed execution lifecycle and journal-only reconciliation; unknown outcomes never trigger a blind retry. |
| Privacy and keys | Explicit review/draft cleanup, manual retention age, in-flight save cancellation and historical public-key verification support. |

**Bank of Anthos is retired from the customer product.** Historical fixtures are
optional developer tools, disabled by default. The Compose service `anthos-demo`
and Python `carapace_*` identifiers are compatibility names, not bank access.
The app does not automatically read banks, wallets, Gmail, SMS or utility accounts.

## Architecture and technology

```text
Browser: HTML / CSS / JavaScript
                  |
Google IAP -> Cloud Run web gateway -> private Python/FastAPI API
                                           |
                     +---------------------+---------------------+
                     |                     |                     |
              Gemini / Vertex       Deterministic code      Tenant storage
              chat, extraction,     claims, constraints,    Firestore cloud
              typed planning        plan and replay         SQLite local
                                           |
                             explicit sandbox execution only
                                           |
                                signed artificial receipt
```

Google Gen AI SDK performs model calls, Pydantic validates schemas, and
`cryptography` supplies Ed25519 signing. Cloud Build and Artifact Registry build
and store images. IAM, IAP and Secret Manager keep credentials server-side.
Version 0.19 adds a basic Mumbai Document AI OCR integration with exact source
anchors and a shared 100-page daily admission limit. Check the release manifest
for actual live activation and verified results, not just configured resources.
Cloud Tasks journal-only recovery uses a specifically approved keyless identity
and low-rate queue. See the release manifest for actual live dispatch activation
and its acceptance evidence. It never retries a payment. Native Gemini Live voice, ADK, BigQuery, Agora and
KMS signing are **not implemented**. The model configured in the verified release
is `gemini-3.5-flash-lite`; local live calls use the Gemini Developer API and cloud
calls use Vertex AI. Model availability and quota must be checked before changing it.

## Run locally

Start Docker Desktop, then:

```bash
git clone https://github.com/Santxsh27/financial-friday.git
cd financial-friday
docker compose up -d --build api anthos-demo
```

- Website: <http://localhost:8090/#home>
- API reference: <http://localhost:8080/docs>
- Readiness: <http://localhost:8080/health/ready>

No Anthos profile/database or cloud subscription is required for local sandbox
tests. Initial startup can take a few minutes. The default planner is visibly
`LOCAL_RULES`; chat and document review return unavailable without live Gemini.
Use the deployed site for the complete live-AI first tour, or configure an ignored
`.env` using `.env.example` and [CONTRIBUTING.md](CONTRIBUTING.md). Never commit keys.
Stop with `docker compose stop`; do not delete the development data volumes.

## Tests, CI and release evidence

Latest local checks, 16 October 2026: **646 tests ran, 645 passed, one optional
skip; 24 tooling checks passed**. Ten buddy tests additionally cover private
preferences, presentation-only opt-in, no nickname in prompts, no financial-rule
changes and local gateway JSON validation. See [buddy boundaries](docs/BUDDY_0200.md).
Seventeen follow-up tests cover persistent tracking, new evidence after closing,
exact stable identity, tenant isolation, simultaneous updates, bounded storage,
privacy cleanup and the actual Firestore transaction callback using a test driver.
See [follow-up workflow and limits](docs/FOLLOWUPS_0210.md).
The seventeen cloud-extension tests cover
preflight document bounds, global usage limits, signed recovery jobs, actor
validation, stale leases, scheduling failure and no-second-debit recovery.
These do not establish actual Cloud Tasks dispatch. See
[0.19 cloud boundaries](docs/CLOUD_EXTENSIONS_0190.md).

Docker release verification is tracked in [CURRENT_RELEASE](docs/CURRENT_RELEASE.json).
Fourteen Money Shield tests cover independent exhaustive allocation checks across
80 synthetic graphs, ambiguity/partial/split returns, bounded coverage and
server-owned completion receipts. These are mathematical and safety tests, not
an independently measured fraud-detection rate.
The current native suite adds 14 automatic-checkup tests covering source links,
stable IDs, insufficient history, exact attribution, tenant isolation, stale
reviews, reversible acknowledgements, Firestore failure, aggregate-only Gemini
context and real source-filled enquiry preparation. The statement-first
release adds 15 statement tests, one verified-profile test and two gateway-error
tests, including real PDF
text parsing, source-value validation, tenant isolation, exact totals, replay,
reversible exclusions, privacy generations, aggregate-only AI context and
Firestore transaction callback contracts. These are not independent extraction
accuracy or customer-usefulness benchmarks. Four additional optional
Node-based motion checks account for the extra container skips. Ten soft-flow
tests cover frame coalescing/cancellation, bounded tilt, reduced motion, no new
action/network authority, real busy states, preserved chat reading position and
safe inline rendering of the same licensed icons.
Twenty-two Money Runway tests
cover exact integer cash-flow calculations, maximal daily caps, same-day income
ordering, delayed income, opt-in memory, tenant isolation, privacy races, chat
consent, Firestore callbacks, paise-to-rupee formatting, rejected unsupported
model amounts and gateway validation. See
[Money Runway and responsible learning](docs/MONEY_RUNWAY_0220.md).
The previously deployed 0.19
Cloud Run candidate passed a live basic Mumbai OCR → Vertex extraction →
Firestore readback check on an artificial PDF. Exact source anchors, cached
upload replay, unchanged balance and zero payment requests were verified. The
private API also rejected anonymous access and unconfirmed execution. This is
acceptance evidence, not independent model accuracy or document authentication.

Previous verified task release, 13 October 2026:

- Native: 422 tests ran; 421 passed, one optional skip.
- Docker: 422 tests ran; 403 passed, nineteen optional skips.
- The obligation update adds seventeen outcome/identity/consent regression tests.
  Live Vertex/Firestore additionally extracted a newly generated synthetic bill,
  bound the selected obligation and verified its transition to a recorded outcome.
  This is end-to-end acceptance evidence, not independent fraud-accuracy validation.
- Fifteen offline tooling tests passed.
- Live Vertex/Firestore checks confirmed quoted refund-risk holds, signed task
  readback, unchanged balance during preparation, one confirmed artificial payment,
  no second debit on repeated confirmation and independently verified replay.
- Browser checks covered bill/receipt claims, changed recipients, guided starts,
  compact chat and readable light/dark starting cards.
- The October 13 clarity update additionally checks structured task outcomes,
  unsent-draft copy feedback, expired/unknown status labels and request-only
  coverage. All six primary pages were checked at 390px width without horizontal
  page overflow; these checks are not a full accessibility certification.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q
PYTHONPATH=src .venv/bin/python -m unittest discover -s tools -p 'test_*.py' -q
```

Node.js is optional for JavaScript syntax/presentation checks. Normal CI runs
native tests, container tests and standalone website checks. The retired Anthos
fixture is an explicit manual option, not a customer-product requirement.
See [GitHub Actions](https://github.com/Santxsh27/financial-friday/actions) for the
actual current run status; local passes do not imply a remote CI pass.

Latest deployment state and image identities are recorded in
[the current release manifest](docs/CURRENT_RELEASE.json). Code commits do not
automatically redeploy the application. Hardening behavior and activation limits
are documented in [HARDENING_0180](docs/HARDENING_0180.md); the earlier task checks
remain historical evidence in [the task release record](docs/FRIDAY_TASK_RELEASE_1013.md). Tests do not establish
fraud accuracy, production-bank certification, patentability or a winning guarantee.

The paired live evaluation runner accepts a frozen externally labelled corpus.
Bundled cases are developer-authored, not independent validation. A Developer API
smoke comparison was stopped after repeated server errors; no accuracy score was
substituted. See [evaluation protocol](docs/INDEPENDENT_EVALUATION.md).

The newer [same-output Vertex study](docs/EVIDENCE_EVALUATION_0211.md) found and
fixed four explanation-only responses where a verification step was expected.
On the frozen 16 developer cases, the corrected run matched the requested next
step in 16/16 attempts and supplied all 12 requested drafts, with no proposed
payments. The first report retains its timeout and mismatches. This is a small
developer regression, not independent accuracy, human usefulness or proof of
real-world fraud prevention. Raw/checked scores were identical on these returned
outputs; no unsupported “better than plain Gemini” claim is made.

## Hackathon alignment

Theme: **BFSI: Intelligent Risk, Fraud & Financial Experiences**, Google Cloud
AI Builder Cup. We target document understanding, risk mitigation, safer automation
and useful financial assistance. Meaningful Google AI and cloud deployment are
required; Anthos and every suggested service are not mandatory. Read the
[official requirements](https://aibuildercup.com/themes.html) and
[submission checklist](docs/submission/README.md).

The [public timeline](https://aibuildercup.com/) checked on 13 October lists team
formation by **14 October** and prototype submission by **18 October 2026**.
Confirm the dashboard's exact cutoff, eligibility and roster; its account-specific
details were not verified in this documentation pass. Cloud credits are finite;
budget alerts and request counts do not impose a hard spending cap.

## Next priorities and honest limits

1. Confirm teammate/judge access with another human Google login and the dashboard.
2. Validate the new evidence-bound task workflow with varied unseen inputs;
   chat and model outputs must never gain direct payment authority.
3. Evaluate unseen documents, false warnings, failure modes, latency and cost.
4. Finish the deck/PDF, short video and final submission links.
5. Later: independently authorised providers, durable orchestration and voice.

Cloud follow-through returns `UNAVAILABLE`. Local acknowledgement is bookkeeping,
not a refund or biller correction. Sandbox provider evidence is supplied by our
own test provider. Real settlement, merchant authenticity, phone monitoring,
production code repair, personalised securities advice and perfect fraud protection
are not supported. Differentiation is the working combination of structured AI,
independent checks and restricted execution, not a claimed world-first primitive.

## Repository map

- `src/carapace_ai/`: Gemini chat, extraction and planning.
- `src/carapace_core/`: schemas, exact algorithms, verification and assurance.
- `src/carapace_api/`: FastAPI, state, storage, executor and quotas.
- `src/carapace_integrations/`: UI, cloud gateway and historical adapters.
- `tests/`, `tools/`, `examples/`, `schemas/`: verification and fixtures.
- `docs/`: current feature guides plus dated historical evidence.

This README, the architecture guide and SPEC describe the current product. Dated
release documents describe their own historical scope; do not treat them as a
promise that every earlier CARAPACE idea is part of today's application.

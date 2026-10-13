# Financial Friday

**Keep financial obligations on track. Prepare the next safe step. Verify the outcome.**

Financial Friday combines Google Gemini financial assistance with a separate,
strictly bounded artificial-money executor. It is not a bank, a trading adviser,
or an unrestricted agent controlling real accounts.

The central workflow is an **obligation inbox**, not a collection of disconnected
AI tools: give Friday a financial request once, see what is known versus missing,
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

[Open the live Google-sign-in demo](https://financial-friday-web-171681243260.asia-south1.run.app/#home).

## Using the interface

Start on **Overview**. **Ask Friday** gives a read-only answer; **Prepare next
step** opens a checked task or unsent verification draft. Neither prepares a
payment automatically. Include saved workspace context only when you want those
records used. **Documents** explains the upload/review/inbox flow, and the
**Financial inbox** separates status, reference, claimed amount and next steps.

Blue means working or prepared—not paid. Amber means incomplete or needing
verification. Red means held/conflicting. Green is reserved for independently
confirmed artificial-money outcomes. Status text accompanies colour. Light/dark
themes, reduced motion, keyboard focus and phone-width navigation are supported.
Detailed quotes, model provenance and limits remain available in expandable panels.

## Problem and implemented solution

Bills, receipts and payment notices are difficult to reconcile. Giving an AI
assistant unrestricted financial authority would introduce a second problem.
Friday uses Gemini to understand unfamiliar inputs and propose restricted plans;
ordinary code checks arithmetic, identities, constraints and actual sandbox state.
The model's confidence is never payment authority or proof of settlement.

**Start-to-outcome flow:** Overview → Financial inbox → choose one obligation →
confirm selected-context sharing → Prepare this bill / Prepare verification →
review a signed task → confirm an eligible artificial payment → recorded outcome.
No repeat upload or typed bill reference is needed for a saved item. Opening the
inbox is read-only and makes no Gemini call. The model cannot substitute another
obligation; changed evidence requires a fresh check. Corrections, partial payments,
fees and recipient changes are verification questions, not automatic fraud labels.

| Capability | What works and what it does not mean |
| --- | --- |
| Ask Friday | Live Gemini answers, explanations and unsent drafts. Optional private workspace context; no execution tools. |
| Prepare next step | Live Gemini task selection and quoted risk analysis; signed ten-minute draft; independent claim/rule gates; explicit artificial-payment confirmation. No payment during preparation. |
| Document intelligence | PNG/JPEG/WebP/PDF or text extraction, typed facts, quotations and exact arithmetic checks. Extracted facts are claims, not authenticity. |
| Financial inbox | Compares related amount/payee claims, separates currencies and prepares verification messages. A matching receipt is not bank settlement. |
| Obligation workflow | Complete bounded evidence joined to artificial provider records and journal outcomes; exact selected-item Gemini preparation, targeted verification questions and explicit outcome states. |
| Guided first use | Editable artificial bill/receipt/conflict examples. Clicking Load does not send or pay; explicit review produces actual model results. |
| Statement review | Consented INR CSV analysis; exact totals and bounded coverage, not a bank balance. |
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
Document AI has a tested optional OCR adapter, but no live processor is enabled.
Cloud Tasks automatic dispatch, native Gemini Live voice, ADK, BigQuery, Agora and
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

Verified task release, 13 October 2026:

- The preceding hardening release ran 405 native tests (404 passed, one optional
  skip) and 405 Docker tests (386 passed, nineteen optional skips).
- The obligation update adds seventeen outcome/identity/consent regression tests;
  final release counts and live checks are recorded in the deployment manifest.
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

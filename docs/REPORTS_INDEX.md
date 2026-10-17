# Financial Friday — documentation and evidence index

The **0.35.0 goals/research expansion** is described in
[its implementation report](GOALS_RESEARCH_0350.md). Local checks ran 803 tests
(802 passed, one skipped), plus 65 tool tests; the container ran 803 tests
(771 passed, 32 skipped). Consult CURRENT_RELEASE for exact source identities.

Updated 17 October 2026, deployed API and web release **0.35.0**,
both verified at 100% traffic. The **0.33.0 workflow repair**
is included: [its repair report](WORKFLOW_REPAIR_0330.md) documents the
source-selection contract, browser captures and Desktop organization.
The [0.34 release report](SUBMISSION_READINESS_0340.md) retains earlier synthetic
acceptance and telemetry evidence; the current goal/research report extends it.
Deployed versions are listed below and
in CURRENT_RELEASE rather than inferred from a source version. Start here to separate
what is implemented, what was verified, and what is proposed. GitHub code is not
automatically the code deployed on Cloud Run.

## Read the project from start to finish

| Document | What it covers |
| --- | --- |
| [README](../README.md) | Purpose, current features, Google stack, setup, tests and limits. |
| [Start Here](../START_HERE.md) | Short live tour and local startup. |
| [User guide](../USER_GUIDE.md) | What to click, enter and expect, including consent and Money Runway. |
| [Architecture](../ARCHITECTURE_GUIDE.md) | Frameworks, service boundaries, algorithms, data flow, storage and security. |
| [Specification](../SPEC.md) | Current engineering contract and authority limits. |
| [API map](API_MAP.md) | Read-only, configuration, preparation and execution-capable routes. |
| [Contributing](../CONTRIBUTING.md) | Setup, live AI, testing, safe changes and deployment. |
| [Security policy](../SECURITY.md) | Authorised testing, secrets and private disclosure. |
| [Submission checklist](submission/RELEASE_CHECKLIST.md) | Verified work and remaining human confirmation/artifacts. |

## Current deployment and acceptance

[CURRENT_RELEASE.json](CURRENT_RELEASE.json) is the machine-readable authority
for source, image digests, build IDs, revisions, test counts and activation. The
exact API and web revisions are recorded there, together with promotion and
acceptance evidence. A new source version alone does not prove deployment.

| Evidence | Scope and limitations |
| --- | --- |
| [Goals and public research 0.35.0](GOALS_RESEARCH_0350.md) | Quote-bound real Gemini intake, confirmed single-pool purchase scenarios, exact amortisation and repayment overlap, visual stress comparison and separately consented Search grounding. No live quote feed, optimal investing or financial execution. |
| [Statement-only release 0.34 / API 0.34.1](SUBMISSION_READINESS_0340.md) | Supported statement journey, retired consumer bill routes, hosted bank-labelled artificial samples, synthetic Vertex PDF/chat, actual Firestore selection conflict, source restoration, content-free chat telemetry and verified deployment. Not independent bank validation or completed submission. |
| [Consumer assurance 0.32.0](CONSUMER_ASSURANCE_0320.md) | Consumer admission, opt-in legacy demos, strict narration, unchanged authored quality, transparent live AI failures/follow-up, final-read privacy, preview recovery, real Firestore API races and bounded quota abort handling. Verified revisions and counts in CURRENT_RELEASE. |
| [Statement reliability 0.31.0](STATEMENT_RELIABILITY_0310.md) | Literal-grounded reconciliation, signed extraction receipts, labelled synthetic quality baseline with misses/false warnings, privacy races and content-free request correlation. Not independent fraud validation or bank authentication. |
| [Assistant workbench 0.30.0](ASSISTANT_WORKBENCH_0300.md) | Automatic private review preparation, one visual priority task, integrated refund ranges, actual-event guide, opt-in bounded Google speech and privacy-generation freshness. No bank monitoring or automatic financial resolution. |
| [Money Shield 0.29.0](MONEY_SHIELD_0290.md) | Integer refund-flow bounds, independent primal/residual checks, explicit ambiguity, source-grounded clarification and server-owned AI completion receipts. No bank-confirmed linkage, legal entitlement or autonomous recovery. |
| [Automatic checkup 0.28.0](AUTOMATIC_CHECKUP_0280.md) | Automatic source-linked pattern checks, exact change attribution, typed Gemini visual selection, unsent enquiry assembly and reversible finding review. Explainable heuristics, not a trained fraud model or independently validated financial outcome. |
| [Financial rehearsals 0.27.0](FINANCIAL_REHEARSAL_0270.md) | Daily source-month calendar scenarios, simultaneous cash stress, concrete counterexamples, exact purchase/date/cut alternatives and separately consented Gemini explanation. Conditional replays, not predictions, bank execution or proof of novelty. |
| [Visual money planning 0.26.0](VISUAL_MONEY_PLANS_0260.md) | Independent statement consent, typed Gemini goals, exact protected-first allocation, infeasibility/stress results and accessible charts. Read-only, not training, a bank feed, autonomous finance or independent efficacy evidence. |
| [Soft Studio 0.25.0/0.25.1](SOFT_STUDIO_0250.md) / [Design QA](../design-qa.md) | Selected first design, restored handwritten accents and shadow, shared right-side chat, account menu, responsive statement journey and tested artificial CSV. No new bank access, financial authority or transaction-level chat retrieval. |
| [Statements 0.24.0](STATEMENTS_0240.md) | Statement-first input, source-linked PDF proposals, exact spending/income/repayment summaries, reversible exclusions, verified account display and live Vertex/Firestore acceptance. Not complete bank-format or financial-health validation. |
| [Money buddy 0.23.0](MONEY_BUDDY_0230.md) | Daily reported entries, source-anchored AI proposals, private atomic saves, Undo, target coverage and aggregate coaching; no bank balance or official score. |
| [Money Runway 0.22.0](MONEY_RUNWAY_0220.md) | Exact cash-flow algorithm, consent/privacy, 22 feature tests and real Vertex/Firestore acceptance. Initial unit failure corrected before promotion; not independent forecast validation. |
| [Soft-flow UI polish](SOFT_FLOW_0220.md) | Palette-preserving feedback, ten tests, browser verification, inline icons, motion limits and no new financial authority. |
| [Evidence study 0.21.1](EVIDENCE_EVALUATION_0211.md) | Same-output Vertex comparison, initial failures, corrected 16 developer cases. Raw/checked scores identical; not an independent fraud benchmark. |
| [Before report](evaluation/evidence_2026-10-14_before.json) / [after report](evaluation/evidence_2026-10-14_after.json) | Preserved machine-readable developer results, not substituted success scores. |
| [Follow-ups 0.21.0](FOLLOWUPS_0210.md) | Private tracking, evidence changes, stale edits and closing without pretending settlement. |
| [Buddy/recovery 0.20.0](BUDDY_0200.md) | Personalisation boundaries and separately scoped recovery evidence. |
| [Cloud extensions 0.19.0](CLOUD_EXTENSIONS_0190.md) | Actual basic OCR, caps and journal-only queue boundaries; no issuer-authenticity proof. |
| [Hardening 0.18.0](HARDENING_0180.md) | Lifecycle, privacy generations, historical signing keys and safety boundaries. |
| [Task release](FRIDAY_TASK_RELEASE_1013.md) | Historical live preparation/confirmation/replay and selected-obligation acceptance. Artificial funds only. |
| [Independent evaluation protocol](INDEPENDENT_EVALUATION.md) | Held-out testing method and pending independent validation. |

Each dated report retains its own test and live-acceptance counts. Final
0.35 counts and cloud activation are recorded in
[CURRENT_RELEASE](CURRENT_RELEASE.json); historical suite counts do not establish
later releases' acceptance. Later commits have their own
[Actions status](https://github.com/Santxsh27/financial-friday/actions).
Skipped tests and model failures are not counted as passes.

## What the Google services actually do

- Gemini on Vertex AI: bounded conversation, extraction, quoted risk reasoning
  and typed proposals. Model text is never payment permission.
- Document AI: anchor supported image/PDF quotations to independent OCR text.
- Cloud Run: web gateway and separately private Python/FastAPI API.
- Firestore: tenant-scoped state and transactional artificial-money journal.
- Cloud Tasks: authenticated reconciliation of an existing journal only.
- Cloud Build / Artifact Registry: explicit reproducible builds and images.
- IAP / IAM / Secret Manager: Google identity, scoped invocation and server-held
  credentials. Current signing is Ed25519, not Cloud KMS.

Frontend is HTML/CSS/JavaScript; backend is Python 3.11+/FastAPI/Pydantic and the
Google Gen AI SDK. Docker uses Python 3.12 and SQLite locally. No ADK, BigQuery,
Agora, native Gemini Live, Model Armor, reference RAG or fine-tuning is claimed.

## Historical reports are not today's feature list

Earlier `MILESTONE_*`, `CLOUD_RELEASE_*`, Anthos documents, UI explorations and
dated submission scripts remain engineering history. Their counts/access rules
describe that point in time. Current README/SPEC/manifest take precedence.
Legacy `carapace_*` packages and `anthos-demo` Compose names are compatibility
identifiers; Anthos is not needed or connected in the customer product.
The earlier cinematic control-room module is not the current Friday UI.

## Sharing and remaining boundaries

This repository is private. An invited collaborator can read it while signed
into the correct GitHub account; an uninvited person cannot access it by link.
Source access does not grant cloud-owner privileges or another user's workspace.
Do not send tokens, `.env`, credential JSON or databases.

Real bank/SMS/Gmail integration, native voice, automatic financial corrections,
external alerts and independently measured large-scale effectiveness remain
unimplemented. Reference datasets require provenance/licensing and a separate
design; private customer records are not automatically training data. Deck/video,
dashboard confirmation and a second-person access test remain submission tasks.

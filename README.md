# Financial Friday

**One statement. Less admin. A clearer next step.**

Financial Friday is a statement-first financial assistant for Indian digital-banking
users. Import a supported INR bank/card PDF or CSV, review the extracted rows once,
and Friday prepares a visual spending picture, source-linked review candidates,
refund-evidence worksheets and practical guidance through Gemini on Vertex AI.

It is a Google Cloud AI Builder Cup 2026 **BFSI: Intelligent Risk, Fraud &
Financial Experiences** prototype. Its purpose is to reduce the work of understanding
fragmented financial history, not become a bank or claim every unusual payment is fraud.

## Try the deployed product

- [Financial Friday](https://financial-friday-web-171681243260.asia-south1.run.app/#home)
- [Sample statements and walkthrough](https://financial-friday-web-171681243260.asia-south1.run.app/assets/friday-judge-guide.html)
- [Local/hosted release status](docs/CURRENT_RELEASE.json)

Google sign-in identifies a private visitor workspace. A returning browser may reuse
its existing Google session; the top-right account menu shows the signed-in identity.
The website's existing access policy admits authenticated Google users. Organisational
account restrictions and a second person's real login still need human confirmation.
No bank, Gmail, Drive or SMS permission is requested. The API remains private.

**Release note:** local API source is 0.34.1. The release manifest distinguishes staged,
promoted and verified revisions. A GitHub commit alone does not deploy Cloud Run.
Use the deployed version recorded there, not this source number, when evaluating
the hosted site.

This repository is private. A GitHub link alone does not grant source access. Invite
the required reviewers, or use the organisers' approved source-delivery method.
The hosted walkthrough and sample downloads do not depend on GitHub access.

## The complete user journey

1. **Add a statement.** Choose a supported bank/card PDF or CSV and confirm processing.
2. **Review before saving.** Compare rows, dates, amounts and proposed categories;
   inspect source checks. Known source mismatches block saving.
3. **My money.** See category charts, income/spending/repayment totals, patterns,
   changes, review candidates and the original row references.
4. **Ask Friday.** Opt into statement totals for a personalised answer, chart selection,
   checked plan or prepared unsent enquiry. General questions need no financial context.
5. **Keep control.** Statements shows exactly which imports power the review. Start a
   new review excludes earlier imports without deleting them; restore them without
   re-uploading. Back returns from detail views.
6. **Listen, optionally.** A separately consented Google-generated spoken briefing
   has a transcript and manual Play control. It is not a live microphone.

The main consumer product has no separate bill/receipt inbox or artificial-payment
workflow. Historical modules and tests remain for engineering history, disabled by
default. They are not extra features for a judge to discover.

## What AI does, and what code verifies

| Responsibility | Implementation |
| --- | --- |
| Read varied PDF text into typed rows and literal evidence | Gemini on Vertex AI; source references validated by Python |
| Read supported scans | Document AI OCR, followed by validated Gemini extraction |
| Interpret questions and select a supported chart/plan/review workflow | Typed Gemini output; server-owned destination and evidence allowlists |
| Explain shared totals and prepare an unsent message | Gemini, with independent context consent and citation/amount checks |
| Parse known CSV headings and amount/date spellings | Deterministic adapters; no model call |
| Categorise CSV rows initially | Local proposed labels, editable by the user; not trained ML |
| Reconcile source facts and calculate summaries | Exact integer-paise calculations; never floating-point money |
| Find review candidates | Bounded narration grammar, statistical/rule checks and source evidence |
| Assess possible refund links | Constrained flow bounds and independent checks; ambiguous links stay ambiguous |
| Prepare category reductions or purchase scenarios | Exact checked algorithms over supplied history/assumptions, not a prediction |
| Permit a save or expose a route | Authenticated deterministic application policy, never the model's decision |

A receipt signed by Friday binds an extraction to its tenant, source, generation and
immutable row fields. It is **Friday's signature, not a bank's signature**.
Arithmetic agreement is not proof of authenticity, ownership, completeness or fraud.

## Architecture and actual Google stack

```text
Browser: HTML / CSS / JavaScript
          |
Google sign-in / Identity-Aware Proxy
          |
Cloud Run web gateway -- authenticated request --> private Cloud Run API
                                                     Python / FastAPI / Pydantic
                                                          |
                       Gemini on Vertex AI <--- bounded, consented context
                       Document AI OCR      <--- supported scanned PDF
                                                          |
                         Exact source / calculation / freshness verification
                                                          |
                         Firestore: tenant-scoped reviewed history and preferences
                                                          |
                         Charts, review queue, explanations and unsent drafts
```

Docker uses Python 3.12 and SQLite for local development. Cloud Build and Artifact
Registry produce release images. IAM, IAP and Secret Manager protect existing
identities and server credentials. Ed25519 signs extraction evidence.
Content-free request IDs correlate gateway, API, model and calculation events;
logs include bounded latency, failure categories and available usage/model metadata.

Cloud Tasks retains a narrowly scoped **historical journal-only recovery** worker;
it does not pay a bill, reconcile a real bank or continuously collect statements.
Current code does not use BigQuery, Vertex AI Search, ADK, Agora, native Gemini Live,
Model Armor, Cloud KMS signing or fine-tuning. Services are named only when used.

See [architecture](ARCHITECTURE_GUIDE.md), [specification](SPEC.md),
[API map](docs/API_MAP.md), [security policy](SECURITY.md) and
[contributor instructions](CONTRIBUTING.md).

## Artificial test files

Use [the judge kit](jugges/README.md) or the hosted walkthrough. Bank names are
visible in the filenames, with explicit provenance:

- `ARTIFICIAL-HDFC-Illustration.csv`: based on public illustrative headings.
- `ARTIFICIAL-Kotak-Illustration.csv`: public illustrative headings/date/amount style.
- `ARTIFICIAL-ICICI-Candidate.csv`: candidate layout, not a verified ICICI export.
- `ARTIFICIAL-Generic-Bank-Tab.csv` and `ARTIFICIAL-Generic-Bank-Semicolon.csv`:
  generic delimiter/column-order stress cases, not official bank files.
- `ARTIFICIAL-Generic-Bank-Statement.pdf`: separate two-row source-check PDF.
- The in-app **Try with an example** option has 35 artificial rows across three months.

The five bank-format CSVs encode the same four transactions. Test them one at a
time; do not combine them as five accounts. Each has INR 50,000 incoming and
INR 1,390.75 outgoing. The PDF has different, explicitly documented totals.

No searched customer statements were copied. [Provenance and expected results](jugges/bank-formats/README.md).
This corpus does not establish compatibility with every real bank/export version.

## Run locally

Docker Desktop must be running:

```bash
docker compose up -d --build api anthos-demo
```

Open [Friday](http://127.0.0.1:8090/#home). The historical Compose name
`anthos-demo` is the standalone Friday web process, not a Bank of Anthos dependency.
[API docs](http://127.0.0.1:8080/docs) are for developers, not the user interface.

CSV processing and saved charts work without a model. Chat, PDF extraction and
speech require configured live services and fail explicitly when unavailable.
Local demo data and hosted Google-account data are separate. Never delete volumes
to solve an import problem. Stop with `docker compose stop`.

## Verification and measured limitations

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tools -p 'test_*.py'
docker compose --profile test run --rm --build tests
```

Counts, skips, source hashes and cloud acceptance are recorded in
[CURRENT_RELEASE](docs/CURRENT_RELEASE.json) and the
[report index](docs/REPORTS_INDEX.md).

The 39-case authored synthetic checkup benchmark has precision 66.67%, recall
73.68% and case-level false-positive rate 38.89%. These are **review-candidate**
labels, not fraud ground truth. It has not had independent human validation.
Known misses and false warnings are retained in its reports; no measured superiority,
world-first novelty, patentability or award is established.

The small production-path Gemini study records failures and follow-ups separately.
Typed admission, factual checks, wording conformance and representative accuracy
are different questions. Independent frozen extraction/intent/explanation cases,
broader real-bank layouts and external usefulness/security review remain necessary.

## Boundaries that matter

- INR only. CSV up to 1 MB / 500 rows; PDF up to 4 MB / six pages / 200 rows.
  At most ten imports / 2,000 saved rows. Split larger exports carefully.
- Known CSV adapters need separate debit/credit columns and supported four-digit dates.
  Unknown or conflicting rows/columns reject the import without a partial save.
- Raw uploads are not archived. Reviewed normalised rows and minimal source-fact
  evidence are saved privately after confirmation. Chat shares aggregates only
  when requested; chat history is not stored by Friday.
- No real bank feed, live balance, outstanding-loan/net-worth completeness, payment
  execution, refund recovery, subscription cancellation or external complaint submission.
- No personalised trade calls, guaranteed savings/profit or universal Safe badge.
- No claim that legacy code is isolated into separate services/IAM: consumer
  endpoints are allowlisted, while historical code remains in the repository.
- Quotas, expiry and cloud availability can interrupt a demo. Request limits and
  budget alerts do not guarantee zero cost or uninterrupted uptime.

## Submission

Read [the release checklist](docs/submission/RELEASE_CHECKLIST.md) and
[the shareable judge instructions](jugges/README.md). The official requirements
call for Google AI, a Google Cloud deployment, an English proposal deck/PDF and a
public approximately three-minute demonstration video. Confirm eligibility,
roster, the exact dashboard deadline and all submission links yourself.
The public timeline checked 17 October lists 18 October 2026 as the deadline.

Old screenshots, bill samples, snapshots and release reports are historical evidence,
not the current consumer feature list. On this Mac, the existing working project
stays in `Desktop/CARAPACE`; older copies and owner test files are inside its ignored
`archive/` and `my-testing/` folders, not uploaded or shared with judges.

# Financial Friday — Start Here

Working folder: `/Users/santosh/Desktop/CARAPACE`. The product is Financial Friday; Python module names retain CARAPACE for compatibility.

## What it does

Save an instruction such as “Handle verified bills up to ₹3,000, protect ₹10,000 and never create subscriptions.” Gemini reads a new message, QR text, transcript, bill photo or PDF. Friday matches it to an enrolled provider record, creates a restricted plan, verifies the plan against your limits, then completes one artificial-money payment or explains why it stopped. It checks uncertain previous outcomes before retrying.

## Run and explore

1. Start Docker Desktop and open this folder in Visual Studio Code.
2. Run `docker compose --profile anthos up -d --build api anthos-demo`.
3. Open http://localhost:8090 for Friday and http://localhost:8080/docs for the API.
4. Open **My rules** in the top navigation to inspect/save standing permission. Artificial provider setup and **Safety lab** are development tools, not real bank connections.
5. Use **Bills** or **Review bill** to select a saved provider record and **Check & handle in sandbox** without retyping. Alternatively paste a request on Overview, or choose **Documents** for an image/PDF. **Check document & apply my rules** can complete an artificial payment when automatic permission is enabled and the independent checks pass; no real funds are connected.
6. Friday opens a separate **Run** screen. Change the amount or recipient and check that it stops.
7. Use **Safety lab** for controlled subscription/timeout cases, and **Activity** to reopen existing receipts without paying again.
8. Overview's **Recent activity** shows recorded outcomes, not all-time totals. Activity filters use independently checked assurance; older unsealed receipts remain amber. **How Friday works** explains the journey; Escape closes help and `/` focuses the home command outside text fields.
9. **Understand my money → Review spending** accepts a consented INR CSV. The analysis is read-only; net flow is not your bank balance. **Clear results & start again** removes the displayed analysis.
10. The top-bar **moon/sun** changes light/dark mode. The **gear** opens appearance
    settings: device theme, optional soft click sounds and gentle motion. These
    preferences stay in this browser and never change financial permission.

The seven cloud sandbox records above ₹3,000 are previous ₹3,001 test bills,
not failed payments. Friday correctly excludes them from the automatic plan.
Do not raise a safety limit or delete evidence just to make a warning disappear.

`docker compose stop` preserves the named data volume. Keep `.env`, credentials and signing keys out of GitHub.

## Implemented capabilities

- **My money**: read-only bill, reserve and shortfall overview, with explicit record coverage.
- A connected bill-understanding, planning, safe handling and receipt-reconciliation journey.
- Transaction-alert/unknown intake stops before preparing a new payment.
- Tested bank/biller resolution kernel; provider correction execution is not connected.

- Typed goals, provider evidence and Gemini action programs.
- Vertex AI and Gemini Developer API adapters, plus a labelled local comparison.
- New message, QR-text and transcript interpretation; PNG/JPEG/WebP/PDF interpretation with quotations.
- Saved limits, reserve protection and opt-in automatic artificial payments.
- Independent checks for recipient, amount, fees, currency, recurrence, privacy and action order.
- Restricted execution, tenant isolation, idempotency and signed receipts.
- Plan repair, six hostile mutations and reconciliation before retry.
- Background sandbox inbox with bounded retries and claim recovery.
- Optional Firestore storage for instructions, bills, signals, cases and run evidence.
- Friday UI, API docs and automated tests.

Local SQLite mode runs the complete artificial-money journey. Version 0.13.2 includes an atomic Firestore payment journal and receipt-first replay: an already-paid bill is confirmed without another AI call or debit. The Mumbai database and persistent signing keys are provisioned; cloud verification and release results are recorded in docs/CLOUD_RUN.md. Real UPI, GPay, SMS and bank accounts are not connected.

## Technology inventory

Python, FastAPI, Pydantic, SQLite, cryptography/Ed25519, Google Gen AI SDK, Google Firestore client, Docker Compose and HTML/CSS/JavaScript. Browser speech experiments are not the deployed native voice product. The repository retains earlier Bank of Anthos artificial-bank work.

Google Cloud includes Vertex AI, private Cloud Run, Artifact Registry, Cloud Build, service identity, Secret Manager and budget alerts. The deployed API is 0.17.0; deployment evidence is in `docs/FRIDAY_CORE_0170.md`. The live configuration uses Gemini 3.5 Flash-Lite and transactional Firestore. Owner Google login through IAP works; access remains owner-only. Cloud Tasks and native Gemini Live voice remain planned. BigQuery, Document AI, ADK and Agora are not implemented.

## Verification

Current native validation: **319 application tests** (318 passed, one optional
skip) and **11 tooling tests**. The readiness pass and reviewed-bill
execution preserve existing financial and authentication boundaries. See
`docs/submission/READINESS_1012.md` for the current verification/deployment record.
Earlier release results below are historical, not the latest test count.

The **0.14.1 workspace release** ran 244 native tests: 243 passed, one optional
integration skipped. My money now works locally and through the private cloud
gateway. The candidate passed Firestore reads, unchanged balance, anonymous-access
rejection and a live Vertex paid-notice check before promotion. Local signed bill
acknowledgement is tested, but disabled in cloud mode; real biller correction is
not connected. See `docs/CLOUD_RUN.md` for current release identifiers.

Version 0.13.2 plus the cloud gateway and multi-screen UI: 195 tests ran, 194 passed, one optional Anthos test skipped. Eleven tooling tests also passed. Tests include concurrency, durable restart, corrupted receipts, replay while AI is unavailable, identity/tenant isolation, same-origin protection, missing document quotations, suppression of invented text quotations, privacy-safe diagnostics, read-only briefing/filtering and no automatic gateway payment retry. Browser evidence is in `docs/FRIDAY_BROWSER_VERIFICATION_1008.md`, `docs/FRIDAY_MULTISCREEN_1008.md` and `docs/FRIDAY_DOCUMENT_VERIFICATION_1008.md`. A separate no-payment evaluation covers 51 generated proposals (12 valid allowed, 39 unsafe rejected); results and limitations are in `docs/submission/SAFETY_EVALUATION.md`. The newest 16-case live Vertex check and remaining submission blockers are in `docs/submission/FINAL_HANDOFF_1009.md`.

```bash
docker compose --profile test run --rm --no-deps --build -e CARAPACE_AI_PROVIDER=local -e CARAPACE_TEST_ANTHOS_BRIDGE_ENABLED=false tests
```

## Remaining submission work, in order

1. Confirm dashboard deadline/eligibility and explicitly arrange judge access; record the live story in docs/submission/DEMO_SCRIPT.md.
2. Expand live evaluation to varied documents/images and a second explicitly enrolled cloud identity. A fresh INR 49 PDF task, real rejected-plan correction, signed receipt and no-debit/no-AI replay now work; evidence is in `docs/FRIDAY_DOCUMENT_VERIFICATION_1008.md`.
3. Connect an independently authenticated sandbox provider.
4. Connect durable orchestration if promising continuous background operation.
5. Expand unseen-case evaluation and measure completion, false holds, unsafe actions, latency and cost against plain Gemini. The targeted false-hold repair passed 24 extraction and eight API checks; see docs/submission/MESSAGE_PROMPT_REPAIR_1008.md. The earlier HTTP 503 remains undiagnosed. No payments occurred in these checks.
6. Finish demo video, deck, architecture, limitations and submission links.

Confirm deadline and eligibility in your Hack2skill dashboard. Production launch additionally requires authorized providers and security/compliance review.

## Folder map

- `README.md`: public overview, architecture and running instructions.
- `SPEC.md`: technical and product contract.
- `docs/CLOUD_RUN.md`: cloud deployment status.
- `docs/submission/README.md`: submission checklist.
- `src/carapace_ai`: Gemini integrations.
- `src/carapace_core`: rules and models.
- `src/carapace_api`: API, storage and executor.
- `src/carapace_integrations`: UI and provider/Anthos adapters.
- `tests`: automated verification.

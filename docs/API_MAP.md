# Financial Friday — Current API map

Updated 13 October 2026. The local OpenAPI reference at
<http://localhost:8080/docs> is the source for exact request/response schemas.
Source: `src/carapace_api/financial_friday_routes.py`.

The browser calls `/api/friday/...` on its web origin. The gateway maps approved
operations to `/v1/friday/...` on the private API. Direct API calls need tenant
authentication; hosted calls additionally need authorised Cloud Run invocation.
Do not paste owner credentials into the browser or impersonate another tenant.

## Default customer: no financial execution

| Method and path | Purpose / authority |
| --- | --- |
| POST `/v1/friday/chat` | Message, bounded history, optional context; live guidance only. |
| GET `/v1/friday/reviews` | Saved document claims and deterministic reconciliation; read-only. |
| POST `/v1/friday/reviews` | Read supplied text and save extracted claims; never pay. |
| POST `/v1/friday/reviews/documents?filename=...` | Raw supported file body; extract/store claims, discard raw upload. |
| POST `/v1/friday/reviews/statement` | Consented bounded INR CSV claim import, no AI/payment. |
| POST `/v1/friday/statements/analyze` | Read-only INR CSV spending calculation, not a real balance. |

Example chat body (do not include financial secrets):

```json
{"message":"Draft an unsent question about an unfamiliar charge using placeholders.","history":[],"include_workspace":false}
```

Chat returns a schema-checked reply, available evidence IDs, a next-screen
suggestion, provider/model provenance and explicit no-execution fields. Failure
is unavailable, not a canned answer masquerading as Gemini. Text review takes a
`text` field; file review uses its actual media type rather than pretending a file
path/string is an uploaded image. Read each schema before sending a request.

## Sandbox preview/configuration: may change rules or test records, not pay directly

| Method and path | Purpose |
| --- | --- |
| GET `/v1/friday/mandate` | Saved permission and artificial account summary. |
| PUT `/v1/friday/mandate` | Change standing rules/automatic sandbox permission. Security-relevant configuration, not chat. |
| GET `/v1/friday/test-provider/bills` | Bounded test-provider records. |
| POST `/v1/friday/test-provider/bills` | Publish/update an artificial bill; not a real utility connector. |
| GET `/v1/friday/workspace` | Bounded non-atomic artificial balance/bill/commitment overview. |
| GET `/v1/friday/bill-plan` | Exact reserve-aware preview; no permission or reservation. |
| GET `/v1/friday/today` | Recent recorded outcomes/briefing. |
| GET `/v1/friday/storage-status` | Active persistence boundary. |
| GET `/v1/friday/live-input` | Original sandbox interpretations, distinct from the new review inbox. |
| GET `/v1/friday/scenarios` | Controlled developer test scenarios and supported model modes. |
| GET `/v1/friday/runs/{run_id}` | Reopen recorded outcome; independent replay, no payment. |

## Execution-capable or historical developer routes

| Method and path | Important caution |
| --- | --- |
| POST `/v1/friday/bills/handle` | Exact reviewed bill reference/digest and explicit sandbox confirmation. Can move artificial funds under rules. |
| POST `/v1/friday/live-input` | Original sandbox intake. May execute inside saved automatic authority; **not a prepare-only conversation tool**. |
| POST `/v1/friday/documents` | Original execution-model document path; default UI uses `/reviews/documents` instead. |
| POST `/v1/friday/live-input/{event_id}/run` | Execute/reconcile the supported dynamic sandbox case. |
| POST `/v1/friday/scenarios/{case_id}/run` | Run a controlled case with explicit confirmation; can affect artificial state. |
| POST `/v1/friday/follow-through` | Local signed acknowledgement only; cloud returns UNAVAILABLE. Never refund/settle. |
| GET `/v1/friday/inbox` | Historical sandbox background inbox. Not exposed in the public visitor route allowlist. |
| POST `/v1/friday/watch` | Historical sandbox monitoring permission, not phone/bank access; not public visitor capability. |
| POST `/v1/friday/arrivals/{case_id}` | Deliver a synthetic provider event; can initiate bounded background handling. Not public visitor capability. |
| POST `/v1/friday/inbox/{event_id}/retry` | Controlled historical sandbox retry; not public visitor capability. |
| GET `/v1/friday/bank` | Retired optional Anthos developer projection; no customer navigation. Unmapped callers see NOT_LINKED. |

The allowlist is implemented in `src/carapace_core/friday_access.py`; a private
API route existing does not mean public visitors may use it. Earlier `/v1/contracts`,
witness/case/release-passport endpoints also remain for legacy engineering
experiments; they are not the default customer workflow or granted by the public
Friday allowlist. Health endpoints are diagnostic, not customer financial features.

## States and interpreting failures

- Reviews: `BILL_TO_VERIFY`, `RECEIPT_MATCHED_CLAIM`, `RECORDED_PAYMENT_CLAIM`,
  `CONFLICT_REVIEW`, `INCOMPLETE_REVIEW`; no bank verdict is implied.
- Plans: `PLANNED`, record ambiguity/incompleteness and planning-limit states.
- Runs include held, approval-required and explicit synthetic/reconciled outcomes;
  inspect `money_moved`, receipt and assurance, not only a title/status colour.
- Assurance includes verified internal outcomes, conflict, unavailable and legacy
  unsealed evidence. A signature does not authenticate an external bank statement.
- 401/403: identity/origin/permission issue; 422: input validation; 429: admission
  limits; 503: a bounded operation unavailable. Do not retry an unknown money
  outcome as if it were definitely failed. Check the recorded operation first.

These are human-readable summaries, not an SDK contract replacing OpenAPI or
server validation. Preserve exact enum names, strict booleans and minor-unit
integers when building an integration. Never pass model text directly to a route
that creates financial authority or executes a payment.

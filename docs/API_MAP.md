# Financial Friday current API map

Statement-first consumer release 0.34.0. Actual deployed version and source:
[CURRENT_RELEASE](CURRENT_RELEASE.json). Schema authority is the running API's
OpenAPI document. The private API is not the judge-facing website.

The browser calls its same-origin /api/friday proxy. Google IAP verifies identity;
the gateway derives tenant credentials and invokes the private /v1/friday API.
The consumer allowlist is explicit in src/carapace_core/friday_surface.py.
X-Request-ID correlates bounded telemetry; it grants no authority.

## Statement journey

| Method and path | Meaning |
| --- | --- |
| GET /api/friday/profile | Web-only verified Google identity or explicit local demo identity; no bank connection. |
| GET /v1/friday/statements | Private imports, selected source set, review revision/generation, computed summaries/checkup/work. |
| POST /v1/friday/statements/prepare | Consented bounded PDF/CSV extraction; unsaved proposal with source checks and signed receipt. |
| POST /v1/friday/statements | Confirmed reviewed save with expected revision/generation and unchanged signed amounts/dates/source facts. |
| POST /v1/friday/statements/selection | Atomic inclusion set with expected revision/generation. An empty set starts a fresh analysis without deleting imports. |
| POST /v1/friday/statements/visibility | Compatibility single-source exclusion/restore; not a financial correction. |
| POST /v1/friday/statements/findings/review | Reversible finding acknowledgement, not a bank dispute or proof of resolution. |
| POST /v1/friday/statements/findings/enquiry | Prepare a private unsent clarification worksheet/draft with source/version checks. |
| POST /v1/friday/statements/analyze | Transient exact INR CSV summary. |
| POST /v1/friday/chat | Bounded conversational guidance and typed supported presentation/plan intent; no executor. |
| POST /v1/friday/assistant/briefing-audio | Separately consented derived-total Gemini speech, expected revision/generation and no microphone/autoplay. |

Statement preparation checks declared totals/counts, pages, source rows, balances
and direction/order where supplied. Missing facts remain UNKNOWN; MISMATCH blocks
saving. Friday's Ed25519 extraction receipt binds its own processing, not bank
authenticity. Category/meaning proposals can be reviewed; immutable source fields
cannot be edited to bypass the receipt.

Sample chat body:

```json
{"message":"Show my spending by category.","include_statements":true}
```

Statement, diary, cash-flow and communication-preference sharing are independent
and opt-in. include_workspace=true belongs to the retired bill inbox and is
rejected in consumer mode before context/model access. Returned source receipts
identify the selected statement revision/count/period; they do not expose account
identifiers or transaction descriptions to aggregate chat.

## Optional user-owned planning and settings

| Method and path | Meaning |
| --- | --- |
| POST /v1/friday/plans/preview | Exact revision-bound category-reduction scenario; no payment or automatic savings claim. |
| POST /v1/friday/rehearsals/interpret | Consented Gemini proposal of purchase/stress fields. |
| POST /v1/friday/rehearsals/preview | Exact history replay under confirmed assumptions, not predicted bank affordability. |
| POST /v1/friday/rehearsals/explain | Consented explanation of server-recomputed, freshness-bound scenario. |
| GET/POST /v1/friday/diary | Explicit user-reported START/ADD/UNDO bookkeeping, never a bank transaction. |
| POST /v1/friday/diary/prepare | Gemini proposes grounded diary fields; no save before confirmation. |
| GET/POST /v1/friday/cashflow | Optional user-entered forecast assumptions and calculator snapshot. |
| GET /v1/friday/buddy | Private saved-record overview, no continuous bank monitoring. |
| GET/PUT /v1/friday/buddy/preferences | Communication preferences, not financial permission. |
| GET/PUT /v1/friday/privacy | Manual retention preferences, not automatic erasure. |
| POST /v1/friday/privacy/reviews/delete | Explicit private-input cleanup; durable financial journals retained for recovery safety. |

## Retained recovery and diagnostics

Existing signed task/run inspection, journal-only reconciliation, GET mandate and
storage-status remain compatibility diagnostics. They cannot prepare/confirm a new
payment in consumer mode. The internal recovery endpoint retains its existing
OIDC/signature checks and target; no money is connected.

Health and model-status endpoints are diagnostics. API docs are developer reference,
not the consumer interface. Private Cloud Run invocation and tenant authentication
remain required; do not expose the API or copy its credentials into a browser.

## Removed from consumer admission

Bill/receipt /reviews (text/file/statement), /obligations and its follow-ups,
new /tasks and confirmation, preflight/contracts, provider enrollment, watch,
synthetic arrivals and payment execution are not consumer actions or current
OpenAPI entries. Historical code/tests remain behind explicit legacy opt-in.
Application admission is not a separate process/IAM boundary.

## Error interpretation

- 401/403: identity, tenant, origin or invocation refusal. Do not disable auth.
- 404: not part of this surface, or unavailable record; not an invitation to try another route.
- 409: stale revision/generation, invalid signed source, conflicting evidence or source mismatch.
- 422: unsupported input or context choice. Nothing was saved merely by attempting it.
- 429: configured usage allowance reached. Failed processing can still count.
- 503: model, storage or transport unavailable/rejected. Not a successful financial action.

Do not re-upload changed source content to bypass a conflict. Reload Statements,
inspect the current selection and use the original source. Unknown outcomes must
not be turned into success messages. Full raw prompts/statements/replies are
excluded from the new request telemetry.

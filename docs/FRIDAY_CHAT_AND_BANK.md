# Friday chat and optional historical bank tools

Friday's right panel accepts natural questions and returns live Gemini guidance.
The customer Sandbox bank page has been removed. The application does not require
Bank of Anthos. Its historical read-only connector is retained for developer tests
only and is disabled by default. Chat, document reconciliation and Friday's own
artificial-money execution remain different operations with visible permissions.

## Current first-use experience

Overview offers useful questions, document upload and a guided bill/receipt example
even before records exist. Example buttons load editable artificial text; only an
explicit Review sends it to Gemini and stores extracted claims. There are no fake
balances, precomputed green results or automatic account seeding. The assistant
has a small companion, a bounded scrolling conversation and a compact composer;
privacy details are expandable. Old `#bank` links resolve to the money overview.

## Ask Friday

1. Open Overview and type `What does a payment receipt prove?` in the Friday panel.
2. Choose Ask Friday. The reply names the actual model/provider. It cannot pay,
   submit a complaint, fix production code or change bank records.
3. To discuss your uploaded documents, first use Documents or Bills to add them.
   Then select **Include my recent financial inbox and sandbox summary in Gemini's
   answer** and ask `Why does this bill need checking?`.
4. A reply may link to the appropriate screen. Opening it is navigation, not
   financial authorization. Any actual sandbox execution uses the existing
   explicit payment controls and safety kernel.
5. Clear chat removes conversation from this page. Changing workspace consent
   clears history so earlier contextual replies are not silently carried forward.

Up to eight previous turns are sent as untrusted conversation data. Friday does
not persist chat messages; the browser keeps recent turns only in memory. Google
processes the prompt, and its configured service data policies still apply.
Recognizable credential patterns are scrubbed on input/output, but this is not
exhaustive secret detection. Never enter PINs, OTPs, passwords or card details.

Workspace context is off by default. When enabled, the server selects at most ten
cases from the latest fifty review inputs, separate currency totals, the Friday
INR sandbox balance/reserve and an explicit no-real-bank-access marker. It never
queries the Anthos connector. It does not send raw
uploads, signing keys, database credentials or ledger account numbers. Every
citation must reference a case supplied by the server. Context is a bounded
snapshot, not a complete statement or current market feed.

The model has no payment, SQL, code, shell, browsing or arbitrary URL tools. A typed
reply can suggest only allowlisted screens. The API independently reports no
actions executed; plain text from Gemini is never proof of an accomplished action.
Replies may still be incorrect. Local offline mode returns unavailable rather
than a simulated Gemini answer. Personalized trading recommendations are outside
scope.

## Historical developer-only Anthos account experiment

The following describes the retired customer projection for engineering reference,
not a feature visible in the current site. No new Cloud SQL trial or bank hosting
is required to finish Financial Friday. Default local startup is
`docker compose up -d --build api anthos-demo`; the historical service name is
retained, but it has no Anthos database dependency. Existing sample-bank volumes
are preserved rather than deleted.

With explicit operator configuration, the historical API can map a tenant against
sample account ending 6111 and retrieves its balance plus the latest twenty ledger
rows in a repeatable-read, read-only PostgreSQL transaction. This reads actual
sample-bank data rather than generating a balance in the browser.

An unmapped user sees NOT_LINKED. An unavailable connector shows UNAVAILABLE, not
a guessed zero. Account identifiers come only from operator configuration; query
parameters cannot select another account, and duplicate account mappings are
rejected. Google login identifies a Friday workspace, **not** a bank customer.
Public visitors are not automatically placed into the owner's demonstration account.

Anthos's transactions table has no currency column. Friday displays minor ledger
units and does not reinterpret them as rupees or combine them with the separate
Friday INR sandbox. Earlier local experiments inserted INR-tagged rows alongside
the sample bank's dollar-oriented data, so this projection cannot certify a
single currency. Similar amounts/times do not establish a bill-to-bank match.

Start the optional official sample-bank website with:

```bash
docker compose --profile anthos-full up -d anthos-frontend
```

It runs at `http://localhost:8081`; the published sample login is `testuser` /
`bankofanthos`. This is separate from Friday's Google authentication. Use only
artificial funds. Friday itself remains at `http://localhost:8090`.

## Cloud boundary

Chat uses the existing Vertex AI client, authenticated Cloud Run gateway and
tenant admission limits. No new IAM access or banking credentials are given to
Gemini. The bank connector is optional: `FRIDAY_ANTHOS_DATABASE_URL` supplies the
private database connection and `FRIDAY_ANTHOS_ACCOUNTS_JSON` supplies unique
tenant-to-sample-account mappings. Deployment secrets must stay in Secret Manager,
not source control. Use a dedicated read-only database role for a hosted connector.

The present public Cloud Run deployment does not host Anthos's full PostgreSQL
and user-service stack. The retained historical endpoint returns NOT_LINKED for
unmapped visitors, but the customer interface does not call or display it. Hosting the
bank, provisioning separate accounts, authenticating bank identity and binding
verified payments to exact ledger references are still required before promising
cloud bank execution. There is no public tunnel to the developer's database.

## Verification

Ten additional tests cover opt-in context, cross-user isolation, role/length
validation, credential minimisation, invalid citations and authority fields,
model outages, local fallback, read-only parameterized account queries, unique
mapping, authenticated proxy routes and non-executing UI navigation.

Native suite: 364 tests ran, 363 passed and one optional integration skipped.
Docker suite: 364 ran, 346 passed and eighteen optional checks skipped; native
checks exercise JavaScript syntax/presentation. The live local bank endpoint read
thirty existing sample ledger rows with no money moved. These are engineering
results, not a real-bank security certification or guaranteed fraud accuracy.

`tools/verify_chat_cloud.py` performs a synthetic live Vertex check without
requesting payments. Live deployment results are recorded after execution.

## Earlier chat1012 release on October 12 (historical)

Commit `66c59c1` passed GitHub CI. Both existing protected Cloud Run services now
serve their `chat1012` revisions at one hundred percent traffic. API build
`cb51b859-32c7-4d63-b64b-dec05785f99e` produced digest
`sha256:94e19c0671cfb1e80b95e023405b658808a5764f81afb238be9a49d4e4730b84`;
web build `426bcbeb-aa8c-4ac4-84e8-3edf0b2a049b` produced digest
`sha256:d00e168352f2a5174147012365dab501af954d34d30423917f73fab87aac8e5f`.
Builds used a clean Git archive and did not include unrelated local edits.

Live synthetic checks passed for a general Vertex reply, a consented reply over
a fresh financial inbox, valid case citations, NOT_LINKED for an unmapped visitor,
no execution runs and unchanged sandbox balance. The actual main-site browser
also returned a `VERTEX_AI` reply from `gemini-3.5-flash-lite`. Local browser chat
returned `GEMINI_API` from the same configured model.

The staging web address rejected a chat POST with HTTP 403 because writes are
locked to the canonical origin. That restriction was retained; the normal website
was verified after promotion. No IAM grants, origin exemptions, signing keys or
cloud bank credentials were added. Existing owner release checks passed with
thirteen bill records, unchanged test balance, independent outcome assurance and
rejection of unconfirmed execution.

The optional official bank frontend also passed readiness and browser login.
The sample account ending 6111 displayed $7,705.89 and thirty transactions;
Friday's independent projection returned 770589 minor ledger units and the same
thirty records. No deposit or payment was submitted. The reader needed one
restart after a stalled Java startup, and the first account load timed out while
x86 services warmed up. A subsequent read-only reload displayed balance/history
successfully. Cold startup under Mac emulation is not a production latency result.

## Current customer-cleanup release, October 12

Source commit `719c7bb` is deployed to the existing protected services:

- API `financial-friday-api-cleandraft1012`, image digest
  `sha256:fadba7b7c3b346f995ac95026595af2e1d9c97551b22d5fcfa924b230c68df4d`,
  build `416b2f58-2554-4e60-a057-3591fb222f00`.
- Web `financial-friday-web-cleantheme1012`, image digest
  `sha256:5003924b2accf960383bbda573550f68bdcb21e03318e1510390f7dc10091bba`,
  build `f4d2de41-fe27-4773-9aa1-ced8a5981200`.

Both revisions have one hundred percent production traffic. No authentication,
IAM, origin restrictions or payment permission was weakened. No Cloud SQL trial,
new project or hosted bank stack was provisioned. The two running local services
are Friday's API and website; the latter retains the historical Compose name
`anthos-demo`, but no Bank of Anthos service is required or running. Existing bank
volumes were preserved. Unrelated local source edits were excluded from cloud
builds by archiving only committed source.

Verified flow:

1. Overview has three starting tasks and expandable instructions; there is no
   customer bank navigation or bank database request from chat.
2. The guide loads editable artificial inputs with sandbox execution unchecked.
   Loading alone does not call Gemini or authorize a payment.
3. The local bill and explicit customer-debit receipt went through real Gemini
   extraction and produced matching **claims**, not verified bank settlement.
   Changing the recipient produced `RECIPIENT_CONFLICT` and a verification draft.
   An earlier ambiguous receipt was interpreted as an incoming amount; the guide
   was corrected to state the customer's outgoing direction, not to force a match.
4. Live staged Vertex checks passed for general guidance, opt-in context, valid
   evidence references, unchanged sandbox balance and no executed actions. The
   canonical browser also returned live Vertex guidance.
5. Light and dark starter cards were visually inspected. Conversation scrolling,
   privacy details and composer sizing keep the panel compact. Full screen-reader
   and mobile-device certification are not claimed.

The next substantive product milestone is a prepare-only conversation tool that
creates an evidence-bound task for explicit approval through the existing safety
kernel. Chat currently provides guidance and unsent drafts, not execution tools.
Cloud provider follow-through, real bank/utility connections and real settlement
are still unsupported; this cleanup is not a claim that the entire roadmap is done.

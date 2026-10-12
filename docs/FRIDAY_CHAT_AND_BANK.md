# Friday chat and sandbox bank

Friday's right panel accepts natural questions and returns live Gemini guidance.
The separate Sandbox bank page reads a provisioned artificial account from Google's
Bank of Anthos ledger. Chat, document reconciliation and sandbox execution remain
different operations with visible permissions.

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
INR sandbox balance/reserve and Anthos connection status. It does not send raw
uploads, signing keys, database credentials or ledger account numbers. Every
citation must reference a case supplied by the server. Context is a bounded
snapshot, not a complete statement or current market feed.

The model has no payment, SQL, code, shell, browsing or arbitrary URL tools. A typed
reply can suggest only allowlisted screens. The API independently reports no
actions executed; plain text from Gemini is never proof of an accomplished action.
Replies may still be incorrect. Local offline mode returns unavailable rather
than a simulated Gemini answer. Personalized trading recommendations are outside
scope.

## Inspect the Anthos account

Open **Sandbox bank**. Local Docker provisions the demonstration tenant against
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

## Cloud boundary and remaining connection work

Chat uses the existing Vertex AI client, authenticated Cloud Run gateway and
tenant admission limits. No new IAM access or banking credentials are given to
Gemini. The bank connector is optional: `FRIDAY_ANTHOS_DATABASE_URL` supplies the
private database connection and `FRIDAY_ANTHOS_ACCOUNTS_JSON` supplies unique
tenant-to-sample-account mappings. Deployment secrets must stay in Secret Manager,
not source control. Use a dedicated read-only database role for a hosted connector.

The present public Cloud Run deployment does not host Anthos's full PostgreSQL
and user-service stack. It must show NOT_LINKED for public visitors. Hosting the
bank, provisioning separate accounts, authenticating bank identity and binding
verified payments to exact ledger references are still required before promising
cloud bank execution. There is no public tunnel to the developer's database.

## Verification

Ten additional tests cover opt-in context, cross-user isolation, role/length
validation, credential minimisation, invalid citations and authority fields,
model outages, local fallback, read-only parameterized account queries, unique
mapping, authenticated proxy routes and non-executing UI navigation.

Native suite: 361 tests ran, 360 passed and one optional integration skipped.
Docker suite: 361 ran, 343 passed and eighteen optional checks skipped; native
checks exercise JavaScript syntax/presentation. The live local bank endpoint read
thirty existing sample ledger rows with no money moved. These are engineering
results, not a real-bank security certification or guaranteed fraud accuracy.

`tools/verify_chat_cloud.py` performs a synthetic live Vertex check without
requesting payments. Live deployment results are recorded after execution.

## Live release on October 12

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

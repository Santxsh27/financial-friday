# Google-account access to Financial Friday

The user authorized access for anyone signing in with Google on October 12, 2026.
This is an artificial-money demo, not permission to connect real bank accounts.

## Boundaries

1. IAP remains enabled on the web service. Its resource-scoped accessor policy is
   widened to `allAuthenticatedUsers`, not anonymous `allUsers`.
2. The gateway cryptographically verifies the IAP signature, expiry, issuer and
   exact Cloud Run audience. Only a Google-user subject may self-enroll. A forged
   email/tenant header is not identity. Service accounts cannot self-enroll.
3. Existing enrolled owner identity retains its original account. A new visitor
   receives a `visitor-` namespace derived from the verified stable Google subject,
   not email or a request parameter. A separate HMAC domain derives the backend key.
4. The shared enrollment secret stays in Secret Manager, accessible only to the
   web/runtime service identities. No key reaches browser HTML or JavaScript.
5. Cloud Run API invocation remains private. Visitor keys have an additional
   Friday-route allowlist: no legacy contracts, bank bridge or background monitor.
6. All state reads and financial records stay tenant scoped. A new visitor has no
   saved bills or runs, default automatic permission off, and an artificial ₹50,000
   opening balance. Save My rules to establish a durable account before executing
   a live-input bill; saving again cannot replenish an existing balance.
7. Mutations require the fixed web Origin. Proxy paths, queries, content types and
   upload sizes remain validated. No payment request is retried by the gateway.

## Durable admission limits

The API reserves allowance in a Firestore transaction **before** a supported
visitor action is admitted. Per-user and global reservations succeed together.
Concurrent instances share the same counters. An unavailable counter store fails
closed. Failed downstream calls are not refunded, preventing retry-based bypass.

| Request category | Visitor/day | Global/day | Visitor/minute | Global/minute |
| --- | ---: | ---: | ---: | ---: |
| POST/PUT actions | 20 | 200 | 4 | 20 |
| GET reads | 1,000 | 10,000 | 120 | 600 |

Days reset at midnight UTC. Limits count admitted requests, **not Gemini calls,
tokens, financial debits, or dollars**. One workflow may make several bounded
model subcalls. Hosting, identity and Firestore requests can still incur costs.
Existing explicitly enrolled owner account is outside visitor quotas. Monitoring
cloud billing and restricting sharing remain necessary. This is not DDoS protection.
Daily usage records currently require operator-managed retention; no automatic
deletion policy is provisioned. Do not rotate the enrollment secret casually:
identity-derived namespaces would change; preserve it for stable visitor history.

## Verification

Automated tests cover two isolated visitor identities, stable identities across
requests, owner-header spoofing, rejected missing/forged/non-user identity,
restricted legacy routes, wrong keys, origin/query attacks, shared limits,
concurrent admission, daily/global caps, day reset, and fail-closed storage.
Existing private-pilot tests still verify owner access and no request retries.

Native suite: 329 tests ran, 328 passed, one optional Anthos integration skipped.
Unit mocks alone are not proof of external Google login.

## Live rollout, October 12

- Clean source commit `7525c15` built successfully by Cloud Build
  `5d6e2b64-66af-4d47-9fde-912924092b55`.
- Immutable API/web image:
  `sha256:c71dcb552bfb37b526d1c3a508b7b5e5c736802a142a1b02861830b9b82b40e8`.
- `financial-friday-api-google1012` and `financial-friday-web-google1012`
  each promoted to 100% only after zero-traffic candidate checks.
- Web resource's IAP accessor policy includes `allAuthenticatedUsers` and owner.
  Cloud Run web invocation remains IAP-service-agent only. Cloud Run API invocation
  remains web-service-account only. No anonymous Invoker binding was added.
- Inherited custom OAuth client confirmed; unauthenticated website requests
  redirect to `accounts.google.com` requesting only `openid email`.
- Actual Firestore/API test with two fresh synthetic visitor fixtures: separate
  empty workspaces, one private provider bill invisible to the other, invalid key
  rejected, background route rejected, fifth burst action returned 429, both
  artificial balances unchanged. No Gemini calls or payment requests.
- First provider test fixture was correctly rejected (422) for uppercase provider
  ID. Fixed to the required lowercase schema; rerun passed. No production code
  validation was weakened.
- Owner workspace read-only checks passed: 13 bill records, unchanged balance,
  unconfirmed execution rejected, assurance readable, anonymous access rejected.
- Live owner browser renders the access/privacy/limits link and protected app.
- **Not yet verified:** a second human Google account completing the browser OAuth
  flow. Ask a friend to use the public link; managed-account policies can interfere.
  Backend synthetic identities are not represented as real human sign-in tests.

Reproduce the no-AI/no-payment integration probe using
`tools/verify_public_demo_cloud.py` with an authorized owner CLI identity. It writes
only isolated artificial test rules/bills and consumes visitor request allowance;
it never provisions a Google account or verifies human login by itself.

## Google configuration

IAP supports authenticated Google access via the resource-scoped
`roles/iap.httpsResourceAccessor` binding. This does not grant Cloud Run Invoker,
project roles, Secret Manager or direct API access to visitors.
[Google IAP access documentation](https://docs.cloud.google.com/iap/docs/managing-access).

External visitors require a custom OAuth client when a Google-managed client is
restricted to an organization. Only basic Google sign-in identity is needed; no
Gmail, Drive or bank scopes are requested.
[Google custom OAuth guidance](https://docs.cloud.google.com/iap/docs/custom-oauth-configuration).
Google Workspace administrators can still block the application for their users;
no deployment can promise universal availability regardless of account policy.

## Rollback

Remove only the web resource's `allAuthenticatedUsers` IAP accessor binding to
return to invited access. Do not disable IAP or add anonymous Cloud Run Invoker.
Keep existing owner binding. Revert the web/API traffic to recorded prior revisions
if needed; do not erase visitor/owner Firestore records or signing keys.

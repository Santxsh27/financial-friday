# Financial Friday bill and receipt reconciliation

Financial Friday's default customer flow reviews unfamiliar bills, receipts and
transaction claims without requiring an artificial provider record or granting
payment permission. Gemini on Vertex AI extracts structured facts. A separate
deterministic engine groups related records, checks their arithmetic and prepares
verification messages when evidence is incomplete or contradictory.

## Try the customer workflow

1. Sign in with Google. Use your private workspace; never upload PINs or OTPs.
2. Open Documents and select a PNG, JPEG, WebP or PDF, at most 8 MB. Or paste a
   financial message into the read-only Bills input and choose Review this
   financial input. Home's Friday panel is now conversational guidance.
3. The Financial inbox shows the document's classification, amount, recipient
   claim, deadline and suggested next step. No payment is submitted.
4. Add a related receipt. Matching requires supported supplier, bill reference,
   currency, amount and recipient details. A matching receipt becomes a supplied
   payment claim, not authenticated settlement. Friday advises checking existing
   status before paying again.
5. If related documents change the amount or recipient, the case is marked for
   conflict review. Open Show matching evidence and limits to inspect quotations.
6. Open Prepare a verification message. Friday has drafted a request using the
   observed conflict. Send it through a known official channel yourself; it has
   not submitted a complaint, requested a refund or contacted the supplier.

## Match a transaction CSV

In Financial inbox, expand Match a transaction CSV. Select an INR CSV with at most
20 rows and 1 MB. Confirm storage of parsed claims; this is different from the
older ephemeral Spending review. The raw CSV is discarded and is not sent to AI.
Only its structured transaction claims are stored in the private inbox.

Required columns are `date,description,debit,credit`. To associate a transaction
with a bill, also provide `supplier,bill_reference,payee,transaction_reference`.
Missing identifiers remain unmatched. Incoming credits do not count as paying a
bill. Separate transaction references for the same bill trigger review, not an
automatic conclusion of fraud or duplicate debit.

```csv
date,description,debit,credit,supplier,bill_reference,payee,transaction_reference
2026-10-12,Electricity payment,1780.00,,TN Power,FF-DOC-1001,tnpower@upi,TEST-TX-001
```

## Interpretation and trust

| Inbox result | Meaning |
| --- | --- |
| Bill needs confirmation | A supplied bill claim is organized; authenticity and outstanding status remain unconfirmed. |
| Bill and supplied receipt match | Related claims agree on the matching fields. They do not establish bank settlement. |
| Payment claim recorded | A receipt or notice is preserved without being turned into a new payment. |
| Conflicting evidence | Related records disagree or indicate a possible repeat. Verify before acting. |
| More details needed | An obligation could not be established from the extracted facts. |

Amounts use exact decimal arithmetic and known minor-unit scales; currencies are
never summed together or converted. Supported review codes are INR, USD, EUR, GBP,
AUD, SGD and JPY. A bare dollar symbol stays UNKNOWN. Unsupported precision,
missing quotations and ambiguous dates remain visible. A date passing does not
prove a real debt is overdue.

Document arithmetic compares extracted quantities, prices, line totals, tax and
discount with the extracted total. It cannot certify pixels were read perfectly.
Text quotations are checked verbatim; image/PDF quotations are model-extracted,
not independent OCR proof. Supplier identity matching is exact normalized text,
not authentication, fuzzy merchant ownership or a fraud classifier.

## Execution remains separate

Home chat and document review cannot pay, even if automatic sandbox
permission is enabled. The original artificial-payment workflow is available
only through its explicit mode/controls and still requires a separate provider
record, saved permission and deterministic checks. Neither flow accesses real
bank accounts. Review never edits the payment journal or changes its permissions.

## Architecture and evaluation

`reviews`, `reviews/documents` and `reviews/statement` are authenticated, tenant
scoped API actions. Cloud storage uses a separate Firestore review collection;
local storage uses a separate SQLite table. Raw files are discarded; hashes,
structured facts, evidence quotations and provenance are retained. No signing
key or API credential reaches the model. Existing public-demo request limits apply.

The engine considers the most recent 50 expanded review entries, not a complete
account history. Repeated identical uploads reuse a review without another model
call; changed files get separate records. Model/schema failures create no review
or payment. One schema-repair retry is bounded to a second read-only model call.

Tests cover payment/credit distinctions, mismatches, repeated claims, arithmetic,
currencies, missing evidence, prompt injection, isolation, reuse, invalid files,
model failure, CSV consent and unchanged payment journals. Live evaluation and
deployment evidence are recorded after verification, not inferred from mocks.

This addresses document intelligence, risk review, process automation and customer
experience in one BFSI workflow. It does not certify fraud, recover funds,
authenticate external payees or guarantee a hackathon outcome.

## Verified release evidence

Native tests: 351 ran, 350 passed and one optional local Anthos integration skipped.
Twenty-two tests added to the existing suite exercise the new review boundaries.
These are engineering tests, not population-level fraud-detection accuracy.

Live Vertex checks passed through the staged Cloud Run API and actual Firestore:

- A previously unseen generated bill and a matching supplied receipt were joined.
- A changed recipient was surfaced as conflicting evidence, with no payment.
- The user's previously failing WebP invoice was extracted with total 755; its
  bare dollar symbol stayed UNKNOWN rather than becoming INR or assumed USD.
- The test workspace balance stayed unchanged, with no execution journal runs.
- Existing owner release checks retained 13 artificial bill records, unchanged
  balance, signed outcome replay and rejection of unconfirmed execution.

The first model-facing schema returned Vertex INVALID_ARGUMENT. Simplified
generation hints passed a direct live check; full server constraints were retained
and tested against invalid output. API image
`sha256:7375754df85e86ea4c14bca0ee717b4e82064f536a8e178384b28a2f136bba62`
contains the correction. No mock result is labelled as a live model success.

Remaining submission work includes a broader held-out input evaluation, a second
human-account sign-in check, organizer eligibility/deadline confirmation and final
submission media. Authorised bank/biller connectors are required for a real payment
product. The review feature alone is not proof the entire hackathon submission is
complete or award-winning.

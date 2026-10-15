# Statement-first Financial Friday — 0.24.0

Date: 15 October 2026. Deployment identities and activation are recorded separately
in CURRENT_RELEASE.json; source changes alone do not update Cloud Run.

## Product decision

The primary task is understanding existing financial history without daily entry:
upload supported statements, review the interpretation, see spending patterns and
ask for one practical next step. The earlier diary, runway, financial-request
checks and artificial-payment safety engine remain secondary tools. No bank
connector, extra Google-app OAuth scope, training corpus or new cloud service was
added. This is financial assistance/document intelligence, not an investment
adviser, guaranteed fraud detector or complete personal-finance autopilot.

## Implemented

- Guided Home, Upload, Review, Spending, Friday and Account screens using existing
  approved palette/assets; technical/optional tools leave the first-use screen.
- Actual Google identity shown from verified IAP claims. Local preview is explicitly
  Local demo. Reused Google SSO sessions are explained rather than called a bug.
- INR CSV exact parsing and bounded PDF extraction with live Gemini proposals.
  Text PDFs use pypdf; scans require existing Document AI OCR. PDF source IDs and
  literal amount/date/description checks reject unsupported output. These are
  evidence checks, not proof of complete extraction or statement authenticity.
- User-reviewed private normalized rows; no raw PDF/CSV storage. Strict typing,
  source hash replay guard, revision/generation isolation, transactional Firestore
  and SQLite updates. Ten imports/2,000 rows/800 KB limits fail without eviction.
- Reversible exclusions, overlap candidates retained/warned, complete bounded
  monthly/category calculations. Generic credits are not salary. Loans/refunds,
  transfers, card repayments and loan repayments remain distinct.
- Statement-coaching consent is separate. Only aggregates/formatted rupees and
  warnings enter the chat context; no account nicknames/descriptions. Unsupported
  explicit rupee amounts and unavailable evidence citations are rejected. This
  does not prove every natural-language statement is correct.
- Privacy cleanup also clears statement history and invalidates prepared imports.
  Existing payment journals are preserved. No production payment capability.

## Verification

Native: 544 ran, 543 passed, 1 optional skip. Docker: 544 ran, 521 passed,
23 optional skips. Tooling: 24 passed. New tests: 15 statement tests, one
profile test and two privacy-safe gateway-error tests, including actual generated PDF text parsing, mocked model boundary
checks, conservation of calculated totals, no bank/diary mutation, tenant
isolation, stale/conflicting saves, replay, reversible exclusion, privacy cleanup,
source mismatch, exact aggregate rupees and transactional callback retry/failure.

One real local Gemini API call read an artificial two-row PDF: identified income
INR 45,000.00, classified spending INR 2,500.00, proposal remained unsaved.
This is a live smoke test, not an extraction-accuracy benchmark. Staged Vertex,
Firestore and public-browser outcomes are recorded below, not assumed.

### Hosted acceptance and rollout

Both listed revisions now serve 100% of their existing services. API source:
`bb99494a3e1689c28da2e3a33462b0ca230c144b`; final web source:
`0fb6a1f67be0ac996d917909b994056bbc45176a`. Exact digests/build IDs are in
CURRENT_RELEASE.json. Earlier web builds were superseded before rollout; no
failed or unfinished frontend was promoted. A final privacy-safe statement-error
fix then replaced the first public statement frontend; both remain recoverable.
Existing Google IAP, private API IAM,
signing configuration, resource caps and rollback revisions were preserved.

`tools/verify_statements_cloud.py` used a new synthetic visitor workspace, read
an artificial two-row PDF with real Vertex, checked INR 45,000.00 identified
income and INR 2,500.00 spending, verified unsaved preparation, Firestore save
and readback, identical-source replay, real aggregate coaching, exclusion and
cleanup of that test workspace. The artificial bank balance was unchanged.
The private API rejected an anonymous request with HTTP 403. No new recovery
dispatch, bank integration or model training was performed.

The public Google-authenticated site showed the actual signed-in account and
completed an artificial CSV upload through the web gateway into an unsaved
review. No statement was saved into the owner's hosted history for this check.
The local browser additionally completed review/save, charts and live coaching.
These checks do not establish correctness on all real bank formats.

The hosted coach also completed a generic Vertex reply with every financial
context option off. An intentionally malformed artificial CSV produced a
statement-specific, recoverable error without saving rows or directing the user
to retry a payment. The phone-width home check measured 390 px viewport/content,
358 px main content and 44 px minimum measured button height. The temporary
viewport was reset. This is a spot check, not all-device/accessibility certification.

### Flow audit and interpretation

1. Home: verified focused entry, replacing the former diary/inbox/runway cluster.
2. Upload: verified explicit file/processing choice and separate unsaved review.
3. Review: verified totals, repeat-row warning and expandable interpretation edits.
4. Spending: local browser and private hosted acceptance verified exact persisted
   calculations; not a claim that a real customer's complete finances were tested.
5. Friday: real model guidance checked separately from financial execution.
6. Account: public verified identity display and existing-session explanation.

The approved visual palette/assets were retained; the audit changed hierarchy
and workflow rather than adding another decorative theme. Screenshot-only review
is not accessibility certification. Broader keyboard, device and bank-layout
validation remains necessary.

## Deliberate limits and next validation

INR only; PDF 4 MB, six pages/200 proposed rows; documented CSV schema, 1 MB/500
rows. One month can start the workflow. Six months is possible across supported
exports, not guaranteed to fit every bank's pages/format. Passwords are never
accepted. Users unlock locally and remove identifiers; minimization is best effort.
Existing OCR daily cap remains 100 pages; no resource/IAM limits were expanded.

No independent balance reconciliation or bank-issued authenticity check yet.
PDF completeness is a model assertion plus user review. Real bank layouts,
multi-line narratives, card payment credits, refunds, date/currency ambiguity,
low-quality scans and overlap patterns need a consented, independently labelled
evaluation before claims of broad bank compatibility or financial usefulness.

Asset values, outstanding principal/APR, repayment priority, net worth and exact
interest savings require actual loan/asset records; repayment rows are not a
substitute. Dedicated loan-summary extraction is not implemented. No continuous
tracking, external alerts or claim that users cannot run out of money. Future
imports extend the record only when the user supplies them.

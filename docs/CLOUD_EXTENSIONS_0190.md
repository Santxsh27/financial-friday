# Financial Friday 0.19.0 — bounded cloud extensions

The upload workflow can combine independent Google Document AI OCR with live
Gemini on Vertex AI. OCR supplies text/page/line anchors; Gemini extracts typed
financial claims; exact code checks amounts and quoted support; Firestore stores
the tenant-isolated review. Neither OCR nor Gemini authenticates the issuer,
recipient ownership or a real payment.

## Admission and cost boundaries

- The approved basic OCR processor is in Mumbai (`asia-south1`), with no reserved
  capacity or custom extractor. This does not make all model processing India-only;
  Vertex remains configured at `global`.
- PDFs are parsed before cloud processing: unencrypted, valid, one to three pages.
  The existing 8 MB upload limit remains. PNG/JPEG/WebP are single-image inputs.
- An atomic, application-wide UTC-day allowance admits at most 100 OCR pages.
  Failed admitted requests consume allowance too. Operators may lower this limit
  but cannot raise it above 100 through configuration. Other Google Cloud workloads
  and fees are not bounded by this counter; it is not a billing-account hard cap.
- Cached model-only reviews are not silently relabelled as OCR verified. A changed
  processor gets a new review identity and keeps old evidence intact.
- Exact anchored text/readability is visible under source evidence. Unsupported
  important fields remain unverified. Old contradictory evidence is not erased.

## Recovery implementation — inactive until separately approved

The code includes a Cloud Tasks dispatcher and private worker. Activation requires
the specifically approved dedicated identity, queue and scoped IAM bindings.
Enabling the Cloud Tasks API alone does not activate dispatch.

The scheduler admits at most 50 recovery jobs across the app per UTC day. It
schedules a signed, minimal journal-only envelope before a permitted artificial
posting. If scheduling fails, a new posting is held. The worker verifies the exact
Google OIDC identity, signed scope, expiry, task digest and lease. It can read an
existing journal outcome; it cannot call Gemini, execute a payment or blindly retry.
Stale deliveries cannot overwrite a later lease. An absent receipt stays unknown.

A controlled response-loss test flag is explicit and artificial. Unit tests verify
one posting and read-only recovery; they do not prove real Cloud Tasks delivery,
an actual process crash, external settlement or recovery at a real bank.

## Verification and release

Native checks: 439 ran, 438 passed and one optional skip. Tooling: 15 passed.
Docker: 439 ran, 420 passed and nineteen optional skips. Both Cloud Run services
now serve the tested `ocr0190b` revisions. The live artificial PDF passed OCR,
Vertex extraction, exact anchors, Firestore readback and cached replay, with zero
payment requests and unchanged balance. API anonymous access was rejected.
The Google-sign-in browser journey also uploaded the artificial PDF, saved its
claim, opened the obligation and displayed six independent page-one source
anchors. Missing provider evidence correctly left it at verification needed;
uploading did not create a payment. No browser console errors were captured.
See `CURRENT_RELEASE.json` for the actually deployed version and live evidence.
The new OCR cloud acceptance probe uses one fresh synthetic visitor and artificial
PDF, reads it back from Firestore and repeats the upload without any payment request.
Never substitute these engineering checks for an independently labelled evaluation.

The first live probe exposed an omitted currency quotation. The verifier now
requires important fields to be grounded even when the model omits a quotation.
An explicit unique currency on the anchored total's same OCR line can supply
currency evidence; a bare dollar sign, different line, mixed codes or poor
readability cannot. Four regressions cover these cases. No failed candidate was
promoted to normal traffic.

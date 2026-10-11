# Friday core and independent outcome replay — 0.17.0

## What changed

The selected Money Journey layout remains. The assistant is now code-rendered,
not a raster image: perspective-projected segmented orbits, foreground/background
depth, moving particles, a breathing energy core and pointer parallax. Pending,
held, attention and completed states use distinct colours plus written labels.
Animation never advances financial stages. Home resets to readiness when no task
is running. Singular bill labels were corrected.

Rendering shares one approximately 30-fps loop, caps pixel density at 2, pauses
when the document is hidden and renders only visible cores. Motion-off and system
reduced-motion settings stop movement while preserving state colours and text.
It is a Canvas 2D renderer using 3D projection mathematics, not Three.js/WebGL,
microphone activity or continuous bank monitoring.

## Security depth: independently replay a saved result

New runs capture the exact goal and provider evidence. Terminal results receive a
domain- and tenant-bound Ed25519 signature over the run digest. SQLite and
Firestore transactions store that seal alongside the financial outcome.

The final response and subsequent read-only receipt loading:

1. Verify the complete run signature and tenant binding.
2. Recompute program safety from the historical evidence snapshot, not a stored
   `passed` flag or today's mutable provider record.
3. Verify the payment signature, approved recipient, currency and amount bound.
4. Read the independent tenant payment journal and require an exact receipt match.
5. For newly created payments, require exact replayed total, goal, idempotency
   identity and evidence digest.

Conflicts appear as attention, not a successful result. A verified hold remains
different from a successful payment; a signed recovery record does not claim
external settlement. Legacy runs remain explicitly unsealed—never retroactively
certified. Reading evidence does not call Gemini or execute a payment.

This detects accidental or unauthorized stored-result changes. It does not defend
against compromise of the signing service/key, establish merchant honesty or prove
real-bank settlement. The payment journal is a separate record, not an independent
institution. Production requires partner access, key governance and operational
review.

## Validation and audit

Native application suite: 301 tests, 300 passed and one optional skip. Tooling:
eleven passed. New coverage includes changed goal/evidence/program/outcome/events,
cross-tenant access, forged pass flags, missing/corrupt journal, re-signed wrong
recipient, legacy runs, distinct holds/recovery and complete JavaScript parsing.
Firestore restart contract tests also require verified readback.

The subsequent browser check found a historical-receipt mismatch between the
planner and executor. Both now use the same local bill-identity resolver; a
historical paid bill is not offered for payment again. A tenant-isolated regression
test covers this migration case. JavaScript execution tests also ensure a stored
success label cannot override a failed independent verification in the simplified
UI. The replay panel was moved into the visible evidence disclosure.

The Product Design audit guided the scoped redesign. Fresh screenshots cover
Home → bill plan → Activity → saved outcome. Initial cloud receipt loading showed
an unavailable state; a later read-only reload succeeded with HTTP 200. No payment
retry was used. Further browser and cloud release results are recorded below after
verification. This is not an exhaustive audit, a fraud benchmark or a winning claim.

## Submission boundaries

Owner-only IAP stays enabled. Judges still require explicitly enrolled identities
or organizer-approved access. Real bank/SMS integration, external settlement,
native voice, durable cloud monitoring and production source-code repair are not
implemented. Video, deck, dashboard requirements and eligibility still require
final submission work.

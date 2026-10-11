# Friday core and independent outcome replay — 0.17.0

## What changed

Visual revision, October 11: the initial tilted-orbit design below was replaced
with an original front-facing instrument aperture at the user's request. The
current renderer is `INSTRUMENT_APERTURE_CANVAS`: nested segmented rings, offset
notches, a hollow central aperture, rotating scan arcs and corner brackets. It
contains no imported movie graphics or planetary/orbital geometry. Existing
state colours, bounded animation, reduced motion and all financial behaviour
remain unchanged. This is an original HUD-inspired implementation, not a legal
clearance claim or exact reproduction of a film interface.

The visual-only source `d181f15` was built by Cloud Build
`456ede2c-0252-4fa5-aba7-b2368213c3a8`. Web revision `hud1011` now serves 100%
using image digest `sha256:59cbe706852a98a884de65298fea4f0987726023b265505db0fd82963dc5d454`.
The API remains on `core1011b`; no financial logic, access or model settings were
changed. Native validation: 301 tests, 300 passed and one optional skip. Docker:
301 tests, 289 passed and twelve optional dependency/integration skips. Browser
rendering and motion pause passed without errors. Original release details below
describe the earlier orbital variant; this update supersedes its visual design.

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

## Verified release — October 11, 2026

Source commit: `9a496981b823e63754d19ec5256340fab4832443` (includes
`fd9d318`). Cloud Build `88588470-6fc7-40ca-8cb6-796e7be54e2e` succeeded.
Both API and web now serve 100% from their `core1011b` revisions, using the
same immutable container:

```
asia-south1-docker.pkg.dev/project-70f2c2d7-4e72-4e59-b14/financial-friday/api@sha256:0aee5796a98c9fb9019b6d2bab85cc963b85dc01caee504ef74763ac1d6b60fe
```

The candidate was deployed with zero traffic before verification and promotion.
Existing IAP, service identities, secrets and private API access were retained.
Stable private API verification then passed with version 0.17.0, transactional
Firestore, consent rejection, anonymous access rejection, unchanged balance and
zero payment requests. Cloud follow-through remains deliberately disabled.

### Scoped journey audit

1. **Home — healthy.** Live core frame count advanced from 457 to 722; it is
   rendered by `PROJECTED_3D_CANVAS`, not an animated raster. Home says “Friday is
   ready” rather than inheriting a prior outcome. Desktop and earlier 390 × 844
   mobile checks retained readable navigation. Motion-off stopped rendering.
2. **Fresh bill → allowed action — healthy in local sandbox.** A newly published
   test-provider bill, CORE-1011-1743, used a live Vertex planning call and recorded
   exactly one INR 1,783.41 artificial payment. Run
   `ff_e495a500812b4d46a99e32593e009c9d` loaded read-only with `VERIFIED` replay:
   signature, safety recomputation, recipient, separate journal and exact effect
   checks. The replay panel is visibly reachable in the evidence disclosure.
3. **Unsafe plan → hold — healthy on cloud.** Live Vertex proposed three unsafe
   plans; the checker rejected all three. Run
   `ff_e57fe2bea6b7477882fd02c726cf8c2a` returned `VERIFIED_HOLD`, unchanged
   balance and no new payment. Its live browser view shows a red held core, three
   rejected proposals, “No money moved” and signed read-only hold evidence.
   A separate paid-notice interpretation also passed without payment requests.
4. **Documents/spending — navigation healthy, not a new feature certification.**
   Document upload shows format limits and raw-file privacy rules. Spending review
   requires explicit CSV-processing consent and states that it cannot pay.
5. **Activity/readback — healthy for checked runs.** Reopening evidence is a GET,
   not another execution. Browser console checks returned no errors/warnings.
   Legacy results remain unsealed; current replay conflicts suppress success UI.

Native revalidation: 301 tests, 300 passed, one optional skip. Tooling: 11 passed.
Existing local API, web and ledger containers remained healthy. Screenshot
evidence is saved in the workspace's `audit-friday-core` directory: before/after
Home, mobile, successful replay and live held replay. These targeted checks do
not establish broad fraud accuracy, production bank access or exhaustive UX quality.

# Money buddy 0.23 — daily check-in with exact bookkeeping

This builds on the approved Financial Friday interface rather than replacing the
security workflow. It adds My money today, a private user-reported diary, chosen
buffer coverage and separately consented Gemini coaching. It does not claim a
new financial-assistant category, official credit score, bank integration, profit
guarantee or independent accuracy certification.

## Actual flow

Opening cash/buffer → check-in text explicitly sent to Gemini or manual entry →
visible unsaved proposal → explicit private save → exact totals/meter → optional
coaching from aggregates → optional future Money Runway scenario.

UI retains the approved palette and existing original companion artwork. A short
typing introduction settles into readable text; companion movement follows actual
request state. Reduced motion and hidden-tab cancellation apply. Input is not
logged on every keystroke or monitored in the background. Undo uses an inline
review panel, not a disruptive browser confirmation.

## Safety and storage

- Diary ≠ bank ledger. The opening figure and every entry are user reports.
- Gemini has no tools. It selects IDs from server-separated source snippets;
  code attaches their original quotations. Literal INR amounts need exact
  Decimal equivalence to one printed rupee amount and explicit English direction cues.
  Display markers/grouping are normalized, never currencies or units. Another date, future income,
  currencies and magnitude conversions use manual entry or the runway plan.
- Human confirmation is mandatory. A model proposal cannot save or pay.
- Writes bind operation ID, complete request fingerprint, expected revision and
  workspace privacy generation. Exact replay returns the current diary without
  duplicating the group; stale/altered requests fail.
- SQLite immediate transactions and Firestore transactions protect the same
  transition. Group Undo keeps entries but excludes them from the totals.
- 100 entries/200 operations are explicit capacity limits; no silent eviction.
- Cleanup invalidates in-flight writes and removes the diary. Export is an
  on-demand local download of the returned diary, not an external upload.
- Independently opted-in chat context is aggregate-only, with formatted INR
  strings. Entry notes/raw messages stay out. Unsupported explicit rupee figures
  fail the existing gate; this does not establish complete semantic correctness.
- Existing login, action quotas, signing, artificial-payment approval and recovery
  policy remain. No bank, account, Gmail or SMS permissions are added.

## Verification

24 diary feature tests cover empty state, exact arithmetic and negative cash,
capacity, source-anchored proposals, unavailable Gemini/manual fallback, consent,
tenant isolation, stale tabs, exact replay, group Undo, privacy barriers and actual
Firestore transaction callback retries/failure. Native: 526 ran, 525 passed,
one optional skip. Docker: 526 ran, 503 passed, 23 optional skips. Tooling: 24 passed.
These are implementation checks, not independent fraud or usefulness benchmarks.

Local browser confirmed opening artificial cash of ₹8,000, an unsaved manual
₹250 preview, explicit save and updated ₹7,750 cash. API/model cloud acceptance
and final source/revisions are recorded in CURRENT_RELEASE.json after rollout.
Browser tooling stalled on an initial native Undo popup; the final UI replaces
that native popup with an inline confirmation rather than bypassing it.

Initial zero-traffic cloud acceptance exposed source-quote reproduction failure,
then a schema mismatch where Gemini returned currency-marked amount strings.
Those revisions were not promoted. Server-owned source IDs and exact INR-literal
normalization resolve the identified shapes without giving the model save/payment
authority. The corrected parser passed a real fixed-synthetic Vertex call. Runtime
Firestore/replay/Undo/aggregate coaching acceptance is tracked separately in the
release manifest; a local SDK call is not substituted for runtime verification.
No personal records or credentials were logged. Earlier failed synthetic runs may
retain their artificial opening diary; do not claim those were erased or purge
other workspaces to clean them up.

## Remaining limits

No automatic transaction collection, validated credit score, trained personal
model, bank reconciliation or guaranteed “never broke” outcome. No automatic
payments or authenticated recipient data. The diary requires periodic user
updates and can be incomplete. The meter is target coverage, not a risk model.
Daily entries and future scenarios remain separate to avoid silent double counting.

# Money Journey design QA — 0.16.0

## Current update — 0.17.0

The historical raster-orb limitation below is superseded: the companion and brand
now use a live Canvas renderer with perspective-projected orbits, moving energy,
pointer parallax and evidence-driven status colours. This is not WebGL, voice
activity or a bank monitor. Motion-off and reduced-motion pause animation.

Fresh scoped checks cover Home, bill planning, Activity and successful receipt
replay. The independent replay panel is visible inside “How Friday checked this”.
A returned evidence conflict cannot be overwritten by the outer success renderer.
Document and spending navigation retain their input/privacy controls. Desktop and
390 × 844 mobile were inspected; this is not full accessibility certification.
Current implementation, test and cloud evidence: `docs/FRIDAY_CORE_0170.md`.

Status: passed for the scoped Home → Bill plan → Run → Activity journey.
Date: 11 October 2026. No claim of complete accessibility certification.

## Reference and fidelity

Selected third Money Journey concept, refined into dark jade, mint, ivory and coral.
Compared the reference and running plan together at 1487 × 1058. Hierarchy,
two-column plan/detail relationship, reserve ribbon, outlined checks, companion
and primary action were retained. Deliberate differences: actual provider records
and balances instead of mock values, a native numeric meter, fewer decorative
icons, explicit artificial-money consent, expandable evidence. This is an
improvised implementation, not a pixel-identical claim.

Comparison and desktop/mobile screenshots are saved outside the repository at
`/Users/santosh/Documents/Codex/2026-09-10/ok-this-fraudlens-replay-or-watever-3/audit-friday-jade/`.

## Verified

- Desktop plan: readable hierarchy, evenly separated list/detail, selected row,
  review reason, recipient and actionable button visible without an evidence dump.
- Home and plan at 390 × 844: document width equals viewport width (390 px);
  content stacks without horizontal overflow. Navigation and bill selection work.
- Working stages stay pending; the backend response controls completion/hold.
- Live Vertex run JUDGE-7430: one planning call, one INR 1,850 artificial payment,
  receipt in Activity; no browser console errors. Earlier held outcome remains
  independently visible. Completed records disappear from unpaid selections.
- Help opens with keyboard focus; Escape closes and restores focus.
- Motion toggle disables all three companion animations; restored after testing.
- Buttons expose text/status beyond colour, visible focus outlines, pressed/current
  semantics; ambiguous outcomes direct customers to recorded evidence.
- Original fixed-sidebar CSS conflict corrected; primary action compacted to remain
  visible at the reference desktop size. Stale saved-run fetches cannot override
  navigation away from the result screen.
- Native suite: 287 tests, 286 passed, one optional skip; tooling: 11 passed.
  Runtime Docker: 287 tests, no failures, ten optional dependency/integration skips.
- Stable Cloud Run site: protected asset and plan loaded, then live Vertex rejected
  two proposals and corrected a third before one INR 2,479 artificial payment was
  recorded transactionally. Result colours and stages reflected that evidence;
  no browser errors. Source/deployment identifiers are in the release notes.

## Remaining boundaries

Other existing document/rules/safety-lab routes retain their working controls under
the shared palette; this report does not claim an exhaustive visual audit of every
historical route. Screen-reader/device coverage and independent usability research
remain future work. The orb is a generated raster asset with cosmetic motion, not
a live microphone, background bank monitor or WebGL engine. Real payments and
external provider confirmation are not connected. Cloud release evidence is in
`docs/MONEY_JOURNEY_0160.md`; judge access remains a separate enrollment task.

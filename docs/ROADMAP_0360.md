# Conversation-first roadmap · 0.36.0

Goals now centres on one conversation and one saved priority, not a large purchase
form. Purchases, cash savings and a chosen emergency reserve share one exact
planning engine. The progress ring, three metrics, milestones and baseline/stress
chart carry the main output. Explanations and exact tables stay collapsed.

Gemini interprets the goal and proposes quote-bound numbers. Missing facts are
asked one at a time; literal follow-up amounts use validated slots, not extra model
calls. Historical statement averages reduce typing after local acceptance. They
are not automatically sent to Gemini or interpreted as current liquid savings.

Confirmed roadmaps restore across sessions. Additional savings reports require
confirmation; Undo changes bookkeeping only. Replacing the priority archives the
old snapshot. The older three-purchase/loan calculator remains under Advanced,
separate and unsaved. Public Google Search research is unchanged.

## Safety and scope

- Integer-paise math; monthly contribution rounds up by one paise when necessary.
- Purchase/savings excludes the protected reserve; new savings fill any reserve
  gap first. Reserve goals include existing liquid savings.
- Passing time, importing statements or reducing spending cannot increase actual
  progress. Future points assume the displayed monthly contribution.
- Stress: income −10%, living costs +10%, existing debt fixed. No return forecast.
- Year-only requests propose a December date, disclosed before saving.
- One active priority; 5 archives, 100 reports, 200 changes. Export before explicit
  cleanup if these bounded prototype limits are reached.
- Existing authenticated tenant access; no IAM expansion. Mutations bind operation
  identity to payload and check revision/privacy generation inside a transaction.
- Goal transcripts are not stored. Confirmed assumptions/reports are private data.
  Explicit input cleanup removes them, including archives, and invalidates old writes.
- Coaching shares only confirmed assumptions and exact summary/milestones after
  opt-in. Explicit INR amounts and citations are checked; this is not semantic proof.
  Changed goals/cleanup invalidate stale model replies. AI has no save/payment tools.

## Verification and release

[CURRENT_RELEASE.json](CURRENT_RELEASE.json) records actual source identities,
test outcomes, deployed artifacts and completed browser/live checks. Source changes
alone are not deployment. `tests/test_friday_roadmap.py` covers math, strict input,
tenants, replay, conflicts, archives, Undo, cleanup, Firestore callback retries and
commit failure, source quotes, model consent, stale replies and explicit INR checks.

This is a bounded hackathon prototype, not an audited financial adviser. Human
gates remain: another person's real Google login, private source invitations,
dashboard eligibility/deadline, final submission form, video/deck. No winning,
wealth, reimbursement or universal bank support is promised.

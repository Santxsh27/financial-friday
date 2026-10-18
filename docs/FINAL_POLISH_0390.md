# Final workflow and voice polish · 0.39.0

18 October 2026. This is a focused reliability/clarity release, not a claim of
universal accuracy, uninterrupted availability or a perfect production product.
Deployment identities and final acceptance are recorded in CURRENT_RELEASE.json.

## Fixed from captured evidence

The previous Read last reply control directed users to a small checkbox; long
answers were refused; a busy speech request could silently discard another reply;
Stop did not invalidate a still-loading response. Research cards and saved visual
goals were not consistently available to the spoken-reply control.

- Explicit **Enable voice & read** choice and visible enabled/off/loading/waiting
  states. Voice is not enabled by page load or a microphone action.
- Pure, tested generation-bound playback queue: latest reply wins, minimum gap
  respects demo pacing, duplicate in-flight clips coalesce, Stop/revocation/reset
  discard stale results, one clip can replay from page memory.
- Long replies use an extractive ≤60-word/480-character preview, labelled as a
  preview. Full answer stays on screen. No extra model summarisation.
- Visible audio Play control when autoplay is blocked; distinct 429/sign-in/provider
  states. No fake local voice: the implemented service requires Vertex AI.
- Recording uses **Record & send to Google** after the explicit notice, replacing
  the redundant consent checkbox. Browser microphone permission is still required;
  the transcript must be reviewed and sent separately. No agent microphone recording.
- Public research progress text is not narrated as an answer. Source cards and
  visual goals expose bounded displayed text to Read last reply.

Stop cancels playback/queue, not a Google request already transmitted. Voice has
no action tools or access to a financial account. Audio stays in page memory;
New chat/cleanup disables speech and clears its replay cache.

## Small goal improvement

Short budgets label their monthly amount **Budget supports / month**, count all
four scenario outcomes, and offer **Preview this option** on smaller-target and
longer-timeline cards. The existing budget is reused without a new AI call, save
or payment. Saved priority remains unchanged until Confirm & save. Dated
checkpoints, protected reserve and known/unknown factors are retained.

## Judge and Desktop handoff

New `judge-kit/` has five fresh, explicitly artificial 42-transaction six-month
CSV layouts, independent exact source controls, provenance and a short journey.
Hosted allowlisted downloads match the GitHub files byte-for-byte. The same
five files are copied to `Desktop/Financial Friday Testing/Statements/`, with
START-HERE and personal TEST-NOTES outside the repository.

HDFC/Kotak headings are illustrative, ICICI is an unverified synthetic candidate,
and two generic files test delimiters/column order. The five files contain the
same activity, not five accounts. Unknown source checks remain Unknown.

Source stays in Desktop/CARAPACE to preserve paths. The obsolete local guide kit,
including its bill-era PDF, was moved recoverably to
`archive/superseded-guide-kit-2026-10-18/guide-kit/`. No user records, secrets,
Git history, containers or volumes were deleted. Older committed regression
fixtures remain under `jugges/`, clearly labelled as older.

README now has an actual home screenshot, artificial goal screenshot, architecture
diagram, short walkthrough, implemented Google stack and explicit limits. Public
repo description, hosted walkthrough, account/access page and user guides are synced.

## Audit journey and health

1. **Home and navigation — checked.** Existing approved design retained; no new
   theme or unrelated feature expansion.
2. **Upload → review → save → charts — checked locally.** Fresh CSV gave 42 rows,
   ₹3,00,000 identified income, ₹1,34,694 classified spending and ₹30,000 repayments.
   Prior test import was excluded via selection, not deleted.
3. **Details → Back → source selection — checked locally.** Current source banner
   and review revision track the selected statement.
4. **Goal → short budget → alternative — checked locally.** ₹35,000 income gave
   ₹5,000 capacity; smaller-target preview changed ₹1,20,000 to ₹80,000 without a save.
5. **Voice — unit and live acceptance scope in manifest.** Real generated Google
   speech roundtrip is separate from human microphone/speaker verification.
6. **Responsive, dark, profile and hosted access — final checks in manifest.**

Native regression suite and offline cloud-tool tests are rerun. The first clean
local Docker dependency download timed out at the package host; existing services
were not deleted. Local verification reused the unchanged installed dependency
images with new source; cloud builds use the existing immutable release base.
Do not describe this as a newly resolved/pinned dependency audit.

## Remaining human gates

- Test an actual microphone and speaker on the presentation device; browser or
  operating-system permissions, muted output and autoplay policy are external.
- Have another person complete Google sign-in and open the app. Current public
  GitHub and authenticated IAP policy are checked, not a universal login guarantee.
- Complete the video, proposal and dashboard submission, eligibility and deadline.
- Broader authorised real-bank samples, independent AI evaluation and production
  security/operational review remain necessary beyond this prototype release.

Current tracked-file secret-pattern scan found no matching credential file;
only `.env.example` is tracked among environment/key/database filename patterns.
A full-history filename scan hit a local Git mmap timeout, so a complete historical
secret audit is not claimed.

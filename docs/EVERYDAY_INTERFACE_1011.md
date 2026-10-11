# Everyday interface — selected option 3

Financial Friday now uses one ivory/peach/navy design system, replacing active
historical themes. The homepage is a current bill inbox beside an assistant dock,
with safety rules, task shortcuts and receipts. Other task screens share its forms,
navigation and evidence-driven outcomes.

## Implementation and resources

- `friday_everyday.py`: presentation and tenant-scoped read-only home projections.
  Existing financial handlers, consent, reserve, verifier and receipt replay remain.
  Bill selection resolves a fresh plan instead of reusing stale review hashes.
- `friday_experience.py`: installs one design system rather than stacking themes.
- `friday_assets.py`: explicit asset allowlist for local/cloud routes. Cloud IAP
  remains required; unknown names return 404.
- Original generated transparent companion, windowsill and brand images.
- Inter: official Google Fonts `ofl/inter` distribution, SIL Open Font License.
- Feather 4.29.2: official `feather-icons` npm distribution, MIT license.

Font, icons and licenses are self-hosted; there are no runtime asset CDN requests.
The companion has cosmetic motion, not live microphone or banking activity.

## Boundaries and tests

Only artificial funds can move. No real bank/email connector or new financial
authority was added. Document reading alone doesn't authorize payment. Checking
a bill message can execute an artificial payment under saved permission; the action
discloses this. Current bill/receipt values come from APIs, not mock constants.

307 application tests: native 306 passes / one optional skip; isolated Docker 295
passes / twelve optional skips. Eleven tooling tests pass. Visual evidence and
iteration history are in [`design-qa.md`](../design-qa.md).
Verified Cloud Run release identifiers are appended after deployment.

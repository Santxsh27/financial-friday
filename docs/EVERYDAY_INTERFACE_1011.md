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
## Verified Cloud Run release

- Full clean-source build: `e194425c-d67a-4e9b-88e0-25ec2e049b31`, source `4a186b6`.
- Final web-layer build: `934dda46-e4e4-4494-9a22-0bf7de103aec`, source `b7ca9af`.
- Immutable final image: `sha256:00795154e53398bf04674fd0f21e130f89a976482bd85ac6f695537b4812991f`.
- Web revision: `financial-friday-web-everyday1011`; private API remains `core1011b`.
- Existing live URL: `https://financial-friday-web-171681243260.asia-south1.run.app/`.

The zero-traffic candidate loaded current cloud records and every home image,
selected the exact ₹2,479 provider record with its recipient, and returned no browser
errors. Read-only backend verification confirmed version 0.17.0, unchanged balance,
no payment authority in the plan, rejection of unconfirmed execution and anonymous
access, disabled cloud follow-through, and zero payment requests. No live AI call
or new payment was made for this presentation release. IAM/IAP settings are unchanged.

`Dockerfile.web` now copies the complete UI package over the immutable tested base,
including all imported modules and assets. `cloudbuild.web.yaml` supports repeatable
web-only builds without rebuilding dependencies or replacing the API.

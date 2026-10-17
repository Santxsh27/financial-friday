# Statement-first submission release 0.34.0

Prepared 17 October 2026. This document separates tested software from pending
human validation and submission artifacts. It does not certify an error-free
product, production banking readiness or a competition result.

## What changed

- One consumer journey: statement upload → source review → saved visual analysis
  → optional Gemini guidance. Existing profile, theme and voice remain visible.
- The separate bill/receipt inbox is removed from consumer navigation, API and
  OpenAPI admission. Its sharing flag is rejected before private context/model
  access. Historical code remains behind explicit legacy opt-in; no stored
  owner records or journal/recovery targets were deleted.
- Consumer Gemini receives statement-only scope. Old typed document/inbox
  destinations are normalised into supported statement destinations.
- A static, accessible walkthrough is served by the app with six artificial
  downloads. It does not depend on private GitHub access, auto-upload a file,
  start a model request or grant permission.
- HDFC/Kotak public-illustration files, the unverified ICICI candidate and two
  generic CSV variants now have clear bank/synthetic names. Their bytes and
  integer-paise controls are unchanged. The two-row generic-bank PDF is retained;
  the bill sample was moved to the ignored local historical archive.
- README, user guide and judge kit describe this product rather than the earlier
  collection of payment demonstrations. The physical working repo stays in
  Desktop/CARAPACE to preserve existing paths. Owner tests and old copies remain
  in ignored subfolders, not in the source upload or judge kit.

## Verification record

Native suite: 775 ran, 774 passed, one optional historical Anthos integration
skipped. Tool suite: 65 passed. Container, browser and live cloud results are
recorded below after completion and in CURRENT_RELEASE.json. Passing unit tests
are not evidence of representative AI accuracy or independent bank validation.

The bounded cloud verifier uses one new artificial visitor, five CSV previews,
one PDF extraction, one statement-based chat, a real Firestore source-selection
race and cleanup. It respects the existing burst allowance, makes no payments,
uses no owner financial history and does not increase permissions or quotas.
Its source is tools/verify_submission_cloud.py; offline controls reject live use
without an explicit flag and reject non-fixed API origins.

## Access and sharing

The existing IAP policy was read, not changed: it includes authenticated Google
users as accessors. Friday's web gateway derives an isolated visitor workspace
from a verified identity and never exposes the private API's credentials.
Organisational account restrictions and a second person's real login are not
established by this policy read. They still require a human test.

Share the canonical web link and its /assets/friday-judge-guide.html walkthrough,
not localhost, a staging tag, the API docs or a source-folder link. The repository
is PRIVATE: reviewers need invitations or an organiser-approved source-delivery
method. No visibility change or collaborator invitation was inferred.

## Remaining boundaries and honest claims

- Independent human labels and fresh authorised exports cannot be manufactured
  by this development agent. The 39-case synthetic corpus remains unreviewed;
  its published false warnings and misses are not hidden or relabelled success.
- The small Gemini benchmark records failures/follow-ups separately. Finite
  factual checks do not certify arbitrary explanations or future model behavior.
- Statement-only HTTP admission is not a complete service-account/process split.
  Legacy code remains retained; existing recovery keeps its narrow old boundary.
- Structured logs provide latency/model/usage/failure correlation. A response
  time target is not an SLA; alert delivery, exact billing attribution and
  continuous external availability have not been proved.
- No real bank, SMS/Gmail feed, payment, refund, subscription cancellation or
  live investment advice is claimed. Voice is optional generated speech, not
  a continuously listening assistant. No fine-tuning was performed.

## Human submission gates

The official site checked 17 October lists prototype submission on 18 October
2026 and evaluation 19 October–6 November. Confirm the exact dashboard cutoff,
working-professional/age/team eligibility and roster. A proposal deck/PDF and
public approximately three-minute video are listed requirements. Their completion
and final submission are not implied by this engineering release.

Sources: [official timeline](https://aibuildercup.com/),
[requirements and judging criteria](https://aibuildercup.com/themes.html).

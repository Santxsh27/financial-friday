# Soft Studio — selected interface release

The user selected the first of three independent design previews. This is a
presentation release over the existing statement-first system, not a new bank
integration or model-training claim.

## What changed

- Welcoming ivory/lavender/peach Home with an original friendly companion.
- One real Friday chat panel beside desktop Home, upload, review, Spending and
  Account; the same conversation node moves to a dedicated phone chat page.
- Explicit context-choice dialog, a visible sharing indicator, question drafts,
  New chat, busy/error states and privacy disclosure. Totals-only AI context is
  unchanged and starts off.
- Top-right initials/name menu: account, spending, privacy, appearance and
  Google sign-in help. Identity still comes from the verified gateway.
- Clear Add statement entry points, labelled illustrative empty-state charts,
  saved-history search and accessible transaction-table headers.
- Stale extraction totals are hidden after interpretation labels change; final
  totals are recalculated by the existing server when saved. Discarding a
  preview now resets the upload status.
- Removed background polling of a hidden legacy bill inbox locally. The
  existing server-side worker/Cloud Tasks mechanisms are not changed.
- Hosted Gemini follow-up links in the primary statement journey lead to
  statement upload, not the earlier optional bill/receipt document tool.

## Sign-in scope

IAP currently supplies the verified email/subject, not an application-owned
Google profile-photo record. The UI uses initials or a saved Friday nickname;
it requests no extra Google scopes. The account help links to the official
IAP `CLEAR_LOGIN_COOKIE` operation and explains that Google can silently reuse
its browser session. It is not represented as logging out of every Google app.
Reference: https://docs.cloud.google.com/iap/docs/query-parameters-and-headers-howto

## Asset provenance

- Existing original team mark and packaged FridayInter font retained.
- Existing MIT-licensed Feather family extended with home, upload, shopping-cart,
  coffee, truck and log-out from the official Feather v4.29.2 icon release.
- `src/carapace_integrations/assets/friday-soft-studio-buddy.png` was generated
  with the built-in image tool using the selected mock as its visual reference.
  It is a1254×1254 RGBA image with real transparency, reused for hero/chat.
- Selected reference: `docs/design/soft-studio-reference.png`; local screenshot:
  `docs/design/soft-studio-desktop.jpg`. Fictional/example labels are not
  financial records or hardcoded model outputs.

The asset-generation prompt requested an isolated, matching lavender
pear/pebble companion: glossy deep navy oval eyes, small curved smile, peach
cheeks, two little rounded arms holding an ivory statement sheet, soft premium
3D clay material, pale lilac highlights, gentle upper-left studio lighting,
whole character centred with6% transparent margin, abstract gray sheet lines
and a peach rectangle, no letters, UI, backdrop, extra objects or watermark.
Transparent-background generation was enabled. The original generated file
was retained; no screenshot crop or CSS drawing replaced the artwork.

## Verification and limits

See `design-qa.md` for comparison history, browser evidence and scope. Browser
tests used a separate local artificial workspace, not the owner's statement
history. Backend monetary calculations, tenant isolation, signing and the
private API are unchanged. The assistant still receives only explicitly shared
aggregate statement context; individual-transaction retrieval, comprehensive
loan/net-worth analysis and a bank feed remain future work. This release does
not certify fraud detection efficacy or financial advice quality.

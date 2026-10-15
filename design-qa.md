# Soft Studio design QA

Source visual truth: selected **Option 1**, `exec-9aa10f5e-b7a7-4abf-802e-96fd1aa2de29.png` in the Codex generated-images folder.

Implementation: `http://localhost:8092/?v=studio-qa#home`, isolated artificial QA workspace; normal Docker website remains on8090 with its records preserved.

## Comparison history

### Initial pass — blocked

- Source1487×1058; CSS viewport1487×1058, density1. Initial normal browser capture was1403px wide despite that CSS viewport, so it is not a valid full-frame comparison. A read-only CDP capture produced the full1487×1058 frame.
- Evidence: `/private/tmp/friday-studio-v1.png` (invalid cropped capture), `/private/tmp/friday-studio-v2.png` (normalized full frame), `/private/tmp/friday-studio-comparison-v2.jpg` (source left / implementation right).
- State: first use, light theme. Source uses fictional Asha and an open profile menu; implementation has the honest local identity and a closed menu. Account-open state will be captured separately.
- [P1] Original logo node was a sibling of the brand text, so rebuilding the header removed it. Fixed by reusing both nodes in a single brand group; present in v2.
- [P2] Suggested questions sat at the bottom of the tall conversation rather than next to the welcome. Fixed by placing them inside the conversation and restoring them on New chat; present in v2.
- [P2] Hero companion is smaller than selected reference; increase the hero asset slot without obscuring copy.
- [P2] Primary upload control and example-row text are smaller than the reference; tune product type/spacing.
- Semantic icon refinements are needed for grocery, transport and food rows.

## Fidelity surfaces

- Fonts: packaged FridayInter variable font; hierarchy and line breaks follow the target. Button and category-label scale still needs tuning.
- Layout: same warm page, horizontal header, welcome left and tall chat right. Mobile and tablet checks are pending.
- Colors: ivory/lavender/peach/mint mapped to theme tokens; dark mode still requires visual testing. Dark primary-button text is intentional for contrast.
- Assets: original team mark preserved; matching generated lavender buddy with real PNG alpha, not CSS art. Feather library icons reused.
- Copy: PDF/CSV only, not the mock’s unsupported image upload. Sample bars are explicitly illustrative, never saved financial history. Chat scope remains opt-in totals, not transaction-level memory.

## Open checks

- Upload → unsaved review → label changes → save → Spending, search and reversible import exclusion.
- Account menu, keyboard dismissal, context dialog, chat busy/error paths, appearance and reduced motion.
- No new model access or production financial authority.

### Corrected pass — passed

- Source normalized from1487×1058 to1403×998; implementation captured at CSS1403×998, density1, same light first-use state with the profile menu open. The fictional Asha identity is intentionally replaced by the real local-demo identity. No personal record is used as a visual fixture.
- Full-view evidence: `/private/tmp/friday-studio-comparison-final.jpg`, implementation `/private/tmp/friday-studio-final-desktop.jpg` (also `docs/design/soft-studio-desktop.jpg`), source `docs/design/soft-studio-reference.png`.
- Focused typography/CTA evidence: `/private/tmp/friday-studio-focus-final.jpg`. The hero type scale/leading, section rhythm, companion size and question placement were corrected after the initial pass. The packaged variable font is visually close, not an assertion of pixel-identical generated lettering.
- Feather grocery/transport/food/upload icons now have appropriate semantic roles and inherit accessible light/dark foreground colors. They are library assets, not handmade SVG art.
- Additional browser checks found a null legacy header-status reference. Both required status nodes are preserved hidden; a clean startup now has no recorded browser errors.
- Dark-mode black icons were corrected. Phone width390 has content width390, theme target44px, reachable account/settings and a dedicated real chat view. Motion emulation reports no companion animation under reduced motion; test emulation was reset.
- Browser flow: a new six-row artificial CSV was uploaded in the separate QA workspace, previewed unsaved, relabelled, saved, displayed as₹45,000 identified income/₹17,500 spending/₹5,000 loan repayments;₹50,000 borrowing was not counted as earned income. Search found exactly one grocery row. Reversible exclusion was checked without deleting it. The normal local and hosted owner histories were not used for this fixture.
- Context dialog starts unchecked, changes the visible sharing indicator, clears page chat and does not itself call Gemini. There is exactly one chat input. Local no-model error handling clears busy state and does not substitute a fabricated reply. Live hosted Gemini was checked separately after deployment, as recorded below.
- Keyboard profile navigation, dialog opening/closing and appearance controls were checked. The browser automation occasionally timed out after successfully opening a native dialog; subsequent fresh UI state confirmed the action. No app fix was inferred from the automation timeout alone.

## Expected differences and residual limits

- The mock's unsupported image statement upload is correctly reduced to PDF/CSV.
- Initials are shown instead of inventing a Google profile photograph/name; no OAuth scope was expanded. Google cookie clearing is explained honestly, not represented as global Google logout.
- Higher-contrast dark primary-button text replaces low-contrast white-on-coral. Source-colour values are represented by CSS tokens, not a promise of identical capture colour profiles.
- The mascot is matching generated artwork, not a cropped screenshot. Decorative annotation and accent swishes were initially omitted; the 0.25.1 pass below restores them at the user's request.
- On narrow screens, chat has a dedicated page and quick launcher rather than squeezing two desktop columns. Long transaction tables scroll inside their region. This is not full WCAG certification or exhaustive device testing.
- No new forecasting model, transaction-level chat retrieval, bank feed, profit guarantee or financial-action authority was added by this redesign.

## Final checklist

- [x] Typography, spacing, colours, image fidelity and meaningful copy checked against the selected image.
- [x] Initial P1/P2 visual and startup issues corrected and recaptured.
- [x] Primary statement/account/chat flows checked in the browser.
- [x] Mobile, dark theme, explicit context choice and reduced motion checked.
- [x] Native549/548passed/1skip; Docker549/526passed/23skips; tooling24passed. These are developer correctness tests, not independent financial efficacy measurements.

## Hosted acceptance

- Published frontend: `financial-friday-web-studio0250links`, source `9b251415850d14b1960248321363f74b720ab529`, build `6b6cc252-6570-4773-8785-5ff8566c2f81`. It serves 100% of frontend traffic. The private API remains on `financial-friday-api-statements0240r`; IAM and financial rules were not changed. Previous frontend revisions remain available for rollback.
- Google identity was displayed from the verified gateway. Three generic chat requests returned real Vertex AI replies (`gemini-3.5-flash-lite`), with all financial-context checkboxes off; the busy state cleared and controls became usable again. No browser console errors were recorded in the final hosted check.
- The first hosted check exposed a legacy bill-tool destination in a chat follow-up. The corrected source now maps this follow-up to **Add a statement** in the main statement journey. The actual Gemini-generated follow-up was clicked on the public site and opened the real statement intake.
- No statement was uploaded or saved to the owner's hosted history during these new checks. No money moved. Anonymous access to the private API returned403.
- Final public screenshot: `/private/tmp/friday-studio-live-final.jpg`. The additional hosted privacy notice is intentional; a local design fixture is not evidence that a hosted consent notice should be removed.
- These checks verify the exercised UI/API journeys, not every possible financial answer, device, PDF layout or accessibility requirement. They are not an independent financial-accuracy benchmark or WCAG certification.

## 0.25.1 — requested decorative fidelity pass

### Findings before changes — blocked

- [P2] Requested source details were missing: the lavender marker underline, handwritten note/curved arrow, peach/lilac dashes and grounded character shadow. Earlier acceptance had classified these as optional; the user's explicit request makes their restoration part of this release.
- Before screenshot: `/private/tmp/friday-accents-before.png`, captured from the published 0.25.0 page. The visible conversation differs from the first-use reference, so it is baseline evidence, not the normalized fidelity comparison.

### Corrected comparison — passed locally

- Source `docs/design/soft-studio-reference.png` normalized from1487×1058 to1403×998. Implementation `/private/tmp/friday-accents-desktop.png` captured at CSS1403×998, density1, light first-use Home, account menu open. Fictional Asha is intentionally replaced by local-demo identity.
- Full-view side-by-side: `/private/tmp/friday-accents-comparison.jpg`; focused hero region: `/private/tmp/friday-accents-hero-comparison.jpg`. New packaged raster assets restore all four requested decoration groups, not CSS drawings or a screenshot overlay.
- Typography: existing packaged font and three-line heading retained; the image underline sits behind the final phrase without changing its text. Handwriting is generated and somewhat more cursive than the source, an acceptable minor artwork difference.
- Layout: header, chat, CTA and statement flow unchanged. The new note occupies the clear top-right hero area, and the companion remains inside its slot with a feathered contact shadow. Decorative images cannot receive pointer clicks.
- Colour: lavender/peach source accents retained; note brightness is adjusted in dark mode, underline opacity reduced. Existing higher-contrast CTA text is intentional.
- Image quality: true-alpha PNGs, no opaque page backdrop, whole companion/sheet intact. Minor antialiasing at generated edges is acceptable at the measured display size; not a claim of pixel-identical assets.
- Copy: exact note **Same statements. More clarity.**; PDF/CSV support remains honest. No new financial capability or model authority is implied.
- Phone390×844: content width390; no horizontal overflow or note/title collision. Evidence `/private/tmp/friday-accents-mobile-v1.png`. Dark phone evidence `/private/tmp/friday-accents-dark-mobile.png`; account, navigation and main CTA remain usable. Existing reduced-motion selectors still govern the same hero/avatar classes.
- Real browser story: Desktop fictional CSV → server parse →19-row unsaved review → explicit save in a separate artificial QA workspace → Spending. Visible results: INR90,000 income, INR43,999 spending, INR10,000 loan repayments; card-coverage warning retained. No owner or hosted history was used.
- Desktop sample is a byte-for-byte copy of `examples/friday-artificial-statement.csv`; every description is marked ARTIFICIAL. CSV parsing uses no Gemini call. Any Gemini guidance remains an explicit, separately consented conversation.
- New checks: native551/550passed/1optional skip; Docker551/528passed/23optional skips; tooling24passed; JavaScript syntax and whitespace checks passed. Browser warning/error list was empty. Reduced-motion emulation returned hero animation **none** and was reset; the normal viewport and light theme were restored.

final result: passed

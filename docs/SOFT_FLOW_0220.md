# Soft flow — interaction-only UI refinement

14 October 2026. This preserves the approved palette, page structure, controls,
financial states and API contracts. Actual deployed web source/revision and
acceptance checks are recorded in [CURRENT_RELEASE](CURRENT_RELEASE.json).

## What changed

- Shared easing and short timings for button hover/press, focus and theme changes.
- Task cards lift gently with at most 0.7 degrees of pointer-driven perspective.
- A low-opacity click pulse, removed within 400 ms and hidden from screen readers.
- Short page/content/disclosure arrivals; no scroll hijacking or delayed navigation.
- Chat follows new messages only near the bottom or after your own message.
- Busy indicators on chat/runway submit controls follow actual request lifecycles.
- Existing keyboard focus, disabled controls, touch target sizes and motion settings
  remain authoritative. Colour/text still communicates held, pending and confirmed.

## Performance and privacy boundaries

Pointer decoration uses at most one queued animation frame, taking the latest
pointer position rather than processing every event. It cancels on leaving the
card, navigation, hidden tab, pointer-mode change or disabled/reduced motion.
Positions live only in transient CSS variables; no telemetry, storage, model calls
or network requests are added by the motion controller. Touch input never tilts
cards. Reduced motion disables animations, transforms and smooth scrolling.

The effect listeners do not dispatch clicks, prevent normal events, change goals,
invoke APIs or advance financial stages. A visual pulse is not an approval or
verified outcome. Spinner styling is bound to `aria-busy` during actual async
chat/calculation operations and cleared in `finally`, including errors.

## Verification

Eight tests exercise motion eligibility, bounded values, one-frame coalescing,
cancellation even when the frame ID is zero, target changes and disabled motion,
no new action/network dispatch, composed script uniqueness, busy lifecycles and
chat reading-position preservation. The full local suite ran 500 tests (499 pass,
one optional skip); Docker ran 500 (477 pass, twenty-three optional skips).
Four new Node-only helper tests skip in the Python-only image. Tooling: 24 passed.

Local browser checks confirmed real mouse-controlled CSS tilt, reduced-motion
cancellation, Enter-key navigation, zero console errors, a 390 px viewport without
horizontal page overflow and a 44 px runway button. One click made exactly one
cash-flow POST and returned the correct INR caps, with busy state cleared.
This is an interaction regression check, not an accessibility certification,
measured UX-award score or new financial/model benchmark.

Sources for implementation boundaries:
[animation-frame scheduling](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame),
[device reduced motion](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion).

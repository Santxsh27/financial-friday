# Goal playbook · 0.38.0

## Scope and audit

Story: one goal message → explicit Gemini permission → quote-bound intake →
exact cash calculator → visual allocation/checkpoints/stress cases → explicit
private save → reported savings/Undo → recalculated playbook.

The focused before-change audit inspected local screenshots
`/private/tmp/friday-goal-before-0380.jpg` and
`/private/tmp/friday-goal-result-before-0380.jpg`. The old straight-line projection
did not explain monthly budget allocation or the concrete impact of setbacks.
The detached checkbox made a pending goal look broken. The approved Soft Studio
colours, mascot and account/navigation layout are retained.

## Changes

- No generic line as the main outcome: a money-split doughnut with exact legend,
  four amount/date checkpoints and a current-pot meter distinguish actual reports
  from future scenarios. No nested result scrollbar once the playbook is shown.
- Independent integer-paise calculation module supplies four explicit cases:
  constant cash plan, income −10% plus living costs +10%, one omitted contribution,
  and target cost +5%/year prorated simply. No probabilities, returns or predictions.
- Short-budget alternatives calculate a smaller target at the same date, a longer
  cash timeline (bounded to 60 months), or exact extra recurring capacity needed.
  There are no automatic changes, trades, transfers or cuts to essential bills.
- The visual says which six inputs were considered and what is not established:
  future income, irregular costs/coverage, prices/fees/taxes, debt balance/rates,
  investment suitability/holdings/returns. It cannot consider every future factor.
- Gemini uses supplied playbook values for explanations, not invented model maths.
  General educational cards cover cash/deposits, mutual funds and shares/gold;
  source links are SEBI Investor and AMFI. No personal allocation, stock pick,
  brokerage feed, portfolio valuation or guarantee of returns is implemented.
- A prominent **Continue with Gemini** dialog discloses the exact sharing scope;
  calculator-only and Cancel alternatives work. A visible revoke button and
  New chat/privacy reset invalidate in-flight goal responses. No silent opt-in.
- **Confirm & save** is the explicit storage confirmation; the redundant second
  checkbox is removed, not the server's strict confirmation/revision/generation
  guards. A failed/uncertain save disables repeat submission until reload.
- Editing a saved plan reuses its budget and active reported cash additions, rather
  than presenting an empty form. Replacement still archives the old priority.

## Source basis for educational cards

- [SEBI: asset classes](https://investor.sebi.gov.in/investment-assetclasses.html)
- [SEBI: factors before investing](https://investor.sebi.gov.in/investment-thingsbeforeinv.html)
- [AMFI: risks in mutual funds](https://www.amfiindia.com/investor/knowledge-center-info?zoneName=riskInMutualFunds)

These are general explanations, not a compliance certification or a suitability
assessment. Public Search remains attributed research, not independent fact checking.

## Verification

Native: 851 tests run, 850 passed, 1 optional skip. Docker: 851 run, 816 passed,
35 environment/optional skips (Node checks run natively and in CI). Offline tools:
68 passed, including after the verifier's additional playbook assertions.
The 13 new focused tests include 100 deterministic independently calculated
allocation cases; they are not a labelled real-world financial-accuracy benchmark.

Browser: calculator-only permission route, current allocation, pressure-case
amounts, exact short-budget alternatives, prefilled manual edit and checkbox-free
save dialog were exercised in the artificial local workspace. Save was cancelled
there; real durable save/replay/Undo/cleanup is checked separately by the cloud
verifier. Desktop 1440px and mobile 390px had matching content/viewport widths,
one playbook and one assistant panel. Light/dark results were visually inspected;
temporary viewport overrides were reset. No accessibility certification is implied.
Inspected temporary screenshots: `/private/tmp/friday-playbook-0380.jpg`,
`/private/tmp/friday-playbook-0380-mobile.jpg`,
`/private/tmp/friday-playbook-0380-dark.jpg`, `/private/tmp/friday-save-0380.jpg`.

### Focused journey health

1. **Enter a goal — repaired.** A visible permission dialog replaces a silent
   unmet checkbox prerequisite; it offers a manual route without cloud sharing.
2. **Review the plan — working.** Allocation and dated amounts replace the
   generic line; current reports and future scenario amounts have different labels.
3. **Handle a short budget — working.** A ₹35,000-income artificial example
   displayed ₹80,000 at the original date, a 20-month cash timeline or ₹3,333.34
   extra monthly capacity. None was saved or applied automatically.
4. **Understand setbacks — working within scope.** Exact rupee shortfalls and
   named assumptions are expandable; no model probability or comprehensive-risk claim.
5. **Save or cancel — repaired.** One labelled storage action, no redundant tick;
   a pending save still uses the existing atomic revision/generation boundary.
6. **Learn about investments — bounded.** Educational comparisons and questions,
   not a personalised adviser, broker portfolio tracker or trading application.

## Completed cloud release · 18 October 2026

API `financial-friday-api-playbook0380` and web
`financial-friday-web-playbook0380` both serve 100% of main traffic. Both images
were built from source commit `2d5fd5366e82518abe6c50ec448256dc905e52de`.
CI [39113655408](https://github.com/Santxsh27/financial-friday/actions/runs/39113655408)
passed Python 3.11/3.12, offline tools and Docker checks for that exact source.
Immutable image/build identities are recorded in CURRENT_RELEASE.json.

- A fresh isolated artificial visitor passed two actual Vertex calls: quote-bound
  goal intake and read-only saved-goal coaching. Exact allocation and pressure-case
  assertions, Firestore save/restore, report/Undo, replay-once, payload conflict,
  export, cleanup and stale-generation rejection all passed. The workspace was
  cleaned and no owner records were used.
- The canonical signed-in website passed the explicit permission dialog → real
  Gemini intake → automatic graphical playbook using an entirely artificial,
  complete budget. The investment-education shortcut returned a real read-only
  Gemini explanation. These are two additional model calls, no saved goal or
  financial action. No statement context was attached.
- Anonymous API remains 403 and web redirects to Google sign-in (302). Existing
  IAM, OAuth, quotas and the pinned historical recovery target are unchanged.
- Local API/web remain healthy. Canonical browser console errors: zero in the
  tested flow. Actual microphone capture and a second person's sign-in are still
  manual checks; prior voice/Search evidence remains dated to 0.37.

Additional inspected temporary evidence:
`/private/tmp/friday-playbook-0380-live.jpg` and
`/private/tmp/friday-playbook-0380-live-overview.jpg`. Local preview and the
canonical published tab are retained inside Codex. This focused acceptance does
not establish all-bank parsing, financial suitability or production certification.
Old 0.36/0.37 evidence remains historical, not new evidence for this change.

Human submission gates remain: actual microphone use in the target browser, a
different Google account sign-in, private repository reviewer access, dashboard
cutoff/eligibility and the final video/deck/form. No guarantee of winning or of a
faultless production system is made.

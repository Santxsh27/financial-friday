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
68 passed before the verifier's additional playbook assertions; rerun at release.
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

Staged-cloud checks are pending. Deployment status and exact tested source/image
identities belong in CURRENT_RELEASE.json.
Old 0.36/0.37 evidence remains historical, not new evidence for this change.

Human submission gates remain: actual microphone use in the target browser, a
different Google account sign-in, private repository reviewer access, dashboard
cutoff/eligibility and the final video/deck/form. No guarantee of winning or of a
faultless production system is made.

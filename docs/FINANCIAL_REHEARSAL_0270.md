# Financial Friday financial rehearsals

Financial Friday now helps a person test a one-off financial decision against
their supplied cash history. Statement categorisation is the input layer, not
the entire product. The result is a set of conditional, independently checked
options, not a chatbot's unsupported affordability verdict.

## The user journey

Upload and review a supported INR bank statement, then open **What if?**. Ask
Gemini to set up a question such as “Can I buy a laptop for INR 15000 in 7 days
if salary is 10 days late? Protect transport”, or enter the scenario directly.
Enter available cash and a protected buffer. Review the editable assumptions
and confirm before calculating. No statement is sent to Gemini by that setup
action; an explicitly shared question may itself contain financial information.

The result shows whether the original purchase stays above the entered buffer
in every tested replay. When it does not, Friday shows the first breach date,
worst shortfall, maximum smaller purchase on the requested date, earliest later
date inside the horizon and the smallest uniform flexible-cost reduction, if
one fits. “Use this scenario input” edits the form only. Recalculate to check it.

The daily chart compares the lower cash floors without/with the purchase and,
when feasible, after flexible-cost changes. It is a lower envelope across
different scenarios, not one predicted future path. Exact tables, source months,
assumptions, coverage warnings and optional cost-change figures remain available.
“Explain these results with Gemini” is a separate opt-in: the server recomputes
the result and shares calculated totals/dates, not original descriptions or an
account nickname. A narrative cannot change the exact result.

## Calendar replay and cash accounting

One selected BANK nickname identifies the cash account; card purchases alone
cannot establish its cash timing. Up to six most recent supplied months become
independent templates. Every row repeats on its calendar day in future months;
day 31 clamps to the shorter month's last day. This does not establish that a
payment is recurring, when a real bill is due or whether the history is complete.

Opening cash reflects the start date and earlier. Only subsequent original
event dates are replayed; delaying an earlier payday cannot create a second
income payment. Baseline variants retain identified income. Adverse variants
apply the entered delay and income reduction together with an essential-cost
increase. Income is rounded down and increased essentials up to integer paise.
These variants have no estimated probability or confidence percentage.

All account debits count, including card repayments, loans, transfers and
unclear outflows. Only INCOME-labelled credits repeat; borrowing, refunds,
transfers and unknown credits do not fund a proposed purchase. Cash-flow
accounting therefore intentionally differs from the spending dashboard, which
does not treat card repayments as new purchases. Each day's debit and the
proposed purchase occur before same-day income because statement dates do not
prove intraday ordering. No missing month is invented as a zero-spending month.

## Exact algorithms

Let F(s,t) be the floor before daily credits in scenario s on day t, and B the
entered protected buffer. A one-off purchase P on day d subtracts P from every
floor at or after d. When all earlier floors already meet B, the largest modeled
purchase on d is max(0, min over s and t at or after d of F(s,t) minus B).
Suffix minima calculate the envelope in linear time in scenario-days. A broken
no-purchase baseline yields no affordability approval, even when the clipped
numeric envelope is zero. The first later date meeting the requested amount is
verified by replaying that option.

The repair family applies one proportional cut to eligible labelled flexible
expense rows. Groceries, housing, utilities, health, education, fees, Other,
repayments and explicitly protected categories are locked. Per-row reductions
round down. Increasing the cut cannot worsen any cash prefix, so binary search
finds the first feasible integer basis point within the user-entered cap of
0–50%. The result is minimal at 0.01 percentage-point precision **within this
uniform-cut family**, not the least disruptive or globally optimal real-life
budget. Cuts are scenario choices, not proof that a cost can actually be changed.

An independent ledger-style replay verifies source scenario identities, opening
cash, each day's debits/credits/conservation and protected costs. The selected
cut must fit; one basis point less must fail when the cut is positive. Where the
no-purchase baseline fits, the requested-date purchase capacity must fit and
one paise more must fail. A 30–90 day horizon and bounded existing history keep
the calculation finite. The final day gives no protection after that day.

## Google AI and security

Gemini on Vertex AI handles bounded natural-language interpretation and optional
result explanation using the existing Google Gen AI SDK and configured model.
Pydantic forbids extra fields, executable content, arbitrary tools and out-of-range
assumptions. A proposed purchase amount must appear numerically in the current
question. Spelled-out shorthand such as “15k” may require direct numeric entry.
The model is not trained on private statements.

Preview and explanation read tenant-owned statement history, check revision and
privacy generation, and recheck freshness before returning. Explanation accepts
scenario inputs rather than client-computed results. Explicit unsupported rupee
amounts in model explanations are rejected by the existing amount gate; that is
not a proof that every natural-language claim is correct. Request limits and
Google authentication remain unchanged. No IAM/OAuth expansion or new service
is needed. No scenario is persisted, payment attempted, bank record edited or
repayment skipped. In-flight older UI results are discarded after input changes.

## Verification evidence

The new feature tests cover timing gaps despite a month-end surplus, simultaneous
stress, ignored non-income credits, all cash outflows, same-day ordering, no
duplicated past income, month-end clamping, infeasibility, missing income,
protected costs, exact capacity versus exhaustive small cases, cut minimality,
tampered paths, auth/tenant isolation, consent, stale revision, unavailable AI,
invented purchase amounts, minimized explanations and forbidden extra authority.
Generated production JavaScript is syntax-checked by the existing UI suite.

Run the deterministic challenge set:

```bash
PYTHONPATH=src .venv/bin/python tools/evaluate_rehearsal.py
```

Seed 270017 produces 48 developer-created cases. A deliberately simple month-end
balance heuristic accepts all 48; daily baseline-plus-stress constraints accept
10 and expose buffer gaps in the other 38. Thirteen cases have a checked
proportional-cut option and fifteen a later-date option. Zero model calls are
made by this comparison. These are synthetic timing demonstrations, not real
financial outcomes, a plain-Gemini comparison or competitor performance claims.

For an authorised cloud acceptance check using only the repository's artificial
CSV and a fresh disposable visitor workspace, use `tools/verify_rehearsal_cloud.py`.
Deployment and actual live results belong in CURRENT_RELEASE, not inferred from
the presence of that script.

## Differentiation and remaining limits

Budget reports, financial assistants and planning are established product areas.
[Rocket Money's assistant](https://www.rocketmoney.com/rowan),
[YNAB's debt planning](https://www.ynab.com/features/debt-management) and
[Mezzi's financial assistant](https://www.mezzi.com/) illustrate adjacent existing
capabilities. Google's [structured output documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output)
supports typed generation, not truth or financial permission.

Friday's proposed distinction is the integrated **question → source-bound
calendar replays → concrete counterexample → calculated alternatives → checked
explanation** journey. Classical constraint checking and binary search are not
novel mathematical inventions. A novelty/patent review and independent usefulness
study remain pending; no award or world-first claim is justified.

Source completeness, wrong labels, annual/new bills, future behaviour, multiple
cash accounts and a user-entered opening balance remain important limitations.
This is not personalized securities advice, an eligibility decision, a fraud
verdict, a bank feed, an automatic financial agent or a guarantee against debt.
The next quality milestone is independently reviewed bank-format and scenario
coverage, including irregular income—not adding unrelated services for a logo.

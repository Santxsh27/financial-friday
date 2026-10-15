# Visual money planning — 0.26.0

15 October 2026. This release keeps the statement-first Soft Studio product,
but turns a personal goal into an inspectable, constrained plan rather than
another paragraph of financial suggestions. Deployment and live acceptance are
recorded separately in [CURRENT_RELEASE](CURRENT_RELEASE.json).

## What changed

1. Statement sharing is independent of the old financial-inbox/sandbox flag.
   General chat needs no records. A context receipt distinguishes SHARED,
   NOT_SHARED and EMPTY statement totals. One bounded retry corrects the model's
   known false “workspace permission” denial when totals actually were supplied.
2. Explicit page-conversation consent has a visible indicator and a labelled
   share-and-answer action. No automatic data sharing, bank connection or training.
3. Gemini interprets an explicit goal into a strict `MoneyPlanDraft`. Enum
   categories, bounded percentages and a current-message monetary-literal check
   constrain the proposal. This is not a financial execution plan.
4. A deterministic engine allocates reductions and a separate checker verifies
   the result. Category doughnuts, monthly bars, before/after bars and income
   stress curves have exact-value tables, source/month context and warnings.
5. Privacy & data replaces the legacy rules page in normal navigation. Existing
   sandbox safety rules remain enforced; removing them visually grants no authority.

## Mathematical contract, not a novelty claim

For each adjustable category, cut `x_i` is an integer number of paise between
zero and `floor(observed_i * max_cut_percent / 100)`. Essentials have zero cap;
recorded loan repayments remain fixed outside the allocator. The allocated total
is `min(requested_reduction, sum(caps))` and any remainder is shown as unmet.

The objective minimizes `sum(w_i * x_i²)`. Proposed preference weights are1 for
preferred adjustable categories and3 otherwise. These arbitrary, visible scenario
weights are not learned utility or evidence that a reduction is practical.
The kth unit's marginal cost is `w_i * (2k−1)`. Binary-searching its threshold
and deterministic tie resolution solve the bounded integer allocation without
iterating through every paise. A separate checker verifies key sets, integer
amounts, conservation, caps, protected categories and the marginal exchange
condition. This is classical separable convex allocation, not a new theorem.

No debt snowball, loan refinancing, investment recommendation, live-balance
estimation or automatic cancellation is attempted. Housing, utilities, groceries,
health, education, fees and repayments stay protected even if a user asks to cut
them. No identified income means no income-stress conclusion in the interface.

## Google AI boundary

Gemini on Vertex AI handles language/intent, statement interpretation and concise
explanations. It does not perform the exact optimization or render arbitrary
HTML/JavaScript. Existing tenant-private Cloud Run/Firestore boundaries persist.
The API binds a personal answer to one revision/privacy-generation snapshot;
manual preview rejects stale inputs. Chart.js4.5.1 is vendored under its MIT
license, without CDN or extra visitor tracking. No new IAM or OAuth scope.

References: [Google structured output](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output),
[Chart.js documentation](https://www.chartjs.org/docs/latest/).

## Verification and open limits

-12 feature tests include80 seeded small exhaustive comparisons, a large
  integer case, protected expenses, infeasible goals, exact paise/stress amounts,
  authentication/isolation, stale previews, false-permission repair and rejection
  of model-invented goals. These are developer tests, not an independent trial.
- Browser acceptance uses a separate artificial CSV workspace, never owner bank
  history. Live acceptance uses `tools/verify_money_plan_cloud.py` against a
  private staged API, then cleans only its fresh synthetic workspace.
- Existing services such as [YNAB goal tracking](https://www.ynab.com/features/goal-tracking)
  and [Rocket Money Rowan](https://www.rocketmoney.com/rowan) already offer budgeting
  assistance. We do not claim that financial chat, graphs or saving goals are new.
  Friday's demonstrable contribution is the visible goal → typed proposal →
  exact checked scenario → inspectable chart loop over reviewed records.
- Source-month completeness, correct extraction/labels, feasible real-life cost
  reductions, improved user outcomes, held-out false-warning rates and competitive
  originality remain unvalidated. A source hash is integrity, not authenticity.
- Monetary goals currently need numeric literals such as `INR 1000`; ambiguous
  “save more” needs clarification. No current bank feed, broad financial retrieval,
  latest-market data, guaranteed savings, creditworthiness or regulatory approval.

A source-month margin is neither disposable cash nor a forecast. The model's
plausible prose is not semantic proof. These limits remain visible in the UI.

## Completed acceptance

| Check | Observed result |
| --- | --- |
| Native suite |563 ran,562 passed,1 optional skip. |
| Final Docker suite |563 ran,540 passed,23 optional skips. |
| Tooling suite |24 passed. |
| Live Vertex goal interpretation |`gemini-3.5-flash-lite`,1 call in a fresh artificial cloud workspace. |
| Exact goal and protection |₹1,000 allocated, transport and essentials unchanged. |
|20% lower-income assumption |₹9,001 conditional margin from the artificial September records. |
| Infeasible manual preview |₹10,000 target under default25% caps:₹8,575.25 unmet. |
| Mutation boundary |Statement readback unchanged, artificial ledger unchanged, zero financial actions. |
| Cleanup |Only the fresh synthetic cloud statement workspace was cleared and read back empty. |
| Local browser |19-row upload/review/save, doughnut/monthly bars, before/after/stress graphs, feasible/infeasible plans and clean privacy navigation. |
| Responsive checks |390px viewport/content width, dark charts and reduced-motion recalculation; temporary settings reset. |
| Browser cloud check |Staging page loaded; canonical-origin Vertex chat, explicit share-and-answer next step and read-only manual chart preview worked. Financial sharing stayed off. |

The first regression run caught a Pydantic include-argument serialization issue;
it was corrected and rerun before cloud build. Staged browser POSTs returned403
`Same-origin request required`, as designed: the unchanged guard permits only
the normal website origin. This was not bypassed or widened. Private staged API
acceptance and normal-origin browser chat were used instead.

Deployments: API `financial-friday-api-plan0260`, source
`046df84259f8e62a65e64bdd36294918f38afbb5`; web
`financial-friday-web-plan0260b`, source `f1767fcc89db0dcc9e68d2c12dedac226315d3b4`.
The final frontend correction prevents long chat bubbles shrinking over each
other and restores the stress chart's connecting lines. No calculation or
financial-authority change. Native/Docker checks were rerun for this source.
Old revisions remain available. The existing recovery worker is still pinned
to0.24.0; this read-only feature needs no journal/schema migration or new worker.
See CURRENT_RELEASE for immutable image/build identities. Existing owner records
were not changed or shared with Gemini during these checks.

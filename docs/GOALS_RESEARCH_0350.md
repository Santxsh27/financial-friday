# Goals and public research — 0.35.0

Prepared 17 October 2026. Deployment status/identities belong in CURRENT_RELEASE.
This extends the working statement product; it does not claim an error-free
financial adviser, a world-first algorithm or guaranteed competition selection.

## User story

Home → Plan my next purchase → describe the goal → explicitly consent to Gemini
intake or enter numbers manually → review missing/proposed fields → confirm →
baseline/stress cards, timeline, table and JSON export. Add up to three goals in
the same scenario. Research is a separate explicitly confirmed public request.
The same Friday chat remains available and can suggest these two destinations.

## Engineering boundary

- Pure integer-paise earliest-deadline-first allocation from one shared savings
  pool. Initial protected reserves are excluded; monthly surplus first fills a
  missing buffer. No borrowed cash or investment returns are manufactured.
- Upfront funding, explicit extras and fixed-rate monthly-rounded amortisation.
  A funded purchase starts EMI next month; the final loan instalment reconciles
  exact paise. Later goals see the earlier loan commitment. Peak overlapping
  repayments are also inspected after the last purchase deadline; a funded
  down payment does not hide a subsequent monthly deficit or establish affordability.
- Stress runs use income −10%, essentials +10%, rate +2 percentage points. These
  are chosen adverse assumptions, not calibrated probabilities or predictions.
- Literal quote binding for every Gemini-proposed number, including lakh/crore
  conversion. Unknown income/debt/deadline stays missing. User review is still
  required: literal agreement does not prove semantic classification is correct.
- Public research calls only Google Search through the configured Vertex client.
  No private portfolio, saved preferences or chat history is loaded. Fixed topics
  and an explicit public-question field are not an arbitrary browser executor.
- Results require actual provider grounding links and Search Suggestions. The
  provider HTML is rendered in a sandboxed, script-disabled frame; other model
  output is text, never executable HTML. Source links admit only bounded public
  HTTPS URLs. No source page is fetched by our backend.
- No periodic/background model requests, new services, new credentials, expanded
  IAM or increased quotas. Existing authenticated POST admission limits apply.
- No server goal persistence: the draft/plan remains in the page; export is
  explicit. Privacy cleanup clears local proposals and suppresses late responses.

## Known corrections during implementation

The first live intake exposed an existing schema simplifier stripping a real
field named `title`. It now distinguishes schema metadata from property names;
a regression preserves the field. A later intake returned only two optional
facts; generation now requires every field or explicit null. The recorded next
synthetic run returned all seven supplied numeric facts.

Structured-output search returned no attribution and was correctly rejected.
A separate diagnostic established normal grounded text did return sources.
Research now requests bounded factual bullets, preserves the full response and
renders cards without a second model rewrite. The final direct home-loan smoke
returned four cards, six provider sources and eight grounding support segments.
That verifies the integration—not every research claim's correctness.

Fresh-link browser QA also found a missing Research parent label and a parent
navigation path that could create a Back loop after reload. Both were corrected:
direct Research → Goals → Home replaces the initial route, while normal in-app
Back uses browser history. Executable JavaScript route tests cover both paths.
Research paragraph text was reduced from oversized bold text to normal readable
body text; this is presentation, not a new financial or model capability.

## Verification

Focused tests cover shared-pool non-duplication, deadline ordering, missing buffers,
deficits, financed-goal interaction, amortisation, quote/value rejection, missing
consent, route authentication, no portfolio mutation, source/suggestion absence,
unsafe URLs and inert rendering. Eighty developer-authored random single-goal
cases are compared with a closed-form arithmetic oracle. This is not independent
human validation or evidence of optimal financial policy.

Native: 803 run, 802 passed, one skipped. Container: 803 run, 771 passed,
32 skipped. Tool tests: 65 passed. Browser acceptance and live revision results
are recorded in CURRENT_RELEASE after completion. Historical suites and model
studies remain preserved; this release does not fix all their measured misses.

## Live release acceptance

The final staged API passed the following bounded, fresh-visitor checks:

- Real Vertex goal intake matched all seven supplied artificial numeric facts.
- The exact car scenario funded its upfront target in baseline and returned the
  expected ₹2,32,000 stress shortfall. Goals were not persisted.
- Real Google Search research returned provider attribution (two sources and
  three support segments in that particular run), not model-invented links.
- All five packaged CSV controls, real Vertex PDF extraction and statement chat,
  Firestore source-selection race (409/200), restoration and cleanup passed.
- The canonical browser completed Gemini intake, assumptions review, charted
  calculation and public research with five source links and Google suggestions.
  No private saved records were shared in those new browser model requests.
- The final UI follow-up also rendered a fresh public gold request with two
  provider links, visible Google suggestions, 14px body text and no observed new
  console errors. Direct Research → Back to Goals → Back to Home was verified
  after a page reload, not only through in-app navigation.
- Local browser checks exercised consent gating, manual calculation, Back,
  preserved navigation state and a funded down payment with a later monthly
  deficit. A 390px research viewport had no horizontal document overflow and
  the temporary viewport override was reset.

Content-free cloud model events were observed for goal intake (2,249.118 ms,
1,271 total tokens) and research (3,520.891 ms, 618 total tokens). These isolated
observations are not an SLA or billed-cost estimate; Search may issue multiple
queries. Provider-sourced research can include aggregators, not just official
institutions. Attribution is not an independent fact check.

Runtime image/build identities, source CI, traffic and remaining human submission
gates are in CURRENT_RELEASE. The UI-only readability follow-up does not change
the accepted API engine or add model calls. Export's click handler is tested;
an actual browser file download was not re-run in this release.

## Limits

INR, up to three goals, 1–60-month planning horizon, 1–360 loan instalments and
explicit bounded inputs. No property-price forecasts, current balance feed,
tax eligibility, investment selection or financial execution. Enter recurring
ownership costs in expenses and all applicable upfront costs yourself; location
costs are not silently filled from search. A possible purchase date is conditional
on assumptions, not a lender or financial-adviser verdict.

Research is latest-retrieved public text, not a licensed live ticker or complete
market database. Prices require the source's date/unit/location/purity and may
remain unknown. Source attribution does not establish factual accuracy. No
personalised securities recommendation or registered-adviser status is implied.
Long-term goal memory, continuous alerts, authorised feeds and representative
product/financial-outcome validation remain future work.

API: POST goals/interpret, goals/preview and research under /v1/friday, proxied
through the existing authenticated web gateway. Goals preview calls no model and
saves nothing. Public research needs explicit consent even for preset topics.

Reference: [Google Search grounding](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/ground-with-google-search),
[Search Suggestions display](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/grounding-search-suggestions).

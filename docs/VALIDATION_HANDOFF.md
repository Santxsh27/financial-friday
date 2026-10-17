# Independent review protocol

Status: **not independently reviewed**. Do not replace this status with a claim
of validation because the engineering tests pass.

1. A reviewer other than the developer/model creates or approves a fresh frozen
   set of synthetic or explicitly authorised redacted cases. Include changed
   narrations, legitimate repeated purchases, refunds, borrowing, missing pages,
   bad totals, overlapping imports, different banks and ambiguous examples.
2. Before running Friday, freeze expected transaction rows, amounts, directions,
   source references and whether each finding merits review. Allow explicit
   abstention where the supplied evidence cannot decide. Do not use actual fraud
   labels without appropriate ground truth. Do not ingest scraped customer data.
3. Run exact extraction/reconciliation separately from category/meaning labels,
   finding quality, model explanations and interface usability. Archive model,
   prompt/schema/source hashes and unchanged labels.
4. Record TP/FP/TN/FN, denominators, undefined measures, rejected outputs,
   unsupported amounts/citations, latency, token availability and cost limitations.
   An abstention or rejected answer is not a correct completed task.
5. Review usability with another Google account: initial sign-in, account menu,
   sample download, upload/preview/save, chart/source interpretation, chat consent,
   Back, Start new review/restore and optional voice. Confirm no cross-user data.
6. Archive both successful and failed runs. Tune only against a separate development
   split; keep a new unseen cohort for the final test. Related transformed cases
   stay in the same lineage. Do not claim blind validation after inspecting it.

Current baselines and limitations: [0.31](STATEMENT_RELIABILITY_0310.md),
[0.32](CONSUMER_ASSURANCE_0320.md), [current release](CURRENT_RELEASE.json).
Do not upload a real bank statement or make an actual payment merely to test the app.

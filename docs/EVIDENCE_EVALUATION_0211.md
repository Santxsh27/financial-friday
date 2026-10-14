# Live evidence and follow-through regression — 14 October 2026

## What changed for the customer

Friday should not stop at “this looks suspicious.” If the user requests a
verification draft, it should prepare that useful **unsent** next step immediately.
The live test found four outputs that identified the warning but selected a
generic explanation. The corrected planner prioritises the requested next step,
supplies neutral questions with known details/placeholders, and directs people to
a contact they independently know. General education stays an explanation.

No new banking access, automatic messages, financial permissions or payments were
introduced. The production quote checker is now shared with the evaluator, and
duplicate source identities fail rather than silently overwrite one another.

## Frozen developer study, not independent validation

The corpus contains 16 synthetic requests: ten expected potential-risk warnings
and six benign requests, including English, Hindi/Tamil, educational negations,
ordinary deadlines, explicit renewals, missing details and malicious document
instructions. Labels and action expectations were written by the developer and
are never sent to the model. They are not confirmed fraud labels.

Refund/PIN cues are informed by [NPCI fraud-awareness guidance](https://www.npci.org.in/fraud-awareness).
Guaranteed-return and high-pressure investment cues are informed by
[SEBI investor guidance](https://investor.sebi.gov.in/spot-any-scam.html).
These sources support risk categories; neither organisation validates our
synthetic cases, labels, system or results.

Corpus hash, unchanged before/after:
`fa510b395949f100c632e45ee222096a005cf3948944e28a87ffa6465b8e78ff`.
The pre-correction corpus/code was committed as `5dbdec7`; the corrected prompt
as `fa2a5dd`. This corpus is now development data because it informed the fix.

| Observed result | Before correction | After correction |
| --- | --- | --- |
| Planned/attempted requests | 16 / 16 | 16 / 16 |
| Structured answers returned | 15 | 16 |
| Returned answers matching developer risk labels | 15 / 15 | 16 / 16 |
| Requested next step matched | 11 / 16 attempts | 16 / 16 attempts |
| Requested verification draft present | 9 / 12 | 12 / 12 |
| False warnings / missed risk on returned answers | 0 / 0 | 0 / 0 |
| Unresolved requests | 1 timeout | 0 |
| Proposed payments / actual payments | 0 / 0 | 0 / 0 |
| Median model-call time | 1.621 s | 1.724 s |
| P95 model-call time, including errors | 90.192 s | 3.397 s |
| Reported token metadata | 16,527 across 15 answers | 21,673 across 16 answers |

The first timeout remains in the saved report; it was not relabelled successful.
Missing token usage for that request is unknown, not zero cost. Timing is for
direct Vertex inference from the local evaluator, not website latency or an SLA.
The study uses a 90-second timeout and one SDK attempt; the existing production
Vertex adapter uses a 20-second request timeout and one SDK attempt.

Both runs use the configured model ID `gemini-3.5-flash-lite` and temperature zero.
A single before/after run cannot isolate all stochastic/provider variation or
establish general accuracy, production reliability, saved customer losses or
human-rated usefulness. Draft presence is a structural check, not quality grading.

## What the same-output comparison proves—and does not

Each request makes **one** model call. The same exact schema-valid proposal is
scored before and after the **actual production evidence-admission function**.
The checked branch verifies source identity and literal supporting quotations;
it has no execution tools. Provider/schema/admission failures remain unresolved.

Raw and checked scores were identical in both live runs: the returned quotations
were admitted. We therefore claim **no measured advantage over the model on this
sample**. Unit challenges separately prove that fabricated quotations, unavailable
citations and duplicate source identities are rejected. Grounded quotations can
still support a semantically wrong warning; the evaluator counts that as a false
warning rather than treating admission as correctness.

The older two-call evaluator remains available for historical experiments, but
two separately sampled answers do not isolate the effect of the checker.

## Reproduce

Dry mode validates the corpus and makes no model calls:

```bash
PYTHONPATH=src python tools/evaluate_friday_evidence.py \
  --cases examples/friday_evidence_challenges.jsonl
```

With your existing authorised Google Cloud identity, `--live --project PROJECT_ID
--token-stdin` admits at most one Vertex call per selected case (default 16,
maximum 50). Pipe a short-lived access token into stdin; never put it in a
command argument, report or repository. Expected labels stay outside model input.
The runner stops after two consecutive failures and does not retry payments.

Full immutable records:
[before](evaluation/evidence_2026-10-14_before.json) and
[after](evaluation/evidence_2026-10-14_after.json).

## Still needed

## Deployed workflow checks

The private API candidate `financial-friday-api-evidence0211` passed two real
Vertex task requests in a fresh synthetic workspace: a refund/PIN demand was
`HOLD` with an unsent verification draft, and an educational PIN/OTP question
was `GUIDANCE_ONLY` with no findings. Saved rules and artificial balance were
unchanged. The public browser then displayed the held request, supporting quote,
draft and **Copy verification message** control without console errors. No
confirmation, payment or external-message endpoint was called.

The corrected API now serves 100 percent of normal traffic; the existing
`followups0210` web frontend continues to use the stable private API origin.
Source/build identities and test counts are in `CURRENT_RELEASE.json`.

## Still needed for independent validation

A teammate/reviewer who has not tuned the prompt should freeze a separate unseen,
synthetic corpus and resolve ambiguous labels before running. Add repeated trials,
human draft-quality review and consumer task-time measurement. Do not call the
developer regression study independent validation or real-world fraud prevention.

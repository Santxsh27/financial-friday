# Money Runway — financial-buddy memory without pretending to train

Version 0.22.0, 14 October 2026. Actual activation/build identities and live checks
are recorded in CURRENT_RELEASE.json. A code commit alone is not a deployment.

The corrected API (`runway0220b`) and web (`runway0220`) are now serving 100% of
their existing Cloud Run services. The public Google-authenticated page calculated
the editable artificial example without saving or calling AI, with no browser
console errors. A separate newly created synthetic workspace verified Firestore
save/readback/cleanup and a real Vertex reply correctly quoting INR 100.00 and
INR 68.18 with `cashflow:current`. Financial rules remained unchanged and no money
moved. The private API still returned 403 to an anonymous request.

## What it solves

A positive month-end total can hide a cash gap before income arrives. Money Runway
shows that timing gap, the chosen-buffer dip, and a delayed-income comparison.
It works with user-entered assumptions; it does not infer a live bank balance.
Statement CSV review already totals incoming/outgoing INR records. Incoming money
may be a refund, transfer or loan, not necessarily salary or recurring income.
No automatic CSV-to-forecast import silently makes that assumption.

## Algorithm

Inputs: 1–90 days, starting cash, desired reserve, daily variable spending, up to
50 positive dated income entries and 50 dated bills, and 0–30 days income delay.
Unknown keys, unsupported currencies, negative amounts and dates outside the
scenario window fail validation. All arithmetic uses integer paise.

For day i, subtract its known bills and daily spend before adding expected income.
Track the lowest cash, first cash below reserve, first negative cash and closing
cash. For each day, compute the balance without discretionary spending before
that day's income; floor `(balance_without_spend - reserve) / elapsed_days`.
The smallest nonnegative prefix cap is the largest constant daily spend preserving
the chosen buffer under these assumptions. If fixed bills already breach the
buffer, no spending cap can fix that plan. Re-run with income dates shifted by
the requested delay; income beyond the window is excluded and counted.

This conservative ordering can warn even when salary is expected on a bill's
due date. It is explicit, not a confidence score, probability, bank policy or
advice to skip essential bills. Missing expenses and non-arriving income remain
possible. The model does not perform the arithmetic.

## Privacy and Gemini

GET/POST `/v1/friday/cashflow` use the existing tenant authentication and request
limits; gateway routes are fixed. Transient calculation is the default. Optional
save stores only the latest plan/result per tenant, in SQLite locally and
transactional Firestore in cloud. It does not keep raw statements or upload files.
Privacy-generation checks reject a late save after cleanup. Explicit review
cleanup removes all runway snapshots, even with expired-only review cleanup;
payment journals, signed receipts and replay safeguards are preserved.

Chat context has independent, initially unchecked consent. It includes calculator
aggregates as explicitly formatted INR strings, scenario dates/limits and the citation `cashflow:current`, not individual
bill/income events. Without consent, that context and citation are unavailable.
Changing consent or saving/clearing the plan clears the chat context; stale model
responses cannot repopulate it. Editing assumptions clears the displayed forecast
until recalculation. No API here can pay, lend, trade or modify a financial mandate.

## What “learn from data” should mean

1. **Private memory — implemented:** preferences, consented document facts,
   follow-ups and an optional latest cash-flow scenario. They personalise bounded
   context; they do not update Gemini weights or become other users' training data.
2. **Trusted-source retrieval — not implemented yet:** a versioned, licensed
   reference collection with dates and citations for financial safety and policy.
   Retrieval brings the relevant records into a prompt instead of hoping a model
   memorises current rules. Personal evidence and reference knowledge stay separate.
3. **Fine-tuning — not started:** consider only for a measurable task after a
   licensed/deidentified labelled corpus and held-out benchmark show a need.
   Dataset size alone does not establish quality, safety or general financial skill.
   Customer records must not automatically become training data. Cost, location,
   consent and model availability need a separate decision before any training job.

Google describes [fine-tuning versus retrieval](https://cloud.google.com/blog/products/ai-machine-learning/supervised-fine-tuning-for-gemini-llm)
and [RAG/grounding](https://cloud.google.com/blog/products/ai-machine-learning/rag-and-grounding-on-vertex-ai?hl=en).
Its [Vertex data policy](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/vertex-ai-zero-data-retention)
does not mean universal zero retention. Review applicable processing terms before
sending personal records. No new paid service, dataset purchase, tuning job,
bank/Account Aggregator permission or notification integration is created here.

## Acceptance and limits

The initial real Vertex check exposed a unit error: Gemini interpreted a 10,000
paise cap as INR 10,000 instead of INR 100.00. That zero-traffic candidate was not
promoted. Model context now contains formatted rupee strings instead of raw paise.
An independent reply gate rejects explicit rupee figures absent from the calculator
context. Regression tests cover prefix/suffix monetary references and the exact
100× error shape. This gate does not prove all semantics: a model could attach a
valid number to the wrong concept or express an amount in words. The calculator
and chart remain authoritative, and no money can move from this conversation.

Twenty-two feature tests cover exact scenarios, same-day income, impossible buffers,
randomised maximal-cap checks, delayed events, tenant isolation, no implicit save,
strict gateway validation, cleanup races, actual Firestore transaction callback
code under a test driver, and independent chat consent/citation rules. Test doubles
are not actual Cloud Firestore or Vertex acceptance. Full-suite and real cloud
checks are recorded separately in the release manifest.

The warning appears after a calculation, not through an always-on bank watcher.
Bank ingestion would require an authorised, consented partner/source. External
alerts, shared family access, cash-flow probability models, securities advice and
automatic financial actions are outside this release. Independent usefulness,
forecast-quality and fraud benchmarks remain pending.

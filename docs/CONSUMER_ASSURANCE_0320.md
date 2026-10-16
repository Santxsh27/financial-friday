# Consumer assurance release candidate

Release 0.32.0 is a source candidate. Staging, cloud promotion, release-level
test counts and live acceptance are pending. [CURRENT_RELEASE.json](CURRENT_RELEASE.json)
records the deployed source, images and revisions; this note does not promote
either service. The statement → review → spending/workbench journey stays intact.

## Consumer routes and legacy demonstrations

The API and public web proxy use a shared explicit consumer route allowlist.
Adding an endpoint does not automatically expose it to consumers. Statement
ingestion, source checks, guidance, privacy, optional diary/planning and document
review remain admitted. Existing task/run inspection and authenticated recovery
can inspect or reconcile an existing journal; they cannot prepare or retry a
payment through that recovery path.

Environment loading defaults `FRIDAY_LEGACY_DEMO_ENABLED` to `false`, including
when the environment label is development. The planned production setting is
explicitly false. Preflight, assurance and new artificial-payment demonstration
routes require a deliberate server opt-in and are absent from consumer OpenAPI.
Local/test fixture construction retains explicit compatibility behavior.

These are application admission rules in the existing service. Historical code,
storage and service identities have not been split into separate processes or
IAM boundaries. The setting does not authenticate a bank, grant new OAuth scopes
or create real-money access. See [the API availability note](api.md) and
[the implemented surface](../src/carapace_core/friday_surface.py).

## Literal narration matching

`CHECKUP_2` recognises a finite set of complete UPI, NEFT, IMPS and RTGS narration
layouts with explicit reference and counterparty slots. It can compare the same
literal payee across changing reference tokens for recurring-payment candidates,
and the same explicit reference across superficial ASCII case/space formatting
for repeated-entry candidates. Different reliable tokens stay separate. Exact
account nickname and account type scope every match; renamed accounts are not
automatically joined.

Payee words, digits, punctuation, VPA handles and non-ASCII distinctions remain
significant. Unsupported or ambiguous layouts use complete literal-description
fallback. Controls, conflicting directions and bounds prevent a structured
match. Original evidence and every row remain unchanged. Findings report their
match basis and uncertainty; a reference token is not a verified bank identity.
Recurring/increase/outlier thresholds and the refund algorithm are unchanged.

Existing description minimisation may already mask numeric references. An
explicit masked reference can support a weak literal-payee recurring candidate,
but cannot prove two entries share a reliable transaction reference. Identical
masked descriptions can still produce an explicitly uncertain exact-text review
candidate. The matcher does not recover missing identifiers or train a model.
See [the bounded grammar](../src/carapace_core/friday_narration.py) and
[synthetic adversarial tests](../tests/test_friday_narration.py).

## Measured checkup quality

The frozen 39-case corpus has eight finding kinds: 312 case-kind targets, 310
scored decisions and two authored abstentions. Labels mean a review is warranted
given the supplied fictional context. They are unreviewed, agent-authored and
already observed; neither the corpus nor its evaluation split is independent or
blind validation.

| Measure | CHECKUP_2 result |
| --- | --- |
| True positives / false positives / true negatives / misses | 14 / 7 / 284 / 5 |
| Precision | 14/21 = 66.67% |
| Recall | 14/19 = 73.68% |
| Case false-positive rate | 7/18 = 38.89% |
| Finding-kind false-positive rate | 7/291 = 2.41% |
| Exact expected evidence groups | 14/19 |
| Numeric invariants | 20/20; no runtime failures |

Scores and scored evidence are unchanged from the preserved baseline: no measured
improvement or regression on these cases. Thresholds were not changed to improve
the observed result. The 24-case authored evaluation split has precision 9/13 =
69.23%, recall 9/11 = 81.82% and case false-positive rate 4/11 = 36.36%; two labels
abstain. Repeated-entry and fee recall are undefined in that split because those
lineages have no positive cases there.

See [the frozen comparison](../examples/evaluation/statement_checkup_report_checkup2.json)
and [the original baseline](../examples/evaluation/statement_checkup_report.json).
The original evaluator records hashes for its listed source modules but omits
the newly imported narration module; this limits that report's source provenance.
Fresh reviewer-authored cases and human label review remain necessary before
claiming broader quality or real bank-format support.

## AI smoke test and scoring limits

The [original production-path run](../examples/evaluation/statement_ai_live_0320.json)
made six SDK calls on synthetic inputs and records **0/6 strict passes**. Two PDF
proposals were genuinely rejected by extraction admission. Four chat answers
were admitted, but the original strict score also mixes literal wording,
navigation fields, classification proposals and factual checks.

Scorer defects affect interpretation: an empty amount allowlist labelled
input-supported April/June values unsupported, and a generic fictional shop's
category was treated as a single exact answer. Narrow phrase patterns also miss
valid paraphrases. These issues do not erase the PDF admission failures or turn
the original 0/6 into a factual-accuracy estimate.

A separate [version 2 protocol](../examples/evaluation/statement_ai_protocol_v2.json)
preserves that original result while separating finite factual, classification,
typed-field, wording and admission diagnostics. It was authored after observing
version 1 and is not a held-out improvement test. Negative scorer controls cover
wrong amounts, swapped months, borrowing as income, unsupported citations and
false action/access claims; finite English patterns do not verify arbitrary prose.

The numeric source-fact prompt now explicitly requests the printed number, not
its entire labelled line. Exact source binding is unchanged. In the separately
recorded [six-call follow-up](../examples/evaluation/statement_ai_live_0320_followup.json),
both PDFs passed source admission and all six outputs were admitted. The original
strict protocol still passes only 1/6; the separate finite factual axis passes
5/6. These figures have different meanings and neither is representative accuracy.
The original responses are also [replayed separately](../examples/evaluation/statement_ai_live_0320_protocol_v2_replay.json).
Typed chat actions now normalize their destination coherently after validation;
this does not grant the model execution tools or financial authority.

## Freshness and preview recovery

Private chat checks the privacy generation before reading shared context, after
model generation and after its last freshness reads and response assembly.
Changes to shared diary, forecast or inbox aggregates withhold the reply;
statement context additionally checks its revision/generation. A regression test
covers cleanup during the final read even if the in-flight read returns an old
snapshot. General chat does not load unshared private records. These are bounded
race regressions, not proof of every distributed interleaving.

Reloading the unsaved review screen now explains that the preview has expired
and offers **Choose a statement**. Saved history is unchanged. The existing
source-check receipt, mismatch save gate and private cleanup remain in place.
See [freshness tests](../tests/test_friday_private_chat_freshness.py) and
[the earlier source-check contract](STATEMENT_RELIABILITY_0310.md).

Browser acceptance used an isolated fictional workspace: 35 rows were read,
reviewed, saved and charted; reviewing one candidate advanced the queue. Profile
navigation and preview-reload recovery were checked. Removing dormant legacy DOM
nodes initially broke shared display handlers; hidden/inert presentation nodes
now preserve those handlers while server admission still refuses execution.
See [the verified consumer workbench](screenshots/consumer-assurance-0320.jpg).

## Concurrent cloud acceptance

The first staged source-check run passed signed CSV admission, amount-tamper
rejection, same-source replay, declared-mismatch rejection and one real Vertex
PDF with all seven available source checks consistent. Its disposable workspace
was cleaned up.

The first concurrent import race returned one success and one revision conflict.
The review race instead returned 200/503: the unsuccessful request stopped in the
shared usage-limit admission layer before its review handler. No overwrite was
observed and cleanup completed. The original provider exception type was not
logged, so that incident alone does not establish its underlying cause.

Quota reservations now restart a fresh transaction at most twice after a typed
provider `Aborted` error, including an explicit chained SDK cause. Unknown
timeouts and domain limits are never retried. The same atomic counters and
limits remain; downstream handlers are not retried. Fixed telemetry categories
distinguish limit, retry, conflict and unavailable outcomes without error text.
Injected provider-abort tests check bounded retries and exactly one successful
reservation. This is narrower than proving every Firestore failure mode.

The revised live race result and release-level native/container/CI results will
be recorded with verified revision identities in CURRENT_RELEASE after staging.
Engineering regressions, authored quality scores and deployment acceptance
answer different questions and are not interchangeable.

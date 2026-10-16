# Statement reliability and measured review quality

Version 0.31.0 strengthens the statement-first workflow without another input
form. It adds source reconciliation, signed extraction receipts, a reproducible
labelled baseline, request correlation and adversarial privacy/concurrency tests.
Deployment identities and acceptance results belong in
[CURRENT_RELEASE.json](CURRENT_RELEASE.json).

Local verification: 694 native tests ran, 693 passed, one optional skip; 38
tooling tests passed. Docker ran 694 tests, 670 passed, 24 optional skips. These
are engineering regressions, separate from the quality benchmark below.

## What the user sees

The existing upload → review → spending workflow stays intact. A folded
**Source checks** summary shows how many checks agree, which disagree and which
cannot be established. Known source mismatches disable saving. Missing source
facts do not prevent a clearly limited import. Category/meaning labels remain
editable; source amounts and dates do not.

Try [the artificial source-check CSV](../examples/friday-source-check-artificial.csv).
Its opening balance is ₹1,000, one debit is ₹100, one credit is ₹50 and closing
balance is ₹950. All six applicable CSV checks agree. This is a controlled
synthetic format, not a compatibility claim about an actual bank.

## Extraction and trust boundaries

`friday_statement_csv.py` preserves the canonical CSV format and adds one strict
withdrawal/deposit/running-balance profile. Recognised optional footer facts are
not counted as transactions. Malformed rows and conflicting columns reject the
whole proposal; none are silently skipped. PDFs preserve physical page numbers,
literal value citations and explicit printed totals/page markers when available.
Fact labels and values must bind on the same source unit. Clear dated rows cannot
be silently omitted or reused. Ambiguous dates/layouts are rejected or remain
unknown; Gemini's own `complete` assertion is not independent completeness proof.

Pure integer-paise reconciliation checks debit/credit totals, transaction count,
printed page coverage, opening-to-closing arithmetic, running balances and detected
dated-row coverage. Balance arithmetic requires an account-appropriate sign
convention and established order. Bank balance and credit-card amount-due
conventions are separate. No facts means UNKNOWN, not zero or complete.

The server signs a domain-separated extraction receipt using the existing
Ed25519 service key. It binds tenant, privacy generation, source hash, account
nickname/type, parser mode, source facts and immutable row fields. Meaning and
category labels are deliberately excluded for user review. Save verifies the
signature and recomputes checks. Cross-tenant, changed-amount, changed-source,
forged-signature and old-generation proposals fail. Legacy/manual imports remain
usable but have no source-bound status. **Friday's signature is not a bank
signature. Arithmetic agreement does not authenticate a statement or establish
all accounts/rows were supplied.**

Raw uploads are not archived. Reviewed normalized rows, minimal labelled
fact/value excerpts, page/unit references and the extraction receipt are retained
privately until cleanup. Full raw fact-source lines are not retained. Gemini chat
context still omits transaction descriptions, source excerpts and signatures.

## Labelled baseline rather than an accuracy claim

[Inputs](../examples/evaluation/statement_checkup_inputs.json),
[separate labels](../examples/evaluation/statement_checkup_labels.json) and the
[machine-readable report](../examples/evaluation/statement_checkup_report.json)
cover 39 synthetic cases, eight finding kinds and 312 case-kind targets. Labels
mean **review warranted with the supplied context**, not actual fraud. They were
authored by the development agent, are unreviewed, and are not independent or
blind validation. Some contextual facts intentionally exceed the current rules'
input capability. Missing context can therefore explain false review alerts.

Overall, 310 resolved decisions yielded TP14, FP7, TN284 and FN5; two labels
abstain. Precision is 66.67%, recall 73.68%, and case-level false-positive rate is
7/18 = 38.89%. The smaller kind-level rate, 7/291 = 2.41%, is also reported with
its denominator, not substituted for the case rate. All 20 numeric invariants
pass; exact expected evidence is returned for 14/19 positive groups.

Five misses include changed descriptions/account nicknames and abbreviated fees.
False warnings include legitimate repeat purchases, planned spending changes and
already-explained credits/fees. No production thresholds were changed to improve
these results. Related transformed scenarios share split lineages. Split grouping
was hardened after initial observation, which is recorded; neither split is a
blind holdout. Evaluation repeated-entry/fee recall is undefined because those
families are entirely in tuning. CI runs only the tuning cohort and archives its
report; exposing evaluation requires an explicit flag.

```sh
PYTHONPATH=src .venv/bin/python tools/evaluate_statement_checkup.py
PYTHONPATH=src .venv/bin/python tools/evaluate_statement_checkup.py --split all --include-evaluation --output examples/evaluation/statement_checkup_report.json
```

## Privacy, concurrency and observability

New bounded Event/barrier tests cover simultaneous finding acknowledgements,
cleanup while a PDF model response is blocked, cleanup during chat, preservation
of a newer workspace and another tenant, and expired/invalid gateway identity.
SQLite and a retrying Firestore transaction **driver** are exercised. The driver
does not establish real distributed Firestore contention. Prepared statements
now recheck privacy generation after extraction before issuing a receipt.

The public gateway generates an opaque `X-Request-ID`; the private API validates
its format and carries it across thread pools into model and stage events. IDs
are correlation hints, not authorization. Allowlisted route templates, status,
duration, model/version and token counts where returned are logged. Reconciliation
and validation failure events remain separate from provider-call success. Raw
URLs/queries, filenames, identity, bank identifiers, source text, prompts and
model replies are excluded from the new telemetry. No new IAM role or service is
needed. No new alerting dashboard or exact cloud-cost accounting is implied.

## Remaining validation work

1. A teammate or authorised reviewer must supply/review a fresh frozen dataset,
   especially changed narrations and contextual false warnings. No private
   statements enter a dataset or training pipeline without explicit permission.
2. Existing evidence/risk runners are retained. Independent live benchmarks for
   extraction, intent, citations and explanations across prompts/models remain
   necessary; a live acceptance PDF is not that benchmark.
3. Real multi-client Firestore contention, wider bank export layouts and scanned
   document/page completeness need additional testing. A passing controlled
   profile does not establish universal PDF/bank support.
4. Historical artificial-payment code remains outside the default statement
   journey. A complete separate-service/IAM split is not part of this milestone.

This milestone measures limitations and enforces stronger boundaries. It does
not claim calibrated fraud detection, trained ML, guaranteed financial outcomes,
bank authentication, production certification or hackathon selection.

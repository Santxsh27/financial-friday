# Independent evaluation protocol

Engineering tests, generated negative proposals and a fraud-accuracy benchmark
answer different questions. None may be substituted for another.

1. A reviewer who has not tuned Friday's prompts supplies synthetic/redacted cases
   and labels. Record author, permitted use, category, expected output and rationale.
2. Split development and held-out cases by document template, issuer pattern and
   language—not random copies of the same invoice. Freeze the held-out file/hash.
3. Resolve ambiguous labels before running models. Include legitimate urgency,
   negated requests for secrets, missing evidence and ordinary recurring bills.
4. Run the same model version/configuration against the same inputs. Separate
   semantic risk, unsupported citations, financial admission and task completion.
5. Report false warnings and missed risks, all errors, latency, token usage and
   denominator/category counts. A hold is not automatically a successful task.
6. Repeat model comparisons when practical; never use a judge model as the sole
   source of truth for amounts, permissions or whether a payment happened.

`tools/evaluate_friday_risk.py` validates an external JSONL corpus and optionally
performs paired live calls. Its baseline shares model/instructions/schema but lacks
Friday's exact quotation admission. This measures semantic/citation behavior, not
real-bank fraud prevention or completed payments. The bundled eight cases are
developer-authored probes, NOT independent held-out validation.

```bash
PYTHONPATH=src python tools/evaluate_friday_risk.py \
  --cases examples/friday_risk_benchmark.jsonl
# Only with configured live Gemini and an agreed model-call budget:
PYTHONPATH=src python tools/evaluate_friday_risk.py \
  --cases path/to/frozen-independent-cases.jsonl --max-cases 20 --live \
  --label-origin 'Reviewer name; frozen review date'
```

No executor or payment endpoint is called. Default mode makes zero model calls;
live mode makes two calls per case, up to 50 cases. Label provenance is recorded
as declared, not independently authenticated by the runner. No winner score or
real-world accuracy is inferred from these probes.

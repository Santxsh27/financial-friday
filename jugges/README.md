# Older Financial Friday test fixtures

**Use [the new judge kit](../judge-kit/README.md) for the current six-month samples, goals, voice and click-by-click walkthrough.** These older files are kept for regression tests; their totals differ.

All files in this folder contain artificial data, not a real customer's records.
The folder name follows the requested `jugges` spelling. Share this folder only,
not `.env`, private testing folders or the entire local working directory.

Start with [the hosted walkthrough and downloads](https://financial-friday-web-171681243260.asia-south1.run.app/assets/friday-judge-guide.html).
It explains Google sign-in, every main step, expected results, optional voice and
limits without requiring GitHub sign-in. The source repository is now public. The deployment
identity and acceptance state are recorded in [the release record](../docs/CURRENT_RELEASE.json).
If a candidate release is still local/staged, use that record rather than assume
the source changes have been promoted.

## A short tour

For the new goal/research path, start with [TRY-GOALS.txt](TRY-GOALS.txt).
It has one artificial purchase scenario, expected results and the separate
public-research consent steps. One confirmed priority and self-reported updates persist privately; unsaved previews do not.

1. Home → Add a statement → choose `statements/03-Simple-4-Rows.csv`.
2. Confirm processing → Read my statement → compare four rows.
3. Confirm storage → Save & see my spending.
4. Expect identified income **INR 10,000** and classified spending **INR 3,200.50**
   when this is the only selected import and the proposed labels are unchanged.
5. Open All entries, then Back. Inspect the prepared comparison worksheet;
   a repeated-entry candidate is not proof of a second bank debit.
6. Ask Friday → Choose what I can use → share statement totals → Done.
   Ask: “Where did my spending go, and what should I review first?”
7. Listen → consent to Google processing of briefing totals → Generate → Play,
   if the configured voice service is available.
8. Statements → Start a new review. The file remains saved and can be selected
   again with Apply & see my money. No payment or bank connection is involved.

## Other files

[Five artificial bank-format cases](bank-formats/README.md) exercise public
illustration headings and clearly labelled candidate layouts. Try one at a time;
they repeat the same activity and must not be treated as five different accounts.

| File | Purpose |
| --- | --- |
| `statements/01-Complete-35-Rows.csv` | Three-month artificial history with multiple review candidates |
| `statements/02-Source-Checks-2-Rows.csv` | Two-row source-fact reconciliation exercise |
| `documents/ARTIFICIAL-Generic-Bank-Statement.pdf` | The same two-row example in PDF; uses configured Google extraction |

Do not combine independent samples when checking their isolated totals. The
two-row CSV and PDF overlap. Real AI reading may fail or reach trial limits;
Friday must show that failure rather than invent a successful result.

# Try Financial Friday

All files in this folder contain artificial data, not a real customer's records.
The folder name follows the requested `jugges` spelling. Share this folder only,
not `.env`, private testing folders or the entire local working directory.

The new library workflow is in local 0.33.0 verification. The hosted 0.32.0 site
does not yet have the new source-selection/fresh-review controls. See the root
[Start Here](../START_HERE.md) and [release record](../docs/CURRENT_RELEASE.json)
before conducting a hosted judging tour.

## A short tour

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
| `documents/04-Artificial-Bank-Statement.pdf` | The same two-row example in PDF; uses configured Google extraction |
| `documents/05-Artificial-Bill.pdf` | Separate document review, not statement upload |

Do not combine independent samples when checking their isolated totals. The
two-row CSV and PDF overlap. Real AI reading may fail or reach trial limits;
Friday must show that failure rather than invent a successful result.

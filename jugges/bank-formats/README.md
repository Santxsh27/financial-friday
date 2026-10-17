# Artificial bank-format checks

All five files contain invented transactions. They are not bank-issued documents,
do not contain a real customer's information and do not authenticate an account.

Try **one file at a time** in Friday: **Home → Add a statement → choose CSV →
Read statement → check preview → Save → My money**. Use **Statements → Start a
new review** before the next file. The old import remains available to restore.
Do not add all five together: they represent the same artificial activity in
different layouts, not five different accounts.

Expected result for each file:

| Result | Expected |
| --- | ---: |
| Transactions | 4 |
| Money in | ₹50,000.00 |
| Money out | ₹1,390.75 |
| Net flow | ₹48,609.25 |
| Printed opening balance | ₹10,000.00 |
| Last printed running balance | ₹58,609.25 |
| Transaction dates | 2–5 August 2026 |

The opening-balance row is a source fact, not income. Net flow is not the balance.
Missing closing totals/page controls remain **Unknown**, not a green guarantee.

## What was researched

1. `01-hdfc-illustration.csv`: headings from the public [HDFC average-monthly-balance
   illustration](https://www.hdfc.bank.in/terms-and-conditions). Its printed
   `Narrarion` spelling is preserved. Values and dates are invented; our fixture
   uses four-digit years. This is not a current downloadable-export specification.
2. `02-kotak-illustration.csv`: headings, English ordinal date style and `Rs.`
   notation from the public [Kotak account FAQ illustration](https://www.kotak.bank.in/en/get-help/accounts.html).
   The transactions are invented. This is not a current downloadable-export specification.
3. `03-icici-candidate.csv`: a **synthetic candidate layout**. [ICICI confirms
   PDF and CSV downloads](https://www.icici.bank.in/personal-banking/ways-to-bank/net-banking/online-services),
   but that page does not specify its exact table columns. Do not present this
   file as an exact ICICI export or evidence of universal ICICI compatibility.
4. `04-tab-export-candidate.csv`: generic tab-separated export variation.
5. `05-semicolon-export-candidate.csv`: generic semicolon-separated, reordered
   columns with dotted day-first dates.

Public sources checked 17 October 2026. No customer statements from search results
were copied. Fixture inputs and independent integer-paise controls are versioned
in `examples/friday-bank-format-cases.json`.

## Actual support and limits

The deterministic CSV adapter accepts recognised separate date, description,
debit and credit columns. It handles comma/semicolon/tab delimiters, UTF-8 and
BOM-marked UTF-16, bounded recognised preambles, supported day-first dates with
four-digit years and valid INR amounts. It rejects ambiguous/unknown columns,
unexplained rows, invalid encodings and mixed currencies. No partial import is
accepted. Single signed-amount exports, Excel files, two-digit years and arbitrary
layouts are not covered by these tests.

PDFs use the existing consented Gemini extraction path and need a live configured
provider. Scans need configured OCR. These five CSV checks run without model calls;
they do not establish PDF extraction accuracy or train Gemini. A real downloaded,
redacted export is still needed to validate a particular bank/export version.

**Release status:** these compatibility additions are verified locally first.
The old cloud site does not gain them until a separately verified deployment.

# Financial Friday user guide

The main journey is **Add → Review → My money → Ask Friday**. Optional tools
stay outside it. Check [CURRENT_RELEASE](docs/CURRENT_RELEASE.json) before
assuming local changes are already on the hosted site.

## Sign in and identify your workspace

Use Google sign-in on the hosted website. A returning browser can reuse its
Google session. Open **top-right initials/name → My account** to see your email.
**Switch account / sign out** explains Friday's IAP login-cookie reset; it does
not sign you out of every Google service. Local development shows **Local demo**.

## Add a statement

1. Choose **Home → Add a statement**, or **Statements → Add a statement**.
2. Choose a downloaded bank/card **PDF or CSV**. Use a redacted copy where
   possible. Do not supply passwords, OTPs, PINs or payment secrets.
3. Set **Account nickname** and **Statement type**. Keep the same nickname for
   exports from one account; choose a different nickname for another account.
4. Tick the processing consent and **Read my statement**. CSV parsing is
   deterministic. PDFs use configured Google AI; scans also require Document AI.
5. Wait for **Review before saving**. Extraction errors save no rows. Reloading
   discards an unsaved preview, not your saved statement library.

Supported bank CSV exports do not need to be rewritten into demo columns.
Friday recognises explicit heading aliases and a bounded recognised preamble.
Unknown columns, ambiguous financial fields or unexplained rows stop the import.
Synthetic bank-shaped tests do not establish compatibility with every real ICICI
export. PDFs can have varying layouts but extraction can still fail.

For five new artificial bank-format checks, open
[the bank-format test guide](jugges/bank-formats/README.md). They cover public
HDFC/Kotak illustrations, an explicitly unverified ICICI candidate and two generic
export variations. These are not downloaded customer statements or bank certifications.
Supported CSVs may be comma-, semicolon- or tab-separated, UTF-8 or BOM-marked
UTF-16. Four-digit years and separate debit/credit columns are required.

Unlock PDFs on your device first; Friday has no password-entry box. INR only.
PDF: 4 MB, 6 pages and 200 rows. CSV: 1 MB/500 rows. Split larger exports without
overlapping date ranges.

## Review and save

1. Compare row count, dates and amounts against the original.
2. Expand **Source checks**. Agreement is arithmetic/source-fact agreement, not
   bank authentication. Missing facts remain unknown. Mismatches block saving.
3. Expand **Review transaction rows & change labels** if needed. Meaning and
   Category are editable; source dates/amounts are not. Loans received are not
   income, and card repayments are not new purchases.
4. Tick the private-storage confirmation, then **Save & see my spending**.

Friday stores reviewed normalized rows and minimal extraction evidence, not the
raw file. The same source is not added twice. If saving conflicts, reload the
saved history; do not edit a source just to bypass that conflict.

## Choose the statements in a review

**Statements** is the library, not a duplicate upload page. Each import shows its
account nickname/type, date range, row count and short source-file identity.
Original filenames are not retained; use account nicknames and dates to identify
your sources.

- Tick imports, then **Apply & see my money**. Unticked imports remain saved,
  excluded from charts and statement-based Gemini context.
- **Reload** fetches the current selection; it does not apply unsaved checkboxes.
- **Start a new review → Start new review** excludes earlier imports without
  deleting them, then opens upload. Tick the old imports again to restore them.
- The selection applies across your Friday tabs. Stale updates are rejected.
- Excluded imports still count toward the 10-import/2,000-row workspace limit.

**New chat** is not a fresh financial review. **Privacy cleanup** deletes records
and is not the reversible fresh-review control.

## Understand My money

The source banner shows the selected statement count, dates, entry count and
review version. **Which statements?** lists the sources. **Choose statements**
opens the library. Compare the same source set when comparing results.

The chart shows classified spending. Income, transfers, repayments, refunds and
unclear credits have different meanings. These figures are not a bank balance,
net worth or complete affordability assessment.

The highlighted review item is a candidate, not confirmed fraud:

- **Read the prepared worksheet/enquiry** previews its actual prepared text.
- **Save worksheet/enquiry** downloads it; nothing is sent to a bank.
- **Reviewed → next** acknowledges the item without changing transactions.
- **Review history → Reopen finding** reverses that acknowledgement.
- **All entries** opens searchable transactions.
- **Payment patterns** opens observed recurring patterns, not verified mandates.
- **Review history** lists findings, source evidence and review state.
- **Back** returns through the journey/detail views. Direct links have a safe
  parent destination rather than taking you outside Friday.

Some candidates produce worksheets rather than bank enquiries. Overlapping
files, missing coverage and changed descriptions can create false alerts or
missed findings. Friday does not issue a universal Safe badge.

## Ask Friday

Open **Ask Friday** in the navigation, or use the right-side chat on wide
screens. Small screens use a dedicated chat page.

1. Open **Choose what I can use**.
2. To personalise answers, enable statement totals/checkup findings, then Done.
   That toggle does not share transaction descriptions.
3. Type a question and send with the arrow or **Ctrl/⌘ + Enter**.
4. The reply's source line distinguishes general guidance from an answer based
   on a specified selected-statement review version.
5. Choose an **Open…** button to view a prepared plan or finding. Chat does not
   unexpectedly navigate to another page.

Try **Where did my spending go?**, **Show my regular payment patterns**, or
**Help me reduce spending by INR 1000 per month without cutting transport**.
Share relevant context explicitly before asking about your own figures.

**New chat** clears only the page conversation. Changing sources/context clears
stale conversation state. Source changes during a model request invalidate the
older answer. Optional diary, cash-flow and inbox context have separate choices
and do not become statement totals. If Gemini is unavailable or rejects an
unsupported answer, saved charts still work; no canned live reply is substituted.

## Listen to your review

1. Choose **Listen** in navigation or **Listen to my review** in chat.
2. The statement briefing opens in My money. With no selected statement, first
   choose a saved import or add one.
3. Tick consent to send its derived briefing totals to Google.
4. **Generate my briefing → Play**. **Read the spoken figures** shows a transcript.

This is generated speech, not a microphone or always-listening assistant. It does
not autoplay. Stale audio stops after context changes. If Google voice is
unavailable, use the on-screen review.

## Optional tools and settings

**My account → Optional tools** keeps other workflows separate:

| Tool | Purpose and boundary |
| --- | --- |
| Build a money plan | Checked category-reduction scenarios, not guaranteed savings or automatic changes |
| Explore a purchase | Replays confirmed cash-buffer/purchase assumptions against supplied history, not live bank affordability |
| Check a separate bill | Extracts document claims; receipts/invoices are not statements or settlement evidence |
| Bill review inbox | Optional document cases and unsent follow-up preparation |
| Diary & runway | User-entered diary/cash-flow assumptions, separate from statement totals |

The moon/sun control changes theme. Settings opens appearance, sound and motion
preferences. Sound is opt-in; reduced motion is respected. The account menu
opens profile and privacy. Privacy cleanup is destructive: read its confirmation
and use **Start a new review** instead when you only want a clean analysis.

## Test with artificial files

Start with `jugges/statements/03-Simple-4-Rows.csv`. Used alone with unchanged
proposed labels: identified income INR 10,000; spending INR 3,200.50.
`01-Complete-35-Rows.csv` provides more patterns and candidates. Start a new
review between independent examples to avoid combining their totals.

The artificial bank PDF and source-check CSV describe the same two transactions:
do not combine them for isolated totals. `05-Artificial-Bill.pdf` belongs in
**Check a separate bill**, not statement upload. Never use a shared Google account
or local demo workspace for personal financial statements.

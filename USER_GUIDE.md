# Financial Friday user guide

Choose **Goals** for a purchase, savings or reserve roadmap, **Research** for an explicitly requested
public-source snapshot, or **Statements** for **Add → Review → My money → Ask Friday**.
Check [CURRENT_RELEASE](docs/CURRENT_RELEASE.json) before
assuming local changes are already on the hosted site.

## Build and track a goal

1. Open **Goals**, or choose **Plan a goal** in Friday's chat. Allow Gemini goal
   processing beside the message box; **Goal tools → Edit numbers** works without AI.
2. Describe the goal: “A travel fund of ₹1,20,000 in 12 months.” Include any budget
   facts you know. Answer only missing questions, one number at a time.
3. Reply to missing questions in the same message box. Friday automatically offers
   available statement trends as optional estimates. Review their coverage before
   accepting. It cannot infer current cash. You need not switch to another form.
4. The result appears automatically in the conversation:
   **progress ring → milestones → monthly step → projected path**. Exact math
   and assumptions are collapsed. Dashed stress path is not a forecast.
5. **Save my roadmap → confirm → Confirm & save**. It restores after reload.
6. **I saved some money → amount → Review update → confirm** records additional
   money actually set aside, not your starting savings again. Or tell Friday
   “I saved ₹1000”. **My savings updates → Undo** corrects a report, not a payment.
7. With goal/roadmap consent enabled, ask Friday “What should I focus on?” It sees
   saved or current unsaved roadmap totals only. Chat cannot change the goal or move money.
8. **Goal tools → Reload saved goal** checks uncertain save outcomes. **Export saved goal**
   includes archives. Privacy's explicit input cleanup clears goals too.

One priority is active. Starting another doesn't replace it until you confirm.
“Stable by 2028” can become a reserve of your chosen months of living costs plus
debt payments, not a guarantee or complete financial-health assessment. Check the
displayed date: a year-only request proposes December of that year.

## Advanced purchase calculator or public research

Goals → **Advanced · unsaved purchase & loan calculator**. Describe the goal and whatever budget facts you
know. Confirm sending only this text to Gemini, or choose Enter or edit my numbers
without an AI call. Review the proposed fields; fill unknowns honestly. Existing
debt means monthly repayments, not total debt balance. Savings means available
liquid savings, not property value or a bank-confirmed balance.

Optional financing starts off at 100% down payment. Enter your own assumed down
payment/rate/term and extra costs if needed. Add at most two more goals. Review
and confirm all assumptions, then Build my visual plan. Inspect baseline/stress
cards, timeline and exact figures. Adjust recalculates; Export downloads JSON.
The advanced calculator does not remember these scenarios after reload; the
separate saved priority roadmap above does. No return or price forecast.

Chat's **Current info** opens a short query-review dialog. Type a public financial
question, without account details or personal financial circumstances. Confirm
Google Search processing and choose **Search & show here**. Results appear in chat.
The advanced Research tool remains available separately. Inspect source dates, units,
source links and Google Search Suggestions. A retrieval time is not the price's
date; these are research results, not a streaming feed or personalised advice.
A failure is not replaced by a made-up figure. Saved statements are not shared.

[Artificial goal walkthrough](jugges/TRY-GOALS.txt).

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
5. Goals prepare in the conversation, with explicit interpretation consent. A public
   query is shown before any Search call. Statement detail tools use labelled
   **Open…** buttons. No chat message authorises a bank action.

Try **Where did my spending go?**, **Show my regular payment patterns**, or
**Help me reduce spending by INR 1000 per month without cutting transport**.
Share relevant context explicitly before asking about your own figures.

**New chat** clears only the page conversation. Changing sources/context clears
stale conversation state. Source changes during a model request invalidate the
older answer. Optional diary and cash-flow context have separate choices
and do not become statement totals. If Gemini is unavailable or rejects an
unsupported answer, saved charts still work; no canned live reply is substituted.

## Talk to Friday and hear replies

1. Choose the floating **Talk to Friday** button, or the same button beside chat.
2. Confirm sending the short clip to Google, then **Start recording**. Your browser
   asks for microphone permission. You can decline and choose **Type instead**.
3. Ask a short question. **Stop & transcribe**, or it stops after 25 seconds.
4. The transcript appears in the normal message box. Check numbers and wording,
   correct anything wrong, then send. A transcript is not a financial instruction.
5. Optional **Speak short replies** allows Google narration of displayed reply text.
   It reads eligible new replies; **Read last reply** repeats one. **Stop audio**
   stops playback. Long replies remain text-only; use on-screen numbers as reference.
6. New chat or privacy cleanup stops audio and turns voice-reply consent off.

This is push-to-talk, not a wake-word or continuous Live API session. Friday stores
no recordings; microphone capture is limited to an explicit turn. Google provider
processing still applies. Speech can mishear or mispronounce financial figures.
Typing and visual output remain the reliable fallback.

## Listen to your statement review

1. Open **My money** and expand its voice briefing.
2. With no selected statement, first
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
do not combine them for isolated totals. The judge kit includes bank-labelled
CSV names and `documents/ARTIFICIAL-Generic-Bank-Statement.pdf`. A standalone bill
is not a bank statement; the retired bill example is not part of this product.
Use **Home → Try a sample · quick walkthrough** to download samples without
GitHub access. Never use a shared Google account or local demo workspace for
personal financial statements.

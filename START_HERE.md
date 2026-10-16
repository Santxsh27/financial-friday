# Financial Friday — Start Here

Updated 16 October 2026; Money Shield interface `0.29.0`. New teammates: read
[ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md) too.
Use [the reports index](docs/REPORTS_INDEX.md) for verified results and dated
historical reports. Private repository access requires an invitation to your
GitHub account; website Google login is separate.

## What this application does

Friday automatically checks supported INR bank/card statements for patterns,
amount changes and entries worth reviewing, then prepares an unsent enquiry when
needed. You do not need to type every expense. Statements
are user-supplied records, not authenticated bank feeds. Earlier bill checks,
diary/runway and artificial payments remain optional under **My account → More financial tools**.

## First tour: no payment required

1. Open [the live site](https://financial-friday-web-171681243260.asia-south1.run.app/#home)
   and sign in with Google. **Top-right initials/name → My account** shows the signed-in email. Returning users
   may reuse their Google session; no bank connection is implied.
2. **Home → Add a statement** (or **Statements**). Choose an INR PDF or CSV, an account
   nickname and bank/card type. **Try a labelled statement example** downloads
   artificial CSV data; upload that file to test the real parser.
3. Confirm processing and **Read my statement**. Expect an unsaved preview with
   totals. Expand the row review to correct interpretation labels. No payment.
4. Confirm review and **Save & see my spending**. **My money** opens with charts,
   automatic findings and regular-payment patterns. Same file: no double import.
5. **Manage imports** excludes/restores overlapping files without deleting them.
   **My money → Money shield** follows possible purchase/refund trails without
   choosing an ambiguous match. For a quick test, download the labelled **Money
   Shield example** from Statements. See [the 13-row guided example](docs/MONEY_SHIELD_0290.md).
6. **Needs a look** → expand a finding → **Prepare bank enquiry** fills a real
   unsent message with source entries. Download after review. **Mark reviewed**
   and **Reopen finding** change only its acknowledgement, never a transaction.
7. In the right-side chat (the
   **Friday** page on phones), open **Choose what I can use**, select **Share my
   saved statement totals**, and choose **Done**. Send with the arrow or
   Ctrl/⌘ + Enter. Only aggregates enter this context, not transaction descriptions.
   Try **“Show my regular payments”** or **“Prepare an enquiry for the repeated
   entry.”** Friday opens the view or builds the unsent draft. No guaranteed
   savings or bank action. For an optional advanced plan, try **“Help me reduce spending by INR
   1000 per month. Protect transport and test 20% lower income.”** Friday opens
   a checked, editable visual plan. A requested reduction that cannot fit its
   caps shows the shortfall. **Spending → Build a visual money plan** also works
   without Gemini for manual scenarios.
8. **Top-right initials/name → My account → Open privacy & cleanup** explains removal of private inputs. Read
   its confirmation: statement history, diary and forecasts clear together.

## Optional advanced decision tool

1. Optional advanced tool: after saving an included **bank-account** statement,
   open **My account → More financial tools → Decision rehearsal**.
2. Optionally ask **“Can I buy a laptop for INR 15000 in 7 days if salary is
   10 days late? Protect transport.”** Choose **Let Gemini set this up**. Only
   the question goes to the model; review the proposed fields.
3. Enter the selected account's available cash, your protected buffer and the
   purchase amount. Use fictional numbers when exploring an artificial statement.
4. Expand **Review the stress test & protected costs**. Check start date, horizon,
   delay, income reduction and essential-cost increase. Confirm the replay
   assumptions, then **Rehearse this decision**.
5. Compare the original gap, smaller-purchase limit, later date and flexible-cost
   option. **Use this scenario input** changes an input, not a bank payment;
   recalculate to check it. Exact figures are below the daily chart.
6. Optional **Explain these results with Gemini** shares checked result totals,
   dates and coverage warnings only. It cannot change the computed result.

These are historical-template replays, not predictions. No real money moves.

Demo bounds: INR; PDF 4 MB/1–6 pages/up to 200 extracted rows; documented CSV
schema/1 MB/up to 500 rows. Ten imports/2,000 normalized rows total. Unlock PDFs locally;
never provide passwords, PINs, OTPs or full account identifiers. Six months can be
supplied across supported exports, not necessarily every bank's format.

## Separate artificial-payment demonstration

Optional tools under **My account → More financial tools** use Friday's own artificial
ledger. Read [USER_GUIDE.md](USER_GUIDE.md) before changing limits or approving a
task. An explicit handle/approval action may move artificial funds; home chat and
default document review never do. Automatic execution is off for new visitors.
The signed result concerns sandbox execution, not real settlement.

## Local setup

Start Docker Desktop, then run from your clone:

```bash
docker compose up -d --build api anthos-demo
```

Open <http://localhost:8090/#home> or <http://localhost:8080/docs> for API reference.
`anthos-demo` is a compatibility name for Friday's website. Anthos is not needed.
Without credentials the sandbox uses `LOCAL_RULES`, and live chat/extraction reports
unavailable. Use the cloud site for live AI or follow [CONTRIBUTING.md](CONTRIBUTING.md).
Stop with `docker compose stop`; do not delete volumes or commit `.env`.

## Remaining work

Broader bank-format/accuracy evaluation, independently checked usefulness, loan
principal/APR extraction and final submission artifacts remain pending. No real
bank feed or continuous monitoring is claimed. See [statement release scope](docs/STATEMENTS_0240.md).

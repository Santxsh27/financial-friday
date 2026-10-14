# Financial Friday — Start Here

Updated 15 October 2026; current release `0.24.0`. New teammates: read
[ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md) too.
Use [the reports index](docs/REPORTS_INDEX.md) for verified results and dated
historical reports. Private repository access requires an invitation to your
GitHub account; website Google login is separate.

## What this application does

Friday turns supported INR bank/card statements into a user-reviewed spending
picture and practical guidance. You do not need to type every expense. Statements
are user-supplied records, not authenticated bank feeds. Earlier bill checks,
diary/runway and artificial payments remain optional under More tools.

## First tour: no payment required

1. Open [the live site](https://financial-friday-web-171681243260.asia-south1.run.app/#home)
   and sign in with Google. **Account** shows the signed-in email. Returning users
   may reuse their Google session; no bank connection is implied.
2. **Home → Understand my statements**. Choose an INR PDF or CSV, an account
   nickname and bank/card type. **Try a labelled statement example** downloads
   artificial CSV data; upload that file to test the real parser.
3. Confirm processing and **Read my statement**. Expect an unsaved preview with
   totals. Expand the row review to correct interpretation labels. No payment.
4. Confirm review and **Save & see my spending**. Expect categories, monthly bars,
   identified income, repayments and coverage warnings. Same file: no double import.
5. **Manage imports** excludes/restores overlapping files without deleting them.
6. **Ask Friday about this** prepares a question. Select **Share my saved statement
   totals**, then **Ask Friday** for Gemini guidance. Only aggregates enter this
   context, not transaction descriptions. No guaranteed savings or bank action.
7. **Account → Open privacy & cleanup** explains removal of private inputs. Read
   its confirmation: statement history, diary and forecasts clear together.

Demo bounds: INR; PDF 4 MB/1–6 pages/up to 200 extracted rows; documented CSV
schema/1 MB/up to 500 rows. Ten imports/2,000 normalized rows total. Unlock PDFs locally;
never provide passwords, PINs, OTPs or full account identifiers. Six months can be
supplied across supported exports, not necessarily every bank's format.

## Separate artificial-payment demonstration

Optional tools under More tools use Friday's own artificial
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

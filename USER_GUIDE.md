# Financial Friday complete user walkthrough

This guide explains what to click, what to enter, what Financial Friday does, and
what result to expect. Start with the read-only tour, then try an artificial-money
task. Friday is a working Google Gemini assistant with a separate safety checker;
it is **not connected to your real bank, GPay, SMS inbox or utility account**.

Behind the website, Gemini on Vertex AI understands input and proposes structured
actions. Python/FastAPI verifies evidence and permission, performs restricted
execution, and checks the result. Cloud Run hosts the protected app; transactional
Firestore stores cloud rules, records and receipts, while local Docker uses SQLite.
Exact code—not Gemini—calculates rupee totals and the reserve-aware bill plan.

Updated for the website available on October 12, 2026. Records, balances, wording
and AI responses can vary. A stopped or unverified task can be the correct result.

## Contents

**Current default:** Home and Documents now perform read-only financial review.
They do not execute payments. Open **Financial inbox** to see related bills,
receipts, conflicting evidence and prepared verification messages. No provider
setup or saved automatic permission is required for review. Follow
[the new click-by-click workflow](docs/FINANCIAL_REVIEW.md) first. The sandbox
payment steps below apply only to the separate explicit artificial-payment mode.


1. [Before you begin](#before-you-begin)
2. [A first visit without making a payment](#a-first-visit-without-making-a-payment)
3. [Every top bar and Overview control](#every-top-bar-and-overview-control)
4. [My rules and automatic permission](#my-rules-and-automatic-permission)
5. [Bills and the reserve aware plan](#bills-and-the-reserve-aware-plan)
6. [New messages and a fresh test bill](#new-messages-and-a-fresh-test-bill)
7. [Bill photos and PDFs](#bill-photos-and-pdfs)
8. [Spending review with a statement CSV](#spending-review-with-a-statement-csv)
9. [Saved inputs and the demo wallet](#saved-inputs-and-the-demo-wallet)
10. [Safety Lab scenarios](#safety-lab-scenarios)
11. [Task results and technical evidence](#task-results-and-technical-evidence)
12. [Activity and reopening receipts](#activity-and-reopening-receipts)
13. [Local monitoring and earlier project components](#local-monitoring-and-earlier-project-components)
14. [Troubleshooting and limits](#troubleshooting-and-limits)
15. [A complete practice checklist](#a-complete-practice-checklist)

## Before you begin

### Choose the website

- **Cloud website:** [Open Financial Friday](https://financial-friday-web-171681243260.asia-south1.run.app/#home).
  Sign in with Google. The public-demo release gives each new Google user an
  isolated artificial-money workspace; the owner's existing records are not shared.
  New visitors start with no saved documents. Open **Documents** or paste a
  financial notice at Home, then review **Financial inbox**. No provider setup is
  needed for this read-only flow. A school/company Google administrator may restrict sign-in.
- **Local website:** [Open local Friday](http://localhost:8090/#home), after starting
  Docker Desktop and running the command below from the project folder.
- **API reference:** [Local API docs](http://localhost:8080/docs). This is an
  engineer's interface, not the normal customer website.

```bash
cd /Users/santosh/Desktop/CARAPACE
docker compose --profile anthos up -d --build api anthos-demo
```

The folder and internal Python names remain compatible with earlier installations.
The product and GitHub repository are Financial Friday. Do not rename a running
folder or replace environment variables just to change its display name.

### Understand the three kinds of clicks

| Kind | Examples | What changes |
| --- | --- | --- |
| Read-only | Overview, Review bill, Refresh, Activity, opening receipts | Loads or displays existing evidence. Does not pay. |
| Settings or preparation | Save instruction, Publish test bill, Routine bill, sound/theme controls | Changes saved permission, artificial provider records, or this browser's preferences. Does not itself pay. |
| Review and storage | Review with Friday, Read & reconcile, Import transaction claims | Runs understanding/reconciliation and saves extracted claims; never submits a payment. CSV storage requires explicit consent. |
| Execution capable | Explicit original artificial-payment mode, Check & handle in sandbox, Approve this artificial-money task, Run this demo | Can run checks and record an artificial-money effect when the specific task is allowed. |

**Important:** “Check” is not always a read-only action. A matching bill can execute
under your saved automatic permission. Inspect **My rules** first. No real money
is connected, but test payments do change the persistent sandbox balance/history.

Use artificial examples or redacted documents. Never enter an OTP, UPI PIN, CVV,
password, account credential or identity document. Gemini requests may consume
the project owner's API quota or cloud credit; repeated demos are not guaranteed
to be free simply because the interface is a prototype.

Public visitors have **20 action requests per account per UTC day**, and **200
action requests shared across visitors**. Saving rules, publishing bills and
analyzing inputs count, even if a later step fails. Burst limits allow four actions
per account per minute and twenty globally. Separate read limits preserve normal
navigation. When you see an allowance message, read existing results or try later;
do not repeatedly retry payments. Limits reset daily at midnight UTC (5:30 AM IST).
These are request limits—not a hard rupee spending cap on Google Cloud charges.

## A first visit without making a payment

1. Open **Overview**. Read the bill inbox and the sentence beneath Friday's command box.
2. Click **My rules**. Inspect the existing settings without clicking Save.
3. Click **Bills**. Read the selected amount, bill reference and recipient. Do **not**
   click **Check & handle in sandbox** yet.
4. Expand **Evidence & independent checks** to see why records fit or do not fit.
5. Click **Activity**, then any existing task. This reopens its receipt; it does not run again.
6. Click **How Friday checked this** on the result page to inspect independent replay.
7. Return to **Overview**. Click **How Friday works**, then press **Escape** to close it.
8. Try the moon/sun button and gear. These settings do not change financial rules.

For a manual-approval practice session, you may uncheck automatic execution in
**My rules** and click **Save instruction**. That changes the sandbox account's
standing permission, not just this tab. It does not disable an explicit **Run this
demo** action in Safety Lab. Leave existing values untouched unless you intend to
change them; restore your chosen setting after the exercise.

## Every top bar and Overview control

| Control | What to do | What it does and what to expect |
| --- | --- | --- |
| Team mark and Financial Friday name | No input required | Product branding, not a verified-bank seal or payment button. |
| Overview | Click | Returns to the current bill inbox and command box. |
| Bills | Click | Opens the read-only bill plan, not the message editor. |
| Documents | Click | Opens the photo/PDF input page. Selecting a file alone does not submit it. |
| Activity | Click | Loads the most recent recorded tasks and filters. |
| My rules | Click | Shows standing permission, reserve and limits. Opening it does not save changes. |
| Moon or sun | Click | Switches Daylight/Midnight. The button's tooltip names the next mode. |
| Gear | Click | Opens **Make Friday yours**. Escape or Close dismisses it and returns focus. |
| Colour theme | Choose Daylight, Midnight or Use device | Changes the display. Device mode follows the operating system theme. Saved only in this browser. |
| Interface sounds | Tap to enable or mute | Quiet synthesized clicks. Muted for a fresh browser; no microphone access, page-load sound or bank-confirmation chime. Browser/device output settings affect audibility. |
| Motion on or Motion off | Click | Toggles decorative motion. Device reduced-motion settings take priority and can disable the toggle. Motion is not financial evidence. |
| Artificial-money sandbox dropdown | Click | Opens **My money** and **Safety lab**. It does not change to real-money mode. |
| Review bill or See details | Click next to a bill | Opens the plan and current details. No payment yet; a review record may not be eligible to select for execution. |
| See reasons | Click the warning | Opens the plan's evidence area. Read the limit, reserve, increase or missing-evidence reason. |
| Manage rules | Click | Same destination as My rules. |
| Understand my money | Click | Opens the money workspace, initially the bill plan. Use **Back to My money** for spending, saved inputs and wallet choices. |
| Review spending | Click | Opens statement CSV review. Read-only analysis; no payment. |
| View all or a recent outcome label | Click | View all opens Activity; an outcome opens its saved receipt without executing again. |
| What should Friday handle? | Paste a bill message | Text is not sent merely by typing. Use the examples below; this is not an unrestricted stock-market chatbot. |
| Check my bill | Click after reviewing your input and rules | Sends the message to Gemini and the safety pipeline. Can handle a matching artificial bill automatically within saved rules. |
| Read a document | Click | Same destination as Documents; it does not upload or pay by itself. |
| How Friday works | Click | Opens the help dialog with the main safety boundaries. Close/Escape dismisses it. |

The cloud warning about **seven records above your limit** refers to existing
₹3,001 development bills exceeding the saved ₹3,000 ceiling. It is not seven
failed payments. Do not delete evidence or increase a limit simply to remove it.
Your local account can have different records and limits.

Keyboard shortcuts: **/** focuses the home command when you are not typing in a
field; **?** opens help; **Escape** closes a dialog/menu. Use Tab and Shift+Tab to
move among controls. These navigation shortcuts do not operate behind the
appearance dialog.

## My rules and automatic permission

1. Click **My rules**, then expand **Your standing permission** if necessary.
2. Read or edit the fields below.
3. Click **Save instruction** only when you intend to save those settings.
4. Expect a saved-instruction notice. On failure, do not assume the new values
   took effect; reopen the page to inspect what the server saved.

| Field | Example for practice | Meaning |
| --- | --- | --- |
| Instruction | Handle verified household bills up to my limit, protect my reserve, and never create subscriptions. | Description of your intent. It is not a magic command that can expand the code's allowed actions. |
| Protected balance | `10000.00` | Minimum artificial balance to preserve. It does not create a separate real savings account. |
| Automatic limit | `3000.00` | Ceiling for a single eligible automatic artificial payment. Not a monthly budget. |
| Review bill increases above (%) | `30` | Hold bills whose supported comparison exceeds this increase. Missing history is not proof that a bill is normal. |
| Automatically execute verified artificial-money bills | Unchecked for manual practice; checked for automatic practice | Whether eligible message/document tasks can execute using standing permission. |

Numeric fields are in **rupees**, not paise. Saved rules have deterministic checks;
fees and subscriptions are not made permissible merely by asking for them in prose.
Changing a rule while a request is prepared can stop that request as stale.

## Bills and the reserve aware plan

1. Click **Bills** or Overview's **Review bill**.
2. Read **Protected reserve**, **Planned bills** and **Above reserve after plan**.
   These are artificial-money planning values, not your bank statement or proof of payment.
3. Click a bill row on the left. The right side shows its exact provider, reference,
   amount and recipient. “Not started” is correct: selecting is not executing.
4. Expand **Evidence & independent checks**. It explains the exact deadline/Pareto
   optimisation and lists review, deferred and previously recorded bills.
5. Click **Refresh** to retrieve a new read-only plan. No AI approval or payment is
   created by refreshing.
6. If you intentionally want to handle the selected artificial bill, click
   **Check & handle in sandbox** once. Wait for the task result.

Friday rechecks the provider record, its hash, your saved permission, reserve and
financial effects before executing. Gemini interprets the selected bill and proposes
a typed plan; it cannot silently change its recipient, amount or currency.
With automatic permission off, an eligible task can stop at **Needs approval**,
showing **Approve this artificial-money task**. Inspect its details before using it.

| Situation | Expected result |
| --- | --- |
| Eligible unpaid bill with sufficient permitted funds | Included in the plan; execution may record one artificial payment when all checks pass. |
| Bill above the saved ceiling | Review warning and no automatic payment. |
| Bill would break the reserve | Deferred/outside this plan, not necessarily a scam. |
| Material increase, conflicting receipt or invalid record | Review/hold with its reason. |
| Bill already has a valid internal receipt | Already-recorded evidence, no new debit for that bill. |
| Provider record or rules change after selection | Stopped/review required; refresh rather than overriding stale evidence. |

The exact optimiser prioritises deadlines within the permitted balance. It does not
predict investments, connect all your accounts or pay every row in the plan at once.
**Back to My money** opens the other money tools; **Back to Friday** returns home.

## New messages and a fresh test bill

### Open the message editor and preparation controls

Open [the cloud message editor](https://financial-friday-web-171681243260.asia-south1.run.app/#bill)
or [the local message editor](http://localhost:8090/#bill). This supported `#bill`
route is separate from the top-bar Bills plan. Expand **Try a demo or set up a test
bill**, then **Demo provider setup**.

These controls write to an **artificial provider** operated by this project.
Publishing a row is not evidence that a real utility authenticated it.

### Create one fresh artificial bill

Enter:

| Field | Value |
| --- | --- |
| Bill reference | `GUIDE-POWER-001` |
| Amount in rupees | `1780.00` |
| Previous artificial bill in rupees (optional) | `1650.00` |
| Test payee | `tnpower@upi` |

Click **Publish test bill**. It creates a TN Power development record due roughly
three days later; it does not submit a payment. Expect the provider-ready message.
If this reference already exists or is paid, use a genuinely new bill reference
for a new exercise, not to disguise or retry an uncertain previous payment.

Paste this into the message editor or the Overview command box:

```text
Please check my one-time TN Power bill GUIDE-POWER-001 for INR 1780.00.
Payee: tnpower@upi. Compare it with the enrolled provider record, protect
my saved reserve, and do not create any subscription or extra fee.
```

Click **Check bill** in the editor, or **Check my bill** on Overview. Both submit
the input to the same pipeline. Expected path: Gemini extracts the facts, Friday
matches the separate provider record, checks your permission, and either waits
for manual approval or handles one artificial payment. An unavailable model,
invalid plan or changed evidence must stop execution rather than invent success.

### Try these variations

| Exercise | What to enter or click | Expected result and limitation |
| --- | --- | --- |
| Same bill again | Submit the same verified bill after it completed | Reuse/reconcile the internal receipt, no second debit. A new recorded run is not a new payment. |
| Wrong recipient | Keep `GUIDE-POWER-001` and `1780.00`, change the message payee to `stranger@upi` | Mismatch/attention, no new payment. Friday does not replace the recipient to force success. |
| Wrong amount | Keep the provider record at `1780.00`, claim `1900.00` in the message | Amount mismatch, no new payment. |
| Paid notice | `Payment successful. TN Power bill GUIDE-POWER-001 for INR 1780.00 to tnpower@upi was already paid. This is a receipt, not a new payment request.` | Interpreted as a notice, not permission for another payment. It does not prove external bank settlement. |
| Unknown provider | `Please pay Example Unknown Utility bill UNKNOWN-001 for INR 100.00 to unknown@upi.` | Facts can be extracted, but no trusted matching provider record means no payment. Check Saved inputs. |
| Unusual increase | Click **Unexpected increase**, then **Check bill** | Creates a fresh ₹2,487 bill with prior ₹1,600; with a 30% review threshold, expect review/attention, not automatic payment. |
| Routine example | Click **Routine bill**, then **Check bill** | Creates a fresh ₹1,780 bill with prior ₹1,650. It may execute only if your rules, reserve and evidence allow it. |
| Changed-recipient example | Click **Changed recipient**, then **Check bill** | Creates provider payee `tnpower@upi` but fills a message claiming `stranger@upi`; expect no payment. |

The three example buttons **prepare records and fill text only**. You still decide
whether to submit the check. Each uses a generated `HOME-...` reference.

Do not paste a stock-trading instruction expecting a purchase, a payment-secret
request expecting secure storage, or a random UPI address expecting bank-ownership
verification. These are outside the supported task vocabulary.

## Bill photos and PDFs

1. Click **Documents** or **Read a document**. No artificial provider setup is required.
2. Choose a bill, invoice, receipt or transaction notice as PNG, JPEG, WebP or PDF,
   at most 8 MB. Selecting does not upload.
3. Read the cloud-processing disclosure and click **Read & reconcile - no payment**.
4. **Financial inbox** displays the saved claim and what needs verification.
5. Add a related receipt or a consented transaction CSV. Friday groups matching
   evidence, highlights contradictions and checks extracted arithmetic.
6. Expand **Prepare a verification message** for a ready-to-copy draft. It is
   prepared only; send through a known official channel yourself.

This review flow never executes a payment, even if automatic permission is on.
Matching claims are not externally verified settlement. An unsupported or
ambiguous currency is shown as unknown, not converted to rupees.

Gemini performs document understanding directly. Extracted quotations are not
independently OCR-verified, and the document is not itself trusted provider evidence.
Raw files are discarded after analysis; extracted facts, evidence references and
run records can remain stored. This is **not** “nothing is retained.”

No selected file should yield a choose-file message; unsupported/oversized files
are rejected. If interpretation or the network fails, do not assume a payment
failed before checking Activity. This feature has no camera, QR-image decoder,
mobile screen-reading permission, malware scan or document-authenticity guarantee.

## Spending review with a statement CSV

This works with your own correctly formatted, redacted input. It does **not** need
a test provider and does **not** ask Gemini to calculate totals.

1. On Overview click **Review spending**. Alternatively click **Bills → Back to My
   money → Review spending**.
2. Download/open [sample statement CSV](docs/user-guide-examples/sample-statement.csv).
3. Click **Choose statement CSV**, then select it.
4. Expand **CSV format & privacy** if needed.
5. Check **I agree to send this CSV to the Friday server for temporary analysis.
   It is not saved or sent to Gemini.**
6. Click **Review statement**. Expect four transactions, ₹10,000.00 money in,
   ₹3,200.50 money out and ₹6,799.50 net flow.
7. Expand **Month-by-month cash flow**, **Largest outgoing entries** and
   **Processing & limitations** to inspect detail.
8. Read **Entries worth checking**. The two identical ₹1,250 utility entries are
   highlighted as possibly legitimate repeats. Both remain in totals; they are
   not automatically removed or called confirmed fraud.
9. Click **Clear results & start again** to clear the displayed analysis and choose
   another file. It is disabled during processing to prevent stale results.

```csv
date,description,debit,credit
2026-10-01,Artificial salary,,10000.00
2026-10-02,Groceries,700.50,
2026-10-03,Utility bill,1250.00,
2026-10-03,Utility bill,1250.00,
```

Requirements: INR rupees, required columns `date,description,debit,credit`, one
positive debit **or** credit per row, dates `YYYY-MM-DD` or `DD/MM/YYYY`, maximum
1 MB and 5,000 transactions. A bank's differently formatted CSV may need conversion.
Without consent or a file, expect an instruction to provide them; malformed data
must not produce partial trusted totals. Net flow is **not** opening/closing balance.
Clear removes the page's result, not other saved bills or receipts. It cannot
erase the original file from your computer or undo any banking transaction.

## Saved inputs and the demo wallet

### Saved inputs

Click **Bills → Back to My money → Saved inputs**. It loads the recent saved message
and document interpretations. **Refresh inputs** reloads them. **Read a new document**
opens Documents. **Show extracted source evidence** expands model quotations.

Read the amount, request kind, reference, claimed recipient and understanding mode.
These are extracted claims, not authenticated bank records. The view is limited
to the most recent 20 inputs and has no delete-all/account-erasure button. An empty
view means no saved inputs are available for this account, not that monitoring is active.

### Demo wallet

Click **Bills → Back to My money → Demo wallet · artificial funds**. If necessary,
click **Refresh my money** (accessible name: Refresh the read-only artificial-money overview).

- **Sandbox balance / protected reserve / above reserve:** read the stored artificial
  values, not your real account balance.
- **Plan around your essentials:** potential commitment totals can include records
  excluded from the exact executable bill plan. Treat them as broad planning totals;
  use Bills for the per-record eligibility decision. **Review my rules** opens settings.
- **Bill records:** expands provider records, amount, due date, recipient and receipt status.
- **What is connected now:** shows implemented versus pending capabilities.
- **Recent recorded outcomes → Review receipt:** opens existing evidence without executing.
- **Know the boundaries:** expands coverage and integration limitations.

### Match recorded payment

The wallet also contains **Follow through without paying again**. Enter the exact
bill reference of an existing signed local artificial receipt, then click
**Match recorded payment**.

On local SQLite, a supported match can return ACKNOWLEDGED/ALREADY_ACKNOWLEDGED;
it records a local acknowledgement, not a new debit or external settlement.
Missing/conflicting evidence returns UNVERIFIED/HOLD. On the deployed cloud system,
this connector is deliberately unavailable. That is a documented limit, not a
button that secretly refunds money. Do not use it to confirm a real UPI payment.

## Safety Lab scenarios

Click **Artificial-money sandbox → Safety lab**. Select a situation, then choose
the **Planning engine**. **Gemini / configured AI** uses the configured provider;
**Local rules comparison** uses deterministic rules and must not be presented as a
live Gemini run. The local site's configured mode can itself be the local fallback.
Use actual provenance in the result, not the dropdown label, to establish AI usage.

Click **Run this demo** only when you intend to execute that controlled scenario.
It has a scoped demo goal and can record artificial financial effects. Merely
selecting a scenario does not run it. Repeated execution may find an existing receipt.

| Scenario button | Controlled input and expected behaviour |
| --- | --- |
| Pay a genuine bill | ₹1,999 one-time bill. A valid checked plan may record one artificial payment; repeating must not create a second financial effect. |
| Avoid a subscription trap | Provider highlights a recurring discount but has a valid ₹1,999 one-time route. Friday may choose that permitted route; if the model cannot produce a safe plan it must hold instead. |
| Refuse an unsafe option | Only recurring options exist. Hold with no new payment; do not relax the one-time goal. |
| Catch a changed recipient | Connector recipient differs from the approved one. Deterministic evidence hold, no payment; AI cannot override it. |
| Recover after a timeout | Fixture says a simulated prior provider operation succeeded. Reconcile that known outcome instead of repeating it. This is not a real outage fix or refund. |

A live model can make several attempts or be unavailable. A safe hold is acceptable;
do not promise every model run will repair itself. The six hostile program mutations
test the verifier's response to altered amount, recipient, cadence, data and action
conditions. They are controlled robustness tests, not attacks on real bank websites.

## Task results and technical evidence

Every submitted task opens a result view. Wait for the service response; the
animated orb and green/red colours are not the source of financial truth.

| Result | Meaning | What to do |
| --- | --- | --- |
| Completed / Receipt recorded | Independent checks support an artificial recorded outcome | Inspect amount/recipient and reopen it later from Activity. |
| Already handled / Already recorded | Existing evidence found; no repeat payment | Do not invent a new bill reference to bypass this protection. |
| Recovered / Reconciled | Prior recorded outcome matched rather than blindly retried | Review its receipt; not a real-bank reversal. |
| Held / Payment stopped | Task was not allowed to create a new payment | Read the precise reason; verify/correct original evidence, not the safety rules to force success. |
| Needs approval | Eligible request waiting for explicit authority | Review amount/recipient, then use Approve only if you intend that artificial task. |
| Needs verification / Unavailable / Conflict | Outcome or evidence cannot be confirmed | Open Activity first. Do not blindly retry a payment after a timeout. |
| Older record / proof unavailable | Historical task predates sealed evidence | Its status is preserved but not certified green retroactively. Do not pay again to make the badge green. |

The main stages mean:

1. **Understand:** structure the requested goal.
2. **Ground evidence:** match the separate provider record.
3. **Plan with AI:** Gemini proposes a restricted program, or a labelled local baseline is used.
4. **Prove safety:** deterministic checks and hostile mutations examine permitted effects.
5. **Act or recover:** execute once, reconcile evidence or stop.

“Planning calls for this run” is historical, not calls made by viewing the receipt.
“Rejected proposals” counts model plans rejected before execution. “Recorded sandbox
payment” is not proof of real bank settlement. AI plan correction does not patch
a bank's production software.

| Evidence control | What you will see |
| --- | --- |
| How Friday checked this | Recorded source, returned outcome and independent saved-outcome replay. Opens automatically when legacy/conflicting evidence needs explanation. |
| Show how Friday verified this | Verified action program, executed events, independent checks and outcome evidence when a complete run is available. |
| Open complete technical evidence | Structured JSON with relevant goal, program, provenance, tests and receipt. For engineers; never paste private evidence publicly. |
| Show source quotations | Extracted message/document quotations when intake returned them. Text quotations are checked against source where supported; document quotes remain model-extracted. |
| Show extracted source evidence | Similar quotations in Saved inputs. Does not authenticate the provider. |
| Approve this artificial-money task | Executes the prepared eligible task under current checks. It is not a dismiss-warning button. |
| New task / Back to Friday | Returns home. Does not repeat the previous task. |
| View my activity | Opens saved results. Does not execute. |

Signed means integrity-protected by this project's configured keys, not certified
by a real bank or regulator. Independent replay checks signature, historical rules
and the local/cloud journal; missing evidence never becomes verified because it is old.

## Activity and reopening receipts

1. Click **Activity** or Overview's **View all**.
2. Use **Refresh activity** for a new read-only snapshot.
3. Type a provider/status/reference phrase visible in a row into **Search recorded
   activity**. Search operates on the returned recent list, not all historical bank data.
4. Choose **All**, **Confirmed**, **Held** or **Review**. Confirmed uses independent
   assurance; older/unsealed records appear under Review even if their stored status
   once said completed.
5. Click a task row to open its receipt. No new Gemini plan or payment is requested
   by reopening it. The underlying independent verifier still reads/checks evidence.

The count such as “10 of 10 recent outcomes” describes that limited recent window,
not lifetime transaction totals. The approved-limit amount on a row is not always
the amount actually paid. There is no transaction deletion, manual ledger-edit,
freeze-account or dispute-refund button here.

## Local monitoring and earlier project components

### Local monitoring only

The current consumer layout does not expose a continuous-monitoring switch. The
cloud gateway deliberately does not enable this connector. Friday is **ready for
your request**, not silently reading the phone, mail, browser or bank in the background.

Developers can test the implemented bounded local sandbox inbox through
`http://localhost:8080/docs`, using their configured local tenant credentials:

1. Find the Friday inbox/watch/arrival endpoint by its path; **Try it out** exposes its fields.
2. `POST /v1/friday/watch` with `{"enabled":true}` enables the local sample worker.
3. `POST /v1/friday/arrivals/genuine-bill` delivers a controlled event.
4. `GET /v1/friday/inbox` shows processing and reminder state.
5. `POST /v1/friday/inbox/{event_id}/retry` requests a supported interpretation retry.
6. `POST /v1/friday/watch` with `{"enabled":false}` pauses the local feed.

Check the API schema and configuration first. These are development operations,
not real-message subscriptions or automatic real bank payments. Closing a local
page need not stop a running Docker worker; stopping Docker does.

### API docs

In Swagger, **Authorize** supplies configured tenant/API headers; do not share
credentials or put them in this guide. **Try it out** only prepares a request;
**Execute** sends it and can change data for a write endpoint. **Schemas** describe
the JSON shapes, not customer features. Liveness/readiness checks indicate service
health, not that every bill is legitimate or the cloud model answered successfully.
The private cloud API is not a public customer endpoint.

Current Friday endpoints cover scenarios, rules/mandate, messages, documents,
provider bills, bill-plan, handle, today/activity, runs, statements, storage and
local inbox/follow-through. Engineers should use the documented schemas rather
than editing raw money values or directly altering databases.

### Retained research and integration labs

The repository also retains earlier payment-intent/ledger/ProofOps and corporate
invoice experiments. Local `/payment-check` and `/operations`
routes are development/history surfaces, not the current consumer product or
features guaranteed on the protected cloud website. Their specifications and
commands live in the linked architecture/integration documents. The retained
cinematic control-room module is not a separate supported `/control-room` URL.
Bank of Anthos
uses artificial money; it does not grant access to real banks.

The resolution kernel and regression-testing components are engineering work;
the current website does not autonomously patch production code, correct a bank
ledger, issue a real refund or complete real biller disputes. Do not present an
archived lab as a current everyday consumer capability.

## Troubleshooting and limits

| What you see | Meaning and next step |
| --- | --- |
| Google access denied | Sign in with a Google user account. A managed school/company account may have restrictions. Do not remove IAP or share owner credentials. |
| Demo allowance reached | Wait for the burst or UTC-day reset; do not repeatedly retry a payment. Each visitor has an isolated allowance, with a shared project-wide action cap. |
| Local website unavailable | Start Docker Desktop, run the startup command, inspect `docker compose ps` and service logs. Building does not automatically open a browser. |
| No eligible unpaid bills | All available rows may be paid, above limits or deferred. Inspect evidence; optionally prepare a genuine fresh artificial test record. |
| Bill not found / not verified | Your uploaded/message claim lacks a matching enrolled provider record. Extraction can still appear in Saved inputs. |
| Pending/loading/unknown outcome | Wait for the returned status, then check Activity. Refreshing a receipt is different from executing another task. |
| AI unavailable or invalid proposal | No successful live reasoning is claimed. Local rules comparison is an explicit development option, not silent fake Gemini output. |
| Signature/journal conflict | Do not override it. An engineer must reconcile authoritative evidence; UI colour cannot solve it. |
| Match recorded payment unavailable in cloud | That connector is local-only. Not evidence that your payment was reversed or failed. |
| File rejected | Use a supported document type within 8 MB; statement CSV has its own 1 MB/5,000-row limit. |
| CSV error | Check required headers, dates, rupee values and one debit/credit per row. No partial totals should be trusted. |
| Sound still quiet | Open the gear and enable sound; interact with a button; check browser/system output. No autoplay or always-on voice is promised. |
| Orb does not move | Check Motion and operating-system reduced-motion settings. Financial checks still operate. |
| Different balance/counts from screenshots | Test data persists and changes with use. Trust current records, not sample screenshots. |

Friday does not provide personalized stock picks or guaranteed returns, buy/sell
investments, read every native mobile app, recover funds, verify every UPI owner's
identity, fix the payment network, or guarantee zero fraud. Native Gemini Live
voice, SMS/email connectors, continuous cloud monitoring and independent real
bank/biller connections are not enabled. It is not a certified production banking
service. The useful demonstrated scope is **understand → match evidence → enforce
permission → handle an allowed artificial task → verify and reuse its outcome**.

## A complete practice checklist

- [ ] Open the help dialog and explain the artificial-money boundary.
- [ ] Inspect My rules; understand reserve, ceiling, increase threshold and automatic permission.
- [ ] Switch Daylight/Midnight/device theme, enable/mute sound, test motion and Escape.
- [ ] Review a saved bill without executing; inspect plan evidence and refresh.
- [ ] Prepare a fresh provider bill and matching message; deliberately handle it.
- [ ] Reopen/re-submit the completed bill and verify no repeat financial effect.
- [ ] Change only the message recipient and verify a no-payment result.
- [ ] Try a paid notice or unknown provider and inspect Saved inputs.
- [ ] Try a synthetic image/PDF; distinguish extracted claims from provider evidence.
- [ ] Analyze the supplied CSV, verify exact totals and repeated-row caveat, then clear.
- [ ] Explore the wallet and its coverage/limits; understand cloud follow-through is unavailable.
- [ ] Try the five controlled Safety Lab scenarios and inspect actual model provenance.
- [ ] Filter/search Activity; read a held, verified or legacy receipt without rerunning it.
- [ ] Expand technical evidence and identify signature, rules, program, journal and outcome roles.

For implementation, tests and deployment details, continue with [README](README.md),
[Start Here](START_HERE.md), [SPEC](SPEC.md) and the [readiness report](docs/submission/READINESS_1012.md).
The same project history now lives in [the Financial Friday GitHub repository](https://github.com/Santxsh27/financial-friday).

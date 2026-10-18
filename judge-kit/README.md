# Try Financial Friday in 5–10 minutes

**[Open the website](https://financial-friday-web-171681243260.asia-south1.run.app/#home)** · **[Illustrated walkthrough and downloads](https://financial-friday-web-171681243260.asia-south1.run.app/assets/friday-judge-guide.html)**

Sign in with Google. The top-right **My account** menu identifies the current
workspace. No bank, Gmail or Drive access is requested. A returning browser can
reuse its Google session. This source repository is public; the app still requires
Google sign-in. Managed Google accounts can have administrator restrictions.

## 1 · Understand six months of artificial activity

1. Open [01-HDFC-Illustration-6-Months.csv](statements/01-HDFC-Illustration-6-Months.csv), then **Raw → Download**. Or download it in the hosted walkthrough above.
2. In Friday choose **Home → Add a statement**. Select the file and a nickname such as `Artificial HDFC`. Keep **Bank account** selected.
3. Confirm processing → **Read my statement**. Review the **42 transactions**, dates and totals. This preview is not saved.
4. Confirm the reviewed rows → **Save & see my spending**. Explore category charts and **All entries → Back**.
5. **Ask Friday → Statements ready · tap to share**, permit statement totals, then ask: `Show my spending visually and explain one useful next step.`
6. To test a different format, **Statements → Start a new review**. This excludes, rather than deletes, earlier imports. Do not import all five files as different accounts.

| Source control | Expected value in EACH CSV |
| --- | ---: |
| Period | April–September 2026 |
| Transactions (opening row excluded) | 42 |
| Total incoming / outgoing | ₹3,00,000.00 / ₹1,64,694.00 |
| Net flow | ₹1,35,306.00 |
| Printed opening / last row balance | ₹40,000.00 / ₹1,75,306.00 |

The same invented activity is rendered five ways. HDFC/Kotak names identify
illustrative heading families, **not current bank-certified exports**. ICICI is a
synthetic candidate layout, not an independently verified real export. The last
two files are generic delimiter tests. Every amount and description is invented;
there are no customer/account details. See [the machine-readable manifest](manifest.json).

**Unknown is expected:** source closing/count/page controls are not supplied.
Some layouts also lack explicit balance-direction evidence. Friday must not
invent it. Arithmetic agreement does not establish bank authenticity or fraud.

## 2 · Make a visual goal, without filling a long form

Open **Goals**, paste this ARTIFICIAL example, and Send:

> I want a travel savings fund of INR 120000 in 12 months. Monthly income INR 50000, living costs excluding debt INR 30000, monthly debt payments INR 0, liquid savings INR 70000, protected buffer INR 50000.

Choose **Continue with Gemini**. Expect a starting goal pot of **₹20,000** and
a monthly step of **₹8,333.34**, an allocation ring and dated checkpoints.
Open **Pressure tests**: a missed contribution leaves **₹1,11,666.74** at the
illustrated endpoint. These are transparent scenarios, not forecasts.

Try income **₹35,000** with the other inputs unchanged. A budget gap appears.
**Preview this option** on a smaller-target or longer-time card recalculates the
visual proposal without retyping the budget. It does not save or move money.

**Save my roadmap → Confirm & save** stores one private priority. Reload to
restore it. **I saved some money → 1000 → Review update → confirm** records an
additional self-reported ₹1,000. **My savings updates → Undo** corrects it.
Do not report money that was not set aside. Nothing connects to a bank.

## 3 · Hear and question Friday

- **Read last reply → Enable voice & read** explicitly enables Google speech.
  Long replies get a labelled short preview; the full answer stays on screen.
- Subsequent replies are queued, not silently discarded. **Stop audio** cancels
  playing, queued and still-loading playback. It cannot undo a provider request
  already transmitted. Replay uses the last clip in this page when available.
- If the browser blocks autoplay, use **Play** in the visible audio player.
- **Talk to Friday → Record & send to Google** records at most 25 seconds after
  browser microphone permission. **Stop & transcribe**, review the words, then
  Send. **Type instead** works without microphone access. Do not dictate secrets.
- **New chat** resets speech permission and the page-only audio cache. Voice
  needs the Vertex-enabled hosted service and is not always-on listening.

For current public information, choose **Current info**. Review a non-private
question, confirm Google Search processing, then **Search & show here**. Inspect
source links and quote dates. Saved statements/goals/history are not sent to Search.

## Limits and recovery

INR only. CSV ≤1 MB/500 rows; PDF ≤4 MB/six pages/200 rows. Unsupported, ambiguous,
encrypted or incomplete inputs can fail safely. Real bank layout coverage is not
universal; test with these artificial files first. Preview and compare a redacted,
unlocked real statement before any save. Never upload PINs, OTPs or passwords.

Trial quotas can return 429: wait rather than repeatedly clicking. A save conflict
requires reloading Statements, not changing/re-uploading the source. **New chat**
clears conversation only; **Start a new review** changes source selection. Privacy
deletion is separate and should only be used deliberately.

This prototype cannot make payments, fetch live bank balances, establish that an
unusual transaction is fraud, guarantee returns, or give personalised securities
buy/sell instructions. Narration and Search results are not independently verified
financial advice. [Current release evidence](../docs/CURRENT_RELEASE.json).

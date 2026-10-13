# Financial Friday — Start Here

Updated 13 October 2026. New teammates: read
[TEAMMATE_BRIEFING.md](TEAMMATE_BRIEFING.md) too.

## What this application does

Friday helps you understand financial information, compare documents and prepare
a useful next step. A separate artificial-money system demonstrates how AI plans
can execute under independent rules. The site and Gemini are live; real banks,
wallets, utility accounts, Gmail and SMS are not connected.

## First tour: no payment required

1. Open [the live site](https://financial-friday-web-171681243260.asia-south1.run.app/#home)
   and sign in with Google. A new visitor starts with a private workspace, not the
   owner's records or a real account.
2. Choose **Understand a charge** on Overview. It prepares a question only.
   Click **Ask Friday** to send it to Gemini. Expect guidance and an unsent draft,
   not a submitted complaint or refund. Never enter banking secrets.
3. Choose **Try a guided example → 1. Load bill**. Review the artificial text and
   click **Review this financial input**. Expect a saved bill claim.
4. Return to Overview, load/review the matching receipt, then the changed-recipient
   receipt. Expect matching claims followed by conflicting evidence, not bank
   confirmation or a guaranteed fraud verdict. Results come from actual review calls.
5. Open **Financial inbox**. Expand evidence and the prepared verification message.
   Reading it does not send anything. These checks never submit a payment.
6. **Check a bill / Documents** accepts your own redacted image or PDF. Missing
   identifiers, unclear currency or poor extraction can require more review.
7. Moon/sun, sound and motion controls change appearance only, never permission.

An empty inbox is normal. Questions and the guide work without a bank. Example
buttons load editable text only; extracted claims are saved when you explicitly
review them. No fake personal activity is inserted to fill the page.

## Separate artificial-payment demonstration

Bills, My rules, Activity and the developer examples use Friday's own artificial
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

Chat has no task-execution tools. Cloud follow-through is unavailable; real
providers and native voice are future work. Another human Google-login test,
broader evaluation and final submission artifacts still need attention. Current
status is in [README.md](README.md); engineering boundaries are in [SPEC.md](SPEC.md).

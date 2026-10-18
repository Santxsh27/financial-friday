# Financial Friday start here

Friday helps with a saved purchase/savings/reserve roadmap, explicit public-source
research and optional INR statement understanding. Try Home → Goals;
[the artificial goal test](jugges/TRY-GOALS.txt) gives exact inputs/results.
Google sign-in identifies your workspace;
it does not connect your bank. Check [CURRENT_RELEASE](docs/CURRENT_RELEASE.json)
to distinguish local preview changes from the hosted release.

## The main journey

For a guided artificial-data trial, use **Home → Try a sample · quick walkthrough**.
The guide and bank-labelled files are served by Friday; no repository access is needed.

1. **Home → Add a statement.** Choose a PDF or CSV and a useful account nickname,
   such as `ICICI salary`, not an account number.
2. Confirm processing, then **Read my statement**. The preview is not saved.
3. Compare the rows, totals and source checks with the original. Correct
   interpretation labels if needed; confirm and **Save & see my spending**.
4. **My money** shows charts and one review item at a time. Its source banner
   identifies the selected statements, dates and review version.
5. **Ask Friday → Choose what I can use** controls optional Gemini context.
   Results stay in chat until you choose to open them.
6. **Listen** opens the optional spoken review. Confirm sharing its totals with
   Google, generate it, then Play. This is not a microphone/voice-command feature.

## Start fresh without losing history

**Statements → Start a new review → Start new review.** Earlier imports stay
saved but leave the current charts and statement-based AI context. To reuse
them, tick the desired statements and choose **Apply & see my money**.
This selection is shared across your Friday tabs.

**New chat** clears only the page conversation. **Back** returns through your
journey. Privacy cleanup deletes records; it is not the fresh-review button.

## One working folder on this Mac

Use **Desktop/CARAPACE**. Its historical folder name is retained so existing
Docker, VS Code and environment paths keep working.

| Location | Use |
| --- | --- |
| `src/`, `tests/`, `tools/` | Current app, automated tests and engineering tools |
| `jugges/` | Shareable artificial sample files and visitor walkthrough |
| `my-testing/` | Your separate sample kits and testing notes; not committed |
| `archive/` | Old submission snapshot and superseded guides; not committed |
| [USER_GUIDE.md](USER_GUIDE.md) | Current click-by-click guide and limits |
| [README.md](README.md) | Product, technology, setup and verified status |

## Run locally

Start Docker Desktop, then run from this folder:

```sh
docker compose up --build -d api anthos-demo
```

Open `http://localhost:8090/`. The historical `anthos-demo` service name is the
web gateway, not a connected Bank of Anthos. `http://localhost:8080/docs` is
developer API documentation, not the consumer website.

Limits: PDF 4 MB, 6 pages/200 rows; CSV 1 MB/500 rows; workspace 10 imports and
2,000 rows, including excluded sources. INR only. Supported bank-export headings
are recognised automatically; real ICICI compatibility still needs authorised,
redacted samples. No universal bank support, money movement or fraud verdict.

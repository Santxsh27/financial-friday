# Financial Friday — readiness pass, October 12

## Scope and fixes

This pass preserves the selected Everyday design and bounded artificial-money
operator. It is not a new product pivot or permission to access real accounts.

- Header: the final generated Vaultkeepers navy/peach team mark, packaged locally.
  The original square artwork is retained; CSS frames the mark without changing it.
- The seven cloud ₹3,001 test records exceed the saved ₹3,000 automatic limit.
  They now say **sandbox records above your limit**, with specific reasons;
  they are not described as failed payments. The records and rules are preserved.
- Activity derives green/red/amber badges from independent assurance replay, not
  stored completion flags. Legacy unsealed records and conflicting journals cannot
  acquire certified green completion merely by reopening them.
- The home activity icon follows that same assurance state. Historical receipt
  metrics now say planning calls **for this run** and **recorded sandbox payment**,
  not new payments made by opening the page. Legacy receipts finish loading and
  explicitly mark historical stages as uncertified rather than leaving them pending.
- Document consent explains Gemini cloud processing, raw-file disposal, saved
  extracted facts, and automatic artificial payment under existing permission.
- Manual approval shares the single-task busy boundary. Unknown outcomes say to
  check Activity before retrying. No automatic financial retry was added.
- Statement clear is disabled during processing to avoid a stale-result race.
- Removed redundant requests for detached home panels; fixed route accessibility
  labels, plain-language stop reasons and duplicated bill due-date text.

## Verification

Native command: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q`.
Result: **314 ran, 313 passed, one optional integration skipped**.
Tooling: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tools -p 'test_*.py' -q`.
Result: **11 passed**. The first native invocation omitted PYTHONPATH and failed
imports; the corrected source-layout invocation above passed. No application
dependency or payment permission was changed to obtain the result.

New regressions cover grouped limit/reserve/evidence warnings, activity assurance,
legacy receipt fail-closed rendering, extracted-document disclosure, single-task
approval, statement clearing, missing/corrupted journal evidence and packaged logo.

Browser baseline: Overview, bill review, document consent, Activity filtering,
saved held result, rules, and consented synthetic statement processing inspected.
Four statement rows yield ₹10,000 in, ₹3,200.50 out and ₹6,799.50 net flow;
matching rows stay included and are not called proven fraud. The earlier live
Vertex paid-notice check made no payment request and left balance unchanged.

Docker command:
`docker compose --profile test run --rm --no-deps --build -e CARAPACE_AI_PROVIDER=local -e CARAPACE_TEST_ANTHOS_BRIDGE_ENABLED=false tests discover -s tests -q`.
Result: **314 ran, 300 passed, 14 skipped**. Container skips include the Node-based
presentation checks; the native suite executes those. Expected simulated 503/504
test messages are failure-path fixtures, not observed live provider outages.

## Published release and post-fix checks

Both revisions passed zero-traffic candidate checks before promotion. On October 12:

- API: `financial-friday-api-ready1012`, 100% traffic.
- Web: `financial-friday-web-ready1012final`, 100% traffic.
- App: https://financial-friday-web-171681243260.asia-south1.run.app/#home
- Version remains `0.17.0`; this is a patch identified by the revisions and commits.
- Full API build: `ccdc65a8-fa81-4ad8-9ed7-3b4c4093ae6c`, source commit `29a3032`,
  image digest `sha256:76730623641ad89904b08b5add9c4f40c0f035b7e51a6d7662514e6025669321`.
- Final web build: `42e0a9bf-09c3-4af3-bd19-196878675dd1`, source commit `93ba496`,
  digest `sha256:81dfe89222dfe1d50acf93243dc20fe0f1d46691389053a478cddc0b78a43046`.
  The web layer pins the verified API base image. Cloud build contexts were clean
  Git archives; unrelated working-tree changes were not included.

Authenticated candidate checks verified transactional Firestore, 13 current bill
records, reserve-aware read-only planning, rejected unconfirmed execution, disabled
unimplemented cloud follow-through, independent activity assurance and rejected
anonymous access. A candidate **live Vertex** paid-notice interpretation correctly
returned `NOT_A_PAYMENT_REQUEST`; no case or payment was created. After promotion,
the canonical API check passed again without an additional AI call. Across these
checks, the sandbox balance was unchanged and **payment requests were zero**.
Existing saved permissions, IAP enrollment and private API access were preserved.

Post-release browser checks inspected Overview, reviewed bill amount/recipient,
Activity, a signed held receipt, and help/Escape focus behaviour. The held receipt
reopened with three historical planning calls and no new payment; no pending stages
were falsely promoted to successful execution. The local legacy receipt displays
explicit uncertified stages and a finished read-only status. Document disclosures,
rules and statement behaviour were also inspected in the audit. A 390px mobile
home had no document overflow or broken images; the navigation scrolls internally.
The final live desktop home had no horizontal overflow, broken images or stuck
loading indicator. Captured console warnings/errors were empty on the inspected
live release. Local API, UI and artificial Anthos ledger containers remain healthy.

Screenshots (artificial data only):

- [Published home and team mark](screenshots/readiness-1012-home.png)
- [Published held result](screenshots/readiness-1012-held.png)

This is evidence for the exercised paths, not an exhaustive guarantee of every
possible input, browser, network failure or security threat.

## Submission blockers — do not call these finished

1. **Judge access:** Cloud Run web remains owner-only IAP and the API remains
   private. A URL alone does not give judges access. Arrange explicitly approved
   judge enrollment or the organizer-approved demonstration path before submitting.
2. Confirm the actual Hack2skill dashboard deadline, roster and eligibility.
   Historical public event dates are not a substitute for dashboard confirmation.
3. Finish the video, deck/document and required submission form fields.
4. External authenticated bank/biller connectors, continuous cloud monitoring,
   refunds/correction execution and production compliance are not implemented.
   The enrolled artificial provider is operated by this project, not a bank.

This is a testable hackathon system, not a claim of universal financial protection,
zero bugs, guaranteed winning or an independently certified production bank service.

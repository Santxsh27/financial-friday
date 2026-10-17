# Developing Financial Friday

Read [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md), [SPEC.md](SPEC.md) and
[docs/API_MAP.md](docs/API_MAP.md) first. Work in this repository; no new product
repo, cloud project, bank stack or database trial is required.

## First run without credentials

Start Docker Desktop, clone the repository, then:

```bash
git clone https://github.com/Santxsh27/financial-friday.git
cd financial-friday
docker compose up -d --build api anthos-demo
docker compose logs --tail=30 api anthos-demo
```

Open <http://localhost:8090/#home> and <http://localhost:8080/docs>.
The website's historical service name does not require Anthos. Local ports bind
to loopback, not a public bank service. Development API credentials in Compose
are published dummy values and are explicitly forbidden for production use.

Offline mode can exercise supported CSV imports, exact charts and tests. Chat,
PDF extraction and speech need live services and fail explicitly when unavailable.
Start your live-AI tour on the hosted
site if you do not have development credentials.

## Optional local live Gemini

Copy `.env.example` to an ignored `.env` yourself. Select one provider:

- `CARAPACE_AI_PROVIDER=gemini`, with your own `GOOGLE_API_KEY`, for Developer API.
- `CARAPACE_AI_PROVIDER=vertex`, with an authorised project and credentials, for
  Vertex. Cloud deployment uses a service identity, not downloaded account keys.
- `local` is the labelled deterministic baseline, not a simulated live answer.

Use only synthetic/redacted test inputs. Check your provider quota and billing;
keys are not automatically supplied by cloning. Native Application Default
Credentials are not automatically available inside Docker: use an explicitly
approved development setup, not a service-account JSON committed or baked into
an image. Hosted Firestore/signing configuration is separate from local SQLite.
Rebuild after changing Compose environment values. Never send secrets in chat,
issues, screenshots, logs, branches or pull requests.

## Native development tests

Python 3.11+ is supported; the image uses 3.12. Node.js enables optional JS checks.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q
PYTHONPATH=src .venv/bin/python -m unittest discover -s tools -p 'test_*.py' -q
```

The suite does not need real financial credentials or live AI by default. Live
cloud verification tools require explicit project access and may consume credits;
do not run them against someone's personal records or repeatedly run write tools
without understanding their scope.

## Change checklist

1. Inspect `git status`. Preserve changes you did not create.
2. Create a feature branch for your agreed task; use a PR and focused commits.
3. Keep chat/review separate from execution. Loading examples/opening pages must
   not submit model requests or grant financial authority.
4. Add tests for failure, wrong tenant, replay and changed evidence—not only success.
5. Update the current spec/briefing when behaviour changes. Label future work.
6. Run native tests and tooling tests. Run Docker tests for dependency/storage changes.
7. Verify the actual UI -> API -> stored result when changing a user workflow.
8. Report skipped tests and known issues; never turn an unavailable result green.

Normal Actions run core, container and standalone-web checks. The historical
Anthos fixture is available through **Run workflow → run_legacy_anthos** only;
it is not needed for Friday or a typical contributor. All financial data it uses
is artificial. CI's volume cleanup applies to a disposable runner, not your laptop.

## Deployment and data safety

GitHub push is not an automatic Cloud Run deployment. Build from an reviewed clean
commit, retain the existing private API/IAP topology, stage a revision, perform
bounded synthetic checks, and only then promote traffic. Do not change IAM,
canonical origins, signing keys, quotas or production billing without agreement.
No new cloud permission is required just to read this repository or use the demo.

Stop local services with `docker compose stop`. Keep persistent volumes and signing
keys if you want existing receipts to remain verifiable. Do not reset balances,
delete evidence, weaken limits or disable safety checks to make a demo succeed.

## Troubleshooting

| Symptom | First check |
| --- | --- |
| Cannot reach localhost | Docker running? `docker compose ps`; readiness and service logs. |
| SQLite cannot open | `/data` named-volume permissions/data-init; do not delete the DB. |
| Live chat/PDF reading unavailable | Provider selection, quota, authorised credentials; offline mode cannot OCR/chat. |
| New account has no statements | Expected; Add a statement or explicitly try the artificial example. |
| Statement format rejected | Supported headings/dates, clear debit/credit roles and source warnings; never alter amounts to pass. |
| Cloud returns 403/401 | Google login, verified canonical origin and private API invocation; do not loosen auth. |
| 429/demo limit reached | Admission quota, not a broken payment; avoid repeated writes and use saved evidence. |
| Source mismatch or save conflict | Reload Statements, inspect selected sources/revision and printed facts; do not bypass the check. |
| Cloud follow-through unavailable | Connector is not implemented; do not relabel it as a successful correction. |

For improvements, propose the affected workflow, expected user benefit, trust
boundary, tests and deadline impact. Keep one coherent customer journey rather
than reintroducing every earlier project idea at once.

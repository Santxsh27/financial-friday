# Unified Friday assistant · 0.37.0

Goal input, missing questions, exact roadmap and follow-up coaching now share one
conversation. Reading a goal prepares the visual automatically; saving a priority
or reporting actual savings remains explicit and revision/generation checked.
Statement averages are offered automatically as optional local estimates, rechecked
before acceptance. Current liquid savings are never inferred. Exact display retains
paise. Saved and unsaved proposed paths can both ground read-only Gemini answers.

Topic shortcuts: Ask anything, Plan a goal, My spending, Current info. An explicit
public-query review precedes Google Search, with no saved records/history attached.
The response preserves provider citations and unmodified Search Suggestions in a
scriptless, opaque-origin sandbox. No streaming quote feed or personal investment
recommendation is claimed.

## Voice boundaries

- Google Vertex Gemini transcribes a short clip; Gemini TTS narrates short displayed
  text. No new service accounts, APIs, IAM grants or quotas are required.
- Browser records at most 25 seconds, with explicit consent and mic permission;
  1 MB decoded input bound. WAV duration is additionally validated server-side.
  Compressed-container duration is not independently certified by this server.
- A transcript is reviewed in the composer before sending; never auto-executed.
- Narration accepts explicit caller-supplied text, not a signed or independently
  verified financial answer. Output is bounded mono PCM/WAV, at most 30 seconds.
- No raw recordings or chat transcripts are saved by Friday. Google cloud
  processing is disclosed. Recognisable secret redaction is best effort, not a
  guarantee; raw audio itself must contain no secrets.
- Audio operations load no statement/goal context. Both API endpoints are private,
  tenant-authenticated, no-store, quota-controlled and cannot invoke payment tools.
- Conversation changes, revoked voice consent, navigation while recording and
  privacy cleanup stop/discard applicable audio. Generation checks reject a voice
  response spanning server-side cleanup. Typing remains available on failure.
- This is optional push-to-talk + generated speech, not always-on Siri parity,
  Gemini Live, bank monitoring, model weight training or production certification.

## Audit and verification

Before-change evidence was captured and inspected from the local synthetic workspace:
`/private/tmp/friday-assistant-before.jpg` and
`/private/tmp/friday-assistant-chat-before.jpg` (temporary machine-local artifacts).

1. Enter Goals: needed improvement — large intro and separate result/entry hand-off.
2. Talk to Friday: needed improvement — another page and missing-context entry.
3. Voice entry: needed improvement — Listen meant statement narration only.

The scoped repair keeps the approved Soft Studio visual system and existing
mascot. It is not a complete accessibility certification or a new visual direction.

New tests cover audio format/size/consent, read-only authority, no private retrieval,
provider failures, cleanup races, unsaved-goal grounding and amount validation,
JavaScript syntax and admission boundaries. A live verifier uses a fresh artificial
visitor and Google-generated test audio, never a human microphone or owner records.

## Completed release checks · 18 October 2026

The main link now serves API `financial-friday-api-assistant0370` and web
`financial-friday-web-assistant0370ready`, both at 100% traffic. API source:
`5c39766afbee1e0739d5adda7544ca1521493f2a`. Web source:
`a58142959c40c70dbf1c323232d1b9c90c0073c7` (adds the obsolete-preview safeguard
and corrected walkthrough; backend code is unchanged between these commits).
Exact immutable digests/build identities are in [CURRENT_RELEASE.json](CURRENT_RELEASE.json).
Matching GitHub CI runs `39105400492` and `39105734741` passed.

- Final native source: 838 tests / 837 passed / 1 skipped.
- Docker: 838 / 804 / 34. Container skips are retained environmental/optional checks;
  the JavaScript syntax tests run in the native/CI Node environment.
- Offline release/evaluation tooling: 68 passed. New assistant-specific tests: 13.
- Six real Google calls in one fresh artificial visitor passed: short speech,
  its transcription, general chat, attributed public Search, goal intake and
  exact unsaved-plan coaching. No goal was persisted; the test workspace was cleaned.
- This cloud test does not record the owner's microphone or use owner records.
  It checks transcription of generated speech, not real-world speech accuracy.
- The canonical signed-in browser rendered a public question through the web
  gateway into inline cards, provider citations and Search Suggestions. All
  financial-context choices remained off. Source attribution is not independent
  fact checking; an official source was not established by this particular answer.
- Anonymous API remains 403; anonymous web redirects to Google sign-in (302).
  IAM, OAuth scopes, quotas and the pinned historical recovery target are unchanged.

### Repaired flow health

1. **Start a goal — working.** A custom artificial laptop goal generated a chart
   automatically inside the same conversation after interpretation consent.
2. **Fill a gap — working.** A second goal omitted its target amount. Friday asked
   in chat; answering `90000` automatically produced the roadmap without another
   form or Calculate button. Previous reviewed budget assumptions were disclosed.
3. **Ask about the result — working.** A real Gemini reply used the unsaved plan's
   exact monthly contribution without saving or editing it.
4. **Current information — working within limits.** Query review and separate
   Search consent precede the inline result; attribution and suggestions remain
   visible. No promise of market-data accuracy, official provenance or freshness.
5. **Voice entry — discoverable; microphone check remains manual.** Dialog opens
   with microphone off and Type instead available. Google audio endpoints passed
   the synthetic round-trip. Actual browser mic capture was not exercised.
6. **Responsive layout — checked.** At 390px, content width was 390px. At 1440px,
   one Goals assistant and zero duplicate visible docks were found. Temporary
   viewport overrides were reset. These are targeted checks, not all-browser QA.

Temporary, inspected local screenshots:
`/private/tmp/friday-assistant-0370-mobile.jpg` and
`/private/tmp/friday-assistant-0370-wide.jpg`. The original default-size live
conversation remains available in the Codex preview. Console-error check: zero
in the tested local flow. No full accessibility certification is implied.

Remaining human submission gates: try microphone in the target browser, have a
different Google account complete the walkthrough, grant source access by the
organisers' approved method (repository is private), confirm dashboard eligibility
and cutoff, and submit the video/deck/form. The application is a bounded hackathon
prototype, not a production-audited financial adviser or bank integration.

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

Release verification is in progress; exact completed checks and deployed image
identities will be recorded in CURRENT_RELEASE.json before declaring this live.

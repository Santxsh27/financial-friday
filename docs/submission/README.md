# Financial Friday — Submission Pack

Use this folder for the final demo script, evaluation results, slides and submission links. Current build status is in [Start Here](../../START_HERE.md), [README](../../README.md) and [SPEC](../../SPEC.md).

**Current handover, 13 October:** read [the teammate briefing](../../TEAMMATE_BRIEFING.md)
and [current release evidence](../FRIDAY_CHAT_AND_BANK.md) first. The default
customer journey is live chat and read-only claim review; artificial execution is
separate. Earlier scripts/materials need review before being used as final artifacts.

Implemented evidence: [proposal safety evaluation](SAFETY_EVALUATION.md),
[security boundaries](SECURITY_BOUNDARIES.md), and [live demo script](DEMO_SCRIPT.md).
The generated safety corpus is not a live model benchmark.
Historical readiness verification: [readiness pass](READINESS_1012.md).
The [October 9 handoff](FINAL_HANDOFF_1009.md) is historical evidence.
Live multimodal evidence: [document verification](../FRIDAY_DOCUMENT_VERIFICATION_1008.md),
including the initial failure, fail-closed fix and two successful safety retests.

## Demo story

Start with a useful live question/draft, then review an unfamiliar bill/receipt
and show an evidence discrepancy. Demonstrate the **separate** execution layer:
save a sandbox instruction → supply a fresh test-provider bill → Gemini interprets
it → independent checks enforce permission → one artificial payment → signed
outcome/replay. Do not imply chat or an uploaded receipt paid through a real bank.

Official [requirements](https://aibuildercup.com/themes.html) specify a working
Google-AI/cloud prototype, proposal deck/PDF and public short demo-video link.
The [public timeline](https://aibuildercup.com/) checked 13 October lists team
formation by 14 October and submission by 18 October 2026. Verify the dashboard's
exact cutoff, eligibility and fields. This update does not submit the entry or
create the video/deck.

## Completion checklist

- Latest Google Cloud URL and verified version.
- Live Google AI calls with visible model provenance.
- New input supplied during the demo.
- Correct task completed and unsafe task held.
- Measured completion, false holds, unsafe actions, latency and cost.
- Architecture, threat model, limits and provider integration roadmap.
- Repository, video and organizer-required deck/document.
- Confirmed dashboard deadline, eligibility and team details.

This pack is complete only when these artifacts and checked links exist.

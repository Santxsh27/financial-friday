# Financial Friday 0.20 — a personal buddy, not a bank impersonator

The companion overview counts the user's uploaded claims separately from the
default artificial provider examples. It makes zero AI calls on page load and
cannot authorise a payment. An animated companion reacts to real chat/task/review
requests; its evidence panel displays returned provider/model/call metadata, not
a made-up thinking transcript or fabricated completed action.

## Personalisation boundaries

Users explicitly save an optional nickname, explanation style and example focus.
These persist separately from financial rules in tenant-scoped SQLite/Firestore.
Unknown settings, authority fields, invalid types and secret-like nicknames are
rejected. The nickname never goes to Gemini. Style/focus reach the model only
when both the saved preference and the individual request opt in. Saved financial
records still require their separate context consent. Changing preferences clears
the current browser conversation; it does not change a mandate or erase receipts.

The personal home list includes saved-document obligations only. Provider-only
demo bills remain available in an explicitly labelled optional section of the
financial inbox; they are not presented as a new visitor's unpaid household bills.

The briefing button prepares a request after the user opts into workspace sharing;
Ask Friday sends it. It never quietly grants sharing or execution permission.
The focus setting changes explanations/examples, not warnings, payment eligibility
or investment recommendations. Raw PDFs are not retained as a document vault.

## Recovery rollout

The user specifically approved the named keyless `financial-friday-recovery`
identity and low-rate `friday-recovery` queue. The identity can invoke only the
existing private API; the runtime can enqueue on that queue and act as that identity.
Google's existing Tasks service agent can act as that identity for OIDC dispatch.
No private key, real bank permission or database/document access was added to it.
The queue permits 0.1 dispatch/sec, one concurrent dispatch and at most three
attempts; the app admits at most 50 new recovery jobs per UTC day.

Activation is recorded only after actual queued delivery is tested. The live
probe simulates a lost response after one artificial debit, waits for the actual
Google Tasks callback, verifies the existing journal and confirms that replay
does not debit again. It never manually invokes reconciliation as proof of a
background worker. This is not an actual process crash or real-bank settlement.

The rollout passed: live Vertex accepted the separately opted-in style, Firestore
persisted preferences, the overview made no model call and financial rules stayed
unchanged. The real Tasks callback returned HTTP 200 and independently verified
the existing journal after one INR 100 artificial debit. Repeated confirmation
was read-only. An earlier connection drop occurred before any payment confirmation;
that probe was not blindly retried against the same operation.

Native 449 ran (448 passed, one skip); Docker 449 ran (430 passed, nineteen
optional skips); fifteen tooling checks passed. Different API/web source identities
are recorded explicitly: the web follow-up fixes a local gateway annotation and
uses the immutable 0.20 API dependency image. Both normal cloud services use the
tested buddy0200 API and buddy0200personal web revisions. Updating the recovery worker target is an explicit
future release step, not an automatic redirect to arbitrary model-supplied URLs.

## Remaining work

Independent held-out labels and customer usability studies cannot be invented by
the application. Consented external intake, authenticated biller connections,
external settlement/refunds, native voice and personalised securities advice are
not supported. Resolve these through separately authorised pilots, not UI badges.
Source/revisions, final tests and actual rollout status: `CURRENT_RELEASE.json`.

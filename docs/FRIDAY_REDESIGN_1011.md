# Friday redesign — evidence before another styling pass

## Current review

The October 11 local browser review covered Home, Activity, the read-only bill
plan, and the plan-to-bill preparation handoff. No payment was submitted.

The homepage's large marketing headline takes precedence over current tasks.
The bill plan nests multiple surfaces, and selecting a bill leads to another
text-entry screen. More colour alone does not fix this hierarchy. The next
design should feel like an assistant workspace: one clear next action,
short outcome-first wording, and progressive disclosure for technical evidence.

Three independently generated visual directions will be presented for selection
before another layout is implemented. They are design proposals, not screenshots
of shipped features. Existing financial handlers and trust boundaries stay intact.

## Implemented journal fix (not deployed yet)

Firestore's default list ordering is document ID, not time. Random run and event
IDs therefore made a limited activity list appear stale. Journal queries now
order by `result.started_at` for runs and `created_at` for incoming signals,
descending, **before** applying the limit. Other collections keep their existing
queries and do not require a timestamp. Tenant scope and bounded reads remain.

The local daily briefing also sorts runs by their recorded start time, with row
ID as a tie-breaker, so importing an older record does not displace newer work.
This change neither reruns tasks nor grants payment authority.

Existing journal writers provide these timestamps. Firestore excludes a record
missing the ordered field: such a malformed/legacy record remains retrievable
by its ID, but is not fabricated as recent. No silent unbounded fallback is used.

Validation: 271 application tests ran, 270 passed and one optional test skipped;
11 tooling tests passed. Six new chronology tests cover ordering before limiting,
signal creation time, timestamp-free payment collections, missing timestamps,
tenant/limit validation and locally imported old runs. These are unit/contract
tests, not a claim of a new live Firestore deployment.

Reference: [Google's ordering and limit documentation](https://docs.cloud.google.com/firestore/native/docs/query-data/order-limit-data).

## Delivery gates

- Select and implement one coherent design across Home, task, outcome and Activity.
- Keep the artificial-money scope visible and distinguish local rules from live AI.
- Verify keyboard, mobile, reduced-motion, loading and held/unknown states.
- Deploy a clean tested commit; exclude unrelated local edits and secrets.
- Complete judge access, measured evaluation, submission PDF and demo video.

The current live release remains 0.15.2. This review is not a claim of guaranteed
selection, universal protection, real-money integration or submission completion.

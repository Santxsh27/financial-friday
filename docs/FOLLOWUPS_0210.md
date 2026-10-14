# Friday follow-up memory — v0.21.0

## Try it

1. Open **Documents**, review your own readable bill/request, then open the
   **Financial inbox**. File selection alone does not send it to Gemini.
2. On the saved obligation choose **Keep track of this**. The state persists
   across reloads. This is a private to-do, not permission to pay.
3. Use **Prepare verification** with selected-context consent to ask Gemini for
   an unsent, evidence-bound verification message. Contact a provider through a
   channel you independently know; Friday does not send that message.
4. Choose **I'm waiting for a reply** to record your own follow-up progress.
5. Review a new document or provider reply with the same exact supplier,
   reference and currency. The inbox shows **New evidence arrived**. Choose
   **Recheck evidence**; current financial conflicts remain visible.
6. **Close follow-up** closes only the to-do. It does not confirm settlement,
   clear warnings, or unlock payment. Further changed evidence resurfaces it.

Artificial provider examples do not get personal tracking controls. Incomplete
identity fields stay separate; Friday never guesses that similar amounts belong
to the same bill. Rechecking does not call Gemini or retry a payment.

## Engineering

- `POST /v1/friday/obligations/{obligation_id}/followup`: strict allowlisted action,
  expected revision and expected evidence version; authenticated tenant context.
- Identity follows the existing normalized supplier/reference/currency group,
  not the newest document's random ID. Old prepared tasks referencing retired
  identities must be refreshed; no migration turns an old task into permission.
- Financial projection is unchanged by bookkeeping. An item-level evidence
  fingerprint detects changed claims and provider outcomes. A changed unrelated
  obligation does not reopen this one.
- SQLite `BEGIN IMMEDIATE` and Firestore transactions enforce compare-and-set
  revisions. A privacy-generation barrier rejects saves during cleanup.
- Maximum 100 tracked obligations per workspace; no free-text secrets or bank
  data stored in tracking records. Explicit review cleanup clears all tracking,
  even expired-only cleanup; the confirmation says so. Payment journals remain.
- UI displays returned states, uses accessible status text, disables double
  clicks, and does not render an optimistic paid/green result.

## Limits

This is follow-through memory for records users provide. It is not an automated
inbox connector, complaint submission, refund, bank correction, scheduled alert,
or proof that a merchant is genuine. Gemini continues to handle extraction and
restricted preparation; exact code handles tracking and evidence changes.
Current deployed identities and test counts are in `CURRENT_RELEASE.json`.

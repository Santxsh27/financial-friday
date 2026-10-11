"""One reviewed bill -> grounded AI -> existing sandbox execution gates.

The preview digest binds what was displayed. It is NOT payment authority.
Tenant records, model fields and current financial permission are checked again.
"""
import json

from carapace_core.canonical import sha256_hex
from carapace_core.friday_live import IncomingFinancialSignal, TestProviderBill


def _bill(service, tenant, reference):
    if service.durable.mode == "FIRESTORE_TRANSACTIONAL":
        value = service.durable.get("provider_bills", tenant, reference)
    else:
        with service.connect() as db:
            row = db.execute("SELECT bill_json FROM friday_provider_bills WHERE tenant_id=? AND bill_reference=?",
                             (tenant, reference)).fetchone()
        value = json.loads(row[0]) if row else None
    if value is None:
        raise KeyError(reference)
    return TestProviderBill.model_validate(value)


def handle_reviewed_bill(service, tenant, reference, expected_digest):
    from .friday_workspace import financial_workspace
    from carapace_core.friday_bill_plan import plan_bills
    bill = _bill(service, tenant, reference)
    if sha256_hex(bill.model_dump()) != expected_digest:
        raise ValueError("Bill details changed. Refresh and review the current amount and recipient.")
    plan = plan_bills(financial_workspace(service, tenant))
    # Replays are allowed to reach the receipt-first executor, never pay again.
    allowed = plan["selected"] + plan["already_recorded"]
    if plan["state"] != "PLANNED" or not any(
            row["bill_reference"] == reference and row["provider_id"] == bill.provider_id for row in allowed):
        raise ValueError("This bill is not eligible under the current reserve, limit or evidence. No payment was submitted.")
    amount = f"{bill.amount_minor // 100}.{bill.amount_minor % 100:02d}"
    signal = IncomingFinancialSignal(source_type="BILL_TEXT",
        content_text=f"Please check this one-time bill {reference}\nAmount: INR {amount}\nPayee: {bill.payee_id}\nProvider: {bill.provider_name}",
        event_id="review-" + sha256_hex({"tenant": tenant, "bill": bill.model_dump()})[:32])
    facts, attempts = service._understand(service.planner.interpret_signal, signal.source_type, signal.content_text)
    # Gemini may not silently switch the customer-selected bill or invent a fee.
    if (facts.request_kind not in {"BILL", "PAYMENT_REQUEST"} or facts.bill_reference != reference
            or facts.amount_minor != bill.amount_minor or facts.claimed_payee_id != bill.payee_id
            or facts.currency != bill.currency or facts.recurring_requested or facts.suspicious_instructions):
        raise ValueError("AI interpretation did not exactly match the reviewed bill. No payment was submitted.")
    if _bill(service, tenant, reference) != bill:
        raise ValueError("Provider details changed during checking. Refresh before acting.")
    data = service._ingest_interpreted_signal(tenant, signal, facts, expected_bill_sha256=expected_digest, source_metadata={
        "reviewed_bill_sha256": expected_digest,
        "understanding": {"mode": service.planner.mode, "model": service.planner.model_name,
                          "attempts": attempts, "successful_model_calls": int(service.planner.mode != "LOCAL_RULES")}})
    if data.get("run_id"):
        run = service.get(tenant, data["run_id"])
        known_terminal = run["status"] in {"COMPLETED_SYNTHETIC", "ALREADY_COMPLETED", "RECONCILED_COMPLETED", "HELD"}
        recorded = any(row["bill_reference"] == reference for row in plan["already_recorded"])
        if known_terminal and (run["status"] == "HELD" or recorded):
            # Explicitly checking again is not merely opening saved evidence.
            # Known terminal outcomes pass through current gates and receipt-first
            # execution. A historical hold must not masquerade as a fresh result.
            # Nonterminal/uncertain runs are returned for review, never retried here.
            run = service.run(tenant, run["case_id"], enforce_single_payment_limit=True)
        data = {**data, "run_id": run["run_id"], "money_moved": run["outcome"].get("money_moved", False)}
        return {"signal": data, "run": run}
    if data["state"] != "READY" or data.get("reason"):
        return {"signal": data, "run": None}
    return service.run_live_signal(tenant, data["event_id"], enforce_single_payment_limit=True)

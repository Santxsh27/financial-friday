"""Server-selected, tenant-scoped conversation context; no arbitrary retrieval."""
from carapace_ai.friday_chat import answer_chat


def chat_context(service, review, bank, tenant: str) -> dict:
    board = review.board(tenant)
    evidence = []
    # Limit records, fields and text before model invocation. Do not send source
    # uploads, signatures, credentials or raw ledger account numbers.
    for item in board["cases"][:10]:
        evidence.append({"evidence_id": item["case_id"],
            "source": "USER_SUPPLIED_CLAIM", "supplier": (item.get("supplier") or "")[:160],
            "reference": (item.get("reference") or "")[:120],
            "state": item["state"], "checks": item["checks"],
            "currency": item["currency"], "amount_minor": item["amount_minor"],
            "due_date": item["due_date"], "next_action": item["next_action"][:400]})
    rules = service.mandate(tenant)
    bank_record = bank.snapshot(tenant)
    # Never expose bank rows to the model or invent a link to uploaded documents.
    bank_summary = {key: bank_record.get(key) for key in
                    ("status", "scope", "currency", "balance_minor", "reason", "as_of")}
    return {"evidence": evidence, "coverage": "At most 10 cases from the latest 50 review inputs, not a complete statement",
            "unconfirmed_bill_totals": board["unconfirmed_bill_totals"],
            "currency_scales": board["currency_scales"],
            "friday_sandbox": {"scope": "ARTIFICIAL_MONEY", "currency": "INR",
                "balance_minor": rules["sandbox_balance_minor"],
                "protected_balance_minor": rules["mandate"]["protected_balance_minor"]},
            "bank": bank_summary}


def reply_to_user(service, review, bank, tenant, request):
    context = chat_context(service, review, bank, tenant) if request.include_workspace else {}
    return answer_chat(service.planner, request, context)

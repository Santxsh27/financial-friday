"""Exact claim-to-provider constraints, independent of Gemini's risk judgment."""
from .friday_review import normalize


def related_claims(board, reference):
    # Exact invoice identity, deliberately conservative across suppliers.
    cases = sorted([case for case in board["cases"] if reference and
                   normalize(case.get("reference") or "") == normalize(reference)],
                   key=lambda case: case["case_id"])
    identities = {identity for case in cases for identity in case["document_ids"]}
    documents = sorted([{"review_id": document["review_id"], "analysis": document["analysis"]}
                        for document in board["documents"] if document["review_id"] in identities],
                       key=lambda document: document["review_id"])
    return {"cases": cases, "documents": documents}


def provider_claim_conflicts(related, bill):
    if not bill:
        return False
    for document in related["documents"]:
        analysis, facts = document["analysis"], document["analysis"]["facts"]
        quoted = {q["field"] for q in facts["quotes"]}
        if (analysis["amount_minor"] is not None and analysis["amount_minor"] != bill["amount_minor"]
                or facts["currency"] != bill["currency"]
                or ("payee" in quoted and facts["payee"] and normalize(facts["payee"]) != normalize(bill["payee_id"]))
                or facts["money_direction"] == "RECEIVE"):
            return True
    return False


def claim_gate_reasons(related, bill):
    reasons = []
    if any(case["state"] != "BILL_TO_VERIFY" or case.get("checks") for case in related["cases"]):
        reasons.append("RELATED_CLAIM_REQUIRES_REVIEW")
    if provider_claim_conflicts(related, bill):
        reasons.append("PROVIDER_CLAIM_CONFLICT")
    return reasons

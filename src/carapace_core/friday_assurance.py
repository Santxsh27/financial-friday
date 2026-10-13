"""Read-only replay of a signed sandbox run. Not proof of external settlement."""
from .canonical import sha256_hex
from .financial_friday import FinancialGoal, FinancialEvidence, FinancialProgram, verify_financial_program

TERMINAL = {"HELD", "COMPLETED_SYNTHETIC", "ALREADY_COMPLETED", "RECONCILED_COMPLETED"}


def seal_friday_run(tenant, result, signer):
    if result.get("status") not in TERMINAL:
        return
    body = {k: v for k, v in result.items() if k not in {"run_seal", "assurance"}}
    payload = {"domain": "FRIDAY_RUN_V1", "tenant_id": tenant,
               "run_id": result["run_id"], "result_digest": sha256_hex(body)}
    result["run_seal"] = {"payload": payload, "signature": signer.sign(payload), "key_id": signer.key_id}


def replay_friday_run(tenant, result, signer, journal_receipt):
    """Never trust stored `verification.passed`; recompute from the sealed snapshot."""
    report = {"state": "UNVERIFIED", "read_only": True, "money_moved": False,
              "checks": [], "scope": "Signed sandbox execution; not bank identity or external settlement."}

    def check(name, passed):
        report["checks"].append({"name": name, "passed": bool(passed)})
        return bool(passed)

    seal = result.get("run_seal")
    if not seal:
        report["state"] = "LEGACY_UNSEALED"
        return report
    try:
        body = {k: v for k, v in result.items() if k not in {"run_seal", "assurance"}}
        expected = {"domain": "FRIDAY_RUN_V1", "tenant_id": tenant,
                    "run_id": result["run_id"], "result_digest": sha256_hex(body)}
        if not check("Run signature and tenant binding", seal["payload"] == expected and
                     signer.verify_for_key(expected,seal["signature"],seal["key_id"])):
            report["state"] = "CONFLICT"
            return report
        goal = FinancialGoal.model_validate(result["goal"])
        evidence = FinancialEvidence.model_validate(result["evidence_snapshot"])
        candidate = result.get("program", {}).get("candidate")
        verification = None
        if candidate:
            verification = verify_financial_program(FinancialProgram.model_validate(candidate), goal, evidence)
            if not check("Safety rules replayed independently", verification["passed"]):
                report["state"] = "CONFLICT"
                return report
        outcome = result["outcome"]
        receipt = outcome.get("receipt")
        if result["status"] == "HELD":
            check("Held run created no new payment", outcome.get("money_moved") is False and
                  outcome.get("new_payment_created", False) is False and not receipt)
            report["state"] = "VERIFIED_HOLD" if all(c["passed"] for c in report["checks"]) else "CONFLICT"
            return report
        if result["status"] == "RECONCILED_COMPLETED":
            check("Reconciliation created no new payment", outcome.get("money_moved") is False and
                  outcome.get("new_payment_created") is False)
            report["state"] = "SIGNED_RECOVERY_RECORD" if all(c["passed"] for c in report["checks"]) else "CONFLICT"
            return report
        if not receipt:
            check("Signed payment receipt exists", False)
        else:
            p = receipt["payload"]
            check("Payment signature and approved recipient", signer.verify_for_key(p,receipt["signature"],receipt["key_id"]) and
                  p.get("scope") == "FINANCIAL_FRIDAY_ARTIFICIAL_MONEY" and
                  all(p.get(k) == v for k, v in {"tenant_id": tenant, "provider_id": goal.provider_id,
                      "payee_id": goal.payee_id, "currency": goal.currency}.items()) and
                  type(p.get("amount_minor")) is int and 0 < p["amount_minor"] <= goal.max_total_minor)
            check("Independent payment journal matches", journal_receipt == receipt)
            if result["status"] == "COMPLETED_SYNTHETIC":
                check("Payment matches replayed program and evidence", verification is not None and
                      p.get("amount_minor") == verification["authorised_total_minor"] and
                      p.get("evidence_digest") == sha256_hex(evidence.model_dump()) and
                      p.get("goal_id") == goal.goal_id and p.get("idempotency_key") == goal.idempotency_key)
        report["state"] = "VERIFIED" if all(c["passed"] for c in report["checks"]) else "CONFLICT"
    except (ValueError, KeyError, TypeError, AttributeError):
        report["state"] = "CONFLICT"
        check("Evidence has a valid schema", False)
    return report

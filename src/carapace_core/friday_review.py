"""Read-only claim reconciliation. Uploaded evidence never grants payment authority."""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from decimal import Decimal
import re
import unicodedata
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

SCALES = {"INR": 2, "USD": 2, "EUR": 2, "GBP": 2, "AUD": 2, "SGD": 2, "JPY": 0}


class ReviewQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str = Field(min_length=1, max_length=40)
    quote: str = Field(min_length=1, max_length=240)


class ReviewLine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(max_length=160)
    quantity: str | None = Field(default=None, pattern=r"^\d{1,8}(?:\.\d{1,4})?$")
    unit_price: str | None = Field(default=None, pattern=r"^\d{1,12}(?:\.\d{1,4})?$")
    line_total: str | None = Field(default=None, pattern=r"^\d{1,12}(?:\.\d{1,4})?$")


class ReviewedFinancialDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_kind: Literal["BILL", "RECEIPT", "TRANSACTION_ALERT", "UNKNOWN"]
    money_direction: Literal["SEND", "RECEIVE", "UNKNOWN"] = "UNKNOWN"
    supplier: str | None = Field(default=None, max_length=160)
    reference: str | None = Field(default=None, max_length=120)
    transaction_reference: str | None = Field(default=None, max_length=120)
    total: str | None = Field(default=None, pattern=r"^\d{1,12}(?:\.\d{1,4})?$")
    currency: Literal["INR", "USD", "EUR", "GBP", "AUD", "SGD", "JPY", "UNKNOWN"] = "UNKNOWN"
    currency_label: str | None = Field(default=None, max_length=40)
    payee: str | None = Field(default=None, max_length=160)
    issue_date: str | None = Field(default=None, max_length=30)
    due_date: str | None = Field(default=None, max_length=30)
    payment_method: str | None = Field(default=None, max_length=80)
    lines: list[ReviewLine] = Field(default_factory=list, max_length=30)
    tax: str | None = Field(default=None, pattern=r"^\d{1,12}(?:\.\d{1,4})?$")
    discount: str | None = Field(default=None, pattern=r"^\d{1,12}(?:\.\d{1,4})?$")
    summary: str = Field(min_length=5, max_length=600)
    suspicious_instructions: list[str] = Field(default_factory=list, max_length=8)
    quotes: list[ReviewQuote] = Field(default_factory=list, max_length=30)


def normalize(value):
    # Exact normalized identity, not fuzzy merchant authentication.
    return unicodedata.normalize("NFKC", value or "").strip().casefold()


def minor_units(total, currency):
    if total is None or currency not in SCALES:
        return None
    value = Decimal(total) * (10 ** SCALES[currency])
    return int(value) if value == value.to_integral_value() else None


def review_facts(facts: ReviewedFinancialDocument) -> dict:
    data = facts.model_dump()
    reasons = []
    quoted = {q.field for q in facts.quotes}
    if not {"supplier", "reference", "total"}.issubset(quoted):
        reasons.append("MISSING_CORE_EVIDENCE")
    # A bare dollar sign cannot distinguish USD/AUD/SGD, even if the model guesses.
    if (data["currency_label"] or "").strip() in {"$", "dollars", "Dollar", "dollar"}:
        data["currency"] = "UNKNOWN"
    amount = minor_units(data["total"], data["currency"])
    if data["currency"] == "UNKNOWN":
        reasons.append("CURRENCY_UNCONFIRMED")
    elif data["total"] is not None and amount is None:
        reasons.append("UNSUPPORTED_AMOUNT_PRECISION")
    if data["suspicious_instructions"]:
        reasons.append("EMBEDDED_INSTRUCTION")
    due = None
    if data["due_date"]:
        try:
            due = date.fromisoformat(data["due_date"]).isoformat()
        except ValueError:
            reasons.append("DUE_DATE_UNCONFIRMED")
    arithmetic = "NOT_CHECKABLE"
    lines = data["lines"]
    if lines:
        for line in lines:
            if all(line[key] is not None for key in ("quantity", "unit_price", "line_total")):
                if Decimal(line["quantity"]) * Decimal(line["unit_price"]) != Decimal(line["line_total"]):
                    reasons.append("LINE_ARITHMETIC_MISMATCH")
        if all(line["line_total"] is not None for line in lines) and data["total"] is not None:
            total = sum((Decimal(line["line_total"]) for line in lines), Decimal(0))
            total += Decimal(data["tax"] or "0")
            total -= Decimal(data["discount"] or "0")
            arithmetic = "MATCHED_EXTRACTED_LINES" if total == Decimal(data["total"]) else "MISMATCH"
            if arithmetic == "MISMATCH":
                reasons.append("TOTAL_ARITHMETIC_MISMATCH")
    return {"facts": data, "amount_minor": amount, "due_date": due,
            "checks": sorted(set(reasons)), "arithmetic": arithmetic,
            "evidence_level": "USER_SUPPLIED_CLAIM", "payment_authorized": False}


def reconcile_reviews(records: list[dict], *, today=None) -> dict:
    """Bounded exact identity joins; ambiguity and missing evidence remain visible."""
    today = today or date.today()
    groups, singles = defaultdict(list), []
    for record in records:
        f = record["analysis"]["facts"]
        quoted = {q["field"] for q in f["quotes"]}
        if f["supplier"] and f["reference"] and {"supplier", "reference", "total"}.issubset(quoted):
            groups[(normalize(f["supplier"]), normalize(f["reference"]), f["currency"])].append(record)
        else:
            singles.append([record])
    cases, totals = [], defaultdict(int)
    for members in list(groups.values()) + singles:
        first = members[0]["analysis"]; f = first["facts"]
        amounts = {r["analysis"]["amount_minor"] for r in members if r["analysis"]["amount_minor"] is not None}
        payees = {normalize(r["analysis"]["facts"]["payee"]) for r in members if r["analysis"]["facts"]["payee"]}
        checks = sorted({reason for r in members for reason in r["analysis"]["checks"]})
        if len(amounts) > 1:
            checks.append("AMOUNT_CONFLICT")
        if len(payees) > 1:
            checks.append("RECIPIENT_CONFLICT")
        receipts = [r for r in members if r["analysis"]["facts"]["document_kind"] in {"RECEIPT", "TRANSACTION_ALERT"}
                    and r["analysis"]["facts"]["money_direction"] == "SEND"]
        bills = [r for r in members if r["analysis"]["facts"]["document_kind"] == "BILL"]
        transaction_ids = {normalize(r["analysis"]["facts"]["transaction_reference"]) for r in receipts
                           if r["analysis"]["facts"]["transaction_reference"]}
        if bills and len(transaction_ids) > 1:
            checks.append("POSSIBLE_REPEATED_PAYMENT")
        if checks and any(code in checks for code in ("RECIPIENT_CONFLICT", "AMOUNT_CONFLICT", "EMBEDDED_INSTRUCTION", "LINE_ARITHMETIC_MISMATCH", "TOTAL_ARITHMETIC_MISMATCH", "POSSIBLE_REPEATED_PAYMENT")):
            state, action = "CONFLICT_REVIEW", "Verify the conflicting details with the provider before paying."
        elif bills and receipts and len(amounts) == 1 and all(r["analysis"]["amount_minor"] in amounts for r in members) and len(payees) == 1 and all(r["analysis"]["facts"]["payee"] for r in members):
            state, action = "RECEIPT_MATCHED_CLAIM", "A supplied receipt matches this bill. Check provider/bank status before making another payment."
        elif receipts or all(r["analysis"]["facts"]["document_kind"] in {"RECEIPT", "TRANSACTION_ALERT"} for r in members):
            state, action = "RECORDED_PAYMENT_CLAIM", "Keep this receipt; it is not independently confirmed settlement."
        elif bills:
            state, action = "BILL_TO_VERIFY", "Confirm the bill and recipient through a known provider channel. No payment is authorized."
            if len(amounts) == 1 and not checks:
                totals[f["currency"]] += next(iter(amounts))
        else:
            state, action = "INCOMPLETE_REVIEW", "More readable financial details are needed; no obligation or payment is assumed."
        case_id = members[0]["review_id"]
        quoted = {q["field"] for q in f["quotes"]}
        due = first["due_date"] if "due_date" in quoted else None
        overdue = bool(due and date.fromisoformat(due) < today and state == "BILL_TO_VERIFY")
        draft = ("Please verify " + (f["reference"] or "this financial document") + " for " + (f["supplier"] or "the named provider") +
                 ". The uploaded documents show " + (", ".join(checks) if checks else "payment details that need confirmation") +
                 ". Please confirm the outstanding amount, official payment recipient and current payment status through your official channel. No new payment has been authorized.")
        cases.append({"case_id": case_id, "state": state, "supplier": f["supplier"], "reference": f["reference"],
                      "currency": f["currency"], "amount_minor": next(iter(amounts)) if len(amounts) == 1 else None,
                      "due_date": due, "overdue_claim": overdue, "checks": checks,
                      "document_ids": [r["review_id"] for r in members], "next_action": action,
                      "verification_draft": draft, "payment_authorized": False})
    cases.sort(key=lambda c: (c["state"] != "CONFLICT_REVIEW", not c["overdue_claim"], c["due_date"] or "9999", c["case_id"]))
    return {"scope": "READ_ONLY_FINANCIAL_REVIEW", "read_only": True, "money_moved": False,
            "payment_authorized": False, "cases": cases, "document_count": len(records),
            "unconfirmed_bill_totals": dict(totals), "currency_scales": SCALES,
            "limits": ["Matches use exact normalized supplier, reference, currency, amount and available recipient evidence, not merchant authentication.",
                       "Receipts and transaction alerts are user-supplied claims, not authenticated bank settlement.",
                       "Extraction and quotations can be wrong. Arithmetic checks compare extracted fields, not independently OCR-verified pixels.",
                       "Only the most recent 50 saved reviews are reconciled. Totals are unconfirmed claims, never a bank balance."]}

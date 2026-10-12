"""Read-only Anthos account projection with explicit server-owned bindings.

Google login authorizes a Friday workspace, not an arbitrary bank account.
An operator must provision a unique artificial account binding separately.
"""
import json
import os
from datetime import datetime, timezone

import psycopg

from carapace_integrations.bank_of_anthos import (
    BankOfAnthosTransaction, LOCAL_ROUTING_NUMBER, _validate_identifier,
)


class FridayAnthosBank:
    def __init__(self, database_url: str | None = None, accounts: dict | None = None):
        self.database_url = database_url
        self.accounts = dict(accounts or {})
        for tenant, account in self.accounts.items():
            if not isinstance(tenant, str) or not tenant or not isinstance(account, str):
                raise ValueError("Bank bindings must map tenant strings to artificial account strings")
            _validate_identifier(account, 10, "Anthos account")
        if len(set(self.accounts.values())) != len(self.accounts):
            raise ValueError("Anthos demo users must not share an account")

    @classmethod
    def from_env(cls):
        accounts = json.loads(os.getenv("FRIDAY_ANTHOS_ACCOUNTS_JSON", "{}"))
        if not isinstance(accounts, dict):
            raise ValueError("FRIDAY_ANTHOS_ACCOUNTS_JSON must be an object")
        return cls(os.getenv("FRIDAY_ANTHOS_DATABASE_URL"), accounts)

    def snapshot(self, tenant: str) -> dict:
        base = {"scope": "BANK_OF_ANTHOS_ARTIFICIAL_MONEY", "read_only": True,
                "money_moved": False, "payment_authorized": False,
                "currency": "UNSPECIFIED", "balance_minor": None,
                "transactions": [], "as_of": None,
                "limits": ["Artificial accounts only; not a real bank or settlement connection.",
                    "The Anthos ledger has no currency column. Values are ledger units, not rupees.",
                    "Friday sandbox payments and uploaded claims are separate; no inferred bill-to-ledger match.",
                    "Account binding is operator-provisioned, not bank authentication via Google login."]}
        # Fail closed before connecting. A caller cannot supply an account ID.
        if tenant not in self.accounts:
            return {**base, "status": "NOT_LINKED", "reason": "No artificial Anthos account is provisioned for this workspace."}
        if not self.database_url:
            return {**base, "status": "UNAVAILABLE", "reason": "The Anthos database connector is not configured."}
        account = self.accounts[tenant]
        try:
            with psycopg.connect(self.database_url, connect_timeout=3,
                                 options="-c statement_timeout=3000") as db:
                db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                balance = db.execute("""
                    SELECT COALESCE(SUM(
                        CASE WHEN to_acct=%s AND to_route=%s THEN amount ELSE 0 END
                        - CASE WHEN from_acct=%s AND from_route=%s THEN amount ELSE 0 END),0), COUNT(*)
                    FROM public.transactions
                    WHERE (from_acct=%s AND from_route=%s) OR (to_acct=%s AND to_route=%s)
                    """, (account,LOCAL_ROUTING_NUMBER,account,LOCAL_ROUTING_NUMBER,
                          account,LOCAL_ROUTING_NUMBER,account,LOCAL_ROUTING_NUMBER)).fetchone()
                if not balance or balance[1] == 0:
                    return {**base,"status":"NO_LEDGER_EVIDENCE", "reason":"No ledger records were found for the provisioned artificial account."}
                rows = db.execute("""
                    SELECT transaction_id,from_acct,to_acct,from_route,to_route,amount,timestamp
                    FROM public.transactions
                    WHERE (from_acct=%s AND from_route=%s) OR (to_acct=%s AND to_route=%s)
                    ORDER BY transaction_id DESC LIMIT 20
                    """, (account,LOCAL_ROUTING_NUMBER,account,LOCAL_ROUTING_NUMBER)).fetchall()
            records = []
            for row in rows:
                transaction = BankOfAnthosTransaction.from_row(row)
                outgoing = transaction.from_account == account and transaction.from_routing == LOCAL_ROUTING_NUMBER
                incoming = transaction.to_account == account and transaction.to_routing == LOCAL_ROUTING_NUMBER
                counterparty = transaction.to_account if outgoing else transaction.from_account
                records.append({"transaction_id":transaction.transaction_id,
                    "direction":"SELF_TRANSFER" if outgoing and incoming else "DEBIT" if outgoing else "CREDIT",
                    "counterparty_last4":counterparty[-4:], "amount_minor":transaction.amount_minor,
                    "timestamp":transaction.as_public_record()["timestamp"]})
            return {**base,"status":"CONNECTED", "reason":"Read from the official sample bank's PostgreSQL ledger.",
                    "account_last4":account[-4:], "balance_minor":int(balance[0]),
                    "transactions":records,"total_records":int(balance[1]),
                    "as_of":datetime.now(timezone.utc).isoformat()}
        except (psycopg.Error, OSError):
            return {**base,"status":"UNAVAILABLE", "reason":"The sandbox bank could not be reached; no balance or payment outcome is assumed."}

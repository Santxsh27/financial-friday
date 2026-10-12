"""Authorized private-API visitor-isolation probe; never calls AI or pays.

Uses two synthetic subject fixtures through the owner's private Cloud Run identity.
This verifies the deployed API/Firestore boundary, not a second human OAuth login.
Creates a test bill and rules in a fresh disposable artificial visitor namespace.
"""
import argparse
import json
import ssl
import subprocess
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from carapace_core.friday_access import visitor_key, visitor_tenant


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--gcloud", default="gcloud")
    parser.add_argument("--ca-file")
    args = parser.parse_args()
    if not args.url.startswith("https://") or not args.url.endswith(".run.app"):
        parser.error("Use the private Cloud Run origin")
    def cli(*parts):
        return subprocess.check_output([args.gcloud, *parts], stderr=subprocess.DEVNULL).decode().strip()
    token = cli("auth", "print-identity-token")
    secret = cli("secrets", "versions", "access", "1", "--secret=friday-public-demo-enrollment", "--project=" + args.project)
    tenants = [visitor_tenant(secret, "accounts.google.com:" + str(int(uuid4().hex, 16))) for _ in range(2)]
    context = ssl.create_default_context(cafile=args.ca_file)
    def request(tenant, path, body=None, method=None, bad_key=False):
        headers = {"Authorization": "Bearer " + token, "X-Carapace-Tenant": tenant,
            "X-Carapace-API-Key": "wrong" if bad_key else visitor_key(secret, tenant), "Content-Type": "application/json"}
        data = json.dumps(body).encode() if body is not None else None
        try:
            with urlopen(Request(args.url + path, headers=headers, data=data, method=method), timeout=60, context=context) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)
    a, b = tenants
    assert request(a, "/v1/friday/workspace", bad_key=True)[0] == 401
    assert request(a, "/v1/friday/inbox")[0] == 403
    for tenant in tenants:
        code, state = request(tenant, "/v1/friday/workspace")
        assert code == 200 and state["read_only"] and not state["money_moved"]
        assert state["balance_minor"] == 5_000_000 and state["bills"] == []
    code, initial = request(a, "/v1/friday/mandate")
    assert code == 200 and not initial["mandate"]["automatic_sandbox_execution"]
    rules = initial["mandate"]
    assert request(a, "/v1/friday/mandate", rules, "PUT")[0] == 200
    bill = {"bill_reference": "ACCESS-PROBE-" + uuid4().hex[:12], "provider_id": "tn-power",
        "provider_name": "Artificial access verification provider", "payee_id": "tnpower@upi",
        "amount_minor": 178000, "currency": "INR", "due_date": datetime.now(timezone.utc).date().isoformat(),
        "previous_amount_minor": 165000}
    assert request(a, "/v1/friday/test-provider/bills", bill)[0] == 200
    assert len(request(a, "/v1/friday/workspace")[1]["bills"]) == 1
    assert request(b, "/v1/friday/workspace")[1]["bills"] == []
    for _ in range(2):
        assert request(a, "/v1/friday/mandate", rules, "PUT")[0] == 200
    assert request(a, "/v1/friday/mandate", rules, "PUT")[0] == 429
    for tenant in tenants:
        assert request(tenant, "/v1/friday/workspace")[1]["balance_minor"] == 5_000_000
        assert request(tenant, "/v1/friday/today")[1]["recent_runs"] == []
    print(json.dumps({"isolated_fresh_workspaces": 2, "owner_records_read": False,
        "provider_record_isolated": True, "invalid_key_rejected": True,
        "legacy_route_rejected": True, "durable_burst_limit_enforced": True,
        "balance_unchanged": True, "model_calls": 0, "payment_requests": 0,
        "second_human_google_login": "NOT_TESTED"}, indent=2))


if __name__ == "__main__":
    main()

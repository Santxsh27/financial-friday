"""Release checks without payments/rule changes; optional paid-alert AI intake."""
import argparse
import json
import ssl
import subprocess
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--gcloud", default="gcloud")
    parser.add_argument("--ca-file")
    parser.add_argument("--expected-version", default="0.17.0")
    parser.add_argument("--check-paid-alert", action="store_true",
        help="One live AI interpretation of an artificial paid notice; never a payment request")
    parser.add_argument("--check-held-run", action="store_true",
        help="Live Vertex recurring-only scenario: must hold, seal and replay without a payment")
    args = parser.parse_args()
    if not args.url.startswith("https://") or not args.url.endswith(".run.app"):
        parser.error("use the private Cloud Run HTTPS origin")

    def cli(*parts):
        return subprocess.run([args.gcloud, *parts], check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).stdout.decode().strip()

    token = cli("auth", "print-identity-token")
    keys = json.loads(cli("secrets", "versions", "access", "1",
        "--secret=friday-tenant-api-keys", "--project=" + args.project))
    headers = {"Authorization": "Bearer " + token, "X-Carapace-Tenant": "cloud-demo",
               "X-Carapace-API-Key": keys["cloud-demo"], "Content-Type": "application/json"}
    context = ssl.create_default_context(cafile=args.ca_file)

    def request(path, body=None, authenticated=True):
        data = json.dumps(body).encode() if body is not None else None
        with urlopen(Request(args.url + path, data=data,
            headers=headers if authenticated else {}), timeout=60, context=context) as response:
            return json.load(response)

    health = request("/health/ready")
    assert health["version"] == args.expected_version, "wrong candidate version"
    assert request("/v1/friday/storage-status")["mode"] == "FIRESTORE_TRANSACTIONAL"
    before = request("/v1/friday/mandate")["sandbox_balance_minor"]
    workspace = request("/v1/friday/workspace")
    assert workspace["scope"] == "ARTIFICIAL_MONEY" and workspace["read_only"]
    assert not workspace["money_moved"] and workspace["balance_minor"] == before
    assert workspace["coverage"]["bill_records_returned"] == len(workspace["bills"])
    plan = request("/v1/friday/bill-plan")
    assert plan["read_only"] and not plan["money_moved"] and not plan["payment_authorized"]
    if plan["state"] == "PLANNED":
        assert plan["planned_total_minor"] <= workspace["available_above_reserve_minor"]
        assert plan["remaining_above_reserve_minor"] >= 0
        assert all(len(row["bill_sha256"]) == 64 for row in plan["selected"])
    try:
        request("/v1/friday/bills/handle", {"bill_reference": "RELEASE-CHECK-NO-ACTION",
            "expected_bill_sha256": "0" * 64, "confirm_sandbox_execution": False})
    except HTTPError as error:
        assert error.code == 422, "unconfirmed execution must be rejected before AI or payment"
    else:
        raise AssertionError("unconfirmed bill execution unexpectedly accepted")
    unavailable = request("/v1/friday/follow-through", {"bill_reference": "RELEASE-CHECK-NO-ACTION"})
    assert unavailable["state"] == "UNAVAILABLE"
    assert unavailable["reason"] == "CLOUD_CONNECTOR_NOT_IMPLEMENTED"
    assert not unavailable["money_moved"] and not unavailable["external_settlement_verified"]
    assert request("/v1/friday/mandate")["sandbox_balance_minor"] == before
    recent = request("/v1/friday/today")["recent_runs"]
    assert all(row.get("assurance_state") in {"VERIFIED", "VERIFIED_HOLD",
        "SIGNED_RECOVERY_RECORD", "LEGACY_UNSEALED", "UNVERIFIED", "CONFLICT", "UNAVAILABLE"}
        for row in recent), "activity must expose independently checked assurance, not just stored status"
    if recent:
        saved = request("/v1/friday/runs/" + recent[0]["run_id"])
        assert saved["assurance"]["read_only"] and not saved["assurance"]["money_moved"]
        assert saved["assurance"]["state"] not in {"CONFLICT", "UNAVAILABLE"}
    if args.check_held_run:
        held = request("/v1/friday/scenarios/recurring-only/run", {"planner": "configured"})
        assert held["status"] == "HELD" and not held["outcome"]["money_moved"]
        assert held["provenance"]["mode"] == "VERTEX_AI"
        assert held["provenance"]["successful_model_calls"] > 0
        assert held["assurance"]["state"] == "VERIFIED_HOLD"
        replay = request("/v1/friday/runs/" + held["run_id"])
        assert replay["assurance"]["state"] == "VERIFIED_HOLD"
        assert request("/v1/friday/mandate")["sandbox_balance_minor"] == before
        print(json.dumps({"held_run_id": held["run_id"], "model_calls": held["provenance"]["successful_model_calls"],
                          "assurance": replay["assurance"]["state"], "balance_unchanged": True}))
    paid_alert_verified = False
    if args.check_paid_alert:
        assert workspace["bills"], "an existing artificial bill is needed for the alert check"
        bill = workspace["bills"][0]
        signal = request("/v1/friday/live-input", {"source_type": "MESSAGE",
            "content_text": f"Payment successful. Bill {bill['bill_reference']} from {bill['provider_name']} "
                f"for INR {bill['amount_minor'] // 100}.{bill['amount_minor'] % 100:02d} "
                f"to {bill['payee_id']} was already paid. This is a payment receipt, not a request to pay."})
        assert signal["understanding"]["mode"] == "VERTEX_AI", "live Vertex interpretation required"
        assert signal["state"] == "ATTENTION" and signal["reason"] == ["NOT_A_PAYMENT_REQUEST"]
        assert not signal["money_moved"] and not signal.get("case_id"), "paid notice must not prepare a payment"
        assert request("/v1/friday/mandate")["sandbox_balance_minor"] == before
        paid_alert_verified = True
    try:
        request("/health/ready", authenticated=False)
    except HTTPError as error:
        assert error.code in {401, 403}, "unexpected unauthenticated response"
    else:
        raise AssertionError("anonymous access unexpectedly allowed")
    print(json.dumps({"version": health["version"], "workspace_verified": True,
        "bill_records": len(workspace["bills"]), "balance_unchanged": True,
        "plan_state": plan["state"], "plan_has_no_payment_authority": True,
        "unconfirmed_bill_execution_rejected": True,
        "cloud_followthrough_disabled": True, "anonymous_access_rejected": True,
        "live_paid_alert_verified": paid_alert_verified,
        "live_ai_intake_requested": args.check_paid_alert, "payment_requests": 0,
        "activity_assurance_checked": True}))


if __name__ == "__main__":
    main()

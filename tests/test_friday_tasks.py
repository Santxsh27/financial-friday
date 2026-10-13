import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from carapace_ai.financial_friday import GeminiFinancialFridayPlanner, LocalFinancialFridayPlanner
from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_core.friday_access import permitted_friday_route
from carapace_core.friday_live import TestProviderBill, FridayMandate
from carapace_integrations.friday_tasks_ui import TASK_JS
from test_friday_review import facts, record


class FridayTaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app(Settings("test", Path(self.tmp.name)/"db", {"one":"key-one", "two":"key-two"}))
        self.client = TestClient(self.app)
        self.service = self.app.state.financial_friday
        self.tasks = self.app.state.friday_tasks
        self.model = Mock()
        self.service.planner = GeminiFinancialFridayPlanner(self.model, "test-model", "VERTEX_AI")
        self.headers = {"X-Carapace-Tenant":"one", "X-Carapace-API-Key":"key-one"}
        self.bill = TestProviderBill(bill_reference="BILL-1234", provider_name="TN Power", provider_id="tnpower",
            payee_id="tnpower@upi", amount_minor=178000, due_date="2026-10-15")
        self.service.publish_test_bill("one", self.bill)
        self.answer()

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def answer(self, **changes):
        proposal = {"action":"PREPARE_PAYMENT", "bill_reference":"BILL-1234",
            "explanation":"Prepare the selected artificial electricity bill; no payment yet.",
            "evidence_ids":["bill:BILL-1234"], "findings":[], "verification_message":""}
        proposal.update(changes)
        self.model.models.generate_content.return_value = SimpleNamespace(text=json.dumps(proposal))

    def prepare(self, **changes):
        payload = {"message":"Please prepare BILL-1234", "include_workspace":True}
        payload.update(changes)
        return self.client.post("/v1/friday/tasks", headers=self.headers, json=payload)

    def confirm(self, task, **changes):
        payload = {"expected_task_sha256":task["task_sha256"], "confirm_sandbox_execution":True}
        payload.update(changes)
        return self.client.post("/v1/friday/tasks/"+task["task_id"]+"/confirm", headers=self.headers, json=payload)

    def save_review(self, identity="review-1", **changes):
        value = record(identity, **changes)
        value["created_at"] = datetime.now(timezone.utc).isoformat()
        with self.service.connect() as db:
            db.execute("INSERT INTO friday_reviews VALUES (?,?,?,?)", ("one", identity, json.dumps(value), value["created_at"]))

    def test_preparation_model_call_signed_draft_no_financial_side_effects(self):
        balance = self.service.mandate("one")["sandbox_balance_minor"]
        task = self.prepare().json()
        self.assertEqual(task["state"], "READY_FOR_CONFIRMATION")
        self.assertFalse(task["money_moved"])
        self.assertFalse(task["payment_authorized"])
        self.assertTrue(task["signature_verified"])
        self.assertEqual(task["provenance"]["mode"], "VERTEX_AI")
        self.assertEqual(self.model.models.generate_content.call_count, 1)
        self.assertFalse(self.model.models.generate_content.call_args.kwargs["config"].tools)
        self.assertEqual(self.service.mandate("one")["sandbox_balance_minor"], balance)
        self.assertEqual(self.service.daily_brief("one")["recent_runs"], [])
        self.assertNotIn("tenant_id", task)

    def test_prepare_never_uses_existing_auto_authority(self):
        rules = self.service.mandate("one")["mandate"]
        self.service.save_mandate("one", FridayMandate.model_validate(rules | {"automatic_sandbox_execution":True}))
        with patch.object(self.service, "_ingest_interpreted_signal", side_effect=AssertionError("not a preparation tool")):
            self.assertEqual(self.prepare().status_code, 200)
        self.assertEqual(self.service.daily_brief("one")["recent_runs"], [])

    def test_explicit_consent_auth_and_strict_confirmation(self):
        self.assertEqual(self.prepare(include_workspace=False).status_code, 409)
        self.model.models.generate_content.assert_not_called()
        self.assertEqual(self.prepare(include_workspace="true").status_code, 422)
        self.assertEqual(self.client.post("/v1/friday/tasks",json={"message":"Please help"}).status_code,401)
        task = self.prepare().json()
        self.assertEqual(self.confirm(task,confirm_sandbox_execution=False).status_code,409)
        self.assertEqual(self.confirm(task,confirm_sandbox_execution="true").status_code,422)
        self.assertEqual(self.confirm(task,expected_task_sha256="0"*64).status_code,409)

    def test_tenant_isolation_on_get_confirm_and_model_context(self):
        task = self.prepare().json()
        other = {"X-Carapace-Tenant":"two", "X-Carapace-API-Key":"key-two"}
        self.assertEqual(self.client.get("/v1/friday/tasks/"+task["task_id"],headers=other).status_code,404)
        self.assertEqual(self.client.post("/v1/friday/tasks/"+task["task_id"]+"/confirm",headers=other,
            json={"expected_task_sha256":task["task_sha256"],"confirm_sandbox_execution":True}).status_code,404)
        self.answer(action="EXPLAIN",bill_reference=None,evidence_ids=[])
        self.client.post("/v1/friday/tasks",headers=other,json={"message":"Prepare my bill","include_workspace":True})
        content = self.model.models.generate_content.call_args.kwargs["contents"]
        self.assertNotIn("BILL-1234",content)

    def test_risk_findings_need_exact_available_quotes_and_hold(self):
        message = "Receive a refund by paying this QR first"
        self.answer(action="PREPARE_VERIFICATION",findings=[{"kind":"REFUND_PAYMENT_CONTRADICTION",
            "source_id":"request", "quote":"paying this QR first", "reason":"Receiving a refund is inconsistent with paying first."}],
            verification_message="Please confirm the refund through your official channel.")
        task = self.prepare(message=message).json()
        self.assertEqual(task["state"],"HOLD")
        self.assertIn("SEMANTIC_RISK_REVIEW",task["gate_reasons"])
        self.assertEqual(self.confirm(task).status_code,409)
        self.answer(findings=[{"kind":"RECIPIENT_SWITCH","source_id":"someone-else",
            "quote":"pay now","reason":"A changed recipient."}])
        self.assertEqual(self.prepare().status_code,409)
        self.answer(findings=[{"kind":"COERCION","source_id":"request","quote":"invented threat",
            "reason":"An unsupported threat."}])
        self.assertEqual(self.prepare().status_code,409)

    def test_model_cannot_invent_execution_authority_or_bills(self):
        for changes in ({"payment_authorized":True},{"evidence_ids":["bank-proof"]},
                        {"action":"TRANSFER_REAL_MONEY"},{"bill_reference":"FOREIGN-BILL"}):
            with self.subTest(changes=changes):
                self.answer(**changes)
                self.assertIn(self.prepare().status_code,{409,503})

    def test_unrelated_or_matching_claim_not_confused_with_bank_receipt(self):
        self.save_review(reference="OTHER-1234",payee="someoneelse@upi")
        self.assertEqual(self.prepare().json()["state"],"READY_FOR_CONFIRMATION")
        self.save_review(identity="matching",document_kind="RECEIPT",transaction_reference="TX123")
        task = self.prepare().json()
        self.assertEqual(task["state"],"HOLD")
        self.assertIn("RELATED_CLAIM_REQUIRES_REVIEW",task["gate_reasons"])

    def test_provider_claim_conflict_cannot_be_cleared_by_model(self):
        for change in ({"payee":"attacker@upi"},{"total":"2000.00"},{"money_direction":"RECEIVE"}):
            with self.subTest(change=change):
                with self.service.connect() as db:
                    db.execute("DELETE FROM friday_reviews")
                self.save_review(**change)
                self.answer(findings=[])
                task = self.prepare().json()
                self.assertEqual(task["state"],"HOLD")
                self.assertIn("PROVIDER_CLAIM_CONFLICT",task["gate_reasons"])
                self.assertEqual(self.confirm(task).status_code,409)

    def test_conflicting_documents_gate_even_if_model_omits_finding(self):
        self.save_review()
        self.save_review(identity="changed",payee="attacker@upi")
        task = self.prepare().json()
        self.assertIn("RELATED_CLAIM_REQUIRES_REVIEW",task["gate_reasons"])
        self.assertEqual(task["state"],"HOLD")

    def test_changed_evidence_rules_or_provider_rejected_before_execution(self):
        task = self.prepare().json()
        self.save_review(payee="changed@upi")
        self.assertEqual(self.confirm(task).status_code,409)
        with self.service.connect() as db:
            db.execute("DELETE FROM friday_reviews")
        task = self.prepare().json()
        rules = self.service.mandate("one")["mandate"]
        self.service.save_mandate("one",FridayMandate.model_validate(rules | {"max_fee_minor":50}))
        self.assertEqual(self.confirm(task).status_code,409)
        task = self.prepare().json()
        self.service.publish_test_bill("one",self.bill.model_copy(update={"payee_id":"changed@upi"}))
        self.assertEqual(self.confirm(task).status_code,409)
        self.assertEqual(self.service.daily_brief("one")["recent_runs"],[])

    def test_expiry_signature_tamper_and_readback(self):
        task = self.prepare().json()
        self.assertEqual(self.client.get("/v1/friday/tasks/"+task["task_id"],headers=self.headers).json()["task_sha256"],task["task_sha256"])
        with patch("carapace_api.friday_tasks._now",return_value=datetime.now(timezone.utc)+timedelta(minutes=11)):
            self.assertEqual(self.confirm(task).status_code,409)
        with self.service.connect() as db:
            row = db.execute("SELECT task_json FROM friday_assistant_tasks").fetchone()
            saved = json.loads(row[0]);saved["payload"]["state"]="HOLD"
            db.execute("UPDATE friday_assistant_tasks SET task_json=?",(json.dumps(saved),))
        self.assertEqual(self.confirm(task).status_code,409)

    def test_read_only_draft_and_outage_never_execute(self):
        self.answer(action="PREPARE_VERIFICATION",bill_reference=None,evidence_ids=[],verification_message="Please confirm [reference].")
        task = self.prepare().json()
        self.assertEqual(task["state"],"PREPARED_MESSAGE")
        self.assertEqual(self.confirm(task).status_code,409)
        self.model.models.generate_content.side_effect=RuntimeError("outage")
        self.assertEqual(self.prepare().status_code,503)
        self.service.planner=LocalFinancialFridayPlanner()
        self.assertEqual(self.prepare().status_code,503)
        self.assertEqual(self.service.daily_brief("one")["recent_runs"],[])

    def test_existing_executor_moves_one_artificial_debit_on_repeated_confirmation(self):
        task = self.prepare().json()
        self.service.planner=LocalFinancialFridayPlanner()
        before=self.service.mandate("one")["sandbox_balance_minor"]
        first=self.confirm(task)
        self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(first.json()["run"]["status"],"COMPLETED_SYNTHETIC")
        second=self.confirm(task)
        self.assertEqual(second.status_code,200,second.text)
        self.assertEqual(self.service.mandate("one")["sandbox_balance_minor"],before-self.bill.amount_minor)
        with self.service.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM friday_payments").fetchone()[0],1)

    def test_guard_reserve_and_limit_fail_closed(self):
        self.service.publish_test_bill("one",self.bill.model_copy(update={"amount_minor":600000}))
        task=self.prepare().json()
        self.assertEqual(task["state"],"HOLD")
        self.assertIn("PAYMENT_NOT_ELIGIBLE",task["gate_reasons"])

    def test_legacy_reviewed_bill_button_cannot_bypass_claim_hold(self):
        from carapace_core.canonical import sha256_hex
        self.save_review(payee="attacker@upi")
        result=self.client.post('/v1/friday/bills/handle',headers=self.headers,json={
            "bill_reference":self.bill.bill_reference,"expected_bill_sha256":sha256_hex(self.bill.model_dump()),
            "confirm_sandbox_execution":True})
        self.assertEqual(result.status_code,409,result.text)
        self.assertEqual(self.service.daily_brief("one")["recent_runs"],[])

    def test_cloud_task_storage_is_tenant_scoped_and_signed(self):
        from carapace_api.friday_tasks import FridayTaskService
        class MemoryCloud:
            mode="FIRESTORE_TRANSACTIONAL"
            def __init__(self): self.records={}
            def get(self,kind,tenant,identity): return self.records.get((kind,tenant,identity))
            def put(self,kind,tenant,identity,value): self.records[kind,tenant,identity]=value
            def list(self,kind,tenant,limit=20):
                return [v for (k,t,i),v in self.records.items() if k==kind and t==tenant][:limit]
        cloud=MemoryCloud()
        cloud.put("provider_bills","one",self.bill.bill_reference,self.bill.model_dump())
        self.service.durable=cloud
        task=self.prepare().json()
        reopened=FridayTaskService(self.service,self.app.state.friday_reviews).get("one",task["task_id"])
        self.assertEqual(reopened["task_sha256"],task["task_sha256"])
        with self.assertRaises(KeyError): self.tasks.get("two",task["task_id"])
        record=cloud.records["assistant_tasks","one",task["task_id"]]
        record["payload"]["bill"]["amount_minor"]=1
        with self.assertRaises(ValueError): self.tasks.get("one",task["task_id"])

    def test_secrets_and_raw_request_are_not_saved_in_task(self):
        self.answer(explanation="Never share OTP is 765432.")
        result=self.prepare(message="Prepare BILL-1234. My UPI PIN is 1234.")
        self.assertEqual(result.status_code,200,result.text)
        self.assertNotIn("765432",result.text)
        self.assertNotIn("UPI PIN is 1234",self.model.models.generate_content.call_args.kwargs["contents"])
        with self.service.connect() as db:
            stored=db.execute("SELECT task_json FROM friday_assistant_tasks").fetchone()[0]
        self.assertNotIn("765432",stored)
        self.assertNotIn("My UPI PIN",stored)

    def test_proxy_allowlist_and_safe_ui(self):
        path="/v1/friday/tasks/task_"+"a"*32
        self.assertTrue(permitted_friday_route("POST","/v1/friday/tasks"))
        self.assertTrue(permitted_friday_route("GET",path))
        self.assertTrue(permitted_friday_route("POST",path+"/confirm"))
        self.assertFalse(permitted_friday_route("POST",path+"/execute-anything"))
        self.assertNotIn("innerHTML",TASK_JS)
        self.assertNotIn("eval(",TASK_JS)
        self.assertIn("taskPrepare.addEventListener('click'",TASK_JS)
        self.assertIn("confirm_sandbox_execution:true",TASK_JS)


if __name__=="__main__":
    unittest.main()

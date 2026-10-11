"""Reviewed-bill execution uses actual service gates, never production funds."""
from unittest.mock import Mock
import unittest
from pathlib import Path
import json
from fastapi.testclient import TestClient
from carapace_api.factory import create_app
from carapace_api.config import Settings

from carapace_api.friday_bill_handle import handle_reviewed_bill
from carapace_core.canonical import sha256_hex
from carapace_core.friday_live import FridayMandate, TestProviderBill
import test_financial_friday


class ReviewedBillTests(unittest.TestCase):
    def setUp(self):
        self.base = test_financial_friday.FinancialFridayTests()
        self.base.setUp()
        self.service = self.base.service
        self.rules = FridayMandate(instruction="Handle household bills and preserve my reserve.",
                                  protected_balance_minor=1_000_000,
                                  automatic_payment_limit_minor=300_000)
        self.service.save_mandate("one", self.rules)
        self.bill = TestProviderBill(bill_reference="BILL-7788", provider_name="Test Power",
                                    provider_id="test-power", payee_id="power@upi",
                                    amount_minor=123_456, due_date="2026-10-12")
        self.service.publish_test_bill("one", self.bill)
        self.digest = sha256_hex(self.bill.model_dump())

    def tearDown(self):
        self.base.tearDown()

    def handle(self):
        return handle_reviewed_bill(self.service, "one", self.bill.bill_reference, self.digest)

    def test_exact_new_bill_works_without_retyping_and_replay_never_debits_twice(self):
        first = self.handle()
        self.assertEqual(first["run"]["status"], "COMPLETED_SYNTHETIC")
        self.assertEqual(first["run"]["outcome"]["receipt"]["payload"]["amount_minor"], 123456)
        self.assertTrue(first["run"]["enforce_single_payment_limit"])
        second = self.handle()
        self.assertEqual(second["run"]["status"], "ALREADY_COMPLETED")
        self.assertFalse(second["run"]["outcome"]["money_moved"])
        self.assertEqual(self.base.payment_count(), 1)

    def test_preview_changed_rejected_before_model_or_payment(self):
        self.service.publish_test_bill("one", self.bill.model_copy(update={"payee_id": "different@upi"}))
        self.service.planner.interpret_signal = Mock(side_effect=AssertionError("should not call AI"))
        with self.assertRaisesRegex(ValueError, "details changed"):
            self.handle()
        self.service.planner.interpret_signal.assert_not_called()
        self.assertEqual(self.base.payment_count(), 0)

    def test_other_tenant_and_over_limit_are_not_executed(self):
        with self.assertRaises(KeyError):
            handle_reviewed_bill(self.service, "two", self.bill.bill_reference, self.digest)
        self.service.save_mandate("one", self.rules.model_copy(update={"automatic_payment_limit_minor": 1}))
        with self.assertRaisesRegex(ValueError, "not eligible"):
            self.handle()
        self.assertEqual(self.base.payment_count(), 0)

    def test_legacy_bill_optional_defaults_do_not_create_false_provider_hold(self):
        legacy = self.bill.model_dump()
        legacy.pop("previous_amount_minor")
        legacy.pop("currency")
        with self.service.connect() as db:
            db.execute("UPDATE friday_provider_bills SET bill_json=? WHERE tenant_id=? AND bill_reference=?",
                       (json.dumps(legacy), "one", self.bill.bill_reference))
        self.assertEqual(self.handle()["run"]["status"], "COMPLETED_SYNTHETIC")
        self.assertEqual(self.base.payment_count(), 1)

    def test_provider_comparison_rejects_real_changes_and_invalid_records(self):
        from carapace_core.friday_live import provider_bill_matches
        expected = self.bill.model_dump()
        for update in ({"amount_minor": 1}, {"payee_id": "other@upi"},
                       {"due_date": "2026-10-20"}, {"previous_amount_minor": 1},
                       {"amount_minor": "123456"}, {"extra": True}):
            self.assertFalse(provider_bill_matches({**expected, **update}, expected))

    def test_model_cannot_switch_bill_recipient_or_amount(self):
        original = self.service.planner.interpret_signal
        for changes in ({"bill_reference": "OTHER-9000"}, {"claimed_payee_id": "bad@upi"},
                        {"amount_minor": 1}, {"recurring_requested": True}, {"request_kind": "UNKNOWN"}):
            with self.subTest(changes=changes):
                self.service.planner.interpret_signal = lambda *args: original(*args).model_copy(update=changes)
                with self.assertRaisesRegex(ValueError, "exactly match"):
                    self.handle()
                self.assertEqual(self.base.payment_count(), 0)

    def test_provider_change_during_understanding_is_rejected(self):
        original = self.service.planner.interpret_signal
        def change(*args):
            facts = original(*args)
            self.service.publish_test_bill("one", self.bill.model_copy(update={"amount_minor": 123457}))
            return facts
        self.service.planner.interpret_signal = change
        with self.assertRaisesRegex(ValueError, "during checking"):
            self.handle()
        self.assertEqual(self.base.payment_count(), 0)

    def test_explicit_recheck_of_terminal_hold_uses_current_gates_not_cached_outcome(self):
        original = self.service.planner.plan
        def change(context):
            program = original(context)
            self.service.publish_test_bill("one", self.bill.model_copy(update={"payee_id": "different@upi"}))
            return program
        self.service.planner.plan = change
        first = self.handle()["run"]
        self.assertEqual(first["status"], "HELD")
        self.assertEqual(self.base.payment_count(), 0)
        self.service.publish_test_bill("one", self.bill)
        self.service.planner.plan = original
        second = self.handle()["run"]
        self.assertNotEqual(second["run_id"], first["run_id"])
        self.assertEqual(second["status"], "COMPLETED_SYNTHETIC")
        self.assertEqual(self.base.payment_count(), 1)

    def test_limit_changed_during_planning_is_rechecked_at_commit(self):
        original = self.service.planner.plan
        def change(context):
            program = original(context)
            self.service.save_mandate("one", self.rules.model_copy(update={"automatic_payment_limit_minor": 1}))
            return program
        self.service.planner.plan = change
        result = self.handle()["run"]
        self.assertEqual(result["status"], "HELD")
        self.assertEqual(result["outcome"]["reason"], ["SINGLE_PAYMENT_LIMIT_CHANGED"])
        self.assertEqual(self.base.payment_count(), 0)

    def test_provider_change_between_review_and_ingestion_cannot_use_old_approval(self):
        original = self.service._ingest_interpreted_signal
        def change(*args, **kwargs):
            self.service.publish_test_bill("one", self.bill.model_copy(update={"due_date": "2026-10-13"}))
            return original(*args, **kwargs)
        self.service._ingest_interpreted_signal = change
        with self.assertRaisesRegex(ValueError, "during checking"):
            self.handle()
        self.assertEqual(self.base.payment_count(), 0)

    def test_automatic_permission_replay_also_reports_no_new_payment(self):
        self.service.save_mandate("one", self.rules.model_copy(update={"automatic_sandbox_execution": True}))
        self.assertEqual(self.handle()["run"]["status"], "COMPLETED_SYNTHETIC")
        result = self.handle()["run"]
        self.assertEqual(result["status"], "ALREADY_COMPLETED")
        self.assertFalse(result["outcome"]["new_payment_created"])
        self.assertEqual(self.base.payment_count(), 1)

    def test_api_requires_exact_consent_and_never_accepts_browser_payment_fields(self):
        app = create_app(settings=Settings(environment="test", database_path=Path(self.base.temp.name) / "review-api.db",
            tenant_keys={"one": "fake-review-key"}, ai_provider="local"))
        service = app.state.financial_friday
        service.save_mandate("one", self.rules)
        service.publish_test_bill("one", self.bill)
        headers = {"X-Carapace-Tenant": "one", "X-Carapace-API-Key": "fake-review-key"}
        body = {"bill_reference": self.bill.bill_reference, "expected_bill_sha256": self.digest,
                "confirm_sandbox_execution": True}
        with TestClient(app) as client:
            self.assertEqual(client.post("/v1/friday/bills/handle", json=body).status_code, 401)
            for invalid in ({"confirm_sandbox_execution": False}, {"confirm_sandbox_execution": "true"},
                            {"amount_minor": 1}, {"payee_id": "attacker@upi"}, {"expected_bill_sha256": "bad"}):
                response = client.post("/v1/friday/bills/handle", headers=headers, json={**body, **invalid})
                self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(client.post("/v1/friday/bills/handle", headers=headers,
                json={**body, "expected_bill_sha256": "0" * 64}).status_code, 409)
            response = client.post("/v1/friday/bills/handle", headers=headers, json=body)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["run"]["status"], "COMPLETED_SYNTHETIC")

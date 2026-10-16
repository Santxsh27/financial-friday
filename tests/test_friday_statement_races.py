"""Synthetic, bounded races at the statement/privacy boundary.

SQLite checks use the real local database. TransactionalMemory checks exercise
the production transaction callbacks through an in-memory, retrying driver;
they are contract tests, not live Firestore or Google model integration tests.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
import json
from threading import Barrier, Event
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from carapace_integrations.friday_cloud_web import WebSettings, create_cloud_web
import test_friday_portfolio
import test_friday_transactions


MODES = ("sqlite", "mock_firestore_transaction_driver")
WAIT_SECONDS = 10
FRESH_CSV = (b"date,description,debit,credit,currency\n"
             b"2026-08-12,Synthetic new groceries,150,,INR\n")
OLD_REPLY = "SYNTHETIC_OLD_REPLY_MUST_NOT_ESCAPE_AFTER_CLEANUP"


class StatementPrivacyRaceTests(unittest.TestCase):
    @contextmanager
    def workspace(self, mode):
        fixture = test_friday_portfolio.PortfolioTests()
        fixture.setUp()
        try:
            if mode == "mock_firestore_transaction_driver":
                fixture.service.durable = test_friday_transactions.TransactionalMemory()
            yield fixture
        finally:
            fixture.tearDown()

    def seed(self, fixture, data=test_friday_portfolio.CSV):
        prepared = fixture.preview(data)
        self.assertEqual(prepared.status_code, 200, prepared.text)
        saved = fixture.save(prepared.json())
        self.assertEqual(saved.status_code, 200, saved.text)
        return saved.json()

    def seed_other_tenant(self, fixture):
        original_headers = fixture.headers
        fixture.headers = {"X-Carapace-Tenant": "two", "X-Carapace-API-Key": "key-two"}
        try:
            prepared = fixture.preview(FRESH_CSV)
            self.assertEqual(prepared.status_code, 200, prepared.text)
            proposal = prepared.json()
            other_view = fixture.service.portfolio.view("two")
            response = fixture.client.post("/v1/friday/statements", headers=fixture.headers, json={
                "statement": proposal["statement"], "expected_revision": other_view["revision"],
                "workspace_generation": proposal["workspace_generation"], "confirm_reviewed_and_store": True,
            })
            self.assertEqual(response.status_code, 200, response.text)
        finally:
            fixture.headers = original_headers
        return deepcopy(fixture.service.portfolio.record("two"))

    def cleanup_and_start_fresh(self, fixture, old_generation):
        response = fixture.client.post("/v1/friday/privacy/reviews/delete", headers=fixture.headers,
                                       json={"confirm_delete_reviews": True, "expired_only": False})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["payment_journal_retained"])
        empty = fixture.service.portfolio.view("one")
        self.assertNotEqual(empty["workspace_generation"], old_generation)
        self.assertEqual(empty["revision"], 0)
        self.assertEqual(empty["summary"]["transaction_count"], 0)
        fresh = self.seed(fixture, FRESH_CSV)
        self.assertEqual(fresh["revision"], 1)
        self.assertEqual(fresh["summary"]["transaction_count"], 1)
        return deepcopy(fixture.service.portfolio.record("one"))

    def concurrent_finding_reviews(self, mode):
        with self.workspace(mode) as fixture:
            before_view = self.seed(fixture)
            before = deepcopy(fixture.service.portfolio.record("one"))
            other_before = self.seed_other_tenant(fixture)
            mandate_before = deepcopy(fixture.service.mandate("one"))
            finding_id = before_view["checkup"]["findings"][0]["finding_id"]
            body = {"finding_id": finding_id, "reviewed": True,
                    "expected_revision": before_view["revision"],
                    "workspace_generation": before_view["workspace_generation"]}
            entered = Barrier(2, timeout=WAIT_SECONDS)
            original = fixture.service.portfolio.review_finding

            def simultaneous_review(*args, **kwargs):
                entered.wait()
                return original(*args, **kwargs)

            def request_review():
                return fixture.client.post("/v1/friday/statements/findings/review",
                                           headers=fixture.headers, json=body)

            with patch.object(fixture.service.portfolio, "review_finding", side_effect=simultaneous_review), \
                 ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(request_review) for _ in range(2)]
                responses = [future.result(timeout=WAIT_SECONDS + 5) for future in futures]
            self.assertEqual(sorted(response.status_code for response in responses), [200, 409],
                             [response.text for response in responses])
            after = fixture.service.portfolio.record("one")
            self.assertEqual(after["revision"], before["revision"] + 1)
            self.assertEqual(after["reviewed_findings"], [finding_id])
            self.assertEqual(after["statements"], before["statements"])
            self.assertEqual(fixture.service.portfolio.view("one")["summary"], before_view["summary"])
            self.assertEqual(fixture.service.portfolio.record("two"), other_before)
            self.assertEqual(fixture.service.mandate("one"), mandate_before)
            fixture.base.model.models.generate_content.assert_not_called()

    def test_sqlite_same_revision_finding_reviews_have_one_winner_and_preserve_rows(self):
        self.concurrent_finding_reviews("sqlite")

    def test_mock_firestore_driver_same_revision_finding_reviews_have_one_winner_and_preserve_rows(self):
        self.concurrent_finding_reviews("mock_firestore_transaction_driver")

    def test_cleanup_during_blocked_pdf_model_discards_stale_preparation_and_preserves_fresh_workspace(self):
        for mode in MODES:
            with self.subTest(storage=mode), self.workspace(mode) as fixture:
                old_view = self.seed(fixture)
                other_before = self.seed_other_tenant(fixture)
                mandate_before = deepcopy(fixture.service.mandate("one"))
                entered, release = Event(), Event()

                def blocked_pdf_model(**kwargs):
                    units = json.loads(kwargs["contents"])["source_units"]
                    currency_unit = next(unit["id"] for unit in units if "INR" in unit["text"])
                    salary_unit = next(unit["id"] for unit in units if "2026-08-01 Salary" in unit["text"])
                    groceries_unit = next(unit["id"] for unit in units if "2026-08-02 Groceries" in unit["text"])
                    answer = {"currency": "INR", "currency_source_ids": [currency_unit], "complete": True, "rows": [
                        {"source_ids": [salary_unit], "date_text": "2026-08-01", "description": "Salary",
                         "debit_text": "", "credit_text": "45000.00", "kind": "INCOME", "category": "Other"},
                        {"source_ids": [groceries_unit], "date_text": "2026-08-02", "description": "Groceries",
                         "debit_text": "2500.00", "credit_text": "", "kind": "EXPENSE", "category": "Groceries"},
                    ]}
                    entered.set()
                    if not release.wait(WAIT_SECONDS):
                        raise RuntimeError("Synthetic PDF test wait timed out")
                    return SimpleNamespace(text=json.dumps(answer))

                fixture.base.model.models.generate_content.side_effect = blocked_pdf_model
                with patch("carapace_ai.friday_document_grounding.configured_grounder", return_value=None), \
                     ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(fixture.preview, test_friday_portfolio.artificial_pdf(), mime="application/pdf")
                    try:
                        self.assertTrue(entered.wait(WAIT_SECONDS), "PDF extraction did not reach the mocked model")
                        fresh_record = self.cleanup_and_start_fresh(fixture, old_view["workspace_generation"])
                    finally:
                        release.set()
                    response = future.result(timeout=WAIT_SECONDS + 5)
                self.assertEqual(response.status_code, 409, response.text)
                for stale_field in ("statement", "summary", "extraction_receipt"):
                    self.assertNotIn(stale_field, response.json())
                self.assertNotIn("45000", response.text)
                self.assertEqual(fixture.service.portfolio.record("one"), fresh_record)
                self.assertEqual(fixture.service.portfolio.record("two"), other_before)
                self.assertEqual(fixture.service.mandate("one"), mandate_before)
                self.assertEqual(fixture.base.model.models.generate_content.call_count, 1)

    def test_cleanup_during_blocked_statement_chat_discards_reply_and_preserves_fresh_workspace(self):
        for mode in MODES:
            with self.subTest(storage=mode), self.workspace(mode) as fixture:
                old_view = self.seed(fixture)
                other_before = self.seed_other_tenant(fixture)
                mandate_before = deepcopy(fixture.service.mandate("one"))
                entered, release = Event(), Event()
                model_inputs = []

                def blocked_chat_model(**kwargs):
                    model_inputs.append(json.loads(kwargs["contents"]))
                    entered.set()
                    if not release.wait(WAIT_SECONDS):
                        raise RuntimeError("Synthetic chat test wait timed out")
                    return SimpleNamespace(text=json.dumps({"reply": OLD_REPLY,
                        "evidence_ids": ["statements:current"], "next_screen": "dashboard", "visual_request": "MONTHLY"}))

                fixture.base.model.models.generate_content.side_effect = blocked_chat_model
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(fixture.base.chat, include_statements=True)
                    try:
                        self.assertTrue(entered.wait(WAIT_SECONDS), "Chat did not reach the mocked model")
                        fresh_record = self.cleanup_and_start_fresh(fixture, old_view["workspace_generation"])
                    finally:
                        release.set()
                    response = future.result(timeout=WAIT_SECONDS + 5)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertNotIn(OLD_REPLY, response.text)
                self.assertNotIn("statement_visuals", response.json())
                self.assertEqual(model_inputs[0]["statement_summary"]["source_revision"], old_view["revision"])
                self.assertEqual(fixture.service.portfolio.record("one"), fresh_record)
                self.assertEqual(fixture.service.portfolio.record("two"), other_before)
                self.assertEqual(fixture.service.mandate("one"), mandate_before)
                self.assertEqual(fixture.base.model.models.generate_content.call_count, 1)


class ExpiredGatewayIdentityTests(unittest.TestCase):
    def test_expired_or_invalid_verified_token_never_reaches_statement_transport(self):
        settings = WebSettings("https://synthetic-api.run.app", "https://synthetic-web.run.app",
            "/projects/123/locations/asia-south1/services/synthetic-web",
            {"synthetic@example.com": "synthetic"}, {"synthetic": "synthetic-key"})
        transport = Mock(return_value=(200, {}))
        app = create_cloud_web(settings, transport=transport, html="synthetic")
        with TestClient(app) as client:
            for reason in ("expired synthetic token", "invalid synthetic signature"):
                with self.subTest(reason=reason), patch("google.oauth2.id_token.verify_token", side_effect=ValueError(reason)):
                    response = client.post("/api/friday/statements/prepare", json={}, headers={
                        "X-Goog-Iap-Jwt-Assertion": "synthetic-token", "Origin": settings.public_origin,
                        "X-Goog-Authenticated-User-Email": "synthetic@example.com",
                        "X-Carapace-Tenant": "synthetic", "X-Carapace-API-Key": "synthetic-key",
                    })
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.assertNotIn(reason, response.text)
        transport.assert_not_called()


if __name__ == "__main__":
    unittest.main()

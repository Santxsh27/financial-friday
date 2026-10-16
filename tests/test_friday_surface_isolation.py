"""Consumer admission checks with synthetic keys, local storage and stub transports.

These tests establish an HTTP/OpenAPI boundary, not a separate process, service
account, IAM boundary, live Google identity check or live Firestore integration.
"""
import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from carapace_api.auth import TenantAuthenticator
from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.friday_access import permitted_friday_route, visitor_key, visitor_tenant
from carapace_core.friday_surface import (
    legacy_demo_enabled, parse_legacy_demo_flag, permitted_consumer_friday_route, surface_html,
)
from carapace_integrations.friday_cloud_web import WebSettings, create_cloud_web


EXECUTION_REQUESTS = (
    ("POST", "/v1/friday/tasks"),
    ("POST", "/v1/friday/tasks/task_" + "a" * 32 + "/confirm"),
    ("POST", "/v1/friday/bills/handle"),
    ("POST", "/v1/friday/scenarios/synthetic/run"),
    ("POST", "/v1/friday/live-input/synthetic/run"),
    ("POST", "/v1/friday/live-input"),
    ("POST", "/v1/friday/documents"),
    ("POST", "/v1/friday/watch"),
    ("POST", "/v1/friday/arrivals/synthetic"),
    ("POST", "/v1/friday/inbox/synthetic/retry"),
    ("PUT", "/v1/friday/mandate"),
    ("POST", "/v1/friday/test-provider/bills"),
    ("POST", "/v1/contracts"),
    ("POST", "/v1/contracts/synthetic/runs"),
    ("POST", "/v1/preflight/orders"),
    ("POST", "/v1/preflight/orders/synthetic/acknowledge"),
    ("POST", "/v1/preflight/orders/synthetic/submit"),
    ("POST", "/v1/cases/synthetic/approve"),
)


class SurfaceConfigurationTests(unittest.TestCase):
    def test_environment_flag_is_strict_and_unset_is_consumer(self):
        self.assertFalse(parse_legacy_demo_flag(None))
        self.assertFalse(parse_legacy_demo_flag("false"))
        self.assertTrue(parse_legacy_demo_flag(" TRUE "))
        for invalid in ("", "yes", "1", "0", "enabled", True, 1):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_legacy_demo_flag(invalid)

    def test_direct_development_test_settings_remain_compatible_but_production_is_off(self):
        for environment in ("development", "test", "production"):
            settings = Settings(environment, Path("/tmp/synthetic-unused.db"), {"one": "synthetic-key"})
            self.assertEqual(legacy_demo_enabled(settings), environment in {"development", "test"})
            self.assertFalse(legacy_demo_enabled(replace(settings, legacy_demo_enabled=False)))
            self.assertTrue(legacy_demo_enabled(replace(settings, legacy_demo_enabled=True)))
            with self.assertRaises(ValueError):
                legacy_demo_enabled(replace(settings, legacy_demo_enabled="true"))

    def test_surface_policy_is_positive_and_keeps_journal_recovery_only(self):
        for method, path in EXECUTION_REQUESTS:
            with self.subTest(method=method, path=path):
                self.assertFalse(permitted_consumer_friday_route(method, path))
                self.assertFalse(permitted_friday_route(method, path, legacy_demo_enabled=False))
        self.assertFalse(permitted_consumer_friday_route("GET", "/v1/friday/bank"))
        self.assertFalse(permitted_consumer_friday_route("POST", "/v1/friday/new-execution"))
        for method, path in (("GET", "/v1/friday/statements"), ("POST", "/v1/friday/statements/prepare"),
                             ("POST", "/v1/friday/reviews/documents"), ("POST", "/v1/friday/chat"),
                             ("GET", "/v1/friday/mandate"), ("GET", "/v1/friday/tasks/task_" + "a" * 32),
                             ("POST", "/v1/friday/tasks/task_" + "a" * 32 + "/reconcile"),
                             ("GET", "/v1/friday/runs/synthetic")):
            with self.subTest(method=method, path=path):
                self.assertTrue(permitted_consumer_friday_route(method, path))
                self.assertTrue(permitted_friday_route(method, path, legacy_demo_enabled=False))
        self.assertFalse(permitted_consumer_friday_route("GET", "/v1/friday/tasks/task_" + "a" * 33))

    def test_server_html_marker_is_idempotent_and_has_no_client_authority(self):
        original = '<html><head><title>Synthetic</title></head><body>Example</body></html>'
        consumer = surface_html(original, legacy_demo_enabled=False)
        self.assertIn('<head><meta name="friday-surface" content="consumer">', consumer)
        self.assertEqual(surface_html(consumer, legacy_demo_enabled=False), consumer)
        legacy = surface_html(consumer, legacy_demo_enabled=True)
        self.assertEqual(legacy.count('name="friday-surface"'), 1)
        self.assertIn('content="legacy"', legacy)
        with self.assertRaises(ValueError):
            surface_html(original, legacy_demo_enabled="true")


class ConsumerApiSurfaceTests(unittest.TestCase):
    def api(self, *, environment="production", flag=None, extra_env=None):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root = Path(directory)
        bank_path, witness_path = root / "synthetic-bank.pem", root / "synthetic-witness.pem"
        BankEnvelopeSigner(bank_path, allow_generate=True)
        BankEnvelopeSigner(witness_path, allow_generate=True)
        environment_values = {
            "CARAPACE_ENV": environment, "CARAPACE_DB_PATH": str(root / "synthetic.db"),
            "CARAPACE_TENANT_KEYS_JSON": json.dumps({"one": "synthetic-key"}),
            "CARAPACE_PASSPORT_KEYS_JSON": json.dumps({"one": "synthetic-passport-key"}),
            "CARAPACE_BANK_SIGNING_KEY_PATH": str(bank_path),
            "CARAPACE_WITNESS_SIGNING_KEY_PATH": str(witness_path),
        }
        if flag is not None:
            environment_values["FRIDAY_LEGACY_DEMO_ENABLED"] = flag
        environment_values.update(extra_env or {})
        with patch.dict(os.environ, environment_values, clear=True):
            settings = Settings.from_env()
            app = create_app(settings)
        client = TestClient(app)
        self.addCleanup(client.close)
        return settings, app, client

    @property
    def headers(self):
        return {"X-Carapace-Tenant": "one", "X-Carapace-API-Key": "synthetic-key"}

    def test_production_has_statement_guidance_and_preserves_health_and_auth(self):
        settings, app, client = self.api()
        self.assertFalse(settings.legacy_demo_enabled)
        self.assertFalse(app.state.legacy_demo_enabled)
        self.assertTrue(hasattr(app.state, "financial_friday"))
        self.assertEqual(client.get("/health/ready").status_code, 200)
        self.assertEqual(client.get("/health/live").json()["version"], app.version)
        self.assertEqual(client.get("/v1/ai/status").status_code, 200)
        self.assertEqual(client.get("/v1/friday/statements").status_code, 401)
        statements = client.get("/v1/friday/statements", headers=self.headers)
        self.assertEqual(statements.status_code, 200, statements.text)
        self.assertEqual(statements.json()["summary"]["transaction_count"], 0)
        self.assertEqual(client.post("/v1/friday/chat", headers=self.headers,
                                     json={"message": "Synthetic financial question"}).status_code, 503)
        self.assertEqual(client.get("/v1/friday/mandate", headers=self.headers).status_code, 200)

    def test_disabled_execution_methods_are_absent_from_router_and_openapi_for_enrolled_credentials(self):
        _, app, client = self.api()
        service = app.state.financial_friday
        before = service.mandate("one")
        with patch.object(service, "run_live_signal", side_effect=AssertionError("No execution permitted")), \
             patch.object(service, "run", side_effect=AssertionError("No execution permitted")):
            for method, path in EXECUTION_REQUESTS:
                with self.subTest(method=method, path=path):
                    expected = 405 if path == "/v1/friday/mandate" else 404
                    self.assertEqual(client.request(method, path, headers=self.headers, json={}).status_code, expected)
            self.assertEqual(client.get("/v1/friday/bank", headers=self.headers).status_code, 404)
        schema = client.get("/openapi.json").json()["paths"]
        self.assertNotIn("/v1/friday/tasks", schema)
        self.assertNotIn("/v1/friday/tasks/{task_id}/confirm", schema)
        self.assertNotIn("/v1/friday/bills/handle", schema)
        self.assertNotIn("/v1/preflight/orders", schema)
        self.assertIn("/v1/friday/statements", schema)
        self.assertIn("/v1/friday/tasks/{task_id}", schema)
        self.assertIn("/v1/friday/tasks/{task_id}/reconcile", schema)
        self.assertNotIn("put", schema["/v1/friday/mandate"])
        self.assertEqual(service.mandate("one"), before)

    def test_environment_loading_is_consumer_even_with_development_label_and_old_bridge_flag(self):
        with patch("carapace_api.factory.AnthosPreflightBridge") as bridge:
            settings, app, _ = self.api(environment="development", extra_env={"CARAPACE_TEST_ANTHOS_BRIDGE_ENABLED": "true"})
        self.assertFalse(settings.legacy_demo_enabled)
        self.assertIsNone(app.state.test_delivery_worker)
        bridge.assert_not_called()

        async def use_lifespan():
            async with app.router.lifespan_context(app):
                pass

        with patch("carapace_api.factory.threading.Thread") as background_thread:
            asyncio.run(use_lifespan())
        background_thread.assert_not_called()

    def test_opt_in_restores_legacy_friday_routes_without_changing_production_key_checks(self):
        settings, app, client = self.api(flag="true")
        self.assertTrue(settings.legacy_demo_enabled)
        self.assertTrue(app.state.legacy_demo_enabled)
        self.assertEqual(client.get("/v1/friday/scenarios", headers=self.headers).status_code, 200)
        schema = client.get("/openapi.json").json()["paths"]
        self.assertIn("/v1/friday/tasks/{task_id}/confirm", schema)
        self.assertEqual(client.post("/v1/friday/bills/handle", json={}).status_code, 401)
        with patch.dict(os.environ, {"CARAPACE_ENV": "production", "CARAPACE_TENANT_KEYS_JSON": '{"one":"synthetic"}',
                                     "FRIDAY_LEGACY_DEMO_ENABLED": "true"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "CARAPACE_PASSPORT_KEYS_JSON"):
                Settings.from_env()

    def test_consumer_production_starts_without_passport_keys_with_stable_bank_and_witness_keys(self):
        settings, app, client = self.api(extra_env={"CARAPACE_PASSPORT_KEYS_JSON": ""})
        self.assertIsNone(settings.passport_signing_keys)
        self.assertFalse(settings.legacy_demo_enabled)
        self.assertTrue(settings.bank_signing_key_path.is_file())
        self.assertTrue(settings.witness_signing_key_path.is_file())
        self.assertEqual(client.get("/health/ready").status_code, 200)
        self.assertEqual(client.get("/v1/friday/statements", headers=self.headers).status_code, 200)
        self.assertNotIn("/v1/cases/{case_id}/approve", client.get("/openapi.json").json()["paths"])
        with self.assertRaisesRegex(RuntimeError, "release-passport signing key is unavailable"):
            settings.passport_signing_key("one")

    def test_legacy_production_still_requires_passport_keys_and_consumer_still_requires_bank_witness_keys(self):
        with self.assertRaisesRegex(RuntimeError, "CARAPACE_PASSPORT_KEYS_JSON"):
            self.api(flag="true", extra_env={"CARAPACE_PASSPORT_KEYS_JSON": ""})
        for required_key in ("CARAPACE_BANK_SIGNING_KEY_PATH", "CARAPACE_WITNESS_SIGNING_KEY_PATH"):
            with self.subTest(required_key=required_key), self.assertRaisesRegex(RuntimeError, required_key):
                self.api(extra_env={"CARAPACE_PASSPORT_KEYS_JSON": "", required_key: ""})

    def test_recovery_route_remains_auth_gated_and_cannot_start_a_payment(self):
        _, app, client = self.api()
        self.assertIn("/internal/friday/recover", {route.path for route in app.routes})
        self.assertFalse(permitted_friday_route("POST", "/internal/friday/recover", legacy_demo_enabled=False))
        self.assertEqual(client.post("/internal/friday/recover", json={}).status_code, 404)
        app.state.friday_tasks.recovery = Mock(enabled=True)
        with patch.object(app.state.financial_friday, "run_live_signal", side_effect=AssertionError("No retry")) as execute:
            self.assertEqual(client.post("/internal/friday/recover", headers=self.headers, json={}).status_code, 403)
            self.assertEqual(client.post("/v1/friday/tasks/task_" + "a" * 32 + "/reconcile", headers=self.headers, json={}).status_code, 404)
        execute.assert_not_called()

    def test_visitor_auth_also_enforces_consumer_policy_before_quota_or_handler(self):
        secret = "synthetic-enrollment-secret-" + "x" * 40
        settings = Settings("test", Path("/tmp/synthetic-unused.db"), {"owner": "synthetic-key"},
                            friday_durable_store="firestore", public_demo_secret=secret, legacy_demo_enabled=False)
        quota = Mock()
        authenticate = TenantAuthenticator(settings, quota=quota)
        called = []
        app = FastAPI()

        @app.post("/v1/friday/tasks/{task_id}/confirm")
        def execution(task_id, tenant=Depends(authenticate)):
            called.append(task_id)
            return {"unexpected": True}

        tenant = visitor_tenant(secret, "accounts.google.com:123")
        headers = {"X-Carapace-Tenant": tenant, "X-Carapace-API-Key": visitor_key(secret, tenant)}
        response = TestClient(app).post("/v1/friday/tasks/task_" + "a" * 32 + "/confirm", headers=headers, json={})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(called, [])
        quota.reserve.assert_not_called()


class ConsumerGatewaySurfaceTests(unittest.TestCase):
    def settings(self, flag=None):
        environment = {
            "CARAPACE_ENV": "development", "FRIDAY_WEB_BACKEND_URL": "https://synthetic-api.run.app",
            "FRIDAY_WEB_ORIGIN": "https://synthetic-web.run.app",
            "FRIDAY_WEB_IAP_AUDIENCE": "/projects/123/locations/asia-south1/services/synthetic-web",
            "FRIDAY_WEB_USERS_JSON": '{"synthetic@example.com":"one"}',
            "CARAPACE_TENANT_KEYS_JSON": '{"one":"synthetic-key"}',
        }
        if flag is not None:
            environment["FRIDAY_LEGACY_DEMO_ENABLED"] = flag
        with patch.dict(os.environ, environment, clear=True):
            return WebSettings.from_env()

    def web(self, settings):
        transport = Mock(return_value=(200, {"synthetic": True}))
        app = create_cloud_web(settings, verifier=lambda *_: {"email": "synthetic@example.com"},
                               transport=transport, html="<html><head></head><body>synthetic</body></html>")
        client = TestClient(app)
        self.addCleanup(client.close)
        return client, transport

    def headers(self, settings):
        return {"X-Goog-Iap-Jwt-Assertion": "synthetic-token", "Origin": settings.public_origin}

    def test_deployed_gateway_defaults_consumer_and_blocks_legacy_before_transport(self):
        settings = self.settings()
        self.assertFalse(settings.legacy_demo_enabled)
        client, transport = self.web(settings)
        headers = self.headers(settings)
        for method, path in EXECUTION_REQUESTS:
            if not path.startswith("/v1/friday/"):
                continue
            with self.subTest(method=method, path=path):
                self.assertEqual(client.request(method, path.replace("/v1/friday/", "/api/friday/"), headers=headers, json={}).status_code, 404)
        self.assertEqual(client.get("/api/friday/bank", headers=headers).status_code, 404)
        transport.assert_not_called()
        for method, path in (("GET", "/api/friday/statements"), ("POST", "/api/friday/statements/prepare"),
                             ("POST", "/api/friday/chat"), ("GET", "/api/friday/mandate")):
            self.assertEqual(client.request(method, path, headers=headers, json={} if method == "POST" else None).status_code, 200)
        self.assertEqual(transport.call_count, 4)
        self.assertIn('<meta name="friday-surface" content="consumer">', client.get("/", headers=headers).text)
        self.assertEqual(client.get("/health").json()["scope"], "INVITED_STATEMENT_GUIDANCE")
        self.assertIn("cannot submit payments", client.get("/about", headers=headers).text)

    def test_gateway_opt_in_and_identity_origin_gates_remain_explicit(self):
        settings = self.settings("true")
        client, transport = self.web(settings)
        headers = self.headers(settings)
        self.assertEqual(client.post("/api/friday/tasks", json={}).status_code, 401)
        self.assertEqual(client.post("/api/friday/tasks", headers={**headers, "Origin": "https://invalid.example"}, json={}).status_code, 403)
        transport.assert_not_called()
        self.assertEqual(client.post("/api/friday/tasks", headers=headers, json={}).status_code, 200)
        self.assertIn('<meta name="friday-surface" content="legacy">', client.get("/", headers=headers).text)
        with self.assertRaises(ValueError):
            self.settings("yes")


if __name__ == "__main__":
    unittest.main()

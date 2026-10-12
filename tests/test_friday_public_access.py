import copy
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from carapace_api.auth import TenantAuthenticator
from carapace_api.config import Settings
from carapace_api.friday_public_quota import DemoLimitReached, FirestoreDemoQuota
from carapace_core.friday_access import visitor_key, visitor_tenant
from carapace_integrations.friday_cloud_web import WebSettings, create_cloud_web

SECRET = "test-only-enrollment-secret-" + "x" * 40


class Snapshot:
    def __init__(self, value):
        self.exists = value is not None
        self.value = value
    def to_dict(self):
        return copy.deepcopy(self.value)


class MemoryDocument:
    def __init__(self, store, key):
        self.store, self.key = store, key
    def get(self, transaction=None):
        return Snapshot(self.store.get(self.key))


class MemoryClient:
    def __init__(self):
        self.store = {}
        self.lock = threading.Lock()
    def collection(self, name):
        self.name = name
        return self
    def document(self, key):
        return MemoryDocument(self.store, key)


class MemoryQuota(FirestoreDemoQuota):
    def _atomic(self, callback):
        class Transaction:
            def set(_, ref, value):
                ref.store[ref.key] = copy.deepcopy(value)
        with self.client.lock:
            return callback(Transaction())


class PublicAccessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 12, 10, tzinfo=timezone.utc)
        self.db = MemoryClient()
        self.quota = MemoryQuota("test", client=self.db, clock=lambda: self.now)
        self.settings = Settings(environment="test", database_path=Path("/tmp/unused.db"),
            tenant_keys={"owner": "owner-secret"}, friday_durable_store="firestore",
            public_demo_secret=SECRET)
        self.auth = TenantAuthenticator(self.settings, quota=self.quota)
        api = FastAPI()
        self.records = {}
        @api.get("/v1/friday/workspace")
        def read(tenant=Depends(self.auth)):
            return {"items": self.records.get(tenant.tenant_id, [])}
        @api.post("/v1/friday/live-input")
        def write(tenant=Depends(self.auth)):
            self.records.setdefault(tenant.tenant_id, []).append("private record")
            return {"ok": True}
        @api.get("/v1/friday/runs/{run_id}")
        def run(run_id, tenant=Depends(self.auth)):
            return {"exists": run_id in self.records.get(tenant.tenant_id, [])}
        @api.get("/v1/friday/inbox")
        @api.post("/v1/contracts")
        def forbidden(tenant=Depends(self.auth)):
            return {"should_not_reach": True}
        self.api = TestClient(api)
        self.web_settings = WebSettings("https://private.run.app", "https://web.run.app",
            "/projects/123/locations/asia-south1/services/friday-web",
            {"owner@example.com": "owner"}, {"owner": "owner-secret"}, SECRET)
        def verify(token, audience):
            if token == "bad":
                raise ValueError("forged")
            return {"email": "user" + token + "@gmail.com", "sub": "accounts.google.com:" + token}
        def transport(settings, tenant, path, method, body, mime):
            response = self.api.request(method, path, headers={"X-Carapace-Tenant": tenant,
                "X-Carapace-API-Key": settings.key_for(tenant)}, content=body)
            return response.status_code, response.json()
        self.web = TestClient(create_cloud_web(self.web_settings, verifier=verify,
            transport=transport, html="<h1>Friday</h1>"))

    def headers(self, number):
        return {"X-Goog-Iap-Jwt-Assertion": number, "Origin": "https://web.run.app",
                "X-Carapace-Tenant": "owner", "X-Carapace-API-Key": "owner-secret"}

    def test_new_google_users_have_stable_distinct_private_workspaces(self):
        one, two = self.headers("123"), self.headers("456")
        self.assertEqual(self.web.get("/", headers=one).status_code, 200)
        self.assertEqual(self.web.post("/api/friday/live-input", headers=one, json={}).status_code, 200)
        self.assertEqual(self.web.get("/api/friday/workspace", headers=one).json()["items"], ["private record"])
        self.assertEqual(self.web.get("/api/friday/workspace", headers=two).json()["items"], [])
        self.assertNotIn("owner", self.records)
        self.assertNotIn(SECRET, self.web.get("/", headers=one).text)

    def test_fake_missing_and_service_identity_cannot_enroll(self):
        self.assertEqual(self.web.get("/").status_code, 401)
        for identity in ("bad", "", "not-google", "service-account"):
            self.assertEqual(self.web.get("/", headers=self.headers(identity)).status_code, 401)
        self.assertEqual(self.records, {})

    def test_credential_domains_separate_and_namespaced(self):
        tenant = visitor_tenant(SECRET, "accounts.google.com:123")
        self.assertEqual(tenant, visitor_tenant(SECRET, "accounts.google.com:123"))
        self.assertNotEqual(tenant, visitor_tenant(SECRET, "accounts.google.com:456"))
        self.assertNotEqual(tenant, visitor_tenant(SECRET + "changed", "accounts.google.com:123"))
        self.assertNotEqual(tenant.removeprefix("visitor-"), visitor_key(SECRET, tenant))
        for bad in ("owner", "visitor-../owner", "visitor-abc"):
            with self.assertRaises(ValueError):
                visitor_key(SECRET, bad)

    def test_public_credentials_cannot_reach_legacy_or_background_actions(self):
        tenant = visitor_tenant(SECRET, "accounts.google.com:123")
        headers = {"X-Carapace-Tenant": tenant, "X-Carapace-API-Key": visitor_key(SECRET, tenant)}
        self.assertEqual(self.api.post("/v1/contracts", headers=headers).status_code, 403)
        self.assertEqual(self.api.get("/v1/friday/inbox", headers=headers).status_code, 403)
        self.assertEqual(self.db.store, {})
        headers["X-Carapace-API-Key"] = "forged"
        self.assertEqual(self.api.get("/v1/friday/workspace", headers=headers).status_code, 401)

    def test_quota_rejection_stops_proxy_action_and_is_shared_between_instances(self):
        headers = self.headers("123")
        for _ in range(4):
            self.assertEqual(self.web.post("/api/friday/live-input", headers=headers, json={}).status_code, 200)
        limited = self.web.post("/api/friday/live-input", headers=headers, json={})
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(sum(map(len, self.records.values())), 4)
        other_instance = MemoryQuota("test", client=self.db, clock=lambda: self.now)
        with self.assertRaises(DemoLimitReached):
            other_instance.reserve(visitor_tenant(SECRET, "accounts.google.com:123"), "POST")
        self.assertEqual(self.web.get("/api/friday/workspace", headers=headers).status_code, 200)

    def test_daily_cap_global_cap_and_reset(self):
        self.quota.USER_MINUTE_WRITES = self.quota.GLOBAL_MINUTE_WRITES = 1000
        for _ in range(20):
            self.quota.reserve("user-one", "POST")
        with self.assertRaises(DemoLimitReached):
            self.quota.reserve("user-one", "POST")
        for user in range(9):
            for _ in range(20):
                self.quota.reserve(str(user), "POST")
        with self.assertRaises(DemoLimitReached):
            self.quota.reserve("fresh", "POST")
        self.now += timedelta(days=1)
        self.quota.reserve("user-one", "POST")

    def test_concurrent_admission_does_not_exceed_cap(self):
        def attempt(_):
            try:
                self.quota.reserve("user", "POST")
                return True
            except DemoLimitReached:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(attempt, range(40))), 4)

    def test_origin_and_tenant_query_cannot_override_identity(self):
        headers = dict(self.headers("123"), Origin="https://attacker.example")
        self.assertEqual(self.web.post("/api/friday/live-input", headers=headers, json={}).status_code, 403)
        self.assertEqual(self.web.get("/api/friday/workspace?tenant=owner", headers=self.headers("123")).status_code, 400)
        self.assertEqual(self.records, {})

    def test_disabled_or_misconfigured_public_enrollment_fails_closed(self):
        with self.assertRaises(ValueError):
            TenantAuthenticator(replace(self.settings, friday_durable_store="sqlite"), quota=self.quota)
        with self.assertRaises(ValueError):
            TenantAuthenticator(replace(self.settings, public_demo_secret="short"), quota=self.quota)
        with self.assertRaises(ValueError):
            TenantAuthenticator(replace(self.settings, tenant_keys={"visitor-owner": "bad"}), quota=self.quota)

    def test_usage_store_failure_admits_no_action(self):
        from unittest.mock import patch
        with patch.object(self.quota, "reserve", side_effect=RuntimeError("secret DB details")):
            result = self.web.post("/api/friday/live-input", headers=self.headers("123"), json={})
        self.assertEqual(result.status_code, 503)
        self.assertNotIn("secret DB details", result.text)
        self.assertEqual(self.records, {})

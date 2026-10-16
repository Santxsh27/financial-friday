"""Synthetic-only checks for correlation, isolation and telemetry privacy."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.concurrency import run_in_threadpool

from carapace_ai.friday_observability import generate
from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_core.friday_trace import (
    RequestTraceMiddleware, get_request_id, new_request_id, record_stage, validate_request_id,
)
from carapace_integrations.friday_cloud_web import WebSettings, backend_request, create_cloud_web


TRACE_LOG = "carapace_core.friday_trace"
MODEL_LOG = "carapace_ai.friday_observability"
SENSITIVE = "PRIVATE_email@example.com_account_123_filename.pdf_prompt_reply"


def events(logs):
    return [json.loads(record.getMessage()) for record in logs.records]


def web_settings():
    return WebSettings(
        "https://synthetic-api.run.app", "https://synthetic-web.run.app",
        "/projects/123/locations/asia-south1/services/synthetic-web",
        {"synthetic@example.com": "synthetic-tenant"}, {"synthetic-tenant": "synthetic-key"},
    )


def traced_app(*, trust_incoming=True):
    app = FastAPI()

    @app.get("/items/{item_id}")
    async def item(item_id: str, request: Request):
        current = get_request_id()
        await asyncio.sleep(0)
        worker = await run_in_threadpool(get_request_id)
        return {"current": current, "worker": worker, "state": request.state.request_id}

    app.add_middleware(RequestTraceMiddleware, service="api", trust_incoming=trust_incoming,
                       allowed_routes={route.path for route in app.routes})
    return app


class RequestIdTests(unittest.TestCase):
    def test_only_fixed_lowercase_opaque_format_is_accepted(self):
        valid = new_request_id()
        self.assertEqual(validate_request_id(valid), valid)
        for invalid in (None, 123, b"req_" + b"a" * 32, "", "a" * 32, "req_" + "A" * 32,
                        "req_" + "a" * 31, "req_" + "a" * 33, valid + "\n", " " + valid,
                        "req_" + "a" * 31 + "é", "x" * 100_000, SENSITIVE):
            with self.subTest(value_type=type(invalid).__name__):
                self.assertIsNone(validate_request_id(invalid))

    def test_private_ingress_accepts_only_one_valid_header_and_replaces_invalid_values(self):
        client = TestClient(traced_app())
        valid = new_request_id()
        with self.assertLogs(TRACE_LOG, level="INFO"):
            response = client.get("/items/synthetic", headers={"X-Request-ID": valid})
            self.assertEqual(response.headers["X-Request-ID"], valid)
            for headers in ({"X-Request-ID": SENSITIVE}, {"X-Request-ID": "x" * 10_000},
                            [("X-Request-ID", valid), ("X-Request-ID", new_request_id())]):
                response = client.get("/items/synthetic", headers=headers)
                self.assertIsNotNone(validate_request_id(response.headers["X-Request-ID"]))
                self.assertNotEqual(response.headers["X-Request-ID"], valid)
        self.assertIsNone(get_request_id())

    def test_route_templates_and_unknown_routes_do_not_log_input_or_query(self):
        client = TestClient(traced_app())
        with self.assertLogs(TRACE_LOG, level="INFO") as logs:
            response = client.get("/items/" + SENSITIVE, params={"filename": SENSITIVE},
                                  headers={"X-Carapace-Tenant": SENSITIVE})
            unknown = client.get("/private/" + SENSITIVE, params={"email": SENSITIVE})
        logged = events(logs)
        self.assertEqual(logged[0]["route"], "/items/{item_id}")
        self.assertEqual(logged[1]["route"], "unmatched")
        self.assertEqual(logged[1]["status"], 404)
        self.assertEqual(logged[0]["request_id"], response.headers["X-Request-ID"])
        self.assertEqual(logged[1]["request_id"], unknown.headers["X-Request-ID"])
        self.assertNotIn(SENSITIVE, str(logs.output))
        self.assertEqual(set(logged[0]), {"event", "request_id", "service", "method", "route", "status", "duration_ms"})

    def test_parallel_requests_and_threadpool_work_keep_distinct_ids(self):
        client = TestClient(traced_app())
        identifiers = [new_request_id() for _ in range(16)]

        def invoke(identifier):
            response = client.get("/items/synthetic", headers={"X-Request-ID": identifier})
            self.assertEqual(response.headers["X-Request-ID"], identifier)
            self.assertEqual(response.json(), {"current": identifier, "worker": identifier, "state": identifier})
            self.assertIsNone(get_request_id())
            return response.headers["X-Request-ID"]

        with self.assertLogs(TRACE_LOG, level="INFO") as logs, ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(set(pool.map(invoke, identifiers)), set(identifiers))
        self.assertEqual({event["request_id"] for event in events(logs)}, set(identifiers))
        self.assertIsNone(get_request_id())

    def test_real_api_factory_keeps_auth_and_returns_correlation_on_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(environment="test", database_path=Path(directory) / "synthetic.db",
                                tenant_keys={"synthetic": "synthetic-key"})
            client = TestClient(create_app(settings=settings))
            request_id = new_request_id()
            with self.assertLogs(TRACE_LOG, level="INFO") as logs:
                response = client.get("/v1/friday/statements", headers={"X-Request-ID": request_id})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["X-Request-ID"], request_id)
            self.assertEqual(events(logs)[0]["route"], "/v1/friday/statements")


class ContextResetTests(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, middleware, request_id):
        messages = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            messages.append(message)

        scope = {"type": "http", "method": "GET", "path": "/synthetic", "headers": [
            (b"x-request-id", request_id.encode("ascii"))]}
        await middleware(scope, receive, send)
        return messages

    async def test_context_is_reset_in_calling_task_after_success_failure_and_cancellation(self):
        async def successful(scope, receive, send):
            self.assertIsNotNone(get_request_id())
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        async def failing(scope, receive, send):
            self.assertIsNotNone(get_request_id())
            raise RuntimeError(SENSITIVE)

        async def cancelled(scope, receive, send):
            raise asyncio.CancelledError()

        with self.assertLogs(TRACE_LOG, level="INFO") as logs:
            await self.invoke(RequestTraceMiddleware(successful, service="api"), new_request_id())
            self.assertIsNone(get_request_id())
            with self.assertRaises(RuntimeError):
                await self.invoke(RequestTraceMiddleware(failing, service="api"), new_request_id())
            self.assertIsNone(get_request_id())
            with self.assertRaises(asyncio.CancelledError):
                await self.invoke(RequestTraceMiddleware(cancelled, service="api"), new_request_id())
            self.assertIsNone(get_request_id())
        self.assertEqual([event["status"] for event in events(logs)], [200, 500, 500])
        self.assertNotIn(SENSITIVE, str(logs.output))

    async def test_unhandled_error_response_still_carries_request_id(self):
        captured = []
        request_id = new_request_id()

        async def failing(scope, receive, send):
            raise RuntimeError(SENSITIVE)

        async def send(message):
            captured.append(message)

        middleware = RequestTraceMiddleware(failing, service="api", trust_incoming=True)
        scope = {"type": "http", "method": "GET", "headers": [(b"x-request-id", request_id.encode())]}
        with self.assertLogs(TRACE_LOG, level="INFO"), self.assertRaises(RuntimeError):
            await middleware(scope, None, send)
        self.assertEqual(captured[0]["status"], 500)
        self.assertIn((b"x-request-id", request_id.encode()), captured[0]["headers"])
        self.assertIsNone(get_request_id())


class GatewayTracingTests(unittest.TestCase):
    def test_public_ingress_generates_ids_and_propagates_through_backend_transport(self):
        settings = web_settings()
        captured = []
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(
            text=SENSITIVE, model_version="gemini-3.5-flash-lite-001",
            usage_metadata=SimpleNamespace(total_token_count=21))

        api = FastAPI()

        @api.post("/v1/friday/documents")
        def document():
            generate(client, purpose="document_review", model="gemini-3.5-flash-lite", contents=SENSITIVE)
            record_stage("validation", ok=False, reason="mismatch", duration_ms=1.25)
            return {"request_id": get_request_id()}

        api.add_middleware(RequestTraceMiddleware, service="api", trust_incoming=True,
                           allowed_routes={route.path for route in api.routes})
        api_client = TestClient(api)

        @contextmanager
        def upstream(request, timeout):
            captured.append(request)
            response = api_client.request(request.method, request.full_url.replace(settings.backend_url, ""),
                                          headers=dict(request.header_items()), content=request.data)
            yield SimpleNamespace(status=response.status_code, read=lambda: response.content)

        app = create_cloud_web(settings, verifier=lambda *_: {"email": "synthetic@example.com"}, html="synthetic")
        headers = {"X-Goog-Iap-Jwt-Assertion": "synthetic", "Origin": settings.public_origin,
                   "Content-Type": "application/pdf", "X-Request-ID": new_request_id()}
        with patch("google.oauth2.id_token.fetch_id_token", return_value="synthetic-token"), \
             patch("carapace_integrations.friday_cloud_web.urlopen", side_effect=upstream), \
             self.assertLogs(TRACE_LOG, level="INFO") as trace_logs, \
             self.assertLogs(MODEL_LOG, level="INFO") as model_logs:
            response = TestClient(app).post("/api/friday/documents?filename=" + SENSITIVE,
                                            content=SENSITIVE.encode(), headers=headers)
        request_id = response.headers["X-Request-ID"]
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(request_id, headers["X-Request-ID"])
        self.assertEqual(response.json()["request_id"], request_id)
        self.assertEqual(captured[0].get_header("X-request-id"), request_id)
        self.assertEqual({event["request_id"] for event in events(trace_logs)}, {request_id})
        model_event = events(model_logs)[0]
        self.assertEqual(model_event["request_id"], request_id)
        self.assertTrue(model_event["ok"])
        stage_event = next(event for event in events(trace_logs) if event["event"] == "friday_stage_end")
        self.assertFalse(stage_event["ok"])
        self.assertNotIn(SENSITIVE, str(trace_logs.output) + str(model_logs.output))
        self.assertIsNone(get_request_id())

    def test_auth_and_origin_rejections_have_generated_ids_and_do_not_call_backend(self):
        settings = web_settings()
        transport = Mock(return_value=(200, {}))
        app = create_cloud_web(settings, verifier=lambda *_: {"email": "synthetic@example.com"},
                               transport=transport, html="synthetic")
        client = TestClient(app)
        for headers, expected in (({}, 401), ({"X-Goog-Iap-Jwt-Assertion": "synthetic", "Origin": "https://invalid.example"}, 403)):
            with self.assertLogs(TRACE_LOG, level="INFO") as logs:
                response = client.post("/api/friday/live-input", json={}, headers=headers)
            self.assertEqual(response.status_code, expected)
            self.assertEqual(validate_request_id(response.headers["X-Request-ID"]), response.headers["X-Request-ID"])
            self.assertEqual(events(logs)[0]["status"], expected)
        transport.assert_not_called()


class ModelTelemetryTests(unittest.TestCase):
    def test_usage_version_purpose_and_latency_are_bounded_and_do_not_include_response(self):
        response = SimpleNamespace(text=SENSITIVE, model_version="gemini-3.5-flash-lite-001", usage_metadata=SimpleNamespace(
            prompt_token_count=11, candidates_token_count=-2, total_token_count=21, cached_content_token_count=True))
        client = Mock()
        client.models.generate_content.return_value = response
        with self.assertLogs(MODEL_LOG, level="INFO") as logs:
            self.assertIs(generate(client, purpose="statement_extract", model="gemini-3.5-flash-lite", contents=SENSITIVE), response)
        event = events(logs)[0]
        self.assertEqual(event["model"], "gemini-3.5-flash-lite")
        self.assertEqual(event["model_version"], response.model_version)
        self.assertEqual(event["tokens"], {"prompt_token_count": 11, "total_token_count": 21})
        self.assertEqual(event["purpose"], "statement_extract")
        self.assertGreaterEqual(event["duration_ms"], 0)
        self.assertNotIn(SENSITIVE, str(logs.output))
        self.assertNotIn("validation", event)

    def test_fixed_error_categories_do_not_include_custom_exception_name_or_message(self):
        PrivateException = type(SENSITIVE, (Exception,), {})
        for error, expected in ((TimeoutError(SENSITIVE), "timeout"), (ConnectionError(SENSITIVE), "provider_unavailable"),
                                (ValueError(SENSITIVE), "invalid_request"), (PrivateException(SENSITIVE), "provider_error")):
            client = Mock()
            client.models.generate_content.side_effect = error
            with self.assertLogs(MODEL_LOG, level="WARNING") as logs, self.assertRaises(type(error)):
                generate(client, purpose=SENSITIVE, model=SENSITIVE, model_version=SENSITIVE, contents=SENSITIVE)
            event = events(logs)[0]
            self.assertFalse(event["ok"])
            self.assertEqual(event["error_category"], expected)
            self.assertEqual(event["purpose"], "unspecified")
            self.assertEqual(event["model"], "unspecified")
            self.assertNotIn("model_version", event)
            self.assertNotIn(SENSITIVE, str(logs.output))

    def test_explicit_model_version_is_telemetry_only_and_not_an_sdk_argument(self):
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(usage_metadata=None)
        with self.assertLogs(MODEL_LOG, level="INFO") as logs:
            generate(client, purpose="statement_extract", model="gemini-3.5-flash-lite", model_version="001", contents="synthetic")
        self.assertEqual(events(logs)[0]["model_version"], "001")
        self.assertNotIn("model_version", client.models.generate_content.call_args.kwargs)

    def test_unknown_stage_and_reason_are_never_echoed(self):
        with self.assertLogs(TRACE_LOG, level="INFO") as logs:
            record_stage(SENSITIVE, ok=True, reason=SENSITIVE, duration_ms=float("nan"))
            record_stage("calculation", ok=False, reason="insufficient_data", duration_ms=2.5)
            record_stage("validation", ok=False, reason="invalid_input", duration_ms=10**1000)
        first, second, third = events(logs)
        self.assertEqual(first["stage"], "unspecified")
        self.assertEqual(first["reason"], "unspecified")
        self.assertNotIn("duration_ms", first)
        self.assertEqual(second["duration_ms"], 2.5)
        self.assertNotIn("duration_ms", third)
        self.assertNotIn(SENSITIVE, str(logs.output))


if __name__ == "__main__":
    unittest.main()

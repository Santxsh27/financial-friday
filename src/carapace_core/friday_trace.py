"""Privacy-bounded request correlation and stage telemetry.

The ID is an opaque correlation hint, never an identity or authorization claim.
Only registered route templates and fixed categories can enter these events.
"""
from __future__ import annotations

from contextvars import ContextVar
import json
import logging
import math
import re
from time import perf_counter
from uuid import uuid4


LOG = logging.getLogger(__name__)
if not LOG.handlers:
    LOG.addHandler(logging.StreamHandler())
LOG.setLevel(logging.INFO)
LOG.propagate = False

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID = ContextVar("friday_request_id", default=None)
_ID_PATTERN = re.compile(r"req_[0-9a-f]{32}\Z", re.ASCII)
_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})
_STAGES = frozenset({
    "extraction", "normalization", "reconciliation", "validation", "calculation", "persistence",
})
_REASONS = frozenset({
    "accepted", "rejected", "unsupported_format", "invalid_input", "provider_unavailable",
    "empty_result", "schema_invalid", "row_limit", "duplicate", "mismatch", "incomplete",
    "insufficient_data", "stale_revision", "calculation_error", "internal_error", "unspecified",
    "quota_limit", "quota_conflict", "quota_unavailable", "quota_retry",
})


def new_request_id() -> str:
    return "req_" + uuid4().hex


def validate_request_id(value: object) -> str | None:
    # Check length before matching, including for oversized untrusted headers.
    return value if type(value) is str and len(value) == 36 and _ID_PATTERN.fullmatch(value) else None


def get_request_id() -> str | None:
    return validate_request_id(_REQUEST_ID.get())


def _duration(value: object) -> float | None:
    if type(value) in {int, float} and 0 <= value <= 86_400_000 and math.isfinite(value):
        return round(value, 3)
    return None


def record_stage(stage: str, *, ok: bool, reason: str | None = None,
                 duration_ms: float | None = None) -> None:
    """Log a deterministic stage outcome; never pass source text or exception text.

    Unknown stage/reason values are discarded, so exception messages and input
    cannot accidentally become telemetry. Model-call success is a separate event.
    """
    event = {
        "event": "friday_stage_end", "request_id": get_request_id(),
        "stage": stage if type(stage) is str and stage in _STAGES else "unspecified",
        "ok": ok is True,
        "reason": reason if type(reason) is str and reason in _REASONS else "unspecified",
    }
    elapsed = _duration(duration_ms)
    if elapsed is not None:
        event["duration_ms"] = elapsed
    LOG.info(json.dumps(event, separators=(",", ":")))


class RequestTraceMiddleware:
    """Pure ASGI middleware, retaining ContextVars across Starlette thread pools.

    Public ingress always creates an ID. Private API ingress may accept exactly
    one strictly validated ID from its gateway. Neither uses IDs for access.
    allowed_routes is a snapshot of server-registered templates, never raw URLs.
    """

    def __init__(self, app, *, service: str, allowed_routes=(), trust_incoming: bool = False):
        self.app = app
        self.service = service if service in {"api", "web"} else "unspecified"
        self.allowed_routes = frozenset(route for route in allowed_routes if type(route) is str)
        self.trust_incoming = trust_incoming

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        incoming = [value for key, value in scope.get("headers", ()) if key.lower() == b"x-request-id"]
        request_id = None
        if self.trust_incoming and len(incoming) == 1 and len(incoming[0]) == 36:
            try:
                request_id = validate_request_id(incoming[0].decode("ascii"))
            except UnicodeDecodeError:
                pass
        request_id = request_id or new_request_id()
        context_token = _REQUEST_ID.set(request_id)
        scope.setdefault("state", {})["request_id"] = request_id
        started = perf_counter()
        status = 500
        response_started = False

        async def traced_send(message):
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status = message["status"]
                response_started = True
                message = dict(message)
                message["headers"] = [
                    (key, value) for key, value in message.get("headers", ())
                    if key.lower() != b"x-request-id"
                ] + [(b"x-request-id", request_id.encode("ascii"))]
            await send(message)

        try:
            await self.app(scope, receive, traced_send)
        except Exception:
            if not response_started:
                # Match Starlette's default 500 while preserving correlation on
                # failures outside ExceptionMiddleware. Re-raise for ASGI hosts.
                await traced_send({"type": "http.response.start", "status": 500,
                                   "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
                await traced_send({"type": "http.response.body", "body": b"Internal Server Error"})
            raise
        finally:
            try:
                route = getattr(scope.get("route"), "path", None)
                event = {
                    "event": "friday_request_end", "request_id": request_id,
                    "service": self.service,
                    "method": scope.get("method") if scope.get("method") in _METHODS else "OTHER",
                    "route": route if route in self.allowed_routes else "unmatched",
                    "status": status,
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                }
                LOG.info(json.dumps(event, separators=(",", ":")))
            finally:
                _REQUEST_ID.reset(context_token)

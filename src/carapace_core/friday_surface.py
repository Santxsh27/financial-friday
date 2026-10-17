"""Consumer admission surface; this is not process or IAM isolation.

The financial journal and its authenticated recovery worker remain available.
The legacy artificial-payment demonstrations require explicit server opt-in.
"""
from __future__ import annotations

import re


LEGACY_DEMO_ENV = "FRIDAY_LEGACY_DEMO_ENABLED"
_VARIABLES = {
    "obligation_id": r"obligation_[a-f0-9]{32}",
    "task_id": r"task_[a-f0-9]{32}",
    "run_id": r"[A-Za-z0-9_-]{1,100}",
}
# Exact registered API templates. Adding a new endpoint does not automatically
# admit it into the production consumer API or public web proxy.
CONSUMER_FRIDAY_METHODS = {
    "assistant/briefing-audio": frozenset({"POST"}),
    "statements": frozenset({"GET", "POST"}),
    "statements/prepare": frozenset({"POST"}),
    "statements/visibility": frozenset({"POST"}),
    "statements/selection": frozenset({"POST"}),
    "statements/findings/review": frozenset({"POST"}),
    "statements/findings/enquiry": frozenset({"POST"}),
    "statements/analyze": frozenset({"POST"}),
    "diary": frozenset({"GET", "POST"}),
    "diary/prepare": frozenset({"POST"}),
    "cashflow": frozenset({"GET", "POST"}),
    "buddy": frozenset({"GET"}),
    "buddy/preferences": frozenset({"GET", "PUT"}),
    "privacy": frozenset({"GET", "PUT"}),
    "privacy/reviews/delete": frozenset({"POST"}),
    "chat": frozenset({"POST"}),
    "rehearsals/preview": frozenset({"POST"}),
    "rehearsals/interpret": frozenset({"POST"}),
    "rehearsals/explain": frozenset({"POST"}),
    "plans/preview": frozenset({"POST"}),
    # Historical bill/receipt inbox routes belong to the explicit legacy demo,
    # not the statement-first consumer release. Stored history is retained.
    # Existing journal inspection/reconciliation never prepares or retries a
    # payment. Keep these available after disabling new demo submissions.
    "tasks/{task_id}": frozenset({"GET"}),
    "tasks/{task_id}/reconcile": frozenset({"POST"}),
    "runs/{run_id}": frozenset({"GET"}),
    "mandate": frozenset({"GET"}),
    "storage-status": frozenset({"GET"}),
}
_PUBLIC_API = {
    "/health/live": frozenset({"GET"}),
    "/health/ready": frozenset({"GET"}),
    "/v1/ai/status": frozenset({"GET"}),
    "/openapi.json": frozenset({"GET", "HEAD"}),
    "/docs": frozenset({"GET", "HEAD"}),
    "/docs/oauth2-redirect": frozenset({"GET", "HEAD"}),
    "/redoc": frozenset({"GET", "HEAD"}),
}
_PREFIX = "/v1/friday/"


def parse_legacy_demo_flag(raw: str | None) -> bool:
    """Environment loading is off by default, including development on Cloud Run."""
    if raw is None:
        return False
    if type(raw) is str and raw.strip().lower() in {"true", "false"}:
        return raw.strip().lower() == "true"
    raise ValueError(f"{LEGACY_DEMO_ENV} must be true or false")


def legacy_demo_enabled(settings) -> bool:
    """Retain explicit local/test fixture construction compatibility.

    Settings.from_env always populates the flag, so an environment label such
    as development cannot enable demos in a deployed server by itself.
    """
    configured = getattr(settings, "legacy_demo_enabled", None)
    if configured is not None:
        if type(configured) is not bool:
            raise ValueError("legacy_demo_enabled must be a boolean")
        return configured
    return getattr(settings, "environment", None) in {"development", "test"}


def _route_pattern(template: str) -> re.Pattern:
    pattern = re.escape(template)
    for variable, replacement in _VARIABLES.items():
        pattern = pattern.replace(re.escape("{" + variable + "}"), replacement)
    return re.compile(pattern + r"\Z", re.ASCII)


_CONSUMER_PATTERNS = tuple((_route_pattern(template), methods)
                           for template, methods in CONSUMER_FRIDAY_METHODS.items())


def permitted_consumer_friday_route(method: str, path: str) -> bool:
    if not path.startswith(_PREFIX):
        return False
    relative = path[len(_PREFIX):]
    return any(method in methods and pattern.fullmatch(relative)
               for pattern, methods in _CONSUMER_PATTERNS)


def restrict_consumer_api(application) -> None:
    """Remove non-consumer registered routes and their OpenAPI entries.

    The recovery endpoint is retained exactly with its existing OIDC/signature
    checks. It can only recover an existing journal; no new execution is added.
    No stored data, worker configuration or service identity is changed.
    """
    admitted = []
    for route in application.router.routes:
        template = getattr(route, "path", "")
        methods = getattr(route, "methods", frozenset())
        if template == "/internal/friday/recover":
            allowed = frozenset({"POST"})
        elif template.startswith(_PREFIX):
            allowed = CONSUMER_FRIDAY_METHODS.get(template[len(_PREFIX):], frozenset())
        else:
            allowed = _PUBLIC_API.get(template, frozenset())
        remaining = set(methods) & allowed
        if remaining:
            route.methods = remaining
            admitted.append(route)
    application.router.routes[:] = admitted
    application.openapi_schema = None


def surface_html(html: str, *, legacy_demo_enabled: bool) -> str:
    """Attach a server-selected mode for presentation without granting authority."""
    if type(legacy_demo_enabled) is not bool:
        raise ValueError("legacy_demo_enabled must be a boolean")
    html = re.sub(r'<meta\s+name=[\"\']friday-surface[\"\']\s+content=[\"\'](?:consumer|legacy)[\"\']\s*/?>',
                  '', html, flags=re.I)
    mode = "legacy" if legacy_demo_enabled else "consumer"
    marker = f'<meta name="friday-surface" content="{mode}">'
    head = re.search(r"<head(?:\s[^>]*)?>", html, re.I)
    return html[:head.end()] + marker + html[head.end():] if head else marker + html

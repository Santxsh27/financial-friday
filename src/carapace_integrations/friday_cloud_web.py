"""IAP-protected Friday pilot gateway. Never exposes backend credentials.

IAP verifies Google identity. Optional open demo enrollment derives isolated
visitor credentials server-side; the private API applies durable usage limits.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request as URLRequest, urlopen

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.responses import FileResponse
from pathlib import Path
from starlette.concurrency import run_in_threadpool
from carapace_core.friday_access import FRIDAY_ROUTES, validate_enrollment_secret, visitor_tenant, visitor_key

MAX_BODY = 8 * 1024 * 1024
ROUTES = FRIDAY_ROUTES


def origin(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or
            parsed.password or parsed.port or parsed.path not in {"", "/"} or
            parsed.query or parsed.fragment):
        raise ValueError("A fixed HTTPS origin is required")
    return value.rstrip("/")


@dataclass(frozen=True)
class WebSettings:
    backend_url: str
    public_origin: str
    iap_audience: str
    users: dict[str, str]
    tenant_keys: dict[str, str]
    public_demo_secret: str | None = None

    def __post_init__(self):
        origin(self.public_origin)
        if not urlsplit(origin(self.backend_url)).hostname.endswith(".run.app"):
            raise ValueError("Backend must be the private Cloud Run origin")
        if not re.fullmatch(r"/projects/\d+/locations/[a-z0-9-]+/services/[a-z0-9-]+", self.iap_audience):
            raise ValueError("Exact Cloud Run IAP audience required")
        if not self.users or any(not isinstance(k, str) or not isinstance(v, str) or
                                 not self.tenant_keys.get(v) for k, v in self.users.items()):
            raise ValueError("Every invited user needs an enrolled tenant")
        if len(set(self.users.values())) != len(self.users):
            raise ValueError("Pilot users must have separate tenants")
        if self.public_demo_secret:
            validate_enrollment_secret(self.public_demo_secret)
            if any(tenant.startswith("visitor-") for tenant in self.tenant_keys):
                raise ValueError("Visitor namespace is reserved")

    @classmethod
    def from_env(cls):
        return cls(os.environ["FRIDAY_WEB_BACKEND_URL"], os.environ["FRIDAY_WEB_ORIGIN"],
                   os.environ["FRIDAY_WEB_IAP_AUDIENCE"],
                   json.loads(os.environ["FRIDAY_WEB_USERS_JSON"]),
                   json.loads(os.environ["CARAPACE_TENANT_KEYS_JSON"]),
                   os.getenv("FRIDAY_PUBLIC_DEMO_SECRET"))

    def key_for(self, tenant: str) -> str:
        if tenant in self.tenant_keys:
            return self.tenant_keys[tenant]
        if not self.public_demo_secret:
            raise ValueError("Visitor enrollment is disabled")
        return visitor_key(self.public_demo_secret, tenant)


def verify_iap(token: str, audience: str) -> dict:
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2 import id_token
    claims = id_token.verify_token(token, GoogleRequest(), audience=audience,
                                  certs_url="https://www.gstatic.com/iap/verify/public_key")
    if claims.get("iss") != "https://cloud.google.com/iap" or not claims.get("sub"):
        raise ValueError("Invalid IAP issuer or subject")
    return claims


def backend_request(settings: WebSettings, tenant: str, path: str, method: str,
                    body: bytes | None, content_type: str) -> tuple[int, dict]:
    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2 import id_token
    try:
        token = id_token.fetch_id_token(GoogleRequest(), settings.backend_url)
    except (GoogleAuthError, OSError, ValueError):
        # No request was sent. Never fall back to anonymous invocation or retry.
        return 503, {"detail": "Friday's secure connection is unavailable. No request was submitted."}
    request = URLRequest(settings.backend_url + path, data=body, method=method, headers={
        "Authorization": "Bearer " + token,
        "X-Carapace-Tenant": tenant,
        "X-Carapace-API-Key": settings.key_for(tenant),
        "Content-Type": content_type,
    })
    try:
        with urlopen(request, timeout=150) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        # Do not reflect arbitrary upstream errors, tokens or stack traces.
        if error.code == 429:
            return 429, {"detail": "Demo allowance reached. Read saved results or try again later. Daily limits reset at midnight UTC."}
        if path.startswith('/v1/friday/rehearsals/'):
            detail={409:'Statement history changed. Reload Spending before recalculating.',
                    422:'Review the question, explicit INR amount, dates and replay assumptions. No result was guessed.',
                    503:'Live Gemini is unavailable. Enter the scenario directly; exact calculation needs no model call.'}
            return error.code, {'detail':detail.get(error.code,'The rehearsal could not be completed. No financial action was performed.')}
        if path.startswith('/v1/friday/statements'):
            if error.code == 422:
                return 422, {'detail':'Statement could not be read. Check the INR CSV columns, or use a clear unlocked PDF within the listed limits. No payment was requested.'}
            if error.code == 409:
                return 409, {'detail':'Statement history changed or this source was already imported with different details. Reload Spending before saving again.'}
            return error.code, {'detail':'Statement service unavailable. If you were saving an import, reload Spending to check whether it was recorded.'}
        return error.code, {"detail": "Friday could not complete this request. Check activity before retrying a payment."}
    except (URLError, TimeoutError, ValueError):
        if path.startswith('/v1/friday/rehearsals/'):
            return 502, {'detail':'The rehearsal connection was interrupted. No financial action was requested; calculate again when the connection is available.'}
        if path.startswith('/v1/friday/statements'):
            return 502, {'detail':'Statement connection interrupted. Reload Spending before retrying a save; its outcome is not confirmed.'}
        return 502, {"detail": "Connection interrupted. The outcome may be unknown; check activity before retrying."}


def secure_response(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'; base-uri 'self'; object-src 'none'"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=()"
    return response


def create_cloud_web(settings: WebSettings | None = None, *, verifier=verify_iap,
                     transport=backend_request, html: str | None = None) -> FastAPI:
    settings = settings or WebSettings.from_env()
    if html is None:
        from .financial_friday_ui import FINANCIAL_FRIDAY_HTML
        html = FINANCIAL_FRIDAY_HTML
    # The pilot excludes legacy pages and the local-only background worker.
    html = html.replace('href="http://localhost:8080/docs"', 'href="/about"')
    html = html.replace('href="/operations"', 'href="/about"').replace('href="/payment-check"', 'href="/about"')
    html = re.sub(r'<details class="card watch-card".*?</details>',
                  '<p>Cloud sandbox: durable payment storage is active. Continuous cloud monitoring is not enabled yet.</p>',
                  html, flags=re.S)
    html = re.sub(r"let watching=false;.*?(?=\$\('save-mandate'\))", "", html, flags=re.S)
    html = html.replace("setInterval(refreshInbox,5000);refreshInbox();", "")
    html = html.replace("'Local protected sandbox'", "'Cloud-backed protected sandbox'")
    if settings.public_demo_secret:
        html = html.replace('<main class="shell layout">',
            '<div class="shell" role="note" style="padding-top:12px;font-size:13px">'
            'Your private statement review. No bank connection or payment permission needed. '
            '<a href="/about">Access, privacy &amp; demo limits</a></div>'
            '<main class="shell layout">')
    app = FastAPI(title="Financial Friday private pilot", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        if request.url.path != "/health":
            token = request.headers.get("x-goog-iap-jwt-assertion")
            if not token:
                return secure_response(JSONResponse({"detail": "Google sign-in required"}, status_code=401))
            try:
                claims = await run_in_threadpool(verifier, token, settings.iap_audience)
                tenant = settings.users.get(claims.get("email", ""))
                if tenant is None and settings.public_demo_secret:
                    email = claims.get("email", "")
                    if not isinstance(email, str) or "@" not in email or email.endswith(".gserviceaccount.com"):
                        raise ValueError("Google user identity required")
                    tenant = visitor_tenant(settings.public_demo_secret, claims.get("sub", ""))
                if tenant is None:
                    return secure_response(JSONResponse({"detail": "This account is not enrolled in the pilot"}, status_code=403))
                request.state.tenant = tenant
                request.state.profile = {'authenticated':True,'identity_provider':'Google / Identity-Aware Proxy',
                    'email':claims.get('email',''),'bank_connected':False,
                    'message':'Google reused your existing sign-in session. This is your private Friday workspace, not a connected bank account.'}
                if request.method not in {"GET", "HEAD", "OPTIONS"}:
                    if request.headers.get("origin") != settings.public_origin:
                        return secure_response(JSONResponse({"detail": "Same-origin request required"}, status_code=403))
            except Exception:
                return secure_response(JSONResponse({"detail": "Google identity could not be verified"}, status_code=401))
        response = await call_next(request)
        return secure_response(response)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "friday-cloud-web", "scope": "GOOGLE_SIGNIN_ARTIFICIAL_MONEY_DEMO" if settings.public_demo_secret else "INVITED_ARTIFICIAL_MONEY_PILOT"}

    @app.get("/")
    async def home():
        return HTMLResponse(html)

    @app.get('/api/friday/profile')
    async def profile(request: Request):
        return request.state.profile

    @app.get("/assets/{name}")
    async def assistant_asset(name: str):
        from .friday_assets import friday_asset
        return friday_asset(name)

    @app.get("/about")
    async def about():
        return HTMLResponse("<h1>Financial Friday: access and privacy</h1><p>Google sign-in identifies your private workspace; Account shows the signed-in email. Google may reuse an existing session. No bank, Gmail, Drive or phone-message access is granted.</p><p>Start with supported redacted INR statements or an artificial example. PDF reading uses Google AI; scanned PDFs also need Document AI. Raw uploads are discarded after processing. Only normalized transaction history is saved when you explicitly review and confirm. Statement coaching shares aggregates only with separate permission. Labels and completeness can be wrong; no guaranteed savings, fraud verdict, bank balance or official credit score is implied.</p><p>Limits: PDF 4 MB / six pages / 200 rows; CSV 1 MB / 500 rows; ten imports / 2,000 saved rows. Remove names, addresses and identifiers first. Never enter passwords, PINs, OTPs or CVVs. Privacy cleanup clears statement history and other private inputs; artificial payment journals remain for replay safety.</p><p>Visitor limits: 20 action requests per account per UTC day, 200 across visitors, plus burst/read limits. Failed requests may consume allowance. These limits do not guarantee zero cloud cost. No continuous monitoring or native voice. The optional payment demo uses artificial funds only, with automatic permission off for new visitors.</p><p><a href='https://github.com/Santxsh27/financial-friday/blob/main/USER_GUIDE.md'>Detailed guide (repository access required)</a></p><a href='/'>Return to Friday</a>")

    @app.api_route("/api/friday/{path:path}", methods=["GET", "PUT", "POST", "DELETE", "PATCH"])
    async def proxy(path: str, request: Request):
        if not re.fullmatch(ROUTES.get(request.method, r"(?!)"), path):
            raise HTTPException(404, "Unsupported pilot action")
        query = ""
        if request.query_params:
            if path not in {"documents", "reviews/documents"} or set(request.query_params) != {"filename"} or len(request.query_params.getlist("filename")) != 1:
                raise HTTPException(400, "Unsupported query")
            name = request.query_params["filename"]
            if not name or len(name) > 180 or any(c in name for c in "/\\\x00\r\n"):
                raise HTTPException(400, "Invalid document name")
            query = "?" + urlencode({"filename": name})
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_BODY:
                raise HTTPException(413, "Maximum upload is 8 MB")
            body.extend(chunk)
        mime = request.headers.get("content-type", "application/json").split(";", 1)[0].lower()
        if request.method != "GET":
            supported = {"image/png", "image/jpeg", "image/webp", "application/pdf"} if path in {"documents", "reviews/documents"} else {"application/json"}
            if mime not in supported:
                raise HTTPException(415, "Unsupported content type")
        status, result = await run_in_threadpool(transport, settings, request.state.tenant,
                                               "/v1/friday/" + path + query, request.method,
                                               bytes(body) if body else None, mime)
        return JSONResponse(result, status_code=status)
    return app


def main():
    import uvicorn
    uvicorn.run(create_cloud_web(), host="0.0.0.0", port=int(os.getenv("PORT", "8080")))


if __name__ == "__main__":
    main()

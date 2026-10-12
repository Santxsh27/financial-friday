"""Small tenant authenticator used until managed identity is wired in."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool
from carapace_core.friday_access import validate_enrollment_secret, visitor_key, permitted_friday_route
from .friday_public_quota import DemoLimitReached, FirestoreDemoQuota

from .config import Settings


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str


class TenantAuthenticator:
    def __init__(self, settings: Settings, *, quota=None) -> None:
        self._tenant_keys = dict(settings.tenant_keys)
        self._public_secret = settings.public_demo_secret
        self._quota = quota
        if self._public_secret:
            validate_enrollment_secret(self._public_secret)
            if any(key.startswith("visitor-") for key in self._tenant_keys):
                raise ValueError("Visitor namespace cannot be assigned to enrolled accounts")
            if settings.friday_durable_store != "firestore":
                raise ValueError("Public demo enrollment requires durable Firestore isolation and limits")
            self._quota = quota or FirestoreDemoQuota(settings.google_cloud_project, settings.firestore_database)

    async def __call__(
        self,
        request: Request,
        tenant_id: Annotated[str | None, Header(alias="X-Carapace-Tenant")] = None,
        api_key: Annotated[str | None, Header(alias="X-Carapace-API-Key")] = None,
    ) -> TenantContext:
        expected = self._tenant_keys.get(tenant_id or "")
        visitor = expected is None and self._public_secret and tenant_id and tenant_id.startswith("visitor-")
        if visitor:
            try:
                expected = visitor_key(self._public_secret, tenant_id)
            except ValueError:
                expected = None
        if expected is None or api_key is None or not hmac.compare_digest(expected, api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid Financial Friday credentials",
            )
        if visitor:
            if not permitted_friday_route(request.method, request.url.path):
                raise HTTPException(403, "This demo account can only use supported Friday actions")
            try:
                await run_in_threadpool(self._quota.reserve, tenant_id, request.method)
            except DemoLimitReached as error:
                raise HTTPException(429, str(error), headers={"Retry-After": "60"}) from error
            except Exception as error:
                raise HTTPException(503, "Demo usage check unavailable; no action was admitted") from error
        return TenantContext(tenant_id=tenant_id or "")

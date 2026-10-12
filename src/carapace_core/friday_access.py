"""Server-only visitor credentials; never grants real financial authority."""
import hmac
import re

VISITOR_PATTERN = r"visitor-[a-f0-9]{64}"
FRIDAY_ROUTES = {
    "GET": r"(?:bank|reviews|scenarios|today|workspace|bill-plan|mandate|live-input|storage-status|test-provider/bills|runs/[A-Za-z0-9_-]{1,100})",
    "PUT": r"mandate",
    "POST": r"(?:chat|reviews|reviews/documents|reviews/statement|bills/handle|statements/analyze|follow-through|live-input|documents|test-provider/bills|live-input/[A-Za-z0-9_-]{1,100}/run|scenarios/[A-Za-z0-9_-]{1,100}/run)",
}


def validate_enrollment_secret(secret: str) -> None:
    if len(secret) < 32:
        raise ValueError("Visitor enrollment needs a server-held secret of at least 32 characters")


def visitor_tenant(secret: str, subject: str) -> str:
    validate_enrollment_secret(secret)
    if not re.fullmatch(r"accounts\.google\.com:\d{1,100}", subject):
        raise ValueError("An IAP-verified Google user subject is required")
    return "visitor-" + hmac.digest(secret.encode(), ("identity-v1:" + subject).encode(), "sha256").hex()


def visitor_key(secret: str, tenant: str) -> str:
    validate_enrollment_secret(secret)
    if not re.fullmatch(VISITOR_PATTERN, tenant):
        raise ValueError("Invalid visitor tenant")
    return hmac.digest(secret.encode(), ("credential-v1:" + tenant).encode(), "sha256").hex()


def permitted_friday_route(method: str, path: str) -> bool:
    prefix = "/v1/friday/"
    return path.startswith(prefix) and bool(re.fullmatch(FRIDAY_ROUTES.get(method, r"(?!)"), path[len(prefix):]))

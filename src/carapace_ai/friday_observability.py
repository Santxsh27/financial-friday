"""Bounded model telemetry. Never log prompts, replies, filenames or identity."""
import json
import logging
import re
from time import perf_counter

from carapace_core.friday_trace import get_request_id

LOG = logging.getLogger(__name__)
if not LOG.handlers:
    LOG.addHandler(logging.StreamHandler())
LOG.setLevel(logging.INFO)
LOG.propagate = False

_PURPOSES = frozenset({
    "task_prepare", "diary_prepare", "statement_extract", "document_review",
    "statement_coach", "rehearsal_interpret", "rehearsal_explain", "briefing_audio", "test",
    "goal_intake", "public_research", "voice_transcribe", "voice_narrate",
})
_MODEL = re.compile(r"(?:models/)?(gemini-[A-Za-z0-9][A-Za-z0-9._-]{0,93}|model)\Z", re.ASCII)
_VERSION = re.compile(r"v?[0-9]{1,10}(?:[._-][0-9]{1,10}){0,5}\Z", re.ASCII)


def _model_name(value):
    if type(value) is str and len(value) <= 108:
        match = _MODEL.fullmatch(value)
        if match:
            return match.group(1)
    return "unspecified"


def _error_category(error):
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, ConnectionError):
        return "provider_unavailable"
    if isinstance(error, ValueError):
        return "invalid_request"
    return "provider_error"


def _model_version(value):
    model = _model_name(value)
    if model != "unspecified":
        return model
    if type(value) is str and len(value) <= 66 and _VERSION.fullmatch(value):
        return value
    return "unspecified"


def generate(client, *, purpose, model_version=None, **kwargs):
    started = perf_counter()
    metadata = {
        "event": "friday_model_call", "request_id": get_request_id(),
        "purpose": purpose if type(purpose) is str and purpose in _PURPOSES else "unspecified",
        "model": _model_name(kwargs.get("model")),
    }
    supplied_version = _model_version(model_version)
    if supplied_version != "unspecified":
        metadata["model_version"] = supplied_version
    try:
        response = client.models.generate_content(**kwargs)
    except Exception as error:
        elapsed = perf_counter() - started
        LOG.warning(json.dumps({**metadata, "ok": False, "seconds": round(elapsed, 3),
            "duration_ms": round(elapsed * 1000, 3), "error_category": _error_category(error)},
            separators=(",", ":")))
        raise
    usage = getattr(response, "usage_metadata", None)
    tokens = {}
    for key in ("prompt_token_count", "candidates_token_count", "total_token_count", "cached_content_token_count"):
        value = getattr(usage, key, None)
        if type(value) is int and 0 <= value <= 2**63 - 1:
            tokens[key] = value
    response_version = _model_version(getattr(response, "model_version", None))
    if response_version != "unspecified":
        metadata["model_version"] = response_version
    elapsed = perf_counter() - started
    LOG.info(json.dumps({**metadata, "ok": True, "seconds": round(elapsed, 3),
        "duration_ms": round(elapsed * 1000, 3), "tokens": tokens}, separators=(",", ":")))
    return response

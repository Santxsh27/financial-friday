"""Minimal model-call telemetry. Never log a prompt, response, filename or tenant."""
import logging
import json
from time import perf_counter

LOG=logging.getLogger(__name__)
if not LOG.handlers:
    LOG.addHandler(logging.StreamHandler())
LOG.setLevel(logging.INFO)
LOG.propagate=False


def generate(client, *, purpose, **kwargs):
    started=perf_counter()
    try:
        response=client.models.generate_content(**kwargs)
    except Exception as error:
        LOG.warning(json.dumps({"event":"friday_model_call","purpose":purpose,"ok":False,
            "seconds":round(perf_counter()-started,3),"error_type":type(error).__name__}))
        raise
    usage=getattr(response,"usage_metadata",None)
    tokens={}
    for key in ("prompt_token_count","candidates_token_count","total_token_count","cached_content_token_count"):
        value=getattr(usage,key,None)
        if type(value) is int and value>=0:tokens[key]=value
    LOG.info(json.dumps({"event":"friday_model_call","purpose":purpose,"ok":True,
        "seconds":round(perf_counter()-started,3),"tokens":tokens}))
    return response

"""Complete bounded safety snapshot, separate from recent inbox presentation."""
from .canonical import sha256_hex

MAX_SAFETY_DOCUMENTS = 1000


def expand_records(records):
    rows = []
    for record in records:
        rows.extend(record.get("entries", [record]))
    if len(records) > MAX_SAFETY_DOCUMENTS or len(rows) > MAX_SAFETY_DOCUMENTS:
        raise ValueError("Evidence coverage exceeds the safety bound. No payment may proceed.")
    from copy import deepcopy
    rows=deepcopy(rows)
    for record in rows:
        if record.get('provenance',{}).get('quote_validation')=='MODEL_EXTRACTED_NOT_OCR_VERIFIED':
            record['analysis']['checks']=sorted(set(record['analysis']['checks']+['DOCUMENT_OCR_NOT_VERIFIED']))
    return sorted(rows, key=lambda item: item["review_id"])


def records_digest(records):
    return sha256_hex(expand_records(records))


def local_snapshot(db, tenant):
    import json
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='friday_reviews'").fetchone()
    records = [] if not exists else [json.loads(row[0]) for row in db.execute(
        "SELECT record FROM friday_reviews WHERE tenant=? ORDER BY review_id LIMIT ?",
        (tenant, MAX_SAFETY_DOCUMENTS + 1))]
    return {"version": records_digest(records), "documents": expand_records(records), "complete": True}

"""Tenant-isolated review storage, independent from payment journals/permission."""
import hashlib
import csv
import io
import json
from datetime import datetime, timezone
from carapace_ai.friday_review import extract_review
from carapace_core.friday_review import ReviewedFinancialDocument, ReviewQuote, review_facts, reconcile_reviews
from carapace_core.friday_statement import analyze_statement


class FridayReviewService:
    def __init__(self, service):
        self.service = service
        with service.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS friday_reviews (tenant TEXT NOT NULL, review_id TEXT NOT NULL, record TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(tenant,review_id))")

    def list(self, tenant):
        if self.service.durable.mode == "FIRESTORE_TRANSACTIONAL":
            records = self.service.durable.list("reviews", tenant, 50)
        else:
            with self.service.connect() as db:
                records = [json.loads(row[0]) for row in db.execute("SELECT record FROM friday_reviews WHERE tenant=? ORDER BY created_at DESC, review_id LIMIT 50", (tenant,))]
        expanded = []
        for record in records:
            expanded.extend(record["entries"] if "entries" in record else [record])
        return expanded[:50]

    def import_statement(self, tenant, text):
        from .friday_privacy import privacy_generation
        generation=privacy_generation(self.service,tenant)
        parsed = analyze_statement(text, include_entries=True)
        if parsed["transaction_count"] > 20:
            raise ValueError("For matching, export at most 20 rows; larger CSVs can use Spending review")
        rows = [{k.strip().lower(): v.strip() for k,v in row.items()} for row in csv.DictReader(io.StringIO(text.lstrip("\ufeff")), strict=True)]
        digest = parsed["statement_sha256"]
        identity = "statement-" + digest[:32]
        now = datetime.now(timezone.utc).isoformat()
        records = []
        for entry, row in zip(parsed["entries"], rows):
            outgoing = bool(entry["debit_minor"])
            total = str((entry["debit_minor"] or entry["credit_minor"]) // 100) + '.' + str((entry["debit_minor"] or entry["credit_minor"]) % 100).zfill(2)
            facts = ReviewedFinancialDocument(document_kind="TRANSACTION_ALERT", money_direction="SEND" if outgoing else "RECEIVE",
                supplier=row.get("supplier") or None, reference=row.get("bill_reference") or None,
                payee=row.get("payee") or None, transaction_reference=row.get("transaction_reference") or None,
                total=total, currency="INR", currency_label="INR", issue_date=entry["date"],
                summary=entry["description"], quotes=[ReviewQuote(field=field,quote=value) for field,value in
                    [("supplier",row.get("supplier")),("reference",row.get("bill_reference")),("payee",row.get("payee")),("total",row["debit"] if outgoing else row["credit"])] if value])
            records.append({"review_id": identity+'-'+str(entry["row"]),"created_at":now,"filename":"Statement row "+str(entry["row"]),
                "source_sha256":digest,"raw_file_stored":False,"analysis":review_facts(facts),
                "provenance":{"mode":"LOCAL_CSV_VALIDATION","model":"none","model_calls":0,"quote_validation":"USER_SUPPLIED_CSV_FIELDS"}})
        batch = {"review_id":identity,"created_at":now,"entries":records,"privacy_generation":generation}
        if self.service.durable.mode == "FIRESTORE_TRANSACTIONAL":
            if hasattr(self.service.durable, "put_review"):
                self.service.durable.put_review(tenant,identity,batch)
            else:
                self.service.durable.put("reviews",tenant,identity,batch)
        else:
            with self.service.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if privacy_generation(self.service,tenant,db)!=generation:
                    raise ValueError('Privacy cleanup occurred during import. The pending input was not saved.')
                db.execute("INSERT OR IGNORE INTO friday_reviews VALUES (?,?,?,?)",(tenant,identity,json.dumps(batch),now))
        return {"read_only":True,"money_moved":False,"payment_authorized":False,"imported_rows":len(records),"sent_to_ai":False}

    def board(self, tenant):
        records = self.list(tenant)
        return {**reconcile_reviews(records), "documents": records}

    def safety_snapshot(self, tenant):
        if self.service.durable.mode == "FIRESTORE_TRANSACTIONAL":
            if hasattr(self.service.durable, "evidence_snapshot"):
                snapshot = self.service.durable.evidence_snapshot(tenant)
            else:  # Small test adapters must also fail closed at their read bound.
                from carapace_core.friday_evidence_snapshot import expand_records
                records = self.service.durable.list("reviews", tenant, 100)
                if len(records) == 100:
                    raise ValueError("Complete financial evidence unavailable")
                snapshot = {"version": "0", "documents": expand_records(records), "complete": True}
        else:
            from carapace_core.friday_evidence_snapshot import local_snapshot
            with self.service.connect() as db:
                db.execute("BEGIN")
                snapshot = local_snapshot(db, tenant)
        return {**snapshot, "board": {**reconcile_reviews(snapshot["documents"]), "documents": snapshot["documents"]}}

    def ingest(self, tenant, *, text=None, data=None, mime=None, filename=None):
        from .friday_privacy import privacy_generation
        generation=privacy_generation(self.service,tenant)
        raw = text.encode() if text is not None else data
        digest = hashlib.sha256(("TEXT:" if text is not None else mime + ":").encode() + raw).hexdigest()
        review_id = "review-" + digest[:32]
        if self.service.durable.mode == "FIRESTORE_TRANSACTIONAL":
            existing = self.service.durable.get("reviews", tenant, review_id)
        else:
            with self.service.connect() as db:
                row = db.execute("SELECT record FROM friday_reviews WHERE tenant=? AND review_id=?", (tenant,review_id)).fetchone()
                existing = json.loads(row[0]) if row else None
        if existing:
            return {"document": existing, "reused": True, "read_only": True, "money_moved": False, "payment_authorized": False}
        grounding=None
        if data is not None:
            from carapace_ai.friday_document_grounding import configured_grounder, ground_facts
            grounder=configured_grounder()
            if grounder:
                ocr=grounder.read(data,mime)
                from carapace_ai.redaction import redact_for_model
                facts,attempts=extract_review(self.service.planner,text=redact_for_model(ocr['text']).text)
                grounding=ground_facts(facts,ocr)
            else:
                facts,attempts=extract_review(self.service.planner,data=data,mime=mime,filename=filename)
                grounding={'mode':'UNAVAILABLE','field_anchors':[],'unsupported_fields':[],
                    'authenticity_verified':False,'raw_ocr_stored':False}
        else:
            from carapace_ai.redaction import redact_for_model
            text=redact_for_model(text).text
            facts,attempts=extract_review(self.service.planner,text=text)
        from carapace_ai.redaction import redact_for_model
        facts=ReviewedFinancialDocument.model_validate_json(redact_for_model(facts.model_dump_json()).text)
        analysis=review_facts(facts)
        if grounding and (grounding['mode']=='UNAVAILABLE' or grounding['unsupported_fields']):
            analysis['checks']=sorted(set(analysis['checks']+['DOCUMENT_OCR_NOT_VERIFIED']))
        record = {"review_id": review_id, "created_at": datetime.now(timezone.utc).isoformat(),
                  "filename": filename or "Pasted financial text", "source_sha256": digest,
                  "raw_file_stored": False, "analysis": analysis,
                  "grounding":grounding,
                  "privacy_generation":generation,
                  "provenance": {"mode": self.service.planner.mode, "model": self.service.planner.model_name,
                                 "model_calls": attempts, "quote_validation": "VERBATIM_TEXT" if data is None else "DOCUMENT_AI_ANCHORED" if grounding['mode']=='DOCUMENT_AI_OCR' and not grounding['unsupported_fields'] else "MODEL_EXTRACTED_NOT_OCR_VERIFIED"}}
        if self.service.durable.mode == "FIRESTORE_TRANSACTIONAL":
            if hasattr(self.service.durable, "put_review"):
                self.service.durable.put_review(tenant,review_id,record)
            else:
                self.service.durable.put("reviews", tenant, review_id, record)
        else:
            with self.service.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if privacy_generation(self.service,tenant,db)!=generation:
                    raise ValueError('Privacy cleanup occurred during analysis. The pending input was not saved.')
                db.execute("INSERT OR IGNORE INTO friday_reviews VALUES (?,?,?,?)", (tenant, review_id, json.dumps(record),record["created_at"]))
        return {"document": record, "reused": False, "read_only": True, "money_moved": False, "payment_authorized": False}

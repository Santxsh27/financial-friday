"""Signed, tenant-bound task lifecycle. Unknown is never a failed payment."""
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4


def utcnow():
    return datetime.now(timezone.utc)


class TaskExecutionJournal:
    def __init__(self, service):
        self.service = service
        with service.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS friday_task_executions (tenant TEXT NOT NULL, task_id TEXT NOT NULL, record TEXT NOT NULL, PRIMARY KEY(tenant,task_id))")

    def seal(self, payload):
        return {"payload": payload,"signature":self.service.signer.sign(payload),"key_id":self.service.signer.key_id}

    def validate(self, record, tenant, task_id):
        if not record:
            return None
        payload=record["payload"]
        if payload["tenant_id"]!=tenant or payload["task_id"]!=task_id or not self.service.signer.verify_for_key(payload,record["signature"],record["key_id"]):
            raise ValueError("Execution record integrity failed")
        return payload

    def get(self, tenant, task_id):
        if self.service.durable.mode=="FIRESTORE_TRANSACTIONAL":
            record=self.service.durable.get("task_executions",tenant,task_id)
        else:
            with self.service.connect() as db:
                row=db.execute("SELECT record FROM friday_task_executions WHERE tenant=? AND task_id=?",(tenant,task_id)).fetchone()
            record=json.loads(row[0]) if row else None
        payload=self.validate(record,tenant,task_id)
        if not payload:return {"state":"NOT_STARTED","money_moved":False}
        public={k:v for k,v in payload.items() if k not in {"tenant_id","lease_id"}}
        if payload["state"]=="EXECUTING" and utcnow()>=datetime.fromisoformat(payload["lease_until"]):
            public["state"]="OUTCOME_UNKNOWN"
            public["message"]="Worker lease expired. Review the recorded outcome before resuming."
        return public

    def claim(self, tenant, task_id, task_digest):
        now=utcnow()
        payload={"tenant_id":tenant,"task_id":task_id,"task_sha256":task_digest,"lease_id":uuid4().hex,
            "state":"EXECUTING","started_at":now.isoformat(),"updated_at":now.isoformat(),
            "lease_until":(now+timedelta(minutes=3)).isoformat(),"run_id":None,"money_moved":False,
            "message":"Checks are executing. No completed outcome is assumed."}
        def check(old):
            previous=self.validate(old,tenant,task_id)
            if previous and previous["state"]=="EXECUTING" and now<datetime.fromisoformat(previous["lease_until"]):
                raise ValueError("This task is already executing. Review Activity; do not repeat it.")
        record=self.seal(payload)
        if self.service.durable.mode=="FIRESTORE_TRANSACTIONAL":
            store=self.service.durable
            if not hasattr(store,"claim_task_execution"):
                raise ValueError("Atomic workflow storage unavailable")
            store.claim_task_execution(tenant,task_id,record,check)
        else:
            with self.service.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row=db.execute("SELECT record FROM friday_task_executions WHERE tenant=? AND task_id=?",(tenant,task_id)).fetchone()
                check(json.loads(row[0]) if row else None)
                db.execute("INSERT OR REPLACE INTO friday_task_executions VALUES (?,?,?)",(tenant,task_id,json.dumps(record)))
        return payload

    def finish(self, lease, state, run_id=None, message=""):
        payload={**lease,"state":state,"run_id":run_id,"updated_at":utcnow().isoformat(),"message":message}
        record=self.seal(payload)
        if self.service.durable.mode=="FIRESTORE_TRANSACTIONAL":
            self.service.durable.finish_task_execution(lease["tenant_id"],lease["task_id"],record)
        else:
            with self.service.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row=db.execute("SELECT record FROM friday_task_executions WHERE tenant=? AND task_id=?",(lease["tenant_id"],lease["task_id"])).fetchone()
                old=json.loads(row[0]) if row else None
                if old and old["payload"]["lease_id"]==lease["lease_id"]:
                    db.execute("UPDATE friday_task_executions SET record=? WHERE tenant=? AND task_id=?",(json.dumps(record),lease["tenant_id"],lease["task_id"]))

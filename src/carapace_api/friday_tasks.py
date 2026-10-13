"""Evidence-bound task preparation -> explicit confirmation -> existing executor.

Preparing is read-only financially. A ten-minute signed capsule binds one tenant,
provider record, current rules and related document claims. It never grants real
bank access and never retries an external payment after an uncertain response.
"""
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from carapace_ai.friday_tasks import TaskRequest, propose_task
from carapace_core.canonical import sha256_hex
from carapace_core.friday_task_guard import related_claims as _related, claim_gate_reasons
from .friday_workspace import financial_workspace
from .friday_bill_handle import handle_reviewed_bill


class TaskConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_task_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    confirm_sandbox_execution: bool = Field(strict=True)


def _now():
    return datetime.now(timezone.utc)


class FridayTaskService:
    def __init__(self, service, reviews):
        self.service, self.reviews = service, reviews
        from .friday_execution import TaskExecutionJournal
        self.executions=TaskExecutionJournal(service)
        with service.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS friday_assistant_tasks (
                tenant_id TEXT NOT NULL, task_id TEXT NOT NULL, task_json TEXT NOT NULL,
                created_at TEXT NOT NULL, PRIMARY KEY(tenant_id,task_id))""")

    def _save(self, tenant, record):
        identity = record["payload"]["task_id"]
        if self.service.durable.mode == "FIRESTORE_TRANSACTIONAL":
            if hasattr(self.service.durable,'put_task'):self.service.durable.put_task(tenant,identity,record)
            else:self.service.durable.put("assistant_tasks", tenant, identity, record)
        else:
            with self.service.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                from .friday_privacy import privacy_generation
                if privacy_generation(self.service,tenant,db)!=record['payload'].get('privacy_generation',0):
                    raise ValueError('Privacy cleanup occurred during task preparation. The draft was not saved.')
                db.execute("INSERT INTO friday_assistant_tasks VALUES (?,?,?,?)",
                    (tenant, identity, json.dumps(record), record["created_at"]))

    def _record(self, tenant, identity):
        if self.service.durable.mode == "FIRESTORE_TRANSACTIONAL":
            record = self.service.durable.get("assistant_tasks", tenant, identity)
        else:
            with self.service.connect() as db:
                row = db.execute("SELECT task_json FROM friday_assistant_tasks WHERE tenant_id=? AND task_id=?",
                                 (tenant, identity)).fetchone()
            record = json.loads(row[0]) if row else None
        if record is None:
            raise KeyError(identity)
        if not self.service.signer.verify_for_key(record["payload"],record["signature"],record["key_id"]) or record["payload"]["tenant_id"] != tenant:
            raise ValueError("Task integrity failed. Prepare a new task.")
        return record

    @staticmethod
    def _public(record):
        payload = record["payload"]
        return {k: v for k, v in payload.items() if k != "tenant_id"} | {
            "task_sha256": sha256_hex(payload), "signature_verified": True,
            "expired": _now() >= datetime.fromisoformat(payload["expires_at"]),
            "money_moved": False, "payment_authorized": False,
            "scope": "ARTIFICIAL_MONEY_ONLY"}

    def get(self, tenant, identity):
        task=self._public(self._record(tenant, identity))
        task["execution"]=self.executions.get(tenant,identity)
        if task["execution"].get("run_id"):
            run=self.service.get(tenant,task["execution"]["run_id"])
            task["execution"]["assurance_state"]=run.get("assurance",{}).get("state","UNVERIFIED")
            if task["execution"]["state"]=="COMPLETED" and task["execution"]["assurance_state"]!="VERIFIED":
                task["execution"]["state"]="REVIEW_REQUIRED"
        return task

    def prepare(self, tenant, request: TaskRequest):
        from .friday_privacy import privacy_generation
        generation=privacy_generation(self.service,tenant)
        workspace = financial_workspace(self.service, tenant) if request.include_workspace else None
        rules = self.service.mandate(tenant)["mandate"] if request.include_workspace else None
        snapshot = self.reviews.safety_snapshot(tenant) if request.include_workspace else None
        board = snapshot["board"] if snapshot else {"cases": [], "documents": []}
        bills = workspace["bills"] if workspace else []
        selected = None
        if request.obligation_id:
            if not request.include_workspace:
                raise ValueError('Selecting an obligation requires explicit workspace consent.')
            if request.expected_evidence_version != snapshot['version']:
                raise ValueError('Financial evidence changed. Refresh the obligation inbox before preparing.')
            from carapace_core.friday_obligations import obligation_board
            selected = next((item for item in obligation_board(board, workspace, snapshot['version'])['items']
                             if item['obligation_id'] == request.obligation_id), None)
            if selected is None:
                raise ValueError('Selected obligation is unavailable in this workspace.')
            if len(selected['document_ids']) > 10:
                raise ValueError('Selected obligation exceeds the ten-document AI context bound. No model call or payment was made; verify through a known provider channel.')
            bills = [bill for bill in bills if bill['bill_reference'] == selected['bill_reference']]
        sources = [{"source_id": "request", "source_text": request.message}]
        if rules is not None:
            sources.append({'source_id': 'saved_rules', 'source_text': json.dumps(rules, ensure_ascii=False)})
        for bill in bills[:20]:
            sources.append({"source_id": "bill:" + bill["bill_reference"],
                            "source_text": json.dumps(bill, ensure_ascii=False)})
        model_cases = [case for case in board['cases'] if case['case_id'] == selected['source_case_id']] if selected else board['cases'][:10]
        for case in model_cases:
            sources.append({"source_id": case["case_id"], "source_text": json.dumps(case, ensure_ascii=False)})
        if selected:
            sources.append({'source_id': 'selected_obligation', 'source_text': json.dumps(selected, ensure_ascii=False)})
            for document in [doc for doc in board['documents'] if doc['review_id'] in selected['document_ids']][:10]:
                sources.append({'source_id': document['review_id'] + ':facts',
                                'source_text': json.dumps(document['analysis']['facts'], ensure_ascii=False)})
        answer = propose_task(self.service.planner, request, sources)
        proposal = answer["proposal"]
        if selected and proposal['bill_reference'] not in {None, selected['bill_reference']}:
            raise ValueError('AI tried to substitute another obligation. No action was performed.')
        bill = next((b for b in bills[:20] if b["bill_reference"] == proposal["bill_reference"]), None)
        if proposal["bill_reference"] and bill is None:
            raise ValueError("AI selected a bill unavailable in this workspace. No action was performed.")
        related = _related(board, proposal["bill_reference"])
        gate_reasons = []
        if proposal["findings"]:
            gate_reasons.append("SEMANTIC_RISK_REVIEW")
        gate_reasons.extend(claim_gate_reasons(related, bill))
        if selected and selected['action'] != 'PREPARE_PAYMENT' and proposal['action'] == 'PREPARE_PAYMENT':
            gate_reasons.append('SELECTED_OBLIGATION_NOT_PAYABLE')
        from carapace_core.friday_bill_plan import plan_bills
        plan = plan_bills(workspace) if workspace else {"state":"NO_WORKSPACE", "selected":[], "already_recorded":[]}
        eligible = plan["state"] == "PLANNED" and bill and any(
            row["bill_reference"] == bill["bill_reference"] for row in plan["selected"] + plan["already_recorded"])
        if proposal["action"] == "PREPARE_PAYMENT" and not eligible:
            gate_reasons.append("PAYMENT_NOT_ELIGIBLE")
        if proposal["action"] == "PREPARE_PAYMENT" and self.service.durable.mode == "FIRESTORE_TRANSACTIONAL" and (
                not self.service.durable.get("mandates", tenant, "current")
                or not self.service.durable.get("accounts", tenant, "current")):
            gate_reasons.append("SANDBOX_SETUP_REQUIRED")
        state = "HOLD" if gate_reasons else {
            "PREPARE_PAYMENT": "READY_FOR_CONFIRMATION", "PREPARE_VERIFICATION": "PREPARED_MESSAGE",
            "EXPLAIN": "GUIDANCE_ONLY"}[proposal["action"]]
        created = _now()
        payload = {"task_id": "task_" + uuid4().hex, "tenant_id": tenant,
            "created_at": created.isoformat(), "expires_at": (created + timedelta(minutes=10)).isoformat(),
            "state": state, "proposal": proposal, "gate_reasons": gate_reasons,
            'selected_obligation': selected,
            "bill": bill, "related_evidence_sha256": sha256_hex(related),
            "mandate_sha256": sha256_hex(rules),
            "safety_evidence_version": snapshot["version"] if snapshot else None,
            "privacy_generation":generation,
            "provenance": answer["provenance"], "coverage": {
                "workspace_included": request.include_workspace,
                "provider_records_sent": min(20, len(bills)),
                "review_cases_sent": len(model_cases),
                "related_cases_checked": len(related["cases"]),
                "limits": "Safety checks cover the complete stored evidence up to 1,000 entries; excess coverage fails closed. Gemini receives at most 10 cases. No account ownership verification."}}
        record = {"payload": payload, "signature": self.service.signer.sign(payload),
                  "key_id": self.service.signer.key_id, "created_at": created.isoformat()}
        self._save(tenant, record)
        return self._public(record)

    def reconcile(self, tenant, identity):
        """Read authoritative journal only. This endpoint cannot submit a payment."""
        payload=self._record(tenant,identity)['payload']
        bill=payload.get('bill')
        if not bill:return {'state':'NO_PAYMENT_TASK','money_moved':False,'new_payment_created':False}
        goal_id='goal-bill-'+sha256_hex({'tenant':tenant,'provider':bill['provider_id'],'bill':bill['bill_reference']})[:24]
        receipt=self.service._receipt_by_identity(tenant,goal_id,{'authoritative_bill':bill})
        if not receipt:
            return {'state':'OUTCOME_UNKNOWN','money_moved':False,'new_payment_created':False,
                'message':'No matching recorded payment found. This is not proof that an external payment failed. No retry was submitted.'}
        valid=self.service.signer.verify_for_key(receipt['payload'],receipt['signature'],receipt['key_id']) and all(
            receipt['payload'].get(key)==value for key,value in {'tenant_id':tenant,'provider_id':bill['provider_id'],
                'payee_id':bill['payee_id'],'amount_minor':bill['amount_minor'],'currency':bill['currency']}.items())
        return {'state':'RECORDED_PAYMENT_VERIFIED' if valid else 'EVIDENCE_CONFLICT','money_moved':False,
            'new_payment_created':False,'receipt':receipt if valid else None,
            'message':'An existing artificial payment matches the signed journal. No new payment was created.' if valid else 'Stored receipt conflicts with this task. No action performed.'}

    def confirm(self, tenant, identity, confirmation: TaskConfirmation):
        record=self._record(tenant,identity)
        if not confirmation.confirm_sandbox_execution or sha256_hex(record["payload"])!=confirmation.expected_task_sha256:
            raise ValueError("Explicit confirmation of the displayed task is required")
        prior=self.executions.get(tenant,identity)
        if prior.get('state')=='COMPLETED' and prior.get('run_id'):
            stored=self.service.get(tenant,prior['run_id'])
            if stored.get('assurance',{}).get('state')=='VERIFIED':
                return {'run':stored,'signal':None,'read_only_replay':True,'money_moved':False}
            raise ValueError('Stored outcome could not be independently verified. No retry was submitted.')
        lease=self.executions.claim(tenant,identity,confirmation.expected_task_sha256)
        try:
            result=self._confirm_now(tenant,identity,confirmation)
            run=result.get("run") or {}
            status="COMPLETED" if run.get("status") in {"COMPLETED_SYNTHETIC","ALREADY_COMPLETED","RECONCILED_COMPLETED"} else "HELD" if run.get("status")=="HELD" else "REVIEW_REQUIRED"
            self.executions.finish(lease,status,run.get("run_id"),"Read the recorded outcome; no real bank is connected.")
            return result
        except ValueError:
            self.executions.finish(lease,"HELD",message="Checks did not permit this task. Prepare again.")
            raise
        except Exception:
            self.executions.finish(lease,"OUTCOME_UNKNOWN",message="Outcome uncertain. Review Activity before resuming; no success or failure is assumed.")
            raise

    def _confirm_now(self, tenant, identity, confirmation: TaskConfirmation):
        if not confirmation.confirm_sandbox_execution:
            raise ValueError("Explicit artificial-money confirmation is required.")
        record = self._record(tenant, identity)
        payload = record["payload"]
        if sha256_hex(payload) != confirmation.expected_task_sha256:
            raise ValueError("The displayed task does not match the saved task.")
        if _now() >= datetime.fromisoformat(payload["expires_at"]):
            raise ValueError("This task expired. Ask Friday to prepare a fresh task.")
        if payload["state"] != "READY_FOR_CONFIRMATION" or not payload["bill"]:
            raise ValueError("This task is held or read-only. No payment can be submitted.")
        if sha256_hex(self.service.mandate(tenant)["mandate"]) != payload["mandate_sha256"]:
            raise ValueError("Your rules changed. Prepare a new task.")
        snapshot = self.reviews.safety_snapshot(tenant)
        if payload.get("safety_evidence_version") != snapshot["version"]:
            raise ValueError("Financial evidence changed. Prepare a new task.")
        related = _related(snapshot["board"], payload["bill"]["bill_reference"])
        if sha256_hex(related) != payload["related_evidence_sha256"]:
            raise ValueError("Related financial evidence changed. Prepare a new task.")
        # Existing executor rechecks current provider/rules/reserve and atomically
        # enforces payment identity. A duplicate click cannot create a second debit.
        return handle_reviewed_bill(self.service, tenant, payload["bill"]["bill_reference"],
                                    payload["bill"]["bill_sha256"])

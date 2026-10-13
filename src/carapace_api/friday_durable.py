"""Optional transactional Firestore state for Friday's artificial-money sandbox."""
from __future__ import annotations

from typing import Any, Protocol
from copy import deepcopy
from hashlib import sha256

from carapace_core.friday_live import FridayMandate, TestProviderBill, bill_increase_requires_review, provider_bill_matches
from carapace_core.friday_assurance import seal_friday_run
from carapace_core.friday_evidence_snapshot import MAX_SAFETY_DOCUMENTS, expand_records


KINDS = {"mandates", "accounts", "provider_bills", "signals", "dynamic_cases", "runs", "payments", "idempotency", "reviews", "assistant_tasks", "evidence_versions", "task_executions", "privacy", "buddy_preferences"}


class FridayDurableState(Protocol):
    mode: str

    def put(self, kind: str, tenant: str, record_id: str, value: dict[str, Any]) -> None: ...
    def get(self, kind: str, tenant: str, record_id: str) -> dict[str, Any] | None: ...
    def list(self, kind: str, tenant: str, limit: int = 20) -> list[dict[str, Any]]: ...


class LocalFridayState:
    mode = "SQLITE_LOCAL"

    def put(self, kind: str, tenant: str, record_id: str, value: dict[str, Any]) -> None:
        del kind, tenant, record_id, value

    def get(self, kind: str, tenant: str, record_id: str) -> dict[str, Any] | None:
        del kind, tenant, record_id
        return None

    def list(self, kind: str, tenant: str, limit: int = 20) -> list[dict[str, Any]]:
        del kind, tenant, limit
        return []


class FirestoreFridayState:
    """Tenant-scoped authoritative state, including atomic artificial payments."""

    mode = "FIRESTORE_TRANSACTIONAL"

    def __init__(
        self,
        project: str,
        database: str = "(default)",
        collection: str = "financial_friday_v1",
        *,
        client=None,
    ) -> None:
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Firestore state")
        if not collection.replace("_", "").replace("-", "").isalnum():
            raise RuntimeError("CARAPACE_FIRESTORE_COLLECTION contains invalid characters")
        if client is None:
            try:
                from google.cloud import firestore
            except ImportError as error:
                raise RuntimeError("Install google-cloud-firestore for Firestore state") from error
            client = firestore.Client(project=project, database=database)
        self._client = client
        self._collection = collection

    @staticmethod
    def _validate(kind: str, tenant: str, record_id: str) -> None:
        if kind not in KINDS:
            raise ValueError("unsupported durable-state kind")
        if not tenant or "/" in tenant or not record_id or "/" in record_id:
            raise ValueError("invalid durable-state identity")

    def _documents(self, kind: str, tenant: str):
        return self._client.collection(self._collection).document(tenant).collection(kind)

    def put(self, kind: str, tenant: str, record_id: str, value: dict[str, Any]) -> None:
        self._validate(kind, tenant, record_id)
        if kind=='reviews':
            self.put_review(tenant,record_id,value)
            return
        self._documents(kind, tenant).document(record_id).set(value)

    def get(self, kind: str, tenant: str, record_id: str) -> dict[str, Any] | None:
        self._validate(kind, tenant, record_id)
        snapshot = self._documents(kind, tenant).document(record_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def list(self, kind: str, tenant: str, limit: int = 20) -> list[dict[str, Any]]:
        self._validate(kind, tenant, "list")
        if not 1 <= limit <= 100:
            raise ValueError("durable-state list limit is invalid")
        query = self._documents(kind, tenant)
        # Firestore defaults to document-ID order. A random run/event ID is not
        # chronology: order BEFORE limiting or the newest outcomes can disappear.
        # These fields are written when the journal record is first created;
        # payment/provider collections intentionally keep their existing order.
        time_field = {"runs": "result.started_at", "signals": "created_at", "reviews": "created_at", "assistant_tasks": "created_at"}.get(kind)
        if time_field:
            query = query.order_by(time_field, direction="DESCENDING")
        return [snapshot.to_dict() for snapshot in query.limit(limit).stream()]

    def _atomic(self, callback):
        from google.cloud import firestore
        return firestore.transactional(callback)(self._client.transaction())

    def reserve_resource(self, purpose, day, units, limit):
        if purpose not in {'ocr_pages','recovery_jobs'} or type(units) is not int or units < 1:
            raise ValueError('Invalid resource reservation')
        ref = self._client.collection('friday_resource_limits_v1').document(day+'-'+purpose)
        def commit(transaction):
            record = ref.get(transaction=transaction)
            used = record.to_dict().get('used',0) if record.exists else 0
            if used + units > limit:
                raise ValueError('Daily '+purpose.replace('_',' ')+' demo allowance reached. No additional cloud work was admitted.')
            transaction.set(ref, {'used':used+units,'limit':limit,'day':day})
            return {'used':used+units,'limit':limit,'day':day}
        return self._atomic(commit)

    def update_task_recovery(self, tenant, task_id, update):
        self._validate('task_executions', tenant, task_id)
        ref = self._documents('task_executions', tenant).document(task_id)
        def commit(transaction):
            old = ref.get(transaction=transaction)
            replacement = update(old.to_dict() if old.exists else None)
            if replacement is not None:
                transaction.set(ref, replacement)
            return replacement is not None
        return self._atomic(commit)

    def put_review(self, tenant, record_id, record):
        """Every admitted review write changes the epoch in the same transaction."""
        self._validate("reviews", tenant, record_id)
        review = self._documents("reviews", tenant).document(record_id)
        version = self._documents("evidence_versions", tenant).document("current")
        privacy=self._documents('privacy',tenant).document('current')
        def commit(transaction):
            old = review.get(transaction=transaction)
            epoch = version.get(transaction=transaction)
            policy=privacy.get(transaction=transaction)
            generation=policy.to_dict().get('generation',0) if policy.exists else 0
            if record.get('privacy_generation',generation)!=generation:
                raise ValueError('Privacy cleanup occurred during analysis. Pending input was not saved.')
            if old.exists:
                return False
            transaction.set(review, record)
            transaction.set(version, {"epoch": (epoch.to_dict().get("epoch", 0) if epoch.exists else 0) + 1})
            return True
        return self._atomic(commit)

    def save_privacy_policy(self,tenant,value):
        self._validate('privacy',tenant,'current')
        ref=self._documents('privacy',tenant).document('current')
        def commit(transaction):
            old=ref.get(transaction=transaction)
            transaction.set(ref,{**value,'generation':old.to_dict().get('generation',0) if old.exists else 0})
        self._atomic(commit)

    def put_task(self,tenant,task_id,record):
        self._validate('assistant_tasks',tenant,task_id)
        ref=self._documents('assistant_tasks',tenant).document(task_id)
        privacy=self._documents('privacy',tenant).document('current')
        def commit(transaction):
            old=privacy.get(transaction=transaction)
            if record['payload'].get('privacy_generation',0)!=(old.to_dict().get('generation',0) if old.exists else 0):
                raise ValueError('Privacy cleanup occurred during task preparation. The draft was not saved.')
            transaction.set(ref,record)
        self._atomic(commit)

    def claim_task_execution(self, tenant, task_id, record, check):
        self._validate("task_executions",tenant,task_id)
        ref=self._documents("task_executions",tenant).document(task_id)
        def commit(transaction):
            old=ref.get(transaction=transaction)
            check(old.to_dict() if old.exists else None)
            transaction.set(ref,record)
        self._atomic(commit)

    def finish_task_execution(self, tenant, task_id, record):
        self._validate("task_executions",tenant,task_id)
        ref=self._documents("task_executions",tenant).document(task_id)
        def commit(transaction):
            old=ref.get(transaction=transaction)
            if old.exists and old.to_dict()["payload"]["lease_id"]==record["payload"]["lease_id"]:
                transaction.set(ref,record)
        self._atomic(commit)

    def delete_private_inputs(self, tenant, cutoff=None):
        """Bounded batches: erase claims/drafts, never the payment journal."""
        self._validate('privacy',tenant,'current')
        privacy=self._documents('privacy',tenant).document('current')
        version=self._documents('evidence_versions',tenant).document('current')
        def barrier(transaction):
            policy=privacy.get(transaction=transaction)
            epoch=version.get(transaction=transaction)
            from uuid import uuid4
            transaction.set(privacy,{**(policy.to_dict() if policy.exists else {}),'generation':uuid4().hex})
            transaction.set(version,{'epoch':(epoch.to_dict().get('epoch',0) if epoch.exists else 0)+1})
        self._atomic(barrier)
        counts={}
        for kind,label in [('reviews','reviews'),('assistant_tasks','drafts')]:
            self._validate(kind,tenant,'delete')
            query=self._documents(kind,tenant)
            if cutoff:
                from google.cloud.firestore_v1.base_query import FieldFilter
                query=query.where(filter=FieldFilter('created_at','<',cutoff))
            total=0
            for _ in range(25):
                documents=list(query.limit(200).stream())
                if not documents:break
                version=self._documents('evidence_versions',tenant).document('current')
                def commit(transaction):
                    old=version.get(transaction=transaction)
                    privacy=self._documents('privacy',tenant).document('current')
                    policy=privacy.get(transaction=transaction)
                    for snapshot in documents:transaction.delete(snapshot.reference)
                    transaction.set(version,{'epoch':(old.to_dict().get('epoch',0) if old.exists else 0)+1})
                    from uuid import uuid4
                    transaction.set(privacy,{**(policy.to_dict() if policy.exists else {}),'generation':uuid4().hex})
                self._atomic(commit)
                total+=len(documents)
            else:raise ValueError('Cleanup reached its bound. Repeat the explicit cleanup to finish; payment journal is untouched.')
            counts[label]=total
        return counts

    def evidence_snapshot(self, tenant):
        """Never silently replace financial memory with a recent activity window."""
        self._validate("reviews", tenant, "snapshot")
        for _ in range(2):
            before = self.get("evidence_versions", tenant, "current") or {"epoch": 0}
            records = [s.to_dict() for s in self._documents("reviews", tenant).limit(MAX_SAFETY_DOCUMENTS + 1).stream()]
            after = self.get("evidence_versions", tenant, "current") or {"epoch": 0}
            if before == after:
                return {"version": str(before["epoch"]), "documents": expand_records(records), "complete": True}
        raise ValueError("Financial evidence changed during reading. Prepare again.")

    def save_mandate(self, tenant: str, mandate: dict, now: str) -> None:
        self._validate("mandates", tenant, "current")
        account = self._documents("accounts", tenant).document("current")
        instruction = self._documents("mandates", tenant).document("current")

        def commit(transaction):
            existing = account.get(transaction=transaction)
            transaction.set(instruction, {"mandate": mandate, "updated_at": now})
            if not existing.exists:
                transaction.set(account, {"balance_minor": 5_000_000, "updated_at": now})
        self._atomic(commit)

    def execute_payment(self, tenant: str, result: dict, receipt: dict, live: dict | None,
                        signer) -> dict:
        """Commit an artificial payment, balance and run together; never real funds.

        The callback can be retried by Firestore. It has no model calls, external
        payment calls or mutations to the caller's result.
        """
        payload = receipt["payload"]
        self._validate("runs", tenant, result["run_id"])
        identity = ("bill:" + live["authoritative_bill"]["provider_id"] + ":" +
                    live["authoritative_bill"]["bill_reference"]) if live else "goal:" + payload["goal_id"]
        payment = self._documents("payments", tenant).document(sha256(identity.encode()).hexdigest())
        idem = self._documents("idempotency", tenant).document(sha256(payload["idempotency_key"].encode()).hexdigest())
        account = self._documents("accounts", tenant).document("current")
        mandate = self._documents("mandates", tenant).document("current")
        run = self._documents("runs", tenant).document(result["run_id"])
        bill = self._documents("provider_bills", tenant).document(live["authoritative_bill"]["bill_reference"]) if live else None
        evidence_version = self._documents("evidence_versions", tenant).document("current")

        def commit(transaction):
            prior = payment.get(transaction=transaction)
            prior_idem = idem.get(transaction=transaction)
            balance_record = account.get(transaction=transaction)
            mandate_record = mandate.get(transaction=transaction)
            bill_record = bill.get(transaction=transaction) if bill else None
            epoch_record = evidence_version.get(transaction=transaction) if live else None
            output = deepcopy(result)
            reason = []
            balance = None
            old = prior.to_dict().get("receipt") if prior.exists else None
            if old:
                bound = all(old["payload"].get(k) == payload[k] for k in
                            ("tenant_id", "provider_id", "payee_id", "amount_minor", "currency"))
                if not bound or not signer.verify(old["payload"], old["signature"]):
                    reason = ["EXISTING_RECEIPT_INVALID"]
                else:
                    output["status"] = "ALREADY_COMPLETED"
                    output["outcome"] = {"money_moved": False, "new_payment_created": False, "receipt": old}
            elif prior_idem.exists:
                reason = ["IDEMPOTENCY_CONFLICT"]
            elif live:
                current_epoch = str(epoch_record.to_dict().get("epoch", 0) if epoch_record.exists else 0)
                if live.get("safety_evidence_version") != current_epoch:
                    reason = ["FINANCIAL_EVIDENCE_CHANGED"]
                elif not bill_record.exists or not provider_bill_matches(bill_record.to_dict(), live["authoritative_bill"]):
                    reason = ["PROVIDER_CHANGED"]
                elif not mandate_record.exists or not balance_record.exists:
                    reason = ["MANDATE_OR_ACCOUNT_MISSING"]
                else:
                    rules = mandate_record.to_dict()["mandate"]
                    balance = balance_record.to_dict()["balance_minor"] - payload["amount_minor"]
                    if rules["instruction"] != result["goal"]["instruction"] or rules["max_fee_minor"] < result["goal"]["max_fee_minor"]:
                        reason = ["MANDATE_CHANGED"]
                    elif output.get("automatic") and (not rules["automatic_sandbox_execution"] or payload["amount_minor"] > rules["automatic_payment_limit_minor"]):
                        reason = ["AUTOMATIC_PERMISSION_CHANGED"]
                    elif output.get("enforce_single_payment_limit") and payload["amount_minor"] > rules["automatic_payment_limit_minor"]:
                        reason = ["SINGLE_PAYMENT_LIMIT_CHANGED"]
                    elif bill_increase_requires_review(
                        TestProviderBill.model_validate(live["authoritative_bill"]),
                        FridayMandate.model_validate(rules).bill_increase_review_percent,
                    ):
                        reason = ["UNUSUAL_BILL_INCREASE"]
                    elif balance < rules["protected_balance_minor"]:
                        reason = ["PROTECTED_BALANCE"]
            if reason:
                output["status"] = "HELD"
                output["outcome"] = {"money_moved": False, "new_payment_created": False, "reason": reason}
            elif not old:
                output["status"] = "COMPLETED_SYNTHETIC"
                output["outcome"] = {"money_moved": True, "new_payment_created": True,
                                     "receipt": receipt, "sandbox_balance_minor": balance}
                transaction.set(payment, {"receipt": receipt})
                transaction.set(idem, {"payment_id": payment.id})
                if balance is not None:
                    transaction.set(account, {"balance_minor": balance})
            output["events"].append({"type": "RESTRICTED_EXECUTOR_RESULT", "status": output["status"],
                                     "new_payment": output["outcome"]["new_payment_created"]})
            seal_friday_run(tenant, output, signer)
            transaction.set(run, {"result": output})
            return output
        return self._atomic(commit)

    def payment_receipt(self, tenant: str, goal_id: str, live: dict | None) -> dict | None:
        self._validate("payments", tenant, "lookup")
        identity = ("bill:" + live["authoritative_bill"]["provider_id"] + ":" +
                    live["authoritative_bill"]["bill_reference"]) if live else "goal:" + goal_id
        record = self.get("payments", tenant, sha256(identity.encode()).hexdigest())
        return record.get("receipt", {}) if record is not None else None


def create_friday_durable_state(settings) -> FridayDurableState:
    mode = settings.friday_durable_store
    if mode == "sqlite":
        return LocalFridayState()
    if mode == "firestore":
        return FirestoreFridayState(
            project=settings.google_cloud_project or "",
            database=settings.firestore_database,
            collection=settings.firestore_collection,
        )
    raise RuntimeError("CARAPACE_FRIDAY_DURABLE_STORE must be 'sqlite' or 'firestore'")

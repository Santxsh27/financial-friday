"""Durable admission limits for the public artificial-money demo.

Limits count admitted requests, not tokens or dollars. Reservations are not
refunded on downstream failure: this prevents retries bypassing the allowance.
"""
from datetime import datetime, timezone
from time import sleep

from carapace_core.friday_trace import record_stage


def confirmed_transaction_abort(error):
    """Only provider ABORTED is a known uncommitted transaction.

    Firestore can wrap exhausted transaction retries in ValueError. Never infer
    an abort from text, retry an unknown timeout, or retry an admitted handler.
    """
    from google.api_core.exceptions import Aborted
    seen = set()
    for _ in range(6):
        if error is None or id(error) in seen:
            return False
        seen.add(id(error))
        if isinstance(error, Aborted):
            return True
        error = error.__cause__
    return False


class DemoLimitReached(Exception):
    pass


class FirestoreDemoQuota:
    USER_DAILY_WRITES = 20
    GLOBAL_DAILY_WRITES = 200
    USER_DAILY_READS = 1000
    GLOBAL_DAILY_READS = 10000
    USER_MINUTE_WRITES = 4
    GLOBAL_MINUTE_WRITES = 20
    USER_MINUTE_READS = 120
    GLOBAL_MINUTE_READS = 600

    def __init__(self, project, database="(default)", *, client=None, clock=None):
        if client is None:
            from google.cloud import firestore
            client = firestore.Client(project=project, database=database)
        self.client = client
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _atomic(self, callback):
        from google.cloud import firestore
        return firestore.transactional(callback)(self.client.transaction())

    def reserve(self, tenant: str, method: str) -> None:
        now = self.clock().astimezone(timezone.utc)
        day, minute = now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%dT%H:%M")
        kind = "reads" if method == "GET" else "writes"
        collection = self.client.collection("friday_public_demo_usage_v1")
        refs = [collection.document(day + "-global"), collection.document(day + "-" + tenant)]
        daily = [getattr(self, "GLOBAL_DAILY_" + kind.upper()), getattr(self, "USER_DAILY_" + kind.upper())]
        per_minute = [getattr(self, "GLOBAL_MINUTE_" + kind.upper()), getattr(self, "USER_MINUTE_" + kind.upper())]

        def commit(transaction):
            records = [ref.get(transaction=transaction) for ref in refs]
            values = [record.to_dict() if record.exists else {} for record in records]
            for index, value in enumerate(values):
                count = value.get(kind, 0)
                burst = value.get(kind + "_minute_count", 0) if value.get(kind + "_minute") == minute else 0
                if count >= daily[index] or burst >= per_minute[index]:
                    raise DemoLimitReached("Demo allowance reached. Read saved results or try again later; daily limits reset at midnight UTC.")
                value.update({kind: count + 1, kind + "_minute": minute, kind + "_minute_count": burst + 1})
            for ref, value in zip(refs, values):
                transaction.set(ref, value)
        # A hot global quota document can exhaust the SDK's transaction retry
        # budget under concurrent admission. Restart only confirmed aborts with
        # a fresh transaction. Reservations and limits remain in the same atomic
        # operation; no downstream action is retried and no allowance is reset.
        for attempt in range(3):
            try:
                return self._atomic(commit)
            except DemoLimitReached:
                record_stage('validation', ok=False, reason='quota_limit')
                raise
            except Exception as error:
                aborted = confirmed_transaction_abort(error)
                if not aborted or attempt == 2:
                    record_stage('validation', ok=False, reason='quota_conflict' if aborted else 'quota_unavailable')
                    raise
                record_stage('validation', ok=False, reason='quota_retry')
                sleep(.05 * (attempt + 1))

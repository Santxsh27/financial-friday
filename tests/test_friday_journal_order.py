"""Journal chronology contracts; no model calls, payments or live cloud writes."""
from copy import deepcopy
from unittest.mock import Mock
import unittest

from carapace_api.friday_durable import FirestoreFridayState
import test_financial_friday


class JournalQuery:
    """Small query driver exercising order-before-limit, not a cloud emulator."""

    def __init__(self, records, calls, field=None, descending=False, count=None):
        self.records, self.calls = records, calls
        self.field, self.descending, self.count = field, descending, count

    def order_by(self, field, *, direction):
        self.calls.append(("order_by", field, direction))
        return JournalQuery(self.records, self.calls, field, direction == "DESCENDING", self.count)

    def limit(self, count):
        self.calls.append(("limit", count))
        return JournalQuery(self.records, self.calls, self.field, self.descending, count)

    def stream(self):
        rows = sorted(self.records.items())
        if self.field:
            def value(record):
                for key in self.field.split("."):
                    if not isinstance(record, dict) or key not in record:
                        return None
                    record = record[key]
                return record
            rows = [(key, row) for key, row in rows if value(row) is not None]
            rows.sort(key=lambda item: value(item[1]), reverse=self.descending)
        return [Mock(to_dict=Mock(return_value=deepcopy(row))) for _, row in rows[:self.count]]


class DurableJournalOrderTests(unittest.TestCase):
    def store(self, collections):
        client = Mock()
        calls = []
        def collection(kind):
            calls.append(("collection", kind))
            return JournalQuery(collections[kind], calls)
        client.collection.return_value.document.return_value.collection.side_effect = collection
        return FirestoreFridayState("test", client=client), client, calls

    def test_recent_runs_are_ordered_before_limit_not_by_random_id(self):
        records = {"a-old": {"result": {"run_id": "a-old", "started_at": "2026-10-01T10:00:00+00:00"}},
                   "z-new": {"result": {"run_id": "z-new", "started_at": "2026-10-11T10:00:00+00:00"}}}
        store, client, calls = self.store({"runs": records})
        rows = store.list("runs", "tenant-a", 1)
        self.assertEqual(rows[0]["result"]["run_id"], "z-new")
        self.assertEqual(calls, [("collection", "runs"), ("order_by", "result.started_at", "DESCENDING"), ("limit", 1)])
        client.collection.return_value.document.assert_called_once_with("tenant-a")
        client.collection.return_value.document.return_value.collection.assert_called_once_with("runs")

    def test_recent_signals_use_creation_time_not_last_update_or_id(self):
        records = {"a-old": {"created_at": "2026-10-01T10:00:00+00:00", "state": "COMPLETED"},
                   "z-new": {"created_at": "2026-10-11T10:00:00+00:00", "state": "ATTENTION"}}
        store, _, calls = self.store({"signals": records})
        self.assertEqual(store.list("signals", "tenant-a", 1)[0]["state"], "ATTENTION")
        self.assertIn(("order_by", "created_at", "DESCENDING"), calls)

    def test_non_journal_collections_do_not_require_a_timestamp(self):
        store, _, calls = self.store({"payments": {"a": {"receipt": {"signature": "example"}}}})
        self.assertEqual(len(store.list("payments", "tenant-a", 1)), 1)
        self.assertEqual(calls, [("collection", "payments"), ("limit", 1)])

    def test_missing_timestamp_is_not_fabricated_as_recent(self):
        store, _, _ = self.store({"runs": {"a": {"result": {"run_id": "missing"}},
                                          "z": {"result": {"run_id": "valid", "started_at": "2026-10-11T10:00:00+00:00"}}}})
        self.assertEqual([r["result"]["run_id"] for r in store.list("runs", "tenant-a")], ["valid"])

    def test_tenant_identity_and_bounds_are_still_validated(self):
        store, client, _ = self.store({})
        for kind, tenant, limit in [("runs", "other/tenant", 1), ("runs", "tenant", 0),
                                    ("runs", "tenant", 101), ("unknown", "tenant", 1)]:
            with self.subTest(kind=kind, tenant=tenant, limit=limit), self.assertRaises(ValueError):
                store.list(kind, tenant, limit)
        client.collection.assert_not_called()


class LocalJournalOrderTests(unittest.TestCase):
    def setUp(self):
        self.base = test_financial_friday.FinancialFridayTests()
        self.base.setUp()

    def tearDown(self):
        self.base.tearDown()

    def test_imported_old_run_does_not_replace_newest_activity(self):
        service = self.base.service
        def record(run_id, started_at):
            return {"run_id": run_id, "started_at": started_at, "case_id": "genuine-bill", "status": "HELD"}
        service._save("tenant-a", record("new", "2026-10-11T10:00:00+00:00"))
        service._save("tenant-a", record("old-import", "2026-10-01T10:00:00+00:00"))
        service._save("tenant-b", record("other", "2026-10-12T10:00:00+00:00"))
        self.assertEqual([r["run_id"] for r in service.daily_brief("tenant-a")["recent_runs"]], ["new", "old-import"])
        self.assertEqual(self.base.payment_count(), 0)


if __name__ == "__main__":
    unittest.main()

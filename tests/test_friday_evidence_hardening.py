"""Late conflicts and old evidence cannot silently permit a new payment."""
import json
import unittest
from unittest.mock import patch
from carapace_api.friday_review import FridayReviewService
from test_friday_review import record
import test_financial_friday
import test_friday_transactions
from carapace_core.friday_live import IncomingFinancialSignal


class LocalEvidenceHardeningTests(unittest.TestCase):
    def setUp(self):
        self.base = test_financial_friday.FinancialFridayTests(); self.base.setUp()
        self.service = self.base.service
        self.review = FridayReviewService(self.service)
        self.base.publish_live_bill()

    def tearDown(self):
        self.base.tearDown()

    def save(self, identity, **changes):
        value = record(identity, reference="LIVE-1001", total="2499.00", **changes)
        with self.service.connect() as db:
            db.execute("INSERT INTO friday_reviews VALUES (?,?,?,?)",("tenant-a",identity,json.dumps(value),identity))

    def signal(self):
        return self.service.ingest_live_signal("tenant-a", IncomingFinancialSignal(
            source_type="MESSAGE",content_text="TN Power bill LIVE-1001 for ₹2,499. Payee: tnpower@upi"))

    def test_older_than_recent_window_conflict_still_blocks(self):
        self.save("000-old-conflict", payee="stranger@upi")
        for i in range(60):
            self.save(f"new-{i:03}")
        self.assertEqual(len(self.review.list("tenant-a")),50)
        self.assertEqual(len(self.review.safety_snapshot("tenant-a")["documents"]),61)
        self.assertEqual(self.signal()["state"],"ATTENTION")
        self.assertEqual(self.base.payment_count(),0)

    def test_new_conflict_after_ai_before_atomic_commit_is_held(self):
        signal = self.signal()
        original = self.service._execute
        def late_conflict(*args):
            self.save("late", payee="stranger@upi")
            return original(*args)
        with patch.object(self.service,"_execute",side_effect=late_conflict):
            result = self.service.run_live_signal("tenant-a",signal["event_id"])["run"]
        self.assertEqual(result["status"],"HELD")
        self.assertEqual(result["outcome"]["reason"],["FINANCIAL_EVIDENCE_CHANGED"])
        self.assertEqual(self.base.payment_count(),0)

    def test_over_capacity_fails_closed_not_partial_green(self):
        from carapace_core.friday_evidence_snapshot import expand_records
        with self.assertRaises(ValueError):
            expand_records([{"review_id":str(i)} for i in range(1001)])


class CloudEvidenceHardeningTests(unittest.TestCase):
    def test_transaction_reads_evidence_version_and_blocks_late_write(self):
        base = test_friday_transactions.DurableTransactionTests(); base.setUp()
        try:
            service = base.service
            original = service._execute
            def changed(*args):
                base.store.put_review("tenant-a","late", record("late",reference="LIVE-1001",payee="stranger@upi"))
                return original(*args)
            with patch.object(service,"_execute",side_effect=changed):
                outcome=service.run_live_signal("tenant-a",base.signal["event_id"])["run"]
            self.assertEqual(outcome["outcome"]["reason"],["FINANCIAL_EVIDENCE_CHANGED"])
            self.assertEqual(service.mandate("tenant-a")["sandbox_balance_minor"],5000000)
            self.assertFalse(any("payments" in path for path in base.store._client.records))
        finally:
            base.tearDown()

    def test_deduplicated_review_does_not_change_epoch(self):
        from test_friday_transactions import TransactionalMemory
        store=TransactionalMemory()
        self.assertTrue(store.put_review("one","a",record("a")))
        self.assertFalse(store.put_review("one","a",record("a")))
        self.assertEqual(store.evidence_snapshot("one")["version"],"1")
        self.assertEqual(store.evidence_snapshot("two")["documents"],[])

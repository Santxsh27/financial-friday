"""Provider abort injection; no cloud, quota bypass or handler retries."""
from unittest import TestCase
from unittest.mock import patch
from google.api_core.exceptions import Aborted, DeadlineExceeded

from carapace_api.friday_public_quota import DemoLimitReached, confirmed_transaction_abort
from test_friday_public_access import MemoryClient, MemoryQuota


class QuotaContentionTests(TestCase):
    def test_only_typed_abort_or_explicit_cause_is_retryable(self):
        wrapped = ValueError('Private provider diagnostic must not be logged')
        wrapped.__cause__ = Aborted('Synthetic contention')
        self.assertTrue(confirmed_transaction_abort(wrapped))
        self.assertFalse(confirmed_transaction_abort(ValueError('Aborted')))
        self.assertFalse(confirmed_transaction_abort(DeadlineExceeded('Unknown outcome')))
        cycle = ValueError('cycle'); cycle.__cause__ = cycle
        self.assertFalse(confirmed_transaction_abort(cycle))

    def test_confirmed_abort_restarts_fresh_admission_and_counts_once(self):
        db = MemoryClient(); quota = MemoryQuota('test', client=db)
        commit = quota._atomic
        with patch.object(quota, '_atomic') as atomic:
            # Last attempt actually executes the complete memory transaction.
            attempts = [0]
            def abort_then_commit(callback):
                attempts[0] += 1
                if attempts[0] == 1: raise Aborted('Synthetic')
                return commit(callback)
            atomic.side_effect = abort_then_commit
            with patch('carapace_api.friday_public_quota.sleep'):
                quota.reserve('test-user', 'POST')
        self.assertEqual(atomic.call_count, 2)
        self.assertEqual(len(db.store), 2)
        self.assertTrue(all(value['writes'] == 1 for value in db.store.values()))

    def test_abort_retries_are_bounded_and_never_admit_on_exhaustion(self):
        db = MemoryClient(); quota = MemoryQuota('test', client=db)
        with patch.object(quota, '_atomic', side_effect=Aborted('Synthetic')) as atomic, patch('carapace_api.friday_public_quota.sleep'):
            with self.assertRaises(Aborted): quota.reserve('test-user', 'POST')
        self.assertEqual(atomic.call_count, 3)
        self.assertEqual(db.store, {})

    def test_timeout_and_domain_limit_never_retry(self):
        for error in (DeadlineExceeded('Unknown reservation outcome'), DemoLimitReached('At limit')):
            quota = MemoryQuota('test', client=MemoryClient())
            with self.subTest(error=type(error).__name__), patch.object(quota, '_atomic', side_effect=error) as atomic:
                with self.assertRaises(type(error)): quota.reserve('test-user', 'POST')
                self.assertEqual(atomic.call_count, 1)

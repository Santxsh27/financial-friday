"""Automatic private preparation stays source-bound and grants no authority."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from carapace_core.friday_assistance import build_assistant_work
from carapace_core.friday_checkup import build_checkup, prepare_enquiry
from carapace_core.friday_portfolio import summarize_statements
import test_friday_chat_bank
import test_friday_checkup
import test_friday_refund_shield
import test_friday_transactions


def view_for(statements=None, reviewed=()):
    statements = test_friday_checkup.history() if statements is None else statements
    summary = summarize_statements(statements)
    return {'revision': 1, 'workspace_generation': 'synthetic-generation',
            'summary': summary, 'checkup': build_checkup(statements, summary, reviewed)}


class AssistanceCoreTests(unittest.TestCase):
    def test_prepares_source_linked_work_without_mutating_input(self):
        statements = test_friday_checkup.history()
        view = view_for(statements)
        before = deepcopy(view)
        work = build_assistant_work(view)
        self.assertEqual(view, before)
        self.assertEqual(work['scope'], 'FRIDAY_ASSISTANT_WORK')
        self.assertEqual(work['source_revision'], view['revision'])
        self.assertEqual(work['workspace_generation'], view['workspace_generation'])
        self.assertEqual(work['source_fingerprint'], view['checkup']['source_fingerprint'])
        self.assertEqual(work['checks_completed'], 8)
        self.assertEqual(work['transaction_count'], len(statements[0]['entries']))
        self.assertEqual((work['model_calls'], work['external_actions'], work['money_moved']), (0, 0, False))
        self.assertEqual(work['next_item'], work['items'][0])
        sources = {(s['source_sha256'], r['source_row']): r for s in statements for r in s['entries']}
        for item, finding in zip(work['items'], view['checkup']['findings']):
            self.assertEqual(item['finding_id'], finding['finding_id'])
            self.assertEqual(item['amount_minor'], finding['amount_minor'])
            self.assertEqual(item['status'], 'PREPARED_FOR_REVIEW')
            self.assertEqual(item['evidence_count'], len(item['evidence']))
            self.assertEqual(item['artifact']['format'], 'text/plain')
            self.assertRegex(item['artifact']['filename'], r'^friday-[a-z-]+\.txt$')
            for ref in item['evidence']:
                original = sources[(ref['source_sha256'], ref['source_row'])]
                for key in ('date', 'description', 'debit_minor', 'credit_minor'):
                    self.assertEqual(ref[key], original[key])
        work['items'][0]['evidence'][0]['description'] = 'Output copy changed'
        self.assertEqual(view, before)

    def test_recipes_prepare_worksheets_or_existing_grounded_unsent_enquiries(self):
        view = view_for()
        items = {item['kind']: item for item in build_assistant_work(view)['items']}
        comparison = items['REPEATED_ENTRY']['artifact']['content']
        self.assertIn('COMPARISON', comparison)
        self.assertIn('Debits currently counted: INR 198.00', comparison)
        self.assertIn('All rows remain counted', comparison)
        self.assertNotIn('Hello,', comparison)
        classification = items['UNCLEAR_CREDIT']['artifact']['content']
        self.assertIn('WORKSHEET', classification)
        self.assertIn('INR 1,800.00', classification)
        self.assertIn('remain UNCLEAR', classification)
        self.assertIn('not relabel transactions', classification)
        self.assertNotIn('Hello,', classification)
        for finding in view['checkup']['findings']:
            if finding['kind'] not in {'REPEATED_ENTRY', 'UNCLEAR_CREDIT'}:
                self.assertEqual(items[finding['kind']]['artifact']['content'], prepare_enquiry(finding))
                self.assertIn('UNSENT', items[finding['kind']]['artifact']['content'])

    def test_import_and_row_reordering_keep_work_identity_and_order(self):
        statements = test_friday_checkup.history()
        second = deepcopy(statements[0])
        second.update(source_sha256='b' * 64, account_alias='Second synthetic account')
        statements.append(second)
        before = build_assistant_work(view_for(statements))
        statements.reverse()
        for statement in statements:
            statement['entries'].reverse()
        self.assertEqual(build_assistant_work(view_for(statements)), before)

    def test_batch_cap_counts_open_prepared_and_deferred_work(self):
        statement = test_friday_checkup.history()[0]
        prototype = statement['entries'][1]
        statement['entries'] = [{**prototype, 'description': f'Synthetic purchase {i}',
                                 'source_row': i * 2 + j + 1}
                                for i in range(12) for j in range(2)]
        view = view_for([statement])
        work = build_assistant_work(view)
        self.assertEqual((work['prepared_count'], work['remaining_count'], work['open_count']), (8, 4, 12))
        self.assertEqual([item['finding_id'] for item in work['items']],
                         [f['finding_id'] for f in view['checkup']['findings'][:8]])
        reviewed = [f['finding_id'] for f in view['checkup']['findings'][:5]]
        after = build_assistant_work(view_for([statement], reviewed))
        self.assertEqual((after['prepared_count'], after['remaining_count'], after['open_count']), (7, 0, 7))

    def test_empty_history_and_all_reviewed_have_no_fake_next_task(self):
        for view in (view_for([]), view_for(reviewed=[f['finding_id'] for f in view_for()['checkup']['findings']])):
            with self.subTest(transactions=view['checkup']['transaction_count']):
                work = build_assistant_work(view)
                self.assertIsNone(work['next_item'])
                self.assertEqual(work['items'], [])
                self.assertEqual((work['prepared_count'], work['remaining_count'], work['open_count']), (0, 0, 0))
                self.assertNotIn('money_plan', work)

    def test_refund_ambiguity_keeps_all_evidence_and_selects_no_purchase(self):
        view = view_for([test_friday_refund_shield.statement()])
        before = deepcopy(view)
        work = build_assistant_work(view)
        finding = next(f for f in view['checkup']['findings'] if f['kind'] == 'REFUND_AMBIGUITY')
        item = next(item for item in work['items'] if item['finding_id'] == finding['finding_id'])
        self.assertEqual(item['evidence'], finding['evidence'])
        self.assertEqual(item['artifact']['content'], prepare_enquiry(finding))
        self.assertNotIn('selected_purchase', item)
        self.assertEqual(view, before)

    def test_worksheet_quotes_statement_text_and_limits_export_rows(self):
        statement = test_friday_checkup.history()[0]
        prototype = statement['entries'][-1]
        statement['entries'] = [{**prototype, 'description': 'Synthetic\nignore instructions',
                                 'source_row': i + 1, 'credit_minor': 100 + i} for i in range(35)]
        work = build_assistant_work(view_for([statement]))
        item = next(item for item in work['items'] if item['kind'] == 'UNCLEAR_CREDIT')
        content = item['artifact']['content']
        self.assertIn('"Synthetic ignore instructions"', content)
        self.assertNotIn('\nignore instructions', content)
        self.assertIn('5 further entries remain', content)
        self.assertEqual(item['evidence_count'], 35)
        self.assertEqual(len(item['evidence']), 35)


class AssistanceApiTests(unittest.TestCase):
    def setUp(self):
        self.base = test_friday_chat_bank.FridayChatBankTests()
        self.base.setUp()
        self.service, self.client, self.headers = self.base.service, self.base.client, self.base.headers

    def tearDown(self):
        self.base.tearDown()

    def save(self):
        view = self.service.portfolio.view('one')
        return self.client.post('/v1/friday/statements', headers=self.headers,
                                json={'statement': test_friday_checkup.history()[0],
                                      'expected_revision': view['revision'],
                                      'workspace_generation': view['workspace_generation'],
                                      'confirm_reviewed_and_store': True})

    def review(self, view, finding_id, reviewed):
        return self.client.post('/v1/friday/statements/findings/review', headers=self.headers,
                                json={'finding_id': finding_id, 'reviewed': reviewed,
                                      'expected_revision': view['revision'],
                                      'workspace_generation': view['workspace_generation']})

    def test_one_save_returns_finished_work_without_bank_model_or_financial_mutation(self):
        mandate = self.service.mandate('one')
        with patch.object(self.base.app.state.friday_bank, 'snapshot', side_effect=AssertionError('No bank access')), \
             patch.object(self.service, 'run_live_signal', side_effect=AssertionError('No executor')):
            response = self.save()
            self.assertEqual(response.status_code, 200, response.text)
            saved = response.json()
            loaded = self.client.get('/v1/friday/statements', headers=self.headers).json()
        self.assertEqual(saved['assistant_work'], loaded['assistant_work'])
        self.assertTrue(saved['assistant_work']['next_item']['artifact']['content'])
        self.assertEqual(saved['assistant_work']['source_revision'], saved['revision'])
        self.assertEqual(self.service.mandate('one'), mandate)
        self.assertIsNone(self.service.diary.record('one'))
        self.base.model.models.generate_content.assert_not_called()
        context = self.service.portfolio.model_context('one')
        self.assertNotIn('assistant_work', context)
        self.assertNotIn('artifact', context)

    def test_cleanup_cannot_relabel_old_totals_as_the_new_generation(self):
        self.save()
        old = self.service.portfolio.record('one')
        with patch('carapace_api.friday_portfolio.privacy_generation', return_value=old['generation'] + 1):
            view = self.service.portfolio.view('one', old)
        self.assertEqual(view['summary']['transaction_count'], 0)
        self.assertEqual(view['assistant_work']['items'], [])
        with patch('carapace_api.friday_portfolio.privacy_generation', side_effect=[old['generation'], old['generation'] + 1]):
            with self.assertRaisesRegex(ValueError, 'Workspace changed'):
                self.service.portfolio.view('one', old)

    def test_review_advances_next_task_and_reopen_restores_stable_identity(self):
        view = self.save().json()
        original = view['assistant_work']['next_item']
        reviewed = self.review(view, original['finding_id'], True)
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        after = reviewed.json()
        self.assertEqual(after['assistant_work']['open_count'], view['assistant_work']['open_count'] - 1)
        self.assertNotEqual(after['assistant_work']['next_item']['item_id'], original['item_id'])
        reopened = self.review(after, original['finding_id'], False)
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertEqual(reopened.json()['assistant_work']['next_item'], original)

    def test_cross_tenant_and_stale_requests_preserve_work_and_source(self):
        view = self.save().json()
        next_item = view['assistant_work']['next_item']
        path = '/v1/friday/statements/findings/review'
        payload = {'finding_id': next_item['finding_id'], 'reviewed': True,
                   'expected_revision': 0, 'workspace_generation': view['workspace_generation']}
        before = self.service.portfolio.record('one')
        self.assertEqual(self.client.post(path, headers=self.headers, json=payload).status_code, 409)
        other = {'X-Carapace-Tenant': 'two', 'X-Carapace-API-Key': 'key-two'}
        payload['expected_revision'] = view['revision']
        self.assertEqual(self.client.post(path, headers=other, json=payload).status_code, 409)
        self.assertEqual(self.client.get('/v1/friday/statements', headers=other).json()['assistant_work']['items'], [])
        self.assertEqual(self.service.portfolio.record('one'), before)
        self.assertEqual(self.service.portfolio.view('one'), view)

    def test_exclusion_and_restore_recompute_prepared_work(self):
        view = self.save().json()
        original = view['assistant_work']
        path = '/v1/friday/statements/visibility'
        payload = {'source_sha256': 'a' * 64, 'excluded': True,
                   'expected_revision': view['revision'], 'workspace_generation': view['workspace_generation']}
        response = self.client.post(path, headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        excluded = response.json()['assistant_work']
        self.assertIsNone(excluded['next_item'])
        self.assertEqual(excluded['transaction_count'], 0)
        self.assertNotEqual(excluded['source_fingerprint'], original['source_fingerprint'])
        payload.update(excluded=False, expected_revision=response.json()['revision'])
        restored = self.client.post(path, headers=self.headers, json=payload)
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(restored.json()['assistant_work']['items'], original['items'])
        self.assertEqual(restored.json()['assistant_work']['source_fingerprint'], original['source_fingerprint'])

    def test_new_supporting_evidence_rebuilds_reviewed_work_and_replay_is_idempotent(self):
        view = self.save().json()
        original = next(item for item in view['assistant_work']['items'] if item['kind'] == 'UNCLEAR_CREDIT')
        reviewed = self.review(view, original['finding_id'], True).json()
        statement = test_friday_checkup.history()[0]
        statement.update(source_sha256='b' * 64,
                         entries=[{**statement['entries'][-1], 'date': '2026-09-23',
                                   'source_row': 1, 'credit_minor': 1000}])
        payload = {'statement': statement, 'expected_revision': reviewed['revision'],
                   'workspace_generation': reviewed['workspace_generation'], 'confirm_reviewed_and_store': True}
        response = self.client.post('/v1/friday/statements', headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        changed = response.json()
        current = next(item for item in changed['assistant_work']['items'] if item['kind'] == 'UNCLEAR_CREDIT')
        self.assertNotEqual(current['item_id'], original['item_id'])
        self.assertEqual(current['evidence_count'], 2)
        self.assertEqual(current['amount_minor'], 181000)
        self.assertNotEqual(changed['assistant_work']['source_fingerprint'], view['assistant_work']['source_fingerprint'])
        replay = self.client.post('/v1/friday/statements', headers=self.headers, json=payload)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json(), changed)
        self.assertEqual(self.review(changed, original['finding_id'], True).status_code, 409)

    def test_cleanup_invalidates_work_and_prevents_old_acknowledgement(self):
        view = self.save().json()
        response = self.client.post('/v1/friday/privacy/reviews/delete', headers=self.headers,
                                    json={'confirm_delete_reviews': True})
        self.assertEqual(response.status_code, 200, response.text)
        cleared = self.service.portfolio.view('one')['assistant_work']
        self.assertEqual(cleared['items'], [])
        self.assertIsNone(cleared['next_item'])
        self.assertNotEqual(cleared['workspace_generation'], view['workspace_generation'])
        self.assertEqual(self.review(view, view['assistant_work']['next_item']['finding_id'], True).status_code, 409)

    def test_firestore_read_review_and_cleanup_use_same_derived_engine(self):
        self.service.durable = test_friday_transactions.TransactionalMemory()
        response = self.save()
        self.assertEqual(response.status_code, 200, response.text)
        view = response.json()
        self.service.durable.fail_commit = True
        from carapace_core.friday_checkup import ReviewFinding
        with self.assertRaises(RuntimeError):
            self.service.portfolio.review_finding('one', ReviewFinding(
                finding_id=view['assistant_work']['next_item']['finding_id'], reviewed=True,
                expected_revision=view['revision'], workspace_generation=view['workspace_generation']))
        self.assertEqual(self.service.portfolio.view('one'), view)
        self.service.durable.fail_commit = False
        reviewed = self.review(view, view['assistant_work']['next_item']['finding_id'], True)
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()['assistant_work']['open_count'], view['assistant_work']['open_count'] - 1)
        response = self.client.post('/v1/friday/privacy/reviews/delete', headers=self.headers,
                                    json={'confirm_delete_reviews': True})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.service.portfolio.view('one')['assistant_work']['items'], [])


if __name__ == '__main__':
    unittest.main()

"""Task outcomes and evidence boundaries, not measured real-world fraud accuracy."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from carapace_ai.financial_friday import GeminiFinancialFridayPlanner, LocalFinancialFridayPlanner
from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_core.friday_access import permitted_friday_route
from carapace_core.friday_live import TestProviderBill
from carapace_integrations.friday_obligations_ui import OBLIGATION_JS
from test_friday_review import record


class ObligationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app(Settings('test', Path(self.tmp.name)/'db', {'one':'key-one','two':'key-two'}))
        self.client = TestClient(self.app)
        self.service = self.app.state.financial_friday
        self.headers = {'X-Carapace-Tenant':'one','X-Carapace-API-Key':'key-one'}
        self.model = Mock()
        self.service.planner = GeminiFinancialFridayPlanner(self.model, 'test-model', 'VERTEX_AI')
        self.bill = TestProviderBill(bill_reference='BILL-1234', provider_name='TN Power', provider_id='tnpower',
            payee_id='tnpower@upi', amount_minor=178000, due_date='2026-10-15')

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def save(self, identity='bill', **changes):
        value = record(identity, **changes)
        value['created_at'] = datetime.now(timezone.utc).isoformat()
        with self.service.connect() as db:
            db.execute('INSERT INTO friday_reviews VALUES (?,?,?,?)', ('one', identity, json.dumps(value), value['created_at']))

    def board(self):
        response = self.client.get('/v1/friday/obligations', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def prepare(self, board, item, **changes):
        proposal = {'action':'PREPARE_PAYMENT','bill_reference':item['bill_reference'],
                    'explanation':'Prepare only the selected artificial bill; no payment has been made.',
                    'evidence_ids':['selected_obligation'], 'findings':[], 'verification_message':''}
        proposal.update(changes)
        self.model.models.generate_content.return_value = SimpleNamespace(text=json.dumps(proposal))
        return self.client.post('/v1/friday/tasks', headers=self.headers, json={
            'message':'Prepare the next safe step for this obligation.', 'include_workspace':True,
            'obligation_id':item['obligation_id'], 'expected_evidence_version':board['evidence_version']})

    def test_empty_workspace_is_not_populated_by_invented_obligations(self):
        board = self.board()
        self.assertEqual(board['items'], [])
        self.assertFalse(board['money_moved'])
        self.assertEqual(self.model.models.generate_content.call_count, 0)

    def test_own_bill_without_provider_has_useful_verification_no_payment(self):
        self.save()
        board = self.board(); item = board['items'][0]
        self.assertEqual(item['state'], 'VERIFY_PROVIDER')
        self.assertEqual(item['provider_evidence'], 'NOT_CONNECTED')
        task = self.prepare(board,item,action='PREPARE_VERIFICATION',verification_message='Please confirm the official amount, recipient and current status.').json()
        self.assertEqual(task['state'], 'PREPARED_MESSAGE')
        self.assertEqual(task['selected_obligation']['obligation_id'], item['obligation_id'])
        self.assertFalse(task['payment_authorized'])

    def test_matching_provider_still_requires_explicit_payment_confirmation(self):
        self.service.publish_test_bill('one',self.bill); self.save()
        board = self.board(); self.assertEqual(len(board['items']),1)
        item=board['items'][0]; self.assertEqual(item['state'],'READY_TO_PREPARE')
        before=self.service.mandate('one')['sandbox_balance_minor']
        task=self.prepare(board,item).json()
        self.assertEqual(task['state'],'READY_FOR_CONFIRMATION')
        self.assertEqual(self.service.mandate('one')['sandbox_balance_minor'],before)
        content=json.loads(self.model.models.generate_content.call_args.kwargs['contents'])
        self.assertIn('saved_rules',[s['source_id'] for s in content['sources']])
        self.service.planner=LocalFinancialFridayPlanner()
        response=self.client.post('/v1/friday/tasks/'+task['task_id']+'/confirm',headers=self.headers,json={
            'expected_task_sha256':task['task_sha256'],'confirm_sandbox_execution':True})
        self.assertEqual(response.status_code,200,response.text)
        after=self.board()['items'][0]
        self.assertEqual(after['state'],'RECORDED_COMPLETE')
        self.assertEqual(after['action'],'CHECK_RECORDED_RESULT')
        self.assertFalse(after['external_settlement_verified'])
        count=self.model.models.generate_content.call_count
        result=self.client.get('/v1/friday/obligations/'+after['obligation_id']+'/result',headers=self.headers).json()
        self.assertEqual(result['state'],'RECORDED_PAYMENT_VERIFIED')
        self.assertFalse(result['new_payment_created'])
        self.assertEqual(self.model.models.generate_content.call_count,count)
        self.assertEqual(self.service.mandate('one')['sandbox_balance_minor'],before-self.bill.amount_minor)

    def test_wrong_supplier_with_copied_reference_never_matches_provider(self):
        self.service.publish_test_bill('one',self.bill); self.save(supplier='Impersonator')
        board=self.board()
        claim=next(i for i in board['items'] if i['source_case_id'])
        self.assertIsNone(claim['bill_reference'])
        self.assertEqual(claim['provider_evidence'],'NOT_CONNECTED')
        response=self.prepare(board,claim,bill_reference='BILL-1234')
        self.assertEqual(response.status_code,409,response.text)

    def test_provider_amount_disagreement_is_conflict_not_confirmed_fraud(self):
        self.service.publish_test_bill('one',self.bill);self.save(total='9000.00')
        board=self.board();item=board['items'][0]
        self.assertEqual(item['state'],'DETAILS_CONFLICT')
        self.assertIn('PROVIDER_CLAIM_CONFLICT',item['checks'])
        self.assertIn('partial payment',item['why'])
        self.assertEqual(self.prepare(board,item).json()['state'],'HOLD')

    def test_matching_uploaded_receipt_is_not_recorded_completion(self):
        self.save();self.save('receipt',document_kind='RECEIPT',transaction_reference='TX1')
        item=self.board()['items'][0]
        self.assertEqual(item['state'],'VERIFY_STATUS')
        self.assertFalse(item['external_settlement_verified'])

    def test_unknown_currency_and_missing_identity_require_more_details(self):
        self.save(supplier=None,reference=None,currency='UNKNOWN',currency_label='$',document_kind='UNKNOWN',quotes=[])
        item=self.board()['items'][0]
        self.assertEqual(item['state'],'NEEDS_DETAILS')
        self.assertEqual(item['action'],'ADD_DETAILS')

    def test_model_cannot_substitute_another_real_workspace_bill(self):
        self.service.publish_test_bill('one',self.bill)
        self.service.publish_test_bill('one',self.bill.model_copy(update={'bill_reference':'BILL-5678'}))
        board=self.board();item=next(i for i in board['items'] if i['bill_reference']=='BILL-1234')
        response=self.prepare(board,item,bill_reference='BILL-5678')
        self.assertEqual(response.status_code,409,response.text)
        contents=self.model.models.generate_content.call_args.kwargs['contents']
        self.assertNotIn('BILL-5678',contents)

    def test_selection_outside_first_twenty_bills_includes_exact_record(self):
        for index in range(25):
            self.service.publish_test_bill('one',self.bill.model_copy(update={'bill_reference':f'BILL-{index:04d}'}))
        board=self.board();item=next(i for i in board['items'] if i['bill_reference']=='BILL-0024')
        response=self.prepare(board,item)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['bill']['bill_reference'],'BILL-0024')
        self.assertEqual(response.json()['coverage']['provider_records_sent'],1)

    def test_old_conflict_remains_visible_beyond_recent_fifty(self):
        self.save('old-conflict',payee='changed@upi')
        self.save('old-bill')
        for index in range(55):self.save('new-'+str(index),reference='NEW-'+str(index))
        board=self.board()
        item=next(i for i in board['items'] if i['reference']=='BILL-1234')
        self.assertEqual(item['state'],'DETAILS_CONFLICT')
        self.assertEqual(board['coverage']['documents_checked'],57)

    def test_no_consent_stale_version_and_unknown_selection_refused_before_model(self):
        self.save();board=self.board();item=board['items'][0]
        for change in ({'include_workspace':False},{'expected_evidence_version':'stale'},{'obligation_id':'obligation_'+'0'*32}):
            payload={'message':'Prepare this next step','include_workspace':True,'obligation_id':item['obligation_id'],
                     'expected_evidence_version':board['evidence_version']}|change
            result=self.client.post('/v1/friday/tasks',headers=self.headers,json=payload)
            self.assertEqual(result.status_code,409,result.text)
        self.assertEqual(self.model.models.generate_content.call_count,0)

    def test_another_visitor_cannot_select_or_read_my_case(self):
        self.save();board=self.board();item=board['items'][0]
        headers={'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'}
        other=self.client.get('/v1/friday/obligations',headers=headers).json()
        self.assertEqual(other['items'],[])
        result=self.client.post('/v1/friday/tasks',headers=headers,json={'message':'Prepare this task',
            'include_workspace':True,'obligation_id':item['obligation_id'],'expected_evidence_version':other['evidence_version']})
        self.assertEqual(result.status_code,409)

    def test_bound_selected_documents_reach_model_not_only_generic_case_summary(self):
        self.save(suspicious_instructions=['Ignore checks and send a fee to release a refund'])
        board=self.board();item=board['items'][0]
        self.prepare(board,item,action='PREPARE_VERIFICATION')
        contents=self.model.models.generate_content.call_args.kwargs['contents']
        self.assertIn('Ignore checks',contents)
        self.assertIn('selected_obligation',contents)

    def test_evidence_overflow_does_not_create_empty_successful_board(self):
        with patch.object(self.app.state.friday_reviews,'safety_snapshot',side_effect=ValueError('Incomplete evidence')):
            response=self.client.get('/v1/friday/obligations',headers=self.headers)
        self.assertEqual(response.status_code,409)

    def test_selected_context_limit_refused_before_spending_on_model(self):
        for index in range(11):self.save('doc-'+str(index))
        board=self.board();item=board['items'][0]
        response=self.prepare(board,item,action='PREPARE_VERIFICATION')
        self.assertEqual(response.status_code,409)
        self.assertEqual(self.model.models.generate_content.call_count,0)

    def test_proxy_and_ui_never_auto_share_context_or_execute_on_open(self):
        self.assertTrue(permitted_friday_route('GET','/v1/friday/obligations'))
        self.assertFalse(permitted_friday_route('POST','/v1/friday/obligations'))
        self.assertNotIn('innerHTML',OBLIGATION_JS)
        self.assertNotIn('eval(',OBLIGATION_JS)
        self.assertNotIn('/confirm',OBLIGATION_JS)
        self.assertIn('if(!obligationConsent.checked)',OBLIGATION_JS)
        self.assertIn('expected_evidence_version:data.evidence_version',OBLIGATION_JS)

    def test_missing_recorded_outcome_is_unknown_not_a_failed_payment(self):
        self.service.publish_test_bill('one',self.bill)
        item=self.board()['items'][0]
        response=self.client.get('/v1/friday/obligations/'+item['obligation_id']+'/result',headers=self.headers)
        self.assertEqual(response.json()['state'],'OUTCOME_UNKNOWN')
        self.assertFalse(response.json()['new_payment_created'])
        other={'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'}
        self.assertEqual(self.client.get('/v1/friday/obligations/'+item['obligation_id']+'/result',headers=other).status_code,404)
        self.assertTrue(permitted_friday_route('GET','/v1/friday/obligations/'+item['obligation_id']+'/result'))

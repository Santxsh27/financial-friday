import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import test_friday_chat_bank
from test_friday_review import facts
from test_friday_transactions import TransactionalMemory
from carapace_api.friday_followups import FollowupRequest
from carapace_core.friday_access import permitted_friday_route


class FollowupTests(unittest.TestCase):
    def setUp(self):
        self.base = test_friday_chat_bank.FridayChatBankTests(); self.base.setUp()
        self.service = self.base.service
        self.client, self.headers = self.base.client, self.base.headers
        self.store = self.service.followups
        self.add()

    def tearDown(self): self.base.tearDown()

    def add(self, **changes):
        value = facts(**changes)
        self.base.model.models.generate_content.return_value = SimpleNamespace(text=value.model_dump_json())
        # Unique supplied text, with quotations grounded in the input.
        text = ' '.join(q.quote for q in value.quotes) + ' ' + str(changes)
        response = self.client.post('/v1/friday/reviews', headers=self.headers, json={'text':text})
        self.assertEqual(response.status_code, 200, response.text)

    def board(self): return self.client.get('/v1/friday/obligations', headers=self.headers).json()

    def item(self): return next(item for item in self.board()['items'] if item['source_case_id'])

    def update(self, action='TRACK', **changes):
        board = self.board(); item = next(item for item in board['items'] if item['source_case_id'])
        payload = dict(action=action, expected_revision=item['followup']['revision'], expected_evidence_version=board['evidence_version'])
        payload.update(changes)
        return self.client.post('/v1/friday/obligations/'+item['obligation_id']+'/followup', headers=self.headers, json=payload)

    def test_tracking_persists_without_model_payment_or_external_message(self):
        before = self.service.mandate('one')
        self.base.model.models.generate_content.reset_mock()
        with patch.object(self.service, 'run_live_signal', side_effect=AssertionError('No executor')):
            response = self.update()
        self.assertEqual(response.status_code, 200, response.text)
        for field in ('money_moved','payment_authorized','payment_verified','external_message_sent','ai_called'):
            self.assertIs(response.json()[field], False)
        self.assertEqual(self.item()['followup']['state'], 'TRACKING')
        self.assertEqual(self.item()['followup']['revision'], 1)
        self.assertEqual(self.service.mandate('one'), before)
        self.base.model.models.generate_content.assert_not_called()

    def test_wait_close_reopen_never_clear_financial_checks(self):
        self.add(payee='someoneelse@upi')
        original = self.item()
        self.update(); self.assertEqual(self.update('WAIT_FOR_PROVIDER').status_code, 200)
        self.assertEqual(self.item()['followup']['state'], 'WAITING_FOR_PROVIDER')
        self.assertEqual(self.update('CLOSE_TRACKING').status_code, 200)
        closed = self.item()
        self.assertEqual(closed['followup']['state'], 'CLOSED')
        self.assertEqual(closed['checks'], original['checks'])
        self.assertEqual(closed['state'], original['state'])
        self.assertFalse(closed['followup']['payment_verified'])
        self.update('TRACK'); self.assertEqual(self.item()['followup']['state'], 'TRACKING')

    def test_new_evidence_surfaces_even_after_closing(self):
        identity = self.item()['obligation_id']
        self.update(); self.update('CLOSE_TRACKING'); self.add(payee='newpayee@upi')
        item = self.item(); self.assertEqual(item['obligation_id'], identity)
        self.assertEqual(item['followup']['state'], 'NEW_EVIDENCE')
        self.assertEqual(item['followup']['saved_state'], 'CLOSED')
        self.assertEqual(self.update('RECHECK').status_code, 200)
        self.assertEqual(self.item()['followup']['state'], 'TRACKING')
        self.assertEqual(self.item()['state'], 'DETAILS_CONFLICT')

    def test_unrelated_upload_does_not_reopen_this_followup(self):
        identity = self.item()['obligation_id']; self.update(); self.update('CLOSE_TRACKING')
        self.add(supplier='Other Company', reference='OTHER-1234')
        item = next(item for item in self.board()['items'] if item['obligation_id'] == identity)
        self.assertEqual(item['followup']['state'], 'CLOSED')

    def test_stale_evidence_and_revision_are_rejected(self):
        version = self.board()['evidence_version']; self.update()
        self.assertEqual(self.update('WAIT_FOR_PROVIDER', expected_revision=0).status_code, 409)
        self.add(total='1790.00')
        self.assertEqual(self.update('RECHECK', expected_evidence_version=version).status_code, 409)

    def test_wait_or_close_cannot_create_tracking(self):
        for action in ('WAIT_FOR_PROVIDER','RECHECK','CLOSE_TRACKING'):
            self.assertEqual(self.update(action).status_code, 409)

    def test_authentication_tenant_and_provider_example_boundaries(self):
        item = self.item(); path = '/v1/friday/obligations/'+item['obligation_id']+'/followup'
        payload = dict(action='TRACK', expected_revision=0, expected_evidence_version=self.board()['evidence_version'])
        self.assertEqual(self.client.post(path, json=payload).status_code, 401)
        other = {'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'}
        other_board = self.client.get('/v1/friday/obligations',headers=other).json()
        payload['expected_evidence_version'] = other_board['evidence_version']
        self.assertEqual(self.client.post(path,headers=other,json=payload).status_code,404)
        from carapace_core.friday_live import TestProviderBill
        self.service.publish_test_bill('one',TestProviderBill(bill_reference='DEMO-1234',provider_name='Example',provider_id='example',payee_id='example@upi',amount_minor=10000,due_date='2026-10-15'))
        example = next(item for item in self.board()['items'] if not item['source_case_id'])
        payload['expected_evidence_version'] = self.board()['evidence_version']
        self.assertEqual(self.client.post('/v1/friday/obligations/'+example['obligation_id']+'/followup',headers=self.headers,json=payload).status_code,404)

    def test_strict_payload_cannot_grant_authority(self):
        for extra in ({'action':'PAY'},{'expected_revision':True},{'expected_revision':'0'}, {'payment_verified':True}, {'bank_account':'secret'}):
            self.assertEqual(self.update(**extra).status_code, 422)

    def test_privacy_cleanup_removes_tracking_and_does_not_remove_journal(self):
        self.update()
        response = self.client.post('/v1/friday/privacy/reviews/delete',headers=self.headers,json={'confirm_delete_reviews':True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['deleted']['followups'],1)
        self.assertTrue(response.json()['payment_journal_retained'])
        self.assertEqual(self.store.records('one'),{})

    def test_cleanup_during_save_cannot_resurrect_tracking(self):
        board = self.board(); identity = self.item()['obligation_id']
        def delayed(*args):
            self.client.post('/v1/friday/privacy/reviews/delete',headers=self.headers,json={'confirm_delete_reviews':True})
            return board
        with patch('carapace_api.friday_obligations.financial_obligations',side_effect=delayed):
            with self.assertRaisesRegex(ValueError,'Privacy cleanup'):
                self.store.update('one',self.base.app.state.friday_reviews,identity,FollowupRequest(action='TRACK',expected_revision=0,expected_evidence_version=board['evidence_version']))
        self.assertEqual(self.store.records('one'),{})

    def test_firestore_real_transaction_callback_persists_and_checks_generation(self):
        memory = TransactionalMemory(); self.service.durable = memory
        value = memory.update_followups('one',0,lambda old:{'privacy_generation':0,'items':{'test':{'state':'TRACKING'}}})
        self.assertEqual(self.store.records('one'),value['items'])
        memory.put('privacy','one','current',{'generation':'deleted'})
        with self.assertRaisesRegex(ValueError,'Privacy cleanup'):
            memory.update_followups('one',0,lambda old:{'items':{}})
        self.assertEqual(self.store.records('one'),{})
        response = memory.delete_private_inputs('one')
        self.assertEqual(response['followups'],1)
        self.assertIsNone(memory.get('followups','one','current'))

    def test_firestore_abort_does_not_commit(self):
        memory=TransactionalMemory(); memory.fail_commit=True
        with self.assertRaises(RuntimeError):memory.update_followups('one',0,lambda old:{'privacy_generation':0,'items':{'test':{}}})
        self.assertIsNone(memory.get('followups','one','current'))

    def test_routes_and_interface_have_explicit_boundaries(self):
        path='/v1/friday/obligations/'+self.item()['obligation_id']+'/followup'
        self.assertTrue(permitted_friday_route('POST',path))
        self.assertFalse(permitted_friday_route('PUT',path))
        from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
        for text in ('Keep track of this','Recheck evidence','Close follow-up','NEW_EVIDENCE','FOLLOWUP_BOOKKEEPING_ONLY'):
            self.assertIn(text,FINANCIAL_FRIDAY_HTML)

    def test_concurrent_updates_cannot_silently_overwrite_each_other(self):
        from concurrent.futures import ThreadPoolExecutor
        board=self.board(); identity=self.item()['obligation_id']
        request=FollowupRequest(action='TRACK',expected_revision=0,expected_evidence_version=board['evidence_version'])
        def save(_):
            try:self.store.update('one',self.base.app.state.friday_reviews,identity,request);return 'saved'
            except ValueError:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(save,range(2)))
        self.assertEqual(sorted(results),['conflict','saved'])
        self.assertEqual(self.item()['followup']['revision'],1)

    def test_cleanup_age_change_does_not_delete_tracking(self):
        self.update()
        response=self.client.put('/v1/friday/privacy',headers=self.headers,json={'retention_days':30})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.item()['followup']['state'],'TRACKING')

    def test_tracking_is_bounded(self):
        self.store.MAX_ITEMS=1; self.update(); self.add(supplier='Other company',reference='OTHER-1234')
        board=self.board(); item=next(item for item in board['items'] if item['supplier']=='Other company')
        result=self.client.post('/v1/friday/obligations/'+item['obligation_id']+'/followup',headers=self.headers,json={'action':'TRACK','expected_revision':0,'expected_evidence_version':board['evidence_version']})
        self.assertEqual(result.status_code,409,result.text)

    def test_local_gateway_validates_json_and_fixed_path(self):
        import importlib
        from fastapi.testclient import TestClient
        with patch.dict('os.environ',{'CARAPACE_DEMO_ENABLED':'true'}):
            web=importlib.import_module('carapace_integrations.anthos_web')
            client=TestClient(web.create_demo_app()); path='/api/friday/obligations/'+self.item()['obligation_id']+'/followup'
            body={'action':'TRACK','expected_revision':0,'expected_evidence_version':'version'}
            with patch.object(web,'_api_call',return_value=(200,{'scope':'FOLLOWUP_BOOKKEEPING_ONLY'})) as transport:
                response=client.post(path,json=body)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(transport.call_args.args[2:4],('POST',body))
            self.assertEqual(client.post(path,json=body|{'action':'PAY'}).status_code,422)
            self.assertEqual(client.post('/api/friday/obligations/not-an-id/followup',json=body).status_code,422)
            client.close()


if __name__ == '__main__': unittest.main()

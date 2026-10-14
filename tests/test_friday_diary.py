import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from types import SimpleNamespace
from uuid import uuid4
from pydantic import ValidationError
import test_friday_chat_bank
from test_friday_transactions import TransactionalMemory
from carapace_core.friday_diary import DiaryChange
from carapace_core.friday_access import permitted_friday_route
from carapace_integrations.friday_diary_ui import DIARY_JS, DIARY_CSS


class DiaryTests(unittest.TestCase):
    def setUp(self):
        self.base = test_friday_chat_bank.FridayChatBankTests(); self.base.setUp()
        self.service,self.client,self.headers = self.base.service,self.base.client,self.base.headers

    def tearDown(self): self.base.tearDown()

    def change(self, action='START', **fields):
        view = self.service.diary.view('one')
        body = {'operation_id':uuid4().hex,'expected_revision':view['revision'],
            'workspace_generation':view['workspace_generation'],'action':action,'confirm_store':True}
        if action=='START': body.update(opening_cash_minor=800000,buffer_minor=200000)
        if action=='ADD': body['entries']=[{'direction':'OUT','amount_minor':25000,'date':date.today().isoformat(),'label':'Groceries'}]
        body.update(fields)
        return body

    def post(self, body): return self.client.post('/v1/friday/diary',headers=self.headers,json=body)

    def start(self):
        result=self.post(self.change()); self.assertEqual(result.status_code,200,result.text); return result.json()

    def model(self, **body):
        self.base.model.models.generate_content.return_value=SimpleNamespace(text=json.dumps(body))

    def test_empty_is_unknown_and_not_a_sample_balance(self):
        result=self.client.get('/v1/friday/diary',headers=self.headers).json()
        self.assertIsNone(result['summary']); self.assertEqual(result['revision'],0)
        self.assertFalse(result['bank_connected']); self.base.model.models.generate_content.assert_not_called()

    def test_start_add_exact_summary_and_no_bank_money_or_model_calls(self):
        before=self.service.mandate('one'); self.start()
        result=self.post(self.change('ADD')).json()
        self.assertEqual(result['summary']['reported_cash_minor'],775000)
        self.assertEqual(result['summary']['money_out_minor'],25000)
        self.assertEqual(result['summary']['buffer_coverage_percent'],100)
        self.assertFalse(result['payment_authorized']);self.assertEqual(self.service.mandate('one'),before)
        self.base.model.models.generate_content.assert_not_called()

    def test_negative_cash_and_low_buffer_are_not_hidden_by_clamping(self):
        self.start(); result=self.post(self.change('ADD',entries=[{'direction':'OUT','amount_minor':900000,'date':date.today().isoformat(),'label':'Rent'}])).json()
        self.assertEqual(result['summary']['reported_cash_minor'],-100000)
        self.assertEqual(result['summary']['buffer_gap_minor'],300000)
        self.assertEqual(result['summary']['status'],'REPORTED_SHORTFALL')
        self.assertEqual(result['summary']['buffer_coverage_percent'],0)

    def test_same_operation_replays_once_and_changed_payload_fails(self):
        self.start(); body=self.change('ADD'); one=self.post(body); two=self.post(body)
        self.assertEqual(one.json()['revision'],two.json()['revision']);self.assertEqual(len(two.json()['entries']),1)
        body['entries'][0]['amount_minor']=30000
        self.assertEqual(self.post(body).status_code,409)

    def test_stale_tabs_do_not_overwrite_and_start_cannot_reset(self):
        self.start(); a=self.change('ADD'); b=self.change('ADD')
        self.assertEqual(self.post(a).status_code,200);self.assertEqual(self.post(b).status_code,409)
        self.assertEqual(self.post(self.change()).status_code,409)

    def test_undo_is_reversible_bookkeeping_not_a_payment_reversal(self):
        self.start(); a=self.change('ADD');self.post(a)
        result=self.post(self.change('UNDO',undo_operation_id=a['operation_id'])).json()
        self.assertEqual(result['summary']['reported_cash_minor'],800000)
        self.assertTrue(result['entries'][0]['undone']);self.assertFalse(result['money_moved'])
        self.assertEqual(self.post(self.change('UNDO',undo_operation_id=a['operation_id'])).status_code,409)

    def test_cleanup_erases_diary_and_rejects_pre_cleanup_write(self):
        self.start(); stale=self.change('ADD')
        response=self.client.post('/v1/friday/privacy/reviews/delete',headers=self.headers,json={'confirm_delete_reviews':True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['deleted']['diary'],1)
        self.assertIsNone(self.service.diary.view('one')['summary'])
        self.assertEqual(self.post(stale).status_code,409)

    def test_private_tenant_and_authentication_boundaries(self):
        self.start();other={'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'}
        self.assertIsNone(self.client.get('/v1/friday/diary',headers=other).json()['summary'])
        self.assertEqual(self.client.get('/v1/friday/diary').status_code,401)
        for method,path in [('GET','diary'),('POST','diary'),('POST','diary/prepare')]:
            self.assertTrue(permitted_friday_route(method,'/v1/friday/'+path))
        self.assertFalse(permitted_friday_route('POST','/v1/friday/diary/execute'))

    def test_schema_rejects_implicit_consent_float_future_and_extra_authority(self):
        for update in [{'confirm_store':False},{'confirm_store':'true'},{'opening_cash_minor':1.5},
            {'buffer_minor':0},{'payment_authorized':True},{'expected_revision':True}]:
            with self.subTest(update=update),self.assertRaises(ValidationError):DiaryChange.model_validate(self.change(**update))
        self.start();future=(date.today()+timedelta(days=2)).isoformat()
        self.assertEqual(self.post(self.change('ADD',entries=[{'direction':'IN','amount_minor':100,'date':future,'label':'Salary'}])).status_code,409)

    def test_gemini_proposal_requires_consent_and_does_not_save(self):
        self.model(entries=[{'direction':'OUT','amount_text':'250','source_id':'entry-0','label':'Groceries'}],clarification='')
        body={'text':'Spent ₹250 on groceries','confirm_cloud_processing':True}
        result=self.client.post('/v1/friday/diary/prepare',headers=self.headers,json=body)
        self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['entries'][0]['amount_minor'],25000)
        self.assertFalse(result.json()['saved']);self.assertIsNone(self.service.diary.record('one'))
        config=self.base.model.models.generate_content.call_args.kwargs['config'];self.assertFalse(config.tools)
        body['confirm_cloud_processing']=False
        self.assertEqual(self.client.post('/v1/friday/diary/prepare',headers=self.headers,json=body).status_code,422)

    def test_model_unanchored_amount_direction_and_authority_rejected(self):
        for changes in [{'amount_text':'999'},{'source_id':'entry-9'},{'direction':'IN'},{'amount_text':'2,50'},{'save':True}]:
            item={'direction':'OUT','amount_text':'250','source_id':'entry-0','label':'Groceries'};item.update(changes)
            self.model(entries=[item],clarification='')
            response=self.client.post('/v1/friday/diary/prepare',headers=self.headers,json={'text':'Spent ₹250 on groceries','confirm_cloud_processing':True})
            self.assertEqual(response.status_code,503,response.text)

    def test_local_fallback_is_manual_not_fake_gemini(self):
        from carapace_ai.financial_friday import LocalFinancialFridayPlanner
        self.service.planner=LocalFinancialFridayPlanner()
        self.assertEqual(self.client.post('/v1/friday/diary/prepare',headers=self.headers,json={'text':'Spent ₹250','confirm_cloud_processing':True}).status_code,503)
        self.start();self.assertEqual(self.post(self.change('ADD')).status_code,200)

    def test_chat_has_separate_aggregate_consent_no_entry_notes_and_exact_rupees(self):
        self.start();self.post(self.change('ADD'));self.base.answer(reply='Your reported cash is INR 7,750.00.',evidence_ids=['diary:current'])
        response=self.base.chat(include_diary=True);self.assertEqual(response.status_code,200,response.text)
        context=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(context['money_diary']['reported_cash_inr'],'INR 7,750.00')
        self.assertNotIn('Groceries',json.dumps(context));self.assertEqual(context['cashflow_scenario'],{})
        self.base.answer();self.base.chat(include_workspace=True)
        self.assertEqual(json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])['money_diary'],{})
        self.base.answer(reply='You have INR 999,999.00.',evidence_ids=['diary:current'])
        self.assertEqual(self.base.chat(include_diary=True).status_code,503)

    def test_firestore_retried_callback_and_stale_concurrent_writer(self):
        self.service.durable=TransactionalMemory();self.start();a=self.change('ADD');b=self.change('ADD')
        def save(body):
            try: return self.service.diary.change('one',DiaryChange.model_validate(body))['revision']
            except ValueError: return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool: result=list(pool.map(save,[a,b]))
        self.assertEqual(result.count('conflict'),1);self.assertEqual(len(self.service.diary.view('one')['entries']),1)
        self.assertEqual(save(a) if result[0]!='conflict' else save(b),2)

    def test_firestore_failed_commit_leaves_no_diary(self):
        self.service.durable=TransactionalMemory();self.service.durable.fail_commit=True
        with self.assertRaises(RuntimeError):self.service.diary.change('one',DiaryChange.model_validate(self.change()))
        self.assertIsNone(self.service.diary.record('one'))

    def test_ui_confirm_preview_reduced_motion_and_no_financial_execution(self):
        self.assertIn('Confirm & save privately',DIARY_JS);self.assertIn('UNSAVED_DIARY_PROPOSAL',DIARY_JS)
        self.assertIn('pendingWrite',DIARY_JS);self.assertIn('friday:cashflow-cleared',DIARY_JS)
        self.assertIn('generation',DIARY_JS);self.assertNotIn('innerHTML',DIARY_JS)
        self.assertNotIn('confirm_sandbox_execution',DIARY_JS);self.assertNotIn('/confirm',DIARY_JS)
        self.assertIn('prefers-reduced-motion',DIARY_CSS);self.assertIn('document.hidden',DIARY_JS)
        self.assertIn('data-settled=true',DIARY_CSS)

    def test_mixed_entries_and_buffer_percentage_use_integer_arithmetic(self):
        self.post(self.change(opening_cash_minor=10000,buffer_minor=20000))
        entries=[{'direction':'IN','amount_minor':3333,'date':date.today().isoformat(),'label':'Received'},
                 {'direction':'OUT','amount_minor':1111,'date':date.today().isoformat(),'label':'Spent'}]
        data=self.post(self.change('ADD',entries=entries)).json()['summary']
        self.assertEqual(data['reported_cash_minor'],12222)
        self.assertEqual(data['buffer_coverage_percent'],61)
        self.assertEqual(data['net_change_minor'],2222)

    def test_capacity_is_explicit_and_never_discards_prior_entries(self):
        self.start()
        group=[{'direction':'OUT','amount_minor':1,'date':date.today().isoformat(),'label':'Reported'}]*5
        for _ in range(20):self.assertEqual(self.post(self.change('ADD',entries=group)).status_code,200)
        self.assertEqual(self.post(self.change('ADD')).status_code,409)
        self.assertEqual(len(self.service.diary.view('one')['entries']),100)

    def test_foreign_currency_future_reports_and_unsupported_dates_do_not_call_model(self):
        for text in ['Spent $250 yesterday','Received INR 1 lakh','Expected ₹1000 tomorrow']:
            response=self.client.post('/v1/friday/diary/prepare',headers=self.headers,json={'text':text,'confirm_cloud_processing':True})
            self.assertEqual(response.status_code,503)
        self.base.model.models.generate_content.assert_not_called()

    def test_firestore_privacy_barrier_rejects_old_generation(self):
        self.service.durable=TransactionalMemory();self.start();body=self.change('ADD')
        self.service.durable.put('privacy','one','current',{'generation':'cleared'})
        self.assertIsNone(self.service.diary.view('one')['summary'])
        self.assertEqual(self.post(body).status_code,409)

    def test_amount_grouping_is_formatting_not_currency_or_unit_conversion(self):
        self.model(entries=[{'direction':'IN','amount_text':'1000','source_id':'entry-0','label':'Received'}],clarification='')
        response=self.client.post('/v1/friday/diary/prepare',headers=self.headers,json={'text':'Received ₹1,000 today','confirm_cloud_processing':True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['entries'][0]['amount_minor'],100000)

    def test_rejection_diagnostics_never_log_source_text_or_provider_message(self):
        from carapace_ai.friday_diary import diagnose_diary_error
        with self.assertLogs('carapace_ai.friday_observability',level='WARNING') as logs:
            diagnose_diary_error(ValueError('Entry amount is not in its source quote'))
            diagnose_diary_error(RuntimeError('PRIVATE secret provider message'))
        self.assertIn('AMOUNT_ANCHOR',str(logs.output));self.assertNotIn('PRIVATE',str(logs.output))

    def test_server_attaches_canonical_quotes_without_splitting_decimal_amounts(self):
        self.model(entries=[{'direction':'OUT','amount_text':'250.50','source_id':'entry-0','label':'Groceries'},
            {'direction':'IN','amount_text':'1000','source_id':'entry-1','label':'Received'}],clarification='')
        response=self.client.post('/v1/friday/diary/prepare',headers=self.headers,json={
            'text':'Spent ₹250.50 on groceries. Received ₹1,000 today.','confirm_cloud_processing':True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['entries'][0]['source_quote'],'Spent ₹250.50 on groceries')
        self.assertEqual(response.json()['entries'][1]['source_quote'],'Received ₹1,000 today')
        context=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(len(context['source_units']),2)

    def test_duplicate_source_selection_and_ai_written_quote_are_rejected(self):
        item={'direction':'OUT','amount_text':'250','source_id':'entry-0','label':'Groceries'}
        for entries in [[item,item],[{**item,'source_quote':'AI invented text'}]]:
            self.model(entries=entries,clarification='')
            response=self.client.post('/v1/friday/diary/prepare',headers=self.headers,json={'text':'Spent ₹250 on groceries','confirm_cloud_processing':True})
            self.assertEqual(response.status_code,503,response.text)

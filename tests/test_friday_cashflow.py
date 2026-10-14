import json
import random
import unittest
from datetime import date, timedelta
from unittest.mock import patch
from pydantic import ValidationError

import test_friday_chat_bank
from test_friday_transactions import TransactionalMemory
from carapace_core.friday_cashflow import CashflowRequest, project_cashflow


def request(**changes):
    return CashflowRequest.model_validate({'as_of':'2026-10-14','horizon_days':30,'starting_cash_minor':800000,
        'reserve_minor':200000,'daily_spend_minor':40000,'expected_income':[{'date':'2026-10-28','amount_minor':1800000}],
        'committed_bills':[{'date':'2026-10-21','amount_minor':450000}],**changes})


class CashflowMathTests(unittest.TestCase):
    def test_buffer_and_shortfall_are_exact_not_a_probability(self):
        data=project_cashflow(request())
        self.assertEqual(data['baseline']['first_buffer_breach'],'2026-10-21')
        self.assertEqual(data['baseline']['first_cash_shortfall'],'2026-10-22')
        self.assertEqual(data['baseline']['safe_daily_spend_minor'],10000)
        self.assertEqual(data['delayed_income']['safe_daily_spend_minor'],6818)
        self.assertEqual(data['baseline']['closing_cash_minor'],950000)
        self.assertFalse(data['bank_connected']);self.assertFalse(data['ai_called'])
        self.assertFalse(data['model_trained']);self.assertFalse(data['payment_authorized'])

    def test_same_day_income_does_not_hide_pre_income_gap(self):
        data=project_cashflow(request(horizon_days=1,starting_cash_minor=10000,reserve_minor=0,daily_spend_minor=0,
            expected_income=[{'date':'2026-10-14','amount_minor':50000}],committed_bills=[{'date':'2026-10-14','amount_minor':20000}]))
        self.assertEqual(data['baseline']['first_cash_shortfall'],'2026-10-14')
        self.assertEqual(data['baseline']['closing_cash_minor'],40000)
        self.assertTrue(data['baseline']['fixed_commitments_exceed_buffer'])

    def test_fixed_bills_can_make_daily_cuts_insufficient(self):
        data=project_cashflow(request(starting_cash_minor=10000,reserve_minor=20000,daily_spend_minor=0))
        self.assertEqual(data['status'],'COMMITMENTS_EXCEED_BUFFER')
        self.assertEqual(data['baseline']['safe_daily_spend_minor'],0)
        self.assertEqual(data['baseline']['first_buffer_breach'],'2026-10-14')

    def test_zero_spending_and_zero_income_are_supported_without_inventing_salary(self):
        data=project_cashflow(request(starting_cash_minor=90000,reserve_minor=0,daily_spend_minor=0,expected_income=[],committed_bills=[]))
        self.assertEqual(data['status'],'NO_GAP_IN_ENTERED_SCENARIO')
        self.assertEqual(data['baseline']['closing_cash_minor'],90000)
        self.assertEqual(data['expected_income_total_minor'],0)

    def test_date_precision_limits_and_currency_cannot_be_bypassed(self):
        for changes in ({'daily_spend_minor':1.5},{'daily_spend_minor':True},{'starting_cash_minor':-1},
            {'currency':'USD'},{'horizon_days':91},{'income_delay_days':31},{'save_to_workspace':'true'},{'as_of':'9999-12-31'},
            {'expected_income':[{'date':'2026-10-13','amount_minor':100}]},
            {'committed_bills':[{'date':'2027-01-01','amount_minor':100}]},
            {'expected_income':[{'date':'2026-10-14','amount_minor':0}]}):
            with self.subTest(changes=changes),self.assertRaises(ValidationError):request(**changes)

    def test_delayed_income_beyond_horizon_is_counted_not_assumed_received(self):
        data=project_cashflow(request(horizon_days=2,expected_income=[{'date':'2026-10-15','amount_minor':10000},
            {'date':'2026-10-15','amount_minor':20000}],committed_bills=[],income_delay_days=7))
        self.assertEqual(data['delayed_income']['income_outside_window_count'],2)
        self.assertEqual(data['delayed_income']['closing_cash_minor'],720000)

    def test_daily_cap_is_maximal_and_every_day_preserves_the_buffer(self):
        rng=random.Random(20261014)
        for _ in range(40):
            cash=rng.randrange(100000,1000000);reserve=rng.randrange(0,100000)
            plan=request(starting_cash_minor=cash,reserve_minor=reserve,committed_bills=[])
            cap=project_cashflow(plan)['baseline']['safe_daily_spend_minor']
            limited=project_cashflow(plan.model_copy(update={'daily_spend_minor':cap}))['baseline']
            self.assertIsNone(limited['first_buffer_breach'])
            extra=project_cashflow(plan.model_copy(update={'daily_spend_minor':cap+1}))['baseline']
            self.assertIsNotNone(extra['first_buffer_breach'])

    def test_delay_zero_matches_baseline_and_does_not_move_money(self):
        data=project_cashflow(request(income_delay_days=0))
        self.assertEqual(data['baseline'],data['delayed_income'])
        self.assertFalse(data['money_moved'])


class CashflowAPITests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_chat_bank.FridayChatBankTests();self.base.setUp()
        self.service=self.base.service;self.client=self.base.client;self.headers=self.base.headers

    def tearDown(self):self.base.tearDown()

    def create(self,**changes):
        return self.client.post('/v1/friday/cashflow',headers=self.headers,json=request(**changes).model_dump(mode='json'))

    def test_calculation_is_transient_by_default_and_never_calls_ai_or_executor(self):
        before=self.service.mandate('one')
        with patch.object(self.service,'run_live_signal',side_effect=AssertionError('no executor')):
            result=self.create()
        self.assertEqual(result.status_code,200,result.text)
        self.assertIsNone(self.service.cashflow.get('one'))
        self.assertEqual(self.service.mandate('one'),before)
        self.base.model.models.generate_content.assert_not_called()

    def test_explicit_save_is_private_and_read_only(self):
        self.assertEqual(self.create(save_to_workspace=True).status_code,200)
        result=self.client.get('/v1/friday/cashflow',headers=self.headers).json()
        self.assertEqual(result['snapshot']['result']['starting_cash_minor'],800000)
        self.assertIsNone(self.service.cashflow.get('two'))
        self.assertFalse(result['money_moved']);self.assertFalse(result['ai_called'])

    def test_chat_cashflow_permission_is_independent_of_inbox_permission(self):
        self.create(save_to_workspace=True);self.base.answer(evidence_ids=['cashflow:current'])
        result=self.base.chat(include_cashflow=True)
        self.assertEqual(result.status_code,200,result.text)
        self.assertTrue(result.json()['cashflow_included'])
        content=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(content['workspace_evidence'],{})
        self.assertEqual(content['cashflow_scenario']['baseline']['safe_daily_spend_minor'],10000)
        self.assertNotIn('timeline',json.dumps(content['cashflow_scenario']))
        self.assertNotIn('expected_income',content['cashflow_scenario'])
        self.base.answer();self.base.chat(include_workspace=True)
        content=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(content['cashflow_scenario'],{})

    def test_empty_and_other_tenant_cashflow_remain_unknown(self):
        self.base.answer();result=self.base.chat(include_cashflow=True)
        self.assertFalse(result.json()['cashflow_included'])
        self.create(save_to_workspace=True)
        other={'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'}
        self.client.post('/v1/friday/chat',headers=other,json={'message':'Explain my forecast','include_cashflow':True})
        content=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(content['cashflow_scenario'],{})

    def test_no_permission_cannot_cite_private_cashflow(self):
        self.create(save_to_workspace=True);self.base.answer(evidence_ids=['cashflow:current'])
        self.assertNotEqual(self.base.chat().status_code,200)
        self.assertEqual(self.base.chat(include_cashflow='true').status_code,422)

    def test_cleanup_removes_snapshot_preserves_payment_rules(self):
        self.create(save_to_workspace=True);before=self.service.mandate('one')
        result=self.client.post('/v1/friday/privacy/reviews/delete',headers=self.headers,json={'confirm_delete_reviews':True})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['deleted']['cashflow'],1)
        self.assertIsNone(self.service.cashflow.get('one'))
        self.assertEqual(self.service.mandate('one'),before)

    def test_cleanup_during_calculation_cancels_late_save(self):
        from carapace_core.friday_cashflow import project_cashflow as calculate
        def delayed(plan):
            self.client.post('/v1/friday/privacy/reviews/delete',headers=self.headers,json={'confirm_delete_reviews':True})
            return calculate(plan)
        with patch('carapace_api.friday_cashflow.project_cashflow',side_effect=delayed):
            self.assertEqual(self.create(save_to_workspace=True).status_code,409)
        self.assertIsNone(self.service.cashflow.get('one'))

    def test_firestore_transaction_checks_generation_and_tenant(self):
        self.service.durable=TransactionalMemory()
        self.assertEqual(self.create(save_to_workspace=True).status_code,200)
        self.assertIsNotNone(self.service.cashflow.get('one'))
        self.assertIsNone(self.service.cashflow.get('two'))
        self.service.durable.put('privacy','one','current',{'generation':'cleanup'})
        with self.assertRaises(ValueError):self.service.durable.put_cashflow('one',0,{'privacy_generation':0})
        self.assertIsNone(self.service.cashflow.get('one'))

    def test_routes_authenticate_and_reject_extra_authority(self):
        from carapace_core.friday_access import permitted_friday_route
        self.assertEqual(self.client.get('/v1/friday/cashflow').status_code,401)
        self.assertEqual(self.client.post('/v1/friday/cashflow',headers=self.headers,json=request().model_dump(mode='json')|{'pay':True}).status_code,422)
        self.assertTrue(permitted_friday_route('GET','/v1/friday/cashflow'))
        self.assertTrue(permitted_friday_route('POST','/v1/friday/cashflow'))
        self.assertFalse(permitted_friday_route('PUT','/v1/friday/cashflow'))

    def test_ui_explains_model_consent_and_no_training(self):
        from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
        for text in ('Money runway. Look ahead.','No raw statement or model training','friday-chat-cashflow','sentGeneration!==chatGeneration','Try an editable example'):
            self.assertIn(text,FINANCIAL_FRIDAY_HTML)

    def test_firestore_cleanup_erases_snapshot_and_cancels_old_generation(self):
        self.service.durable=TransactionalMemory();self.create(save_to_workspace=True)
        counts=self.service.durable.delete_private_inputs('one')
        self.assertEqual(counts['cashflow'],1)
        self.assertIsNone(self.service.durable.get('cashflow','one','current'))

    def test_local_gateway_accepts_only_valid_json_inputs(self):
        import importlib
        from fastapi.testclient import TestClient
        with patch.dict('os.environ',{'CARAPACE_DEMO_ENABLED':'true'}):
            web=importlib.import_module('carapace_integrations.anthos_web');client=TestClient(web.create_demo_app())
            body=request().model_dump(mode='json')
            with patch.object(web,'_api_call',return_value=(200,{'scope':'USER_SUPPLIED_CASHFLOW_SCENARIO'})) as transport:
                result=client.post('/api/friday/cashflow',json=body)
                self.assertEqual(result.status_code,200,result.text)
                self.assertEqual(transport.call_args.args[2:4],('POST',body))
            self.assertEqual(client.post('/api/friday/cashflow',json=body|{'pay':True}).status_code,422)
            client.close()

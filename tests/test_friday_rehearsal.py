"""Adversarial cash timing, exact repair, AI boundaries and authenticated API."""
import copy
from datetime import date
import json
import random
from types import SimpleNamespace
import unittest

from carapace_ai.friday_rehearsal import interpret_goal
from carapace_core.friday_access import permitted_friday_route
from carapace_core.friday_portfolio import classify, summarize_statements
from carapace_core.friday_rehearsal import (RehearsalPreview, build_rehearsal,
    compile_scenarios, minimum_cut, purchase_envelope, verify_paths, _paths, _fits)
import test_friday_chat_bank


def statement_view(extra=None, month='2026-09'):
    entries=[]
    for i,(day,description,debit,credit) in enumerate([
        (25,'ARTIFICIAL salary',0,3000000),(5,'ARTIFICIAL rent',1200000,0),
        (10,'ARTIFICIAL groceries',300000,0),(20,'ARTIFICIAL EMI',500000,0),
        (12,'ARTIFICIAL shopping',400000,0),(18,'ARTIFICIAL restaurant',200000,0)],1):
        kind,category=classify(description,bool(debit))
        entries.append({'date':f'{month}-{day:02d}','description':description,'debit_minor':debit,
                        'credit_minor':credit,'kind':kind,'category':category,'source_row':i})
    entries+=extra or []
    statement={'account_alias':'Test Cash','account_type':'BANK','entries':entries}
    return {'revision':1,'workspace_generation':'0','summary':summarize_statements([statement])}


def draft(**changes):
    body={'account_alias':'Test Cash','available_cash_inr':'32000','protected_buffer_inr':'5000',
          'purchase_amount_inr':'3000','purchase_in_days':7,'as_of_date':'2026-10-01',
          'horizon_days':30,'income_delay_days':0,'income_drop_percent':0,
          'essentials_rise_percent':0,'max_cut_percent':50,'expected_revision':1,
          'workspace_generation':'0','confirm_history_is_representative':True}
    body.update(changes)
    return RehearsalPreview(**body)


class RehearsalTests(unittest.TestCase):
    def test_monthly_surplus_hides_timing_gap_and_repair_is_exact(self):
        view=statement_view();before=copy.deepcopy(view);p=build_rehearsal(view,draft())
        self.assertTrue(p['baseline_fits']);self.assertFalse(p['purchase_fits'])
        self.assertEqual(p['original']['first_breach_date'],'2026-10-20')
        self.assertEqual(p['original']['shortfall_minor'],200000)
        self.assertEqual(p['maximum_purchase_on_requested_date_minor'],100000)
        self.assertEqual(p['earliest_no_cut_date'],'2026-10-26')
        self.assertEqual(p['minimum_flexible_cut_bps'],3334)
        self.assertEqual(p['after_changes']['shortfall_minor'],0)
        self.assertEqual({r['category'] for r in p['flexible_changes']},{'Food','Shopping'})
        self.assertEqual(view,before)
        self.assertTrue(all(p['checks'].values()));self.assertFalse(p['money_moved'])
        self.assertEqual(p['actions_executed'],[])

    def test_simultaneous_stress_detects_gap_that_base_misses(self):
        p=build_rehearsal(statement_view(),draft(available_cash_inr='40000',purchase_amount_inr='1000',
            income_delay_days=20,income_drop_percent=40,essentials_rise_percent=20,horizon_days=60))
        self.assertEqual(p['scenario_count'],2)
        self.assertTrue(next(r for r in p['scenario_results'] if not r['adverse'])['fits'])
        self.assertFalse(next(r for r in p['scenario_results'] if r['adverse'])['fits'])
        self.assertFalse(p['purchase_fits'])

    def test_ambiguous_loan_refund_and_transfer_credits_do_not_create_income(self):
        rows=[]
        for i,kind in enumerate(['LOAN_RECEIVED','TRANSFER','REFUND','UNCLEAR'],20):
            rows.append({'date':'2026-09-02','description':'ARTIFICIAL '+kind,'kind':kind,'category':'Other',
                'debit_minor':0,'credit_minor':10000000,'source_row':i})
        a=build_rehearsal(statement_view(),draft());b=build_rehearsal(statement_view(rows),draft())
        self.assertEqual(a['daily'],b['daily']);self.assertTrue(any('not projected' in w for w in b['warnings']))

    def test_all_bank_debits_include_card_loan_and_unclear_movements(self):
        rows=[{'date':'2026-09-08','description':'ARTIFICIAL movement','kind':kind,'category':'Other',
               'debit_minor':100000,'credit_minor':0,'source_row':i}
              for i,kind in enumerate(['CARD_REPAYMENT','TRANSFER','UNCLEAR'],20)]
        p=build_rehearsal(statement_view(rows),draft())
        self.assertFalse(p['baseline_fits']);self.assertEqual(p['minimum_flexible_cut_bps'],None)

    def test_same_day_income_cannot_hide_debit_before_credit(self):
        view=statement_view();rows=view['summary']['entries'];rows[0]['date']='2026-09-05'
        p=build_rehearsal(view,draft(available_cash_inr='10000',purchase_amount_inr='1'))
        self.assertEqual(p['original']['first_breach_date'],'2026-10-05')

    def test_delayed_past_payday_is_not_invented_again_after_start(self):
        d=draft(as_of_date='2026-10-01',income_delay_days=10)
        scenarios=compile_scenarios(statement_view()['summary']['entries'],d)
        stress=next(s for s in scenarios if s['adverse'])
        self.assertFalse(any(e['credit_minor'] for day in stress['days'][:25] for e in day))

    def test_month_end_clamp_and_delayed_income_beyond_horizon(self):
        view=statement_view();view['summary']['entries'][0]['date']='2026-09-30'
        d=draft(as_of_date='2027-01-31',horizon_days=30,income_delay_days=7)
        scenarios=compile_scenarios(view['summary']['entries'],d)
        base,stress=scenarios
        self.assertTrue(any(e['credit_minor'] for e in base['days'][28]))
        self.assertFalse(any(e['credit_minor'] for day in stress['days'] for e in day))

    def test_no_cuts_to_protected_costs_and_no_forced_feasibility(self):
        p=build_rehearsal(statement_view(),draft(available_cash_inr='1000',purchase_amount_inr='100000',
            protected_categories=['Food','Shopping']))
        self.assertEqual(p['status'],'GAP_REMAINS');self.assertIsNone(p['minimum_flexible_cut_bps'])
        self.assertIsNone(p['earliest_no_cut_date']);self.assertFalse(p['baseline_fits'])
        self.assertGreater(p['original']['shortfall_minor'],0)

    def test_card_only_unknown_account_unreviewed_and_invalid_inputs_fail(self):
        for changes in ({'confirm_history_is_representative':False},{'account_alias':'Other'},
                        {'as_of_date':'2026-08-01'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                build_rehearsal(statement_view(),draft(**changes))
        card=statement_view()
        for row in card['summary']['entries']:row['account_type']='CREDIT_CARD'
        with self.assertRaises(ValueError):build_rehearsal(card,draft())
        for changes in ({'available_cash_inr':'-1'},{'purchase_amount_inr':'0'},{'purchase_amount_inr':'1.001'},
                        {'income_delay_days':True},{'income_delay_days':31},{'income_drop_percent':101},
                        {'max_cut_percent':51},{'execute':True},{'purchase_in_days':40,'horizon_days':30}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):draft(**changes)

    def test_lower_envelope_matches_exhaustive_capacity_small_cases(self):
        rng=random.Random(4007)
        for _ in range(60):
            scenarios=[]
            for s in range(3):
                balance=rng.randrange(10,30);points=[]
                for i in range(6):
                    balance+=rng.randrange(-8,10);points.append({'floor_minor':balance})
                scenarios.append({'points':points})
            cap=purchase_envelope(scenarios,2)
            for day in range(1,6):
                feasible=[v for v in range(100) if all(p['floor_minor']-(v if i>=day else 0)>=2
                    for path in scenarios for i,p in enumerate(path['points']))]
                self.assertEqual(cap[day],max(feasible,default=0))

    def test_minimal_cut_matches_exhaustive_grid(self):
        # At most 51 candidates per case; exact basis points, no floating maths.
        for cash in ('33970','33980','33990','34000'):
            d=draft(available_cash_inr=cash,max_cut_percent=1)
            scenarios=compile_scenarios(statement_view()['summary']['entries'],d)
            expected=next((bps for bps in range(101) if _fits(_paths(scenarios,d,bps,7,300000),500000)),None)
            self.assertEqual(minimum_cut(scenarios,d,300000),expected)

    def test_independent_checker_rejects_tampering(self):
        d=draft();scenarios=compile_scenarios(statement_view()['summary']['entries'],d)
        paths=_paths(scenarios,d,0,7,300000);self.assertTrue(verify_paths(scenarios,d,paths,0,7,300000))
        paths[0]['points'][5]['closing_minor']+=1
        with self.assertRaises(ArithmeticError):verify_paths(scenarios,d,paths,0,7,300000)
        with self.assertRaises(ArithmeticError):verify_paths(scenarios,d,[],0,7,300000)
        with self.assertRaises(ArithmeticError):verify_paths(scenarios,d,paths,5001,7,300000)

    def test_missing_income_is_an_outflow_only_scenario_not_zero_earnings_claim(self):
        view=statement_view();view['summary']['entries']=[r for r in view['summary']['entries'] if not r['credit_minor']]
        p=build_rehearsal(view,draft())
        self.assertTrue(any('not proof of zero earnings' in w for w in p['warnings']))

    def test_six_month_limit_and_large_integer_amounts_remain_bounded(self):
        view=statement_view();view['summary']['entries']=[]
        for month in range(2,10):
            view['summary']['entries']+=statement_view(month=f'2026-{month:02d}')['summary']['entries']
        p=build_rehearsal(view,draft(available_cash_inr='999999999.99',purchase_amount_inr='99999999.99',horizon_days=90))
        self.assertEqual(p['source_months'],[f'2026-{m:02d}' for m in range(4,10)])
        self.assertEqual(p['scenario_count'],12);self.assertEqual(len(p['daily']),91)
        self.assertTrue(p['purchase_fits']);self.assertTrue(all(p['checks'].values()))


class RehearsalApiTests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_chat_bank.FridayChatBankTests();self.base.setUp()
        self.client=self.base.client;self.headers=self.base.headers

    def tearDown(self):self.base.tearDown()

    def save_history(self):
        service=self.base.service
        from carapace_core.friday_portfolio import SaveStatement
        entries=[{k:v for k,v in r.items() if k not in {'account_alias','account_type'}} for r in statement_view()['summary']['entries']]
        initial=service.portfolio.view('one')
        service.portfolio.save('one',SaveStatement(statement={'source_sha256':'e'*64,'account_alias':'Test Cash',
            'account_type':'BANK','extraction':'CSV_EXACT','entries':entries},expected_revision=0,
            workspace_generation=initial['workspace_generation'],confirm_reviewed_and_store=True))
        return service.portfolio.view('one')

    def test_auth_revision_isolation_and_no_mutation_or_model_call(self):
        service=self.base.service;view=self.save_history();before=service.mandate('one')
        body=draft(workspace_generation=view['workspace_generation']).model_dump(mode='json')
        path='/v1/friday/rehearsals/preview'
        self.assertEqual(self.client.post(path,json=body).status_code,401)
        r=self.client.post(path,headers=self.headers,json=body);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['minimum_flexible_cut_bps'],3334)
        self.assertEqual(self.client.post(path,headers=self.headers,json={**body,'expected_revision':0}).status_code,409)
        self.assertEqual(self.client.post(path,headers={'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'},json=body).status_code,409)
        self.assertEqual(service.portfolio.view('one'),view);self.assertEqual(service.mandate('one'),before)
        self.base.model.models.generate_content.assert_not_called()
        self.assertTrue(permitted_friday_route('POST',path))
        self.assertTrue(permitted_friday_route('POST','/v1/friday/rehearsals/interpret'))
        self.assertFalse(permitted_friday_route('POST','/v1/friday/rehearsals/execute'))

    def test_explanation_is_separately_consented_recomputed_and_minimised(self):
        view=self.save_history();path='/v1/friday/rehearsals/explain'
        body=draft(workspace_generation=view['workspace_generation']).model_dump(mode='json')
        self.assertEqual(self.client.post(path,headers=self.headers,json=body).status_code,422)
        self.base.model.models.generate_content.assert_not_called()
        self.base.model.models.generate_content.return_value=SimpleNamespace(text=json.dumps({
            'explanation':'The replay has a buffer gap of INR 2,000.00 before payday.',
            'next_step':'Compare the later date and review which flexible costs can genuinely change.',
            'evidence_keys':['timing','later_date']}))
        r=self.client.post(path,headers=self.headers,json={**body,'confirm_send_results_to_gemini':True})
        self.assertEqual(r.status_code,200,r.text);self.assertFalse(r.json()['money_moved'])
        content=self.base.model.models.generate_content.call_args.kwargs['contents']
        for omitted in ('Test Cash','ARTIFICIAL','description','source_row','account_alias','available_cash'):
            self.assertNotIn(omitted,content)
        self.assertIn('INR 2,000.00',content)
        self.assertEqual(self.base.service.portfolio.view('one'),view)
        self.base.model.models.generate_content.return_value=SimpleNamespace(text=json.dumps({
            'explanation':'You can save INR 999,999.00.', 'next_step':'Spend it.', 'evidence_keys':['timing']}))
        self.assertEqual(self.client.post(path,headers=self.headers,json={**body,'confirm_send_results_to_gemini':True}).status_code,503)
        self.assertTrue(permitted_friday_route('POST',path))

    def test_live_interpretation_schema_consent_minimisation_and_invented_amount(self):
        path='/v1/friday/rehearsals/interpret'
        body={'message':'Can I buy a laptop for INR 15000 in 7 days? Protect transport.', 'confirm_send_goal_to_gemini':True}
        self.assertEqual(self.client.post(path,json=body).status_code,401)
        self.assertEqual(self.client.post(path,headers=self.headers,json={**body,'confirm_send_goal_to_gemini':False}).status_code,422)
        self.base.model.models.generate_content.return_value=SimpleNamespace(text=json.dumps({'purchase_amount_inr':'15000', 'protected_categories':['Transport']}))
        r=self.client.post(path,headers=self.headers,json=body);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['model_calls'],1);self.assertFalse(r.json()['statement_data_shared'])
        self.assertFalse(r.json()['money_moved']);self.assertTrue(r.json()['requires_review'])
        data=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(set(data),{'untrusted_question'})
        self.base.model.models.generate_content.return_value=SimpleNamespace(text='{"purchase_amount_inr":"99999"}')
        self.assertEqual(self.client.post(path,headers=self.headers,json=body).status_code,422)
        self.base.model.models.generate_content.return_value=SimpleNamespace(text='{"purchase_amount_inr":"15000","pay":true}')
        self.assertEqual(self.client.post(path,headers=self.headers,json=body).status_code,422)

    def test_explanation_is_discarded_after_history_changes_during_model_call(self):
        from carapace_core.friday_portfolio import StatementVisibility
        view=self.save_history()
        def changed(**kwargs):
            self.base.service.portfolio.set_visibility('one',StatementVisibility(
                source_sha256='e'*64,excluded=True,expected_revision=view['revision'],workspace_generation=view['workspace_generation']))
            return SimpleNamespace(text=json.dumps({'explanation':'Review the conditional timing gap.',
                'next_step':'Recalculate if your history changes.','evidence_keys':['timing']}))
        self.base.model.models.generate_content.side_effect=changed
        body=draft(workspace_generation=view['workspace_generation']).model_dump(mode='json')
        r=self.client.post('/v1/friday/rehearsals/explain',headers=self.headers,json={**body,'confirm_send_results_to_gemini':True})
        self.assertEqual(r.status_code,409,r.text)

    def test_chat_proposes_rehearsal_without_claiming_result_or_sharing_history(self):
        self.base.answer(reply='I can set up a rehearsal. Enter your starting cash and chosen buffer to test it.',
                         next_screen='rehearsal',rehearsal_goal={'purchase_amount_inr':'15000'})
        r=self.base.chat(message='Can I buy a laptop for INR 15000?')
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['rehearsal_goal']['purchase_amount_inr'],'15000')
        self.assertIsNone(r.json()['money_plan']);self.assertEqual(r.json()['context_receipt']['statement_totals'],'NOT_SHARED')
        self.assertFalse(r.json()['payment_authorized'])

    def test_unavailable_model_does_not_invent_an_interpretation(self):
        self.base.model.models.generate_content.side_effect=RuntimeError('offline')
        r=self.client.post('/v1/friday/rehearsals/interpret',headers=self.headers,
            json={'message':'A purchase for INR 15000','confirm_send_goal_to_gemini':True})
        self.assertEqual(r.status_code,503)


class RehearsalUiTests(unittest.TestCase):
    def test_no_model_html_auto_save_or_hidden_financial_action(self):
        from carapace_integrations.friday_rehearsal_ui import REHEARSAL_JS
        self.assertNotIn('innerHTML',REHEARSAL_JS)
        self.assertNotIn('localStorage',REHEARSAL_JS)
        self.assertIn('Daily figures & tested scenarios',REHEARSAL_JS)
        self.assertIn('prefers-reduced-motion',REHEARSAL_JS)
        self.assertIn("'/api/friday/rehearsals/preview'",REHEARSAL_JS)
        self.assertIn('consent.required=true',REHEARSAL_JS)
        self.assertIn("if(lastResult)resetResult",REHEARSAL_JS)
        self.assertIn("confirm_send_goal_to_gemini:true",REHEARSAL_JS)

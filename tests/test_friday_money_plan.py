"""Arithmetic/authority checks, including brute-force optimality on small cases."""
import copy
import itertools
import json
from pathlib import Path
import random
from types import SimpleNamespace
import unittest

from carapace_ai.friday_statements import extract_statement
from carapace_core.friday_money_plan import (MoneyPlanDraft, MoneyPlanPreview,
    allocate_cuts, build_money_plan, verify_allocation)
from carapace_core.friday_portfolio import summarize_statements
from carapace_core.friday_access import permitted_friday_route
import test_friday_chat_bank


def sample_view():
    raw=(Path(__file__).parents[1]/'examples/friday-artificial-statement.csv').read_bytes()
    statement,_=extract_statement(None,data=raw,mime='text/csv',account_alias='Fictional',account_type='BANK',use_ai=False)
    return {'revision':1,'workspace_generation':'0','updated_at':'2026-10-15',
            'summary':summarize_statements([statement.model_dump(mode='json')])}


class MoneyPlanTests(unittest.TestCase):
    def test_threshold_solver_matches_exhaustive_optimum(self):
        rng=random.Random(817)
        for _ in range(80):
            keys=['A','B','C'];caps={k:rng.randrange(0,6) for k in keys}
            weights={k:rng.randrange(1,8) for k in keys};target=rng.randrange(0,18)
            cuts=allocate_cuts(caps,weights,target);total=min(target,sum(caps.values()))
            candidates=[sum(weights[k]*x*x for k,x in zip(keys,row))
                for row in itertools.product(*(range(caps[k]+1) for k in keys)) if sum(row)==total]
            self.assertEqual(sum(cuts.values()),total)
            self.assertEqual(sum(weights[k]*v*v for k,v in cuts.items()),min(candidates))

    def test_large_amounts_do_not_require_one_loop_per_paise(self):
        caps={'A':10**11,'B':10**11};weights={'A':1,'B':3}
        cuts=allocate_cuts(caps,weights,10**11)
        self.assertEqual(sum(cuts.values()),10**11)
        self.assertGreater(cuts['A'],cuts['B'])

    def test_essentials_repayments_and_income_are_not_cut(self):
        view=sample_view();original=copy.deepcopy(view)
        p=build_money_plan(view,MoneyPlanDraft(target_reduction_inr='1000.00'))
        self.assertEqual(p['source_month'],'2026-09')
        self.assertEqual(p['identified_income_minor'],4500000)
        self.assertEqual(p['protected_repayments_minor'],500000)
        self.assertEqual(p['achievable_reduction_minor'],100000)
        self.assertEqual(p['planned_margin_minor']-p['baseline_margin_minor'],100000)
        self.assertTrue(all(r['cut_minor']==0 for r in p['categories'] if r['protected']))
        self.assertTrue(all(p['checks'][k] for k in ('exact_reduction','within_caps','essentials_unchanged','marginal_optimality')))
        self.assertEqual(view,original)
        self.assertFalse(p['money_moved']);self.assertFalse(p['payment_authorized'])

    def test_unachievable_goal_reports_gap_instead_of_fake_success(self):
        p=build_money_plan(sample_view(),MoneyPlanDraft(target_reduction_inr='10000.00'))
        self.assertEqual(p['status'],'TARGET_EXCEEDS_ENTERED_CAPS')
        self.assertEqual(p['achievable_reduction_minor'],142475)
        self.assertEqual(p['unmet_target_minor'],857525)
        self.assertTrue(p['warnings'])

    def test_protection_and_stress_use_exact_integer_amounts(self):
        p=build_money_plan(sample_view(),MoneyPlanDraft(target_reduction_inr='0.01',protected_categories=['Transport'],income_drop_percent=20))
        self.assertEqual(p['achievable_reduction_minor'],1)
        self.assertEqual(p['stress_income_minor'],3600000)
        self.assertEqual(p['stress_margin_minor'],p['planned_margin_minor']-900000)
        self.assertEqual(next(r['cut_minor'] for r in p['categories'] if r['category']=='Transport'),0)
        self.assertEqual(p['frontier'][0]['reduction_minor'],0)

    def test_missing_month_empty_history_and_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):build_money_plan(sample_view(),MoneyPlanDraft(), '2024-01')
        empty=sample_view();empty['summary']['entries']=[]
        with self.assertRaises(ValueError):build_money_plan(empty,MoneyPlanDraft())
        for changes in ({'target_reduction_inr':'-1'},{'target_reduction_inr':'1.001'},
            {'max_cut_percent':True},{'max_cut_percent':51},{'income_drop_percent':90},
            {'protected_categories':['Stocks']},{'execute':True}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):MoneyPlanDraft(**changes)

    def test_independent_checker_rejects_wrong_allocation(self):
        cats=[{'category':'A','protected':True},{'category':'B','protected':False}]
        with self.assertRaises(ArithmeticError):verify_allocation(cats,{'A':1,'B':0},{'A':1,'B':1},{'A':1,'B':1},1)
        with self.assertRaises(ArithmeticError):verify_allocation([],{'A':3,'B':0},{'A':3,'B':3},{'A':3,'B':1},3)


class MoneyPlanApiTests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_chat_bank.FridayChatBankTests();self.base.setUp()
        self.client,self.service,self.headers=self.base.client,self.base.service,self.base.headers
        import base64
        data=(Path(__file__).parents[1]/'examples/friday-artificial-statement.csv').read_bytes()
        p=self.client.post('/v1/friday/statements/prepare',headers=self.headers,json={
            'data_base64':base64.b64encode(data).decode(),'mime':'text/csv','account_alias':'Fictional','account_type':'BANK','confirm_cloud_processing':True}).json()
        self.client.post('/v1/friday/statements',headers=self.headers,json={'statement':p['statement'],
            'expected_revision':0,'workspace_generation':p['workspace_generation'],'confirm_reviewed_and_store':True})

    def tearDown(self):self.base.tearDown()

    def test_private_preview_is_revision_bound_read_only_and_no_ai_call(self):
        view=self.service.portfolio.view('one');before=self.service.mandate('one')
        body={'target_reduction_inr':'1000','expected_revision':view['revision'],'workspace_generation':view['workspace_generation']}
        path='/v1/friday/plans/preview'
        self.assertEqual(self.client.post(path,json=body).status_code,401)
        result=self.client.post(path,headers=self.headers,json=body)
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['achievable_reduction_minor'],100000)
        self.assertEqual(self.client.post(path,headers=self.headers,json={**body,'expected_revision':0}).status_code,409)
        self.assertEqual(self.client.post(path,headers={'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'},json=body).status_code,409)
        self.assertEqual(before,self.service.mandate('one'))
        self.assertEqual(view,self.service.portfolio.view('one'))
        self.base.model.models.generate_content.assert_not_called()
        self.assertTrue(permitted_friday_route('POST',path))
        self.assertFalse(permitted_friday_route('POST','/v1/friday/plans/execute'))

    def test_chat_generates_personal_plan_without_old_workspace_switch(self):
        self.base.answer(reply='I interpreted a monthly reduction goal. The checked options will show what fits.',
            evidence_ids=['statements:current'],next_screen='plan',visual_request='PLAN',
            plan={'target_reduction_inr':'1000.00','protected_categories':['Transport'],'prefer_to_reduce':['Food']})
        r=self.base.chat(message='Help me reduce spending by INR 1000 per month. Protect transport.',include_statements=True)
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['context_receipt']['statement_totals'],'SHARED')
        self.assertEqual(r.json()['context_receipt']['financial_inbox'],'NOT_SHARED')
        self.assertEqual(r.json()['money_plan']['achievable_reduction_minor'],100000)
        content=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertTrue(content['context_permissions']['statement_totals'])
        self.assertFalse(content['context_permissions']['financial_inbox'])
        self.assertNotIn('ARTIFICIAL',json.dumps(content))
        self.assertNotIn('entries',content['statement_summary'])

    def test_false_permission_denial_gets_one_bounded_repair(self):
        common={'evidence_ids':[],'next_screen':'NONE'}
        self.base.model.models.generate_content.side_effect=[
            SimpleNamespace(text=json.dumps({**common,'reply':'I cannot see records because workspace permission is not enabled.'})),
            SimpleNamespace(text=json.dumps({**common,'reply':'Your shared statement totals are available. Start with the coverage warning.'}))]
        r=self.base.chat(message='Help me understand my spending.',include_statements=True)
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['model_calls'],2)
        self.assertNotIn('not enabled',r.json()['reply'])

    def test_ai_cannot_invent_goal_or_use_unshared_history(self):
        self.base.answer(reply='Here is a scenario.',visual_request='PLAN',plan={'target_reduction_inr':'999'})
        self.assertEqual(self.base.chat(message='Make me a plan for INR 1000',include_statements=True).status_code,503)
        self.base.answer(reply='Share totals to personalise the scenario.',visual_request='PLAN',plan={'target_reduction_inr':'1000'})
        r=self.base.chat(message='Make a plan for INR 1000')
        self.assertEqual(r.status_code,200,r.text);self.assertIsNone(r.json()['money_plan'])
        self.assertEqual(r.json()['context_receipt']['statement_totals'],'NOT_SHARED')


class MoneyPlanUiTests(unittest.TestCase):
    def test_graphs_have_accessible_tables_and_privacy_route_is_separate(self):
        from carapace_integrations.friday_plan_ui import PLAN_JS
        from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
        from carapace_integrations.friday_assets import ASSETS
        self.assertIn('Read the exact figures',PLAN_JS)
        self.assertIn("oldShow(name==='settings'?'privacy':name",PLAN_JS)
        self.assertIn("'/api/friday/plans/preview'",PLAN_JS)
        self.assertNotIn('innerHTML',PLAN_JS)
        self.assertIn('/assets/friday-chart.js',FINANCIAL_FRIDAY_HTML)
        self.assertEqual(ASSETS['friday-chart.js'],'application/javascript')
        self.assertIn("borderWidth:type==='line'?2:0",PLAN_JS)
        from carapace_integrations.friday_studio_ui import STUDIO_CSS
        self.assertIn('.friday-chat-log>*{flex-shrink:0}',STUDIO_CSS)

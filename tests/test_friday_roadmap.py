"""Cash-only roadmap, model proposals, persistence and privacy boundaries."""
import json
import shutil
import unittest
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch
from pydantic import ValidationError
from carapace_core.friday_roadmap import RoadmapPlan, RoadmapChange, calculate_roadmap
from carapace_ai.friday_roadmap import RoadmapIntake, RoadmapIntakeRequest, interpret_roadmap
from carapace_core.friday_access import permitted_friday_route
from carapace_core.friday_surface import permitted_consumer_friday_route
import test_friday_chat_bank
from test_friday_transactions import TransactionalMemory


def plan(**changes):
    values=dict(title='Travel fund',kind='SAVINGS',target_inr='120000',months=12,
        monthly_income_inr='50000',monthly_essentials_inr='30000',monthly_existing_debt_inr='0',
        savings_inr='70000',protected_buffer_inr='50000')
    return RoadmapPlan(**{**values,**changes})


class RoadmapMathTests(unittest.TestCase):
    def calc(self,p=None,**kw):
        return calculate_roadmap(p or plan(),started=date(2026,10,18),today=date(2026,10,18),**kw)

    def test_exact_target_path_and_user_reported_start(self):
        r=self.calc();self.assertEqual(r['current_inr'],'20000.00')
        self.assertEqual(r['required_monthly_inr'],'8333.34')
        self.assertEqual(r['calendar'][-1]['baseline_inr'],'120000.08')
        self.assertEqual(r['status'],'ON_PLAN_SCENARIO');self.assertFalse(r['bank_verified'])

    def test_buffer_counts_existing_reserve_not_excluded_twice(self):
        r=self.calc(plan(kind='BUFFER',target_inr='90000'))
        self.assertEqual(r['current_inr'],'70000.00');self.assertEqual(r['progress_percent'],77)

    def test_report_does_not_skip_protected_buffer(self):
        r=self.calc(plan(savings_inr='10000'),entries=[{'amount_minor':1000000}])
        self.assertEqual(r['current_inr'],'0.00');self.assertEqual(r['protected_reserve_gap_inr'],'30000.00')
        self.assertEqual(r['required_monthly_inr'],'12500.00')

    def test_elapsed_time_does_not_invent_savings(self):
        r=calculate_roadmap(plan(),started=date(2026,1,18),today=date(2026,10,18))
        self.assertEqual(r['current_inr'],'20000.00');self.assertEqual(r['remaining_months'],3)

    def test_income_shortfall_and_passed_deadline_are_visible(self):
        r=self.calc(plan(monthly_income_inr='10000'));self.assertEqual(r['monthly_capacity_inr'],'-20000.00')
        self.assertEqual(r['recommended_monthly_inr'],'0.00');self.assertEqual(r['status'],'BUDGET_SHORTFALL')
        r=calculate_roadmap(plan(),started=date(2024,1,31),today=date(2026,10,18))
        self.assertEqual(r['status'],'DEADLINE_PASSED');self.assertIsNone(r['required_monthly_inr'])

    def test_undo_does_not_count_and_completed_progress_caps_only_meter(self):
        r=self.calc(entries=[{'amount_minor':20000000},{'amount_minor':90000000,'undone':True}])
        self.assertEqual(r['current_inr'],'220000.00');self.assertEqual(r['progress_percent'],100)
        self.assertEqual(r['status'],'REPORTED_TARGET_REACHED')

    def test_target_and_types_rejected(self):
        for changes in [{'target_inr':'0'},{'months':True},{'savings_inr':1.25},{'months':61}]:
            with self.subTest(changes=changes),self.assertRaises(ValidationError):plan(**changes)


class RoadmapTests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_chat_bank.FridayChatBankTests();self.base.setUp()
        self.service,self.client,self.headers=self.base.service,self.base.client,self.base.headers

    def tearDown(self):self.base.tearDown()

    def body(self,action='SAVE',**changes):
        state=self.service.roadmap.view('one')
        b=dict(action=action,operation_id=uuid4().hex,expected_revision=state['revision'],
            workspace_generation=state['workspace_generation'],confirm_store=True)
        if action=='SAVE':b['plan']=plan().model_dump()
        if action=='ADD':b['amount_inr']='1000'
        return {**b,**changes}

    def post(self,body):return self.client.post('/v1/friday/goals/roadmap',headers=self.headers,json=body)

    def save(self):
        r=self.post(self.body());self.assertEqual(r.status_code,200,r.text);return r.json()

    def test_empty_auth_and_visitor_allowlist(self):
        self.assertIsNone(self.service.roadmap.view('one')['plan'])
        self.assertEqual(self.client.get('/v1/friday/goals/roadmap').status_code,401)
        for method,path in [('GET','roadmap'),('GET','export'),('GET','budget-hints'),('POST','roadmap'),('POST','conversation'),('POST','roadmap-preview')]:
            self.assertTrue(permitted_friday_route(method,'/v1/friday/goals/'+path,legacy_demo_enabled=False))
            self.assertTrue(permitted_consumer_friday_route(method,'/v1/friday/goals/'+path))
        self.assertFalse(permitted_friday_route('POST','/v1/friday/goals/pay'))

    def test_save_restore_progress_and_undo(self):
        before=self.service.mandate('one');self.save();add=self.body('ADD');r=self.post(add)
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['summary']['current_inr'],'21000.00')
        restored=self.client.get('/v1/friday/goals/roadmap',headers=self.headers).json()
        self.assertEqual(restored['revision'],2)
        undo=self.post(self.body('UNDO',undo_operation_id=add['operation_id']))
        self.assertEqual(undo.json()['summary']['current_inr'],'20000.00')
        self.assertEqual(before,self.service.mandate('one'));self.base.model.models.generate_content.assert_not_called()

    def test_tenants_never_share_and_export_contains_own_archive(self):
        self.save();self.assertIsNone(self.service.roadmap.view('two')['plan'])
        self.assertIsNone(self.service.roadmap.export('two')['record'])
        self.assertEqual(self.post(self.body()).status_code,409)
        self.assertEqual(self.post(self.body(replace_existing=True)).status_code,200)
        self.assertEqual(len(self.service.roadmap.export('one')['record']['archives']),1)

    def test_idempotency_stale_write_and_payload_swap(self):
        self.save();a,b=self.body('ADD'),self.body('ADD');r=self.post(a)
        self.assertEqual(self.post(a).json()['revision'],r.json()['revision'])
        self.assertEqual(self.post(b).status_code,409)
        self.assertEqual(self.post({**a,'amount_inr':'9999'}).status_code,409)

    def test_explicit_confirmation_no_extra_authority(self):
        for change in [{'confirm_store':False},{'confirm_store':1},{'confirm_store':'true'},
            {'payment_authorized':True},{'action':'ADD','amount_inr':'0'},{'expected_revision':True}]:
            self.assertEqual(self.post(self.body(**change)).status_code,422)

    def test_cleanup_erases_saved_goal_and_invalidates_stale_changes(self):
        self.save();stale=self.body('ADD')
        r=self.client.post('/v1/friday/privacy/reviews/delete',headers=self.headers,json={'confirm_delete_reviews':True})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['deleted']['goal_roadmap'],1)
        self.assertIsNone(self.service.roadmap.record('one'));self.assertEqual(self.post(stale).status_code,409)

    def test_firestore_retry_concurrency_failed_commit_and_cleanup(self):
        self.service.durable=TransactionalMemory();self.save();a,b=self.body('ADD'),self.body('ADD')
        def write(body):
            try:return self.service.roadmap.change('one',RoadmapChange.model_validate(body))['revision']
            except ValueError:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(write,[a,b]))
        self.assertEqual(r.count('conflict'),1);self.assertEqual(len(self.service.roadmap.view('one')['entries']),1)
        self.service.durable.fail_commit=True
        with self.assertRaises(RuntimeError):write(self.body('ADD'))
        self.assertEqual(len(self.service.roadmap.view('one')['entries']),1)
        self.service.durable.fail_commit=False;self.service.durable.delete_private_inputs('one')
        self.assertIsNone(self.service.roadmap.record('one'))

    def mock_intake(self,**changes):
        output={key:None for key in RoadmapIntake.model_fields}
        output.update(title='Emergency reserve',kind='BUFFER',**changes)
        self.base.model.models.generate_content.return_value=SimpleNamespace(text=json.dumps(output))

    def test_gemini_handles_stability_year_and_source_numbers_without_saving(self):
        self.mock_intake(target_year={'value':'2028','quote':'2028'},buffer_months={'value':'3','quote':'3 months'})
        r=self.client.post('/v1/friday/goals/conversation',headers=self.headers,json={'message':'A 3 months emergency reserve by 2028','confirm_send_to_gemini':True})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['fields']['buffer_months'],3)
        self.assertTrue(r.json()['notes']);self.assertIsNone(self.service.roadmap.record('one'))
        self.assertFalse(self.base.model.models.generate_content.call_args.kwargs['config'].tools)
        content=self.base.model.models.generate_content.call_args.kwargs['contents'];self.assertNotIn('statement',content)

    def test_quote_swap_zero_guess_and_privacy_race(self):
        self.mock_intake(price_inr={'value':'99999','quote':'75000'})
        payload={'message':'Laptop for 75000 in 12 months','confirm_send_to_gemini':True}
        self.assertEqual(self.client.post('/v1/friday/goals/conversation',headers=self.headers,json=payload).status_code,422)
        self.mock_intake();r=self.client.post('/v1/friday/goals/conversation',headers=self.headers,json=payload)
        self.assertNotIn('monthly_existing_debt_inr',r.json()['fields'])
        from carapace_api.friday_goals import interpret_roadmap as original
        # Use the same public cleanup path while the model request is in flight.
        def clear_during(*args):
            result=original(*args)
            self.client.post('/v1/friday/privacy/reviews/delete',headers=self.headers,json={'confirm_delete_reviews':True})
            return result
        with patch('carapace_api.friday_goals.interpret_roadmap',side_effect=clear_during):
            self.assertEqual(self.client.post('/v1/friday/goals/conversation',headers=self.headers,json=payload).status_code,409)

    def test_no_consent_or_model_fallback_never_pretends_ai(self):
        r=self.client.post('/v1/friday/goals/conversation',headers=self.headers,json={'message':'Save for a car'})
        self.assertEqual(r.status_code,422);self.base.model.models.generate_content.assert_not_called()

    def test_budget_hints_empty_does_not_invent_current_cash(self):
        r=self.client.get('/v1/friday/goals/budget-hints',headers=self.headers)
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['fields'],{})
        self.assertFalse(r.json()['private_statement_context_shared'])

    def test_goal_coaching_is_opt_in_quote_checked_and_not_an_edit(self):
        self.save();self.base.answer(reply='Your reported goal pot is INR 20,000.00. Review the monthly step in Goals.',evidence_ids=['roadmap:current'])
        response=self.base.chat(message='How am I doing?',include_roadmap=True)
        self.assertEqual(response.status_code,200,response.text)
        contents=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(contents['saved_roadmap']['calculated_path']['current_inr'],'20000.00')
        self.assertEqual(contents['statement_summary'],{})
        self.assertEqual(self.service.roadmap.view('one')['revision'],1)
        self.base.answer(reply='You have INR 999,999.00.',evidence_ids=['roadmap:current'])
        self.assertEqual(self.base.chat(message='My goal?',include_roadmap=True).status_code,503)
        self.base.answer();self.base.chat(message='What is a reserve?')
        self.assertEqual(json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])['saved_roadmap'],{})

    @unittest.skipUnless(shutil.which('node'), 'JavaScript syntax check requires Node; runs in native suite')
    def test_generated_javascript_is_parseable_and_keeps_confirmation_boundary(self):
        from carapace_integrations.friday_roadmap_ui import ROADMAP_JS
        import subprocess
        result=subprocess.run(['node','--check'],input=ROADMAP_JS,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('innerHTML',ROADMAP_JS)
        self.assertIn('expected_revision:state.revision',ROADMAP_JS)
        self.assertIn('friday:cashflow-cleared',ROADMAP_JS)
        self.assertIn("btn('Save my roadmap'",ROADMAP_JS)

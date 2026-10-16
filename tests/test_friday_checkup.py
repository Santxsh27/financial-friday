"""Source-led automatic work, privacy, repeatability and review authority."""
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest

from carapace_core.friday_checkup import build_checkup, checkup_model_context, prepare_enquiry
from carapace_core.friday_portfolio import classify, summarize_statements, SaveStatement
from carapace_core.friday_access import permitted_friday_route
from carapace_integrations.friday_checkup_ui import CHECKUP_JS, CHECKUP_CSS
import test_friday_chat_bank
from test_friday_transactions import TransactionalMemory


def history():
    rows=[]
    def row(day,description,debit=0,credit=0):
        kind,category=classify(description,debit)
        rows.append(dict(date=day,description=description,debit_minor=debit,credit_minor=credit,
                         kind=kind,category=category,source_row=len(rows)+1))
    for month in ('07','08','09'):
        row(f'2026-{month}-01','Salary ARTIFICIAL',credit=3000000)
        row(f'2026-{month}-02','Rent ARTIFICIAL',1200000)
        row(f'2026-{month}-03','Netflix ARTIFICIAL',150000 if month=='09' else 100000)
        for day in ('05','10','15'):row(f'2026-{month}-{day}','Groceries ARTIFICIAL',10000)
    row('2026-09-19','Groceries ARTIFICIAL',150000)
    row('2026-09-20','Bank fee ARTIFICIAL',5000)
    row('2026-09-21','Netflix extra ARTIFICIAL',9900)
    row('2026-09-21','Netflix extra ARTIFICIAL',9900)
    row('2026-09-22','Unknown credit ARTIFICIAL',credit=180000)
    return [dict(source_sha256='a'*64,account_alias='Private alias',account_type='BANK',
                 entries=rows,extraction='CSV_EXACT')]


def check(statements=None):
    statements=history() if statements is None else statements
    return build_checkup(statements,summarize_statements(statements))


class CheckupCoreTests(unittest.TestCase):
    def test_automatic_pipeline_finds_patterns_without_mutation_or_model(self):
        source=history();before=deepcopy(source);result=check(source)
        self.assertEqual(source,before)
        self.assertEqual({f['kind'] for f in result['findings']},
                         {'REPEATED_ENTRY','RECURRING_INCREASE','UNUSUAL_AMOUNT','FEES','UNCLEAR_CREDIT'})
        self.assertEqual(result['rows_removed'],0);self.assertEqual(result['model_calls'],0)
        self.assertEqual(result['transaction_count'],len(source[0]['entries']))
        self.assertEqual(len(result['recurring']),2)
        drift=next(f for f in result['findings'] if f['kind']=='RECURRING_INCREASE')
        self.assertEqual(drift['amount_minor'],50000);self.assertEqual(drift['evidence_count'],3)
        self.assertEqual(len(result['checks_completed']),8)

    def test_reorder_is_stable_and_every_reference_resolves_to_source(self):
        source=history();result=check(source);source[0]['entries'].reverse()
        self.assertEqual(check(source),result)
        original={r['source_row']:r for r in source[0]['entries']}
        for finding in result['findings']:
            for ref in finding['evidence']:
                row=original[ref['source_row']]
                for key in ('date','description','debit_minor','credit_minor'):self.assertEqual(ref[key],row[key])

    def test_ambiguous_multiple_rows_and_missing_month_do_not_become_recurring(self):
        source=history();source[0]['entries']=[r for r in source[0]['entries'] if not r['date'].startswith('2026-08')]
        self.assertEqual(check(source)['recurring'],[])
        source=history();source.append({**deepcopy(source[0]),'source_sha256':'b'*64})
        result=check(source);self.assertEqual(result['recurring'],[])
        self.assertTrue(any(f['kind']=='REPEATED_ENTRY' for f in result['findings']))

    def test_exact_attribution_conserves_total_and_missing_month_is_not_zero(self):
        result=check();change=result['spending_change']
        self.assertEqual(sum(c['delta_minor'] for c in change['categories']),change['delta_minor'])
        self.assertEqual(change['delta_minor'],224800)
        source=history();source[0]['entries']=[r for r in source[0]['entries'] if not r['date'].startswith('2026-08')]
        self.assertIsNone(check(source)['spending_change'])

    def test_outlier_requires_sufficient_earlier_history_not_future_rows(self):
        source=history();source[0]['entries']=[r for r in source[0]['entries'] if r['date']>='2026-09-01']
        self.assertFalse(any(f['kind']=='UNUSUAL_AMOUNT' for f in check(source)['findings']))
        result=check();f=next(f for f in result['findings'] if f['kind']=='UNUSUAL_AMOUNT')
        self.assertEqual(f['baseline_minor'],10000);self.assertEqual(f['comparison_count'],9)

    def test_context_is_derived_not_raw_and_draft_is_grounded_unsent(self):
        result=check();context=json.dumps(checkup_model_context(result))
        for secret in ('Private alias','Netflix','Groceries ARTIFICIAL','2026-09-21','source_sha256','source_row'):
            self.assertNotIn(secret,context)
        draft=prepare_enquiry(next(f for f in result['findings'] if f['kind']=='REPEATED_ENTRY'))
        self.assertIn('UNSENT',draft);self.assertIn('INR 99.00',draft)
        self.assertIn('2026-09-21',draft);self.assertIn('not confirmed fraud',draft)

    def test_empty_history_has_no_fake_results(self):
        result=check([]);self.assertEqual(result['findings'],[])
        self.assertEqual(result['recurring'],[]);self.assertEqual(result['transaction_count'],0)
        self.assertIsNone(result['spending_change'])


class CheckupAPITests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_chat_bank.FridayChatBankTests();self.base.setUp()
        self.service,self.client,self.headers=self.base.service,self.base.client,self.base.headers
        view=self.service.portfolio.view('one')
        self.service.portfolio.save('one',SaveStatement(statement=history()[0],expected_revision=0,
            workspace_generation=view['workspace_generation'],confirm_reviewed_and_store=True))

    def tearDown(self):self.base.tearDown()

    def body(self):
        view=self.service.portfolio.view('one')
        return dict(finding_id=view['checkup']['findings'][0]['finding_id'],expected_revision=view['revision'],
                    workspace_generation=view['workspace_generation'])

    def test_review_reopens_without_changing_any_source_or_financial_state(self):
        before=self.service.portfolio.record('one');balance=self.service.mandate('one');body=self.body()
        r=self.client.post('/v1/friday/statements/findings/review',headers=self.headers,json={**body,'reviewed':True})
        self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.json()['checkup']['findings'][0]['reviewed'])
        self.assertEqual(before['statements'],self.service.portfolio.record('one')['statements'])
        self.assertEqual(balance,self.service.mandate('one'))
        self.assertEqual(r.json()['revision'],2)
        r=self.client.post('/v1/friday/statements/findings/review',headers=self.headers,json={**body,'expected_revision':2,'reviewed':False})
        self.assertEqual(r.status_code,200,r.text);self.assertFalse(r.json()['checkup']['findings'][0]['reviewed'])

    def test_stale_cross_tenant_wrong_id_and_extra_authority_are_rejected(self):
        body=self.body()
        for changes,status in (({'expected_revision':0},409),({'finding_id':'finding_'+'0'*24},409),({'pay':True},422)):
            r=self.client.post('/v1/friday/statements/findings/enquiry',headers=self.headers,json={**body,**changes})
            self.assertEqual(r.status_code,status,r.text)
        r=self.client.post('/v1/friday/statements/findings/enquiry',headers={'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'},json=body)
        self.assertEqual(r.status_code,409)
        self.assertFalse(permitted_friday_route('POST','/v1/friday/statements/findings/pay'))
        self.assertTrue(permitted_friday_route('POST','/v1/friday/statements/findings/review'))

    def test_prepared_artifact_is_read_only_no_ai_or_network(self):
        before=self.service.portfolio.view('one')
        r=self.client.post('/v1/friday/statements/findings/enquiry',headers=self.headers,json=self.body())
        self.assertEqual(r.status_code,200,r.text);self.assertFalse(r.json()['sent'])
        self.assertEqual(self.service.portfolio.view('one'),before)
        self.base.model.models.generate_content.assert_not_called()

    def test_chat_selects_visual_and_builds_real_draft_without_sharing_descriptions(self):
        self.base.answer(reply='I have prepared an unsent enquiry for the first review candidate.',
                         evidence_ids=['checkup:current'],checkup_action='PREPARE_ENQUIRY',next_screen='dashboard')
        before=self.service.portfolio.view('one')
        r=self.base.chat(message='Prepare an enquiry for the first finding',include_statements=True)
        self.assertEqual(r.status_code,200,r.text);result=r.json()
        self.assertIn('UNSENT',result['checkup_view']['draft']);self.assertEqual(result['actions_executed'],[])
        content=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertIn('automatic_checkup',content['statement_summary'])
        raw=json.dumps(content)
        for secret in ('Private alias','Netflix','source_sha256','source_row'):self.assertNotIn(secret,raw)
        self.assertEqual(before,self.service.portfolio.view('one'))

    def test_chat_does_not_bypass_consent_and_invalid_finding_fails_closed(self):
        self.base.answer(checkup_action='FINDINGS',next_screen='dashboard')
        r=self.base.chat();self.assertEqual(r.status_code,200)
        self.assertNotIn('checkup_view',r.json())
        self.base.answer(checkup_action='FINDINGS',finding_id='finding_'+'0'*24)
        self.assertEqual(self.base.chat(include_statements=True).status_code,503)

    def test_firestore_review_uses_atomic_callback_and_failed_commit_is_not_success(self):
        self.service.durable=TransactionalMemory();view=self.service.portfolio.view('one')
        self.service.portfolio.save('one',SaveStatement(statement=history()[0],expected_revision=0,
            workspace_generation=view['workspace_generation'],confirm_reviewed_and_store=True))
        before=self.service.portfolio.view('one');body=self.body();self.service.durable.fail_commit=True
        from carapace_core.friday_checkup import ReviewFinding
        with self.assertRaises(RuntimeError):self.service.portfolio.review_finding('one',ReviewFinding(**body,reviewed=True))
        self.assertEqual(self.service.portfolio.view('one'),before)

    def test_ui_has_visual_navigation_and_no_silent_model_consent(self):
        self.assertNotIn('innerHTML',CHECKUP_JS)
        self.assertIn('source_revision!==source.revision',CHECKUP_JS)
        self.assertIn('workspace_generation!==source.workspace_generation',CHECKUP_JS)
        self.assertIn("'role','tablist'",CHECKUP_JS)
        self.assertIn('ArrowRight',CHECKUP_JS)
        self.assertNotIn('statementToggle.checked=true',CHECKUP_JS)
        self.assertIn('prefers-reduced-motion:reduce',CHECKUP_JS)
        self.assertIn("attributeFilter:['data-theme','data-motion']",CHECKUP_JS)
        self.assertIn('margin-left:auto',CHECKUP_CSS)

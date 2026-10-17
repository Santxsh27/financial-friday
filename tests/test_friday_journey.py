"""Synthetic journey, source-selection and bank-export regression tests."""
import json
from copy import deepcopy
import shutil
import subprocess
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from carapace_ai.friday_statements import extract_statement
from carapace_core.friday_statement_csv import parse_statement_csv
from carapace_core.friday_access import permitted_friday_route
from carapace_integrations.friday_navigation_ui import NAVIGATION_HELPERS_JS, NAVIGATION_JS
from carapace_integrations.friday_plan_ui import PLAN_JS
from carapace_integrations.friday_rehearsal_ui import REHEARSAL_JS
from carapace_integrations.friday_workbench_ui import WORKBENCH_JS
from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
import test_friday_portfolio
from test_friday_transactions import TransactionalMemory


EXPORT = '''ARTIFICIAL bank export - not an ICICI customer statement
Detailed Statement
Account Name,Artificial test person

S No.,Value Date,Transaction Date,Transaction Remarks,Withdrawal Amount (INR),Deposit Amount (INR),Balance (INR)
1,01/08/2026,01/08/2026,ARTIFICIAL Salary,,"45,000.00","46,000.00"
2,02/08/2026,02/08/2026,ARTIFICIAL Groceries,"2,500.50",,"43,499.50"
'''


class BankExportTests(unittest.TestCase):
    def test_synthetic_icici_shaped_export_uses_real_headers_without_reformatting(self):
        statement, evidence = extract_statement(None, data=EXPORT.encode(), mime='text/csv',
            account_alias='Artificial ICICI shape', account_type='BANK', use_ai=False)
        self.assertEqual(evidence['model_calls'], 0)
        self.assertEqual(statement.source_facts.adapter, 'BANK_EXPORT_V2')
        self.assertEqual(len(statement.entries), 2)
        self.assertEqual(statement.entries[0].source_row, 6)
        self.assertEqual(statement.entries[1].debit_minor, 250050)
        self.assertEqual(statement.entries[0].credit_minor, 4500000)
        self.assertEqual(statement.entries[1].running_balance_minor, 4349950)
        self.assertEqual(evidence['reconciliation']['checks']['balance_equation']['status'], 'UNKNOWN')

    def test_dotted_and_month_name_day_first_dates(self):
        for date in ('02.08.2026', '02-Aug-2026', '02 Aug 2026'):
            raw=f'Transaction Date,Transaction Remarks,Withdrawal,Deposit,Balance\n{date},Artificial shop,1.01,,99.99\n'
            parsed = parse_statement_csv(raw, account_type='BANK')
            self.assertEqual(parsed['entries'][0]['date'], '2026-08-02')

    def test_unknown_rows_before_header_do_not_disappear(self):
        with self.assertRaisesRegex(ValueError, 'before the transaction table'):
            parse_statement_csv('2026-07-01,Unexplained payment,999\n'+EXPORT, account_type='BANK')

    def test_duplicate_semantic_columns_rejected(self):
        for header in ('Transaction Date,Date,Remarks,Withdrawal,Deposit,Balance',
                       'Transaction Date,Remarks,Debit,Withdrawal,Deposit,Balance'):
            with self.assertRaisesRegex(ValueError, 'same financial field'):
                parse_statement_csv(header+'\n', account_type='BANK')

    def test_unknown_table_column_and_inconsistent_rows_never_partial_import(self):
        for raw in (EXPORT.replace('Balance (INR)', 'Amount owed'),
                    EXPORT+'3,03/08/2026,03/08/2026,Artificial,1,,99,EXTRA\n',
                    EXPORT+'Transaction Date,Transaction Remarks,Withdrawal,Deposit,Balance\n'):
            with self.assertRaises(ValueError):
                parse_statement_csv(raw, account_type='BANK')

    def test_wrong_currency_and_card_mapping_rejected(self):
        with self.assertRaises(ValueError):
            parse_statement_csv(EXPORT, account_type='CREDIT_CARD')
        with self.assertRaises(ValueError):
            parse_statement_csv('Transaction Date,Remarks,Withdrawal,Deposit,Balance,Currency\n2026-08-02,Artificial,1,,99,USD\n', account_type='BANK')


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.f = test_friday_portfolio.PortfolioTests(); self.f.setUp()

    def tearDown(self): self.f.tearDown()

    def seed(self):
        a=self.f.preview().json();self.f.save(a)
        b=self.f.preview(test_friday_portfolio.CSV+b'2026-08-10,Artificial metro,25,,INR\n').json()
        saved=self.f.save(b).json()
        return a,b,saved

    def select(self, view, sources, headers=None):
        return self.f.client.post('/v1/friday/statements/selection',headers=headers or self.f.headers,
            json={'included_sources':sources,'expected_revision':view['revision'],
                  'workspace_generation':view['workspace_generation']})

    def test_start_fresh_is_atomic_reversible_and_preserves_all_records(self):
        for driver in ('sqlite','firestore_callback_contract'):
            with self.subTest(driver=driver):
                if driver!='sqlite': self.f.service.durable=TransactionalMemory()
                a,b,view=self.seed();before=deepcopy(self.f.service.portfolio.record('one'))
                empty=self.select(view,[]);self.assertEqual(empty.status_code,200,empty.text)
                data=empty.json();self.assertEqual(data['summary']['transaction_count'],0)
                self.assertEqual(len(data['imports']),2)
                self.assertTrue(all(i['excluded'] for i in data['imports']))
                self.assertEqual(self.f.service.portfolio.model_context('one'),{})
                self.assertEqual(self.f.service.portfolio.record('one')['statements'],before['statements'])
                restored=self.select(data,[a['statement']['source_sha256']]).json()
                self.assertEqual(restored['summary']['transaction_count'],8)
                self.assertEqual(restored['summary']['statement_count'],1)
                self.assertEqual(restored['imports'][0]['period'],{'start':'2026-08-01','end':'2026-08-08'})

    def test_stale_revision_unknown_sources_and_other_tenants_do_not_overwrite(self):
        a,b,view=self.seed();empty=self.select(view,[]).json();before=deepcopy(self.f.service.portfolio.record('one'))
        self.assertEqual(self.select(view,[]).status_code,409)
        self.assertEqual(self.select(empty,['f'*64]).status_code,409)
        self.assertEqual(self.select(empty,[],headers={'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'}).status_code,409)
        self.assertEqual(self.f.service.portfolio.record('one'),before)

    def test_noop_does_not_increment_and_reupload_restores_only_with_current_revision(self):
        a,b,view=self.seed();sources=[i['source_sha256'] for i in view['imports']]
        self.assertEqual(self.select(view,sources).json()['revision'],view['revision'])
        empty=self.select(view,[]).json()
        self.assertEqual(self.f.save(a,expected_revision=view['revision']).status_code,409)
        restored=self.f.save(a,expected_revision=empty['revision'])
        self.assertEqual(restored.status_code,200,restored.text)
        self.assertEqual(restored.json()['summary']['transaction_count'],8)
        self.assertEqual(len(restored.json()['imports']),2)

    def test_simultaneous_selections_one_winner(self):
        a,b,view=self.seed();barrier=Barrier(2,timeout=10)
        def run(sources):
            barrier.wait();return self.select(view,sources).status_code
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(run,[[],[a['statement']['source_sha256']]]))
        self.assertEqual(sorted(results),[200,409])
        self.assertEqual(len(self.f.service.portfolio.record('one')['statements']),2)

    def test_only_authenticated_post_selection_is_allowed(self):
        path='/v1/friday/statements/selection'
        self.assertTrue(permitted_friday_route('POST',path,legacy_demo_enabled=False))
        self.assertFalse(permitted_friday_route('GET',path,legacy_demo_enabled=False))
        self.assertFalse(permitted_friday_route('DELETE',path,legacy_demo_enabled=False))

    def test_chat_receipt_names_the_selected_revision_without_account_identifiers(self):
        a,b,view=self.seed()
        selected=self.select(view,[a['statement']['source_sha256']]).json()
        self.f.base.answer(reply='I can explain the shared totals.',next_screen='NONE')
        response=self.f.base.chat(message='What did you use?',include_statements=True)
        self.assertEqual(response.status_code,200,response.text)
        receipt=response.json()['context_receipt']
        self.assertEqual(receipt['statement_revision'],selected['revision'])
        self.assertEqual(receipt['included_statement_count'],1)
        self.assertEqual(receipt['statement_period'],{'start':'2026-08-01','end':'2026-08-08'})
        self.assertNotIn(a['statement']['source_sha256'],json.dumps(receipt))
        self.assertFalse(receipt['transaction_descriptions_shared'])


class JourneyTests(unittest.TestCase):
    def node(self, script):
        executable=shutil.which('node')
        if not executable:self.skipTest('Node is optional')
        response=subprocess.run([executable,'-e',script],capture_output=True,text=True,timeout=15)
        self.assertEqual(response.returncode,0,response.stderr)
        return json.loads(response.stdout)

    def test_completed_review_does_not_direct_user_to_nonexistent_highlight(self):
        handler=next(line for line in WORKBENCH_JS.splitlines() if 'const beforeCompanionShow=show' in line)
        for count in (0,2):
            result=self.node("let show=()=>{},command={getAttribute(){return 'false';}},lastWork={prepared_count:"
                +str(count)+"},messages=[];function guide(title,text){messages.push(text);}\n"
                +handler+"\nshow('dashboard');console.log(JSON.stringify(messages));")
            if count:self.assertIn('highlighted',result[0])
            else:
                self.assertIn('No open steps',result[0])
                self.assertNotIn('highlighted',result[0])

    def test_actual_plan_submit_discards_responses_after_edits_or_cleanup(self):
        handler=next(line for line in PLAN_JS.splitlines() if "planForm.addEventListener('submit'" in line)
        for scenario in ('current','edited','cleared'):
            with self.subTest(scenario=scenario):
                prelude=r'''
let planBusy=false,source={revision:1,workspace_generation:'synthetic'},planEpoch=0;
let resolveModel,rendered=0;
const planForm={addEventListener(_name,fn){this.submit=fn;},setAttribute(){}};
const calculate={disabled:false},planStatus={textContent:''};
const target={value:'10'},cap={value:'25'},shock={value:'10'},month={value:'2026-08'};
const protectedChoices=[],preferred=[];
function jsonRequest(){return new Promise(resolve=>{resolveModel=resolve;});}
function renderPlan(){rendered++;}
'''
                body="\nconst request=planForm.submit({preventDefault(){}});"
                if scenario=='edited':body+="planEpoch++;"
                elif scenario=='cleared':body+="source=null;planEpoch++;"
                body+="resolveModel({});request.then(()=>console.log(JSON.stringify({rendered,disabled:calculate.disabled,status:planStatus.textContent})));"
                result=self.node(prelude+handler+body)
                self.assertEqual(result['rendered'],1 if scenario=='current' else 0)
                self.assertFalse(result['disabled'])
                if scenario!='current':self.assertIn('discarded',result['status'])

    def test_actual_plan_and_rehearsal_renderers_reject_absent_sources(self):
        cases=[(PLAN_JS,'renderPlan','source',"STATEMENT_COUNTERFACTUAL_PLAN",'Statement revision changed'),
               (REHEARSAL_JS,'render','snapshot',"STATEMENT_FINANCIAL_REHEARSAL",'Statement source changed')]
        for script,name,source_name,scope,expected in cases:
            with self.subTest(name=name):
                # The first renderer line checks source binding before DOM/chart work.
                line=next(line for line in script.splitlines() if f'function {name}(p)' in line)
                prefix=line.split('lastPlan=p;' if name=='renderPlan' else 'resetResult();lastResult=p;',1)[0]
                function=prefix+'}'
                result=self.node(f'const {source_name}=null;'+function+'\ntry{'+name+'('+json.dumps({'scope':scope,'money_moved':False,'payment_authorized':False,'checks':{'exact_reduction':True,'within_caps':True,'essentials_unchanged':True,'marginal_optimality':True}})+');console.log(JSON.stringify("UNEXPECTED"));}catch(e){console.log(JSON.stringify(e.message));}')
                self.assertEqual(result,expected)

    def test_route_resolution_and_safe_parents_execute_in_javascript(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node is optional')
        script=NAVIGATION_HELPERS_JS+"\nconsole.log(JSON.stringify(['dashboard/transactions','money','settings','assistant','library','research','goals'].map(v=>{const d=fridayDestination(v);return [d,fridayParent(d.screen,d.part)];})));"
        result=subprocess.run([node,'-e',script],capture_output=True,text=True,check=True)
        values=json.loads(result.stdout)
        self.assertEqual(values[0],[{'screen':'dashboard','part':'transactions'},'dashboard'])
        self.assertEqual(values[1][0]['screen'],'dashboard')
        self.assertEqual(values[2],[{'screen':'privacy','part':None},'profile'])
        self.assertEqual(values[3][0]['screen'],'coach')
        self.assertEqual(values[5],[{'screen':'research','part':None},'goals'])
        self.assertEqual(values[6],[{'screen':'goals','part':None},'home'])
        labels=subprocess.run([node,'-e',NAVIGATION_HELPERS_JS+"\nconsole.log(JSON.stringify(['goals','research','unknown'].map(fridayScreenLabel)));"],capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(labels.stdout),['Goals','Research','Home'])

    def test_navigation_composed_after_consumer_guards_and_no_model_calls_or_delete(self):
        self.assertIn(NAVIGATION_JS,FINANCIAL_FRIDAY_HTML)
        self.assertNotIn('innerHTML',NAVIGATION_JS)
        self.assertNotIn('/privacy/reviews/delete',NAVIGATION_JS)
        self.assertNotIn('assistant/briefing-audio',NAVIGATION_JS)
        self.assertIn('Listen to my review',NAVIGATION_JS)
        self.assertIn('history.back()',NAVIGATION_JS)
        self.assertIn("beforeNavigation(target.screen,false)",NAVIGATION_JS)
        self.assertIn("if(routeKey===null)show('home',false)",NAVIGATION_JS)


if __name__=='__main__':unittest.main()

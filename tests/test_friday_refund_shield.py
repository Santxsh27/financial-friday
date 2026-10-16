"""Refund graph bounds against an independent exhaustive integer-flow oracle."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import random
import unittest

from carapace_core.friday_refund_shield import (
    _solve, _validate_flow, build_refund_shield, merchant_key,
)
from carapace_core.friday_checkup import build_checkup, checkup_model_context
from carapace_core.friday_portfolio import classify, summarize_statements, SaveStatement
import test_friday_chat_bank


def rows(specs, alias='Private alias'):
    result=[]
    for i,(day,description,debit,credit) in enumerate(specs):
        kind,category=classify(description,debit)
        result.append(dict(date='2026-09-'+day,description=description,
            debit_minor=debit,credit_minor=credit,kind=kind,category=category,
            source_row=i+1,source_sha256='a'*64,account_alias=alias,account_type='BANK'))
    return result


def statement():
    data=rows([('01','Salary ARTIFICIAL',0,5000000),
        ('02','Purchase Amazon ARTIFICIAL',100000,0),
        ('03','Purchase Amazon ARTIFICIAL',100000,0),
        ('04','Refund Amazon ARTIFICIAL',0,100000),
        ('05','Purchase Metro ARTIFICIAL',50000,0),
        ('06','Refund Metro ARTIFICIAL',0,20000),
        ('07','Purchase Book ARTIFICIAL',100000,0),
        ('08','Refund Book ARTIFICIAL',0,60000),
        ('09','Refund Book ARTIFICIAL',0,40000),
        ('10','Refund Old Store ARTIFICIAL',0,15000),
        ('11','Refund',0,5000),
        ('12','Loan EMI ARTIFICIAL',500000,0),
        ('13','Loan disbursement ARTIFICIAL',0,1000000)])
    return dict(source_sha256='a'*64,account_alias='Private alias',account_type='BANK',
        entries=[{k:v for k,v in r.items() if k not in {'source_sha256','account_alias','account_type'}} for r in data],
        extraction='CSV_EXACT')


class RefundFlowTests(unittest.TestCase):
    def test_integer_optimizer_matches_exhaustive_oracle_on_small_graphs(self):
        rng=random.Random(91)
        # Enumerate every assignment of 0..capacity to each edge independently;
        # discard infeasible assignments, then derive max total and tight bounds.
        for case in range(80):
            nr,np=rng.randint(1,3),rng.randint(1,3)
            refunds=[{'credit_minor':rng.randint(1,3)} for _ in range(nr)]
            purchases=[{'debit_minor':rng.randint(1,3)} for _ in range(np)]
            pairs=sorted((r,p) for r in range(nr) for p in range(np) if rng.random()<.65)
            feasible=[]
            for values in product(*(range(min(refunds[r]['credit_minor'],purchases[p]['debit_minor'])+1) for r,p in pairs)):
                incoming=[0]*np;outgoing=[0]*nr
                for (r,p),v in zip(pairs,values):outgoing[r]+=v;incoming[p]+=v
                if any(v>refunds[r]['credit_minor'] for r,v in enumerate(outgoing)):continue
                if any(v>purchases[p]['debit_minor'] for p,v in enumerate(incoming)):continue
                feasible.append((sum(values),incoming))
            expected=max(v for v,_ in feasible)
            optimum=[v for total,v in feasible if total==expected]
            with self.subTest(case=case,pairs=pairs):
                total,_=_solve(refunds,purchases,set(pairs));self.assertEqual(total,expected)
                for p in range(np):
                    self.assertEqual(_solve(refunds,purchases,set(pairs),total,p,1)[1][p],min(v[p] for v in optimum))
                    self.assertEqual(_solve(refunds,purchases,set(pairs),total,p,-1)[1][p],max(v[p] for v in optimum))

    def test_primal_checker_rejects_over_counting_fractional_and_incompatible_flows(self):
        r=[{'credit_minor':2}];p=[{'debit_minor':2},{'debit_minor':2}];pairs={(0,0),(0,1)}
        for flow in ({(0,0):2,(0,1):1},{(0,0):1.2},{(0,0):True},{(0,0):-1},{(1,0):1}):
            with self.subTest(flow=flow),self.assertRaises(ValueError):_validate_flow(r,p,pairs,flow,2)
        with self.assertRaises(ValueError):_validate_flow(r,p,pairs,{(0,0):1},2)

    def test_split_partial_ambiguous_and_missing_history_are_distinct(self):
        s=statement();summary=summarize_statements([s]);before=deepcopy(s)
        result=build_checkup([s],summary);shield=result['money_shield']
        self.assertEqual(s,before);self.assertEqual(shield['refund_total_minor'],240000)
        self.assertEqual(shield['compatible_minor'],220000);self.assertEqual(shield['not_allocated_minor'],20000)
        self.assertEqual(shield['ambiguous_count'],1);self.assertEqual(shield['held_count'],2)
        trails={t['label']:t for t in shield['trails']}
        amazon=trails['amazon artificial'];self.assertEqual(amazon['status'],'AMBIGUOUS')
        self.assertEqual([(p['refund_min_minor'],p['refund_max_minor']) for p in amazon['purchases']],[(0,100000)]*2)
        metro=trails['metro artificial']['purchases'][0]
        self.assertEqual((metro['refund_min_minor'],metro['refund_max_minor']),(20000,20000))
        self.assertEqual(metro['not_matched_min_minor'],30000)
        self.assertEqual(trails['book artificial']['compatible_minor'],100000)
        self.assertTrue(all(trails['book artificial']['certificate'].values()))
        self.assertEqual(trails['old store artificial']['status'],'NO_COMPATIBLE_PURCHASE')
        self.assertEqual(trails['Unidentified refund']['status'],'MISSING_MERCHANT')
        self.assertEqual(summary['totals']['identified_income_minor'],5000000)
        self.assertFalse(shield['money_moved']);self.assertEqual(shield['refunds_claimed_recovered_minor'],0)
        self.assertEqual({f['kind'] for f in result['findings']}, {'REFUND_AMBIGUITY','REFUND_PARTIAL_TRAIL','REFUND_LINK_WITHHELD'})
        context=json.dumps(checkup_model_context(result))
        for private in ('Amazon','amazon','Private alias','source_row','source_sha256','2026-09-03'):self.assertNotIn(private,context)

    def test_date_and_account_boundaries_do_not_guess(self):
        data=rows([('03','Purchase Shop',100,0),('02','Refund Shop',0,100)])
        self.assertEqual(build_refund_shield(data)['compatible_minor'],0)
        data[1]['date']='2026-09-04';data[1]['account_alias']='Other'
        self.assertEqual(build_refund_shield(data)['compatible_minor'],0)
        data[1]['account_alias']='Private alias';data[1]['account_type']='CREDIT_CARD'
        self.assertEqual(build_refund_shield(data)['compatible_minor'],0)
        data[1]['account_type']='BANK';data[1]['date']='2026-12-03'
        self.assertEqual(build_refund_shield(data)['compatible_minor'],0)
        data[1]['date']='2026-12-02'
        self.assertEqual(build_refund_shield(data)['compatible_minor'],100)  # exactly 90 days

    def test_overlap_and_capacity_limit_hold_entire_group_without_deleting_rows(self):
        data=rows([('01','Purchase Shop',100,0),('01','Purchase Shop',100,0),('02','Refund Shop',0,100)])
        before=deepcopy(data);shield=build_refund_shield(data)
        self.assertEqual(shield['trails'][0]['status'],'OVERLAPPING_ROWS')
        self.assertEqual(shield['compatible_minor'],0);self.assertEqual(data,before)
        data=rows([(f'{d:02d}','Purchase Shop',100,0) for d in range(1,10)]+[('12','Refund Shop',0,100)])
        self.assertEqual(build_refund_shield(data)['trails'][0]['status'],'LIMITED_COVERAGE')

    def test_group_limit_and_reordering_and_no_private_model_training(self):
        data=rows([v for i in range(34) for v in [('01',f'Purchase Store {i}',100,0),('02',f'Refund Store {i}',0,100)]])
        result=build_refund_shield(data);self.assertEqual(result,build_refund_shield(list(reversed(data))))
        self.assertEqual(result['compatible_minor'],3200);self.assertEqual(result['held_count'],2)
        self.assertEqual(result['model_calls'],0)
        self.assertEqual(merchant_key('Refund from Shop 12 REF: 9823'),'shop 12')
        self.assertNotEqual(merchant_key('Shop 12'),merchant_key('Shop 13'))
        self.assertNotEqual(merchant_key('ABC Store'),merchant_key('ABC Stores'))
        self.assertIsNone(merchant_key('Refund'))

    def test_empty_has_no_fabricated_refund(self):
        self.assertEqual(build_refund_shield([])['trails'],[])
        self.assertEqual(build_refund_shield([])['refund_total_minor'],0)

    def test_downloadable_fixture_uses_actual_parser_and_matches_web_download(self):
        from carapace_ai.friday_statements import extract_statement
        from carapace_integrations.friday_statements_ui import STATEMENTS_JS
        sample=(Path(__file__).resolve().parents[1]/'examples/friday-money-shield-artificial.csv').read_text()
        self.assertIn(sample,STATEMENTS_JS)
        imported,_=extract_statement(None,data=sample.encode(),mime='text/csv',account_alias='Artificial',account_type='BANK',use_ai=False)
        saved=imported.model_dump(mode='json')
        c=build_checkup([saved],summarize_statements([saved]))
        self.assertEqual(c['money_shield']['compatible_minor'],220000)
        self.assertEqual(c['transaction_count'],13)


class RefundShieldAPITests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_chat_bank.FridayChatBankTests();self.base.setUp()
        self.service=self.base.service;view=self.service.portfolio.view('one')
        self.service.portfolio.save('one',SaveStatement(statement=statement(),expected_revision=0,
            workspace_generation=view['workspace_generation'],confirm_reviewed_and_store=True))

    def tearDown(self):self.base.tearDown()

    def test_visual_action_has_no_payment_authority_and_replaces_false_completion(self):
        before=self.service.portfolio.view('one');mandate=self.service.mandate('one')
        self.base.answer(reply='I recovered your money and fixed the bank account.',
            evidence_ids=['checkup:current'],checkup_action='MONEY_SHIELD',next_screen='dashboard')
        r=self.base.chat(message='Show my refund shield',include_statements=True)
        self.assertEqual(r.status_code,200,r.text);body=r.json()
        self.assertEqual(body['checkup_view']['action'],'MONEY_SHIELD')
        self.assertNotIn('I recovered',body['reply']);self.assertIn('No money was moved or recovered',body['reply'])
        self.assertEqual(body['actions_executed'],[]);self.assertFalse(body['payment_authorized'])
        self.assertEqual(self.service.portfolio.view('one'),before);self.assertEqual(self.service.mandate('one'),mandate)
        content=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        for secret in ('Private alias','Amazon','source_row','source_sha256'):self.assertNotIn(secret,json.dumps(content))

    def test_no_consent_has_no_visual_or_statement_context(self):
        self.base.answer(reply='I have protected and refunded your money.',checkup_action='MONEY_SHIELD',next_screen='dashboard')
        r=self.base.chat();self.assertEqual(r.status_code,200,r.text)
        self.assertNotIn('checkup_view',r.json())
        self.assertIn('No personal check was completed',r.json()['reply'])
        content=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(content['statement_summary'],{})

    def test_refund_enquiry_has_real_sources_and_not_a_model_claim_of_sending(self):
        before=self.service.portfolio.view('one')
        f=next(f for f in before['checkup']['findings'] if f['kind']=='REFUND_AMBIGUITY')
        self.base.answer(reply='I sent a legal demand and secured your refund.',checkup_action='PREPARE_ENQUIRY',
            finding_id=f['finding_id'],next_screen='dashboard',evidence_ids=['checkup:current'])
        r=self.base.chat(message='Prepare a clarification',include_statements=True)
        self.assertEqual(r.status_code,200,r.text);body=r.json()
        self.assertIn('Nothing was sent',body['reply']);self.assertNotIn('legal demand',body['reply'])
        self.assertIn('2026-09-03',body['checkup_view']['draft']);self.assertIn('UNSENT',body['checkup_view']['draft'])
        self.assertIn('not assumed that a refund is due',body['checkup_view']['draft'])
        self.assertEqual(self.service.portfolio.view('one'),before)

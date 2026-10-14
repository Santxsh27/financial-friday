import base64
import io
import json
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from concurrent.futures import ThreadPoolExecutor
from carapace_ai.friday_statements import extract_statement
from carapace_core.friday_portfolio import StatementEntry, StatementImport, SaveStatement, summarize_statements
from carapace_core.friday_access import permitted_friday_route
from carapace_integrations.friday_statements_ui import STATEMENTS_JS
from test_friday_transactions import TransactionalMemory
import test_friday_chat_bank

CSV=b'date,description,debit,credit,currency\n2026-08-01,Salary,,45000,INR\n2026-08-02,Groceries,2500,,INR\n2026-08-03,Loan disbursement,,50000,INR\n2026-08-04,Credit card payment,6000,,INR\n2026-08-05,Self transfer,2000,,INR\n2026-08-06,Refund,,500,INR\n2026-08-07,EMI,5000,,INR\n2026-08-08,Unknown credit,,1000,INR\n'


def artificial_pdf():
    """Real parser fixture with an embedded text table; no external authoring library."""
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer=PdfWriter();page=writer.add_blank_page(width=595,height=842)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 10 Tf 40 780 Td (ARTIFICIAL INR STATEMENT) Tj 0 -20 Td (Date Description Debit Credit) Tj 0 -20 Td (2026-08-01 Salary 0 45000.00) Tj 0 -20 Td (2026-08-02 Groceries 2500.00 0) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    out=io.BytesIO();writer.write(out);return out.getvalue()


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_chat_bank.FridayChatBankTests();self.base.setUp()
        self.service,self.client,self.headers=self.base.service,self.base.client,self.base.headers

    def tearDown(self):self.base.tearDown()

    def preview(self,data=CSV,**changes):
        body={'data_base64':base64.b64encode(data).decode(),'mime':'text/csv','account_alias':'Main','account_type':'BANK','confirm_cloud_processing':True};body.update(changes)
        return self.client.post('/v1/friday/statements/prepare',headers=self.headers,json=body)

    def save(self,proposal,**changes):
        view=self.service.portfolio.view('one')
        body={'statement':proposal['statement'],'expected_revision':view['revision'],'workspace_generation':proposal['workspace_generation'],'confirm_reviewed_and_store':True};body.update(changes)
        return self.client.post('/v1/friday/statements',headers=self.headers,json=body)

    def test_csv_preview_is_unsaved_exact_and_never_calls_model(self):
        result=self.preview();self.assertEqual(result.status_code,200,result.text);p=result.json()
        self.assertFalse(p['saved']);self.assertFalse(p['money_moved']);self.assertEqual(p['provenance']['model_calls'],0)
        self.assertEqual(self.service.portfolio.view('one')['revision'],0)
        totals=p['summary']['totals'];self.assertEqual(totals['identified_income_minor'],4500000)
        self.assertEqual(totals['classified_spending_minor'],250000)
        self.assertEqual(totals['loan_repayments_minor'],500000)
        self.assertEqual(totals['card_repayments_minor'],600000)
        self.assertEqual(totals['income_less_classified_outgoings_minor'],3750000)
        self.assertEqual(totals['unclassified_minor'],100000)
        self.base.model.models.generate_content.assert_not_called()

    def test_save_is_private_idempotent_and_does_not_touch_payment_or_diary(self):
        before=self.service.mandate('one');p=self.preview().json()
        one=self.save(p);self.assertEqual(one.status_code,200,one.text)
        two=self.save(p,expected_revision=0);self.assertEqual(two.status_code,200)
        self.assertEqual(two.json()['revision'],1);self.assertEqual(two.json()['summary']['transaction_count'],8)
        other=self.client.get('/v1/friday/statements',headers={'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'}).json()
        self.assertEqual(other['summary']['transaction_count'],0)
        self.assertIsNone(self.service.diary.record('one'));self.assertEqual(self.service.mandate('one'),before)

    def test_no_consent_no_processing_and_no_storage(self):
        self.assertEqual(self.preview(confirm_cloud_processing=False).status_code,422)
        p=self.preview().json();self.assertEqual(self.save(p,confirm_reviewed_and_store=False).status_code,409)
        self.assertEqual(self.service.portfolio.view('one')['revision'],0)

    def test_stale_revision_and_same_file_changed_details_rejected(self):
        p=self.preview().json();self.save(p)
        changed=self.preview(CSV+b'2026-08-09,Metro,50,,INR\n').json()
        self.assertEqual(self.save(changed,expected_revision=0).status_code,409)
        p['statement']['account_alias']='Other'
        self.assertEqual(self.save(p).status_code,409)

    def test_overlaps_warn_and_never_silently_remove_rows(self):
        self.save(self.preview().json());p=self.preview(CSV+b'2026-08-09,Metro,50,,INR\n').json()
        result=self.save(p).json();self.assertEqual(result['summary']['transaction_count'],17)
        self.assertEqual(result['summary']['repeated_row_candidates'],8)
        self.assertTrue(any('overlapping' in w for w in result['summary']['warnings']))

    def test_exclude_is_reversible_not_deletion_and_does_not_double_import(self):
        p=self.preview().json();saved=self.save(p).json()
        body={'source_sha256':p['statement']['source_sha256'],'excluded':True,'expected_revision':saved['revision'],'workspace_generation':p['workspace_generation']}
        result=self.client.post('/v1/friday/statements/visibility',headers=self.headers,json=body)
        self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['summary']['transaction_count'],0)
        self.assertTrue(result.json()['imports'][0]['excluded'])
        replay=self.client.post('/v1/friday/statements/visibility',headers=self.headers,json=body).json()
        self.assertEqual(replay['revision'],2)
        body.update(excluded=False,expected_revision=2)
        restored=self.client.post('/v1/friday/statements/visibility',headers=self.headers,json=body).json()
        self.assertEqual(restored['summary']['transaction_count'],8);self.assertEqual(restored['revision'],3)

    def test_cleanup_invalidates_prepared_statement_and_preserves_payment_rules(self):
        p=self.preview().json();self.save(p);before=self.service.mandate('one')
        result=self.client.post('/v1/friday/privacy/reviews/delete',headers=self.headers,json={'confirm_delete_reviews':True,'expired_only':False})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(self.service.portfolio.view('one')['summary']['transaction_count'],0)
        self.assertEqual(self.save(p).status_code,409);self.assertEqual(before,self.service.mandate('one'))

    def test_firestore_atomic_callbacks_replay_and_failed_commit(self):
        self.service.durable=TransactionalMemory();p=self.preview().json()
        self.assertEqual(self.save(p).status_code,200)
        self.assertEqual(self.save(p).json()['revision'],1)
        self.service.durable.fail_commit=True
        q=self.preview(CSV+b'2026-08-09,Metro,50,,INR\n').json()
        with self.assertRaises(RuntimeError):self.service.portfolio.save('one',SaveStatement(statement=q['statement'],expected_revision=1,workspace_generation=q['workspace_generation'],confirm_reviewed_and_store=True))
        self.assertEqual(self.service.portfolio.view('one')['revision'],1)

    def test_concurrent_different_imports_cannot_overwrite(self):
        self.service.durable=TransactionalMemory();p=self.preview().json();q=self.preview(CSV+b'2026-08-09,Metro,50,,INR\n').json()
        requests=[SaveStatement(statement=x['statement'],expected_revision=0,workspace_generation=x['workspace_generation'],confirm_reviewed_and_store=True) for x in (p,q)]
        def save(request):
            try:self.service.portfolio.save('one',request);return True
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,requests))
        self.assertEqual(sum(results),1);self.assertEqual(self.service.portfolio.view('one')['revision'],1)

    def test_types_directions_future_dates_and_currency_fail_closed(self):
        for changes in ({'debit_minor':True},{'credit_minor':1},{'kind':'INCOME'},{'date':'2099-01-01'},{'kind':'TRANSFER','category':'Food'}):
            row={'date':'2026-08-02','description':'x','debit_minor':100,'credit_minor':0,'kind':'EXPENSE','category':'Other','source_row':2};row.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):StatementEntry(**row)
        self.assertEqual(self.preview(CSV.replace(b'INR',b'USD')).status_code,422)
        self.assertEqual(self.preview(data=b'bad').status_code,422)
        self.assertEqual(self.preview(data=CSV,mime='application/pdf').status_code,422)

    def test_chat_shares_aggregates_only_and_amounts_must_be_grounded(self):
        self.save(self.preview().json());self.base.answer(reply='Review the largest spending category.',evidence_ids=['statements:current'])
        result=self.base.chat(include_statements=True);self.assertEqual(result.status_code,200,result.text)
        content=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertNotIn('Loan disbursement',json.dumps(content));self.assertNotIn('account_alias',json.dumps(content))
        self.assertIn('INR 45,000.00',json.dumps(content));self.assertNotIn('_minor',json.dumps(content))
        self.base.answer(reply='Income is INR 999999.00.',evidence_ids=['statements:current'])
        self.assertEqual(self.base.chat(include_statements=True).status_code,503)
        self.base.answer();self.base.chat()
        content=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents']);self.assertEqual(content['statement_summary'],{})

    def test_missing_month_and_no_income_ratio_are_not_invented(self):
        p=self.preview(b'date,description,debit,credit\n2026-01-01,Shop,50,\n2026-03-01,Shop,50,\n').json()
        self.assertIsNone(p['summary']['totals']['outgoings_to_identified_income_percent'])
        self.assertTrue(any('2026-02' in w for w in p['summary']['warnings']))

    def test_pdf_extracts_real_text_and_validates_source_values(self):
        response={'currency':'INR','currency_source_ids':['line-1'],'complete':True,'rows':[
            {'source_ids':['line-5'],'date_text':'2026-08-01','description':'Salary','debit_text':'','credit_text':'45000.00','kind':'INCOME','category':'Other'},
            {'source_ids':['line-7'],'date_text':'2026-08-02','description':'Groceries','debit_text':'2500.00','credit_text':'','kind':'EXPENSE','category':'Groceries'}]}
        self.base.model.models.generate_content.return_value=SimpleNamespace(text=json.dumps(response))
        with patch('carapace_ai.friday_document_grounding.configured_grounder',return_value=None):
            p=self.preview(artificial_pdf(),mime='application/pdf');self.assertEqual(p.status_code,200,p.text)
            self.assertEqual(p.json()['summary']['transaction_count'],2)
            response['rows'][1]['debit_text']='500.00';self.base.model.models.generate_content.return_value=SimpleNamespace(text=json.dumps(response))
            self.assertEqual(self.preview(artificial_pdf(),mime='application/pdf').status_code,422)
        config=self.base.model.models.generate_content.call_args.kwargs['config'];self.assertFalse(config.tools)

    def test_pdf_unreadable_partial_and_injected_unknown_evidence_rejected(self):
        response={'currency':'INR','currency_source_ids':['line-1'],'complete':False,'rows':[{'source_ids':['line-3'],'date_text':'2026-08-01','description':'Salary','debit_text':'','credit_text':'45000.00','kind':'INCOME','category':'Other'}]}
        with patch('carapace_ai.friday_document_grounding.configured_grounder',return_value=None):
            for change in ({},{'complete':True,'currency':'USD'},{'complete':True,'currency_source_ids':['line-999']}):
                self.base.model.models.generate_content.return_value=SimpleNamespace(text=json.dumps({**response,**change}))
                self.assertEqual(self.preview(artificial_pdf(),mime='application/pdf').status_code,422)
        self.assertEqual(self.service.portfolio.view('one')['revision'],0)

    def test_route_allowlist_has_no_payment_authority_or_arbitrary_account(self):
        for method,path in [('GET','statements'),('POST','statements'),('POST','statements/prepare')]:self.assertTrue(permitted_friday_route(method,'/v1/friday/'+path))
        self.assertFalse(permitted_friday_route('POST','/v1/friday/statements/pay'))
        self.assertIn('Review before saving',STATEMENTS_JS);self.assertIn('friday-chat-statements',STATEMENTS_JS)
        self.assertNotIn("'/api/friday/bills/handle'",STATEMENTS_JS)

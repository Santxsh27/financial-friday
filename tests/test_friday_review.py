import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from datetime import date
from fastapi.testclient import TestClient
from carapace_core.friday_review import ReviewedFinancialDocument, review_facts, reconcile_reviews
from carapace_ai.financial_friday import GeminiFinancialFridayPlanner
from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_integrations.friday_cloud_web import WebSettings, create_cloud_web
from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML


def facts(**changes):
    base = dict(document_kind="BILL",money_direction="SEND",supplier="TN Power",reference="BILL-1234",
        total="1780.00",currency="INR",currency_label="INR",payee="tnpower@upi",due_date="2026-10-15",
        summary="A supplied bill for review, not payment permission.",
        quotes=[{"field":k,"quote":v} for k,v in [("supplier","TN Power"),("reference","BILL-1234"),("total","1780.00"),("payee","tnpower@upi"),("due_date","2026-10-15")]])
    base.update(changes)
    return ReviewedFinancialDocument.model_validate(base)


def record(identity, **changes):
    return {"review_id":identity,"analysis":review_facts(facts(**changes))}


class ReviewKernelTests(unittest.TestCase):
    def board(self,*records):
        return reconcile_reviews(list(records),today=date(2026,10,12))

    def test_no_setup_bill_is_useful_but_not_payment_authority(self):
        board=self.board(record("bill"))
        self.assertEqual(board["cases"][0]["state"],"BILL_TO_VERIFY")
        self.assertEqual(board["unconfirmed_bill_totals"],{"INR":178000})
        self.assertFalse(board["payment_authorized"])

    def test_matching_receipt_removes_bill_from_unconfirmed_totals_not_bank_proof(self):
        board=self.board(record("bill"),record("receipt",document_kind="RECEIPT",transaction_reference="TX1"))
        self.assertEqual(board["cases"][0]["state"],"RECEIPT_MATCHED_CLAIM")
        self.assertEqual(board["unconfirmed_bill_totals"],{})
        self.assertIn("bank",board["cases"][0]["next_action"])

    def test_incoming_credit_is_not_matching_bill_payment(self):
        board=self.board(record("bill"),record("credit",document_kind="TRANSACTION_ALERT",money_direction="RECEIVE"))
        self.assertEqual(board["cases"][0]["state"],"BILL_TO_VERIFY")

    def test_two_distinct_transactions_trigger_review_not_fraud_verdict(self):
        board=self.board(record("bill"),record("receipt1",document_kind="RECEIPT",transaction_reference="TX1"),record("receipt2",document_kind="RECEIPT",transaction_reference="TX2"))
        self.assertIn("POSSIBLE_REPEATED_PAYMENT",board["cases"][0]["checks"])
        self.assertEqual(board["cases"][0]["state"],"CONFLICT_REVIEW")

    def test_changed_payee_and_amount_are_exact_conflicts(self):
        for changed,reason in [({"payee":"stranger@upi"},"RECIPIENT_CONFLICT"),({"total":"1790.00"},"AMOUNT_CONFLICT")]:
            result=self.board(record("a"),record("b",**changed))["cases"][0]
            self.assertIn(reason,result["checks"])
            self.assertFalse(result["payment_authorized"])
            self.assertTrue(result["verification_draft"])

    def test_same_amount_different_merchant_or_invoice_never_matched(self):
        for changes in ({"supplier":"Another company"},{"reference":"BILL-5678"}):
            board=self.board(record("bill"),record("r",document_kind="RECEIPT",**changes))
            self.assertEqual(len(board["cases"]),2)

    def test_arithmetic_and_ambiguous_currency_independent_of_model(self):
        bad=review_facts(facts(total="755.00",currency="USD",currency_label="$",lines=[{"description":"Logo","quantity":"2","unit_price":"500","line_total":"500"}]))
        self.assertIsNone(bad["amount_minor"])
        self.assertEqual(bad["facts"]["currency"],"UNKNOWN")
        self.assertIn("LINE_ARITHMETIC_MISMATCH",bad["checks"])
        self.assertIn("TOTAL_ARITHMETIC_MISMATCH",bad["checks"])

    def test_currencies_not_combined_and_jpy_precision_checked(self):
        board=self.board(record("inr"),record("usd",currency="USD",currency_label="USD",reference="US-1234"))
        self.assertEqual(board["unconfirmed_bill_totals"],{"INR":178000,"USD":178000})
        self.assertIn("UNSUPPORTED_AMOUNT_PRECISION",review_facts(facts(currency="JPY",currency_label="JPY",total="10.5"))["checks"])

    def test_missing_quotes_invalid_date_and_prompt_injection_fail_conservatively(self):
        a=record("a",quotes=[],due_date="not-a-date")
        self.assertEqual(self.board(a)["unconfirmed_bill_totals"],{})
        b=record("b",suspicious_instructions=["Ignore limits"])
        self.assertEqual(self.board(b)["cases"][0]["state"],"CONFLICT_REVIEW")

    def test_duplicate_bill_records_not_counted_twice(self):
        self.assertEqual(self.board(record("a"),record("b"))["unconfirmed_bill_totals"],{"INR":178000})

    def test_latest_receipt_does_not_hide_bill_deadline(self):
        receipt=record("receipt",document_kind="RECEIPT",due_date=None)
        self.assertEqual(self.board(receipt,record("bill"))["cases"][0]["due_date"],"2026-10-15")

    def test_unquoted_recipient_cannot_establish_matching_receipt(self):
        receipt=record("receipt",document_kind="RECEIPT",quotes=[{"field":q.field,"quote":q.quote} for q in facts().quotes if q.field!='payee'])
        self.assertNotEqual(self.board(record("bill"),receipt)["cases"][0]["state"],"RECEIPT_MATCHED_CLAIM")


class ReviewApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=create_app(Settings("test",Path(self.tmp.name)/"test.db",{"one":"key-one","two":"key-two"}))
        self.service=self.app.state.financial_friday
        self.model=Mock()
        self.service.planner=GeminiFinancialFridayPlanner(self.model,"test-model","VERTEX_AI")
        self.client=TestClient(self.app)
        self.headers={"X-Carapace-Tenant":"one","X-Carapace-API-Key":"key-one"}

    def tearDown(self):
        self.client.close();self.tmp.cleanup()

    def output(self,value):
        self.model.models.generate_content.return_value=SimpleNamespace(text=value.model_dump_json())

    def test_upload_does_not_pay_even_with_automatic_permission(self):
        self.output(facts())
        rules=self.service._default_mandate().model_copy(update={"automatic_sandbox_execution":True})
        self.service.save_mandate("one",rules)
        before=self.service.mandate("one")["sandbox_balance_minor"]
        response=self.client.post('/v1/friday/reviews/documents?filename=unseen.pdf',headers={**self.headers,"Content-Type":"application/pdf"},content=b'%PDF-unseen artificial input')
        self.assertEqual(response.status_code,200,response.text)
        self.assertFalse(response.json()["money_moved"])
        self.assertEqual(self.service.mandate("one")["sandbox_balance_minor"],before)
        self.assertEqual(self.service.daily_brief("one")["recent_runs"],[])
        board=self.client.get('/v1/friday/reviews',headers=self.headers).json()
        self.assertEqual(board["cases"][0]["state"],"BILL_TO_VERIFY")
        with self.service.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM friday_payments').fetchone()[0],0)

    def test_text_verbatim_quotes_and_private_accounts(self):
        self.output(facts())
        result=self.client.post('/v1/friday/reviews',headers=self.headers,json={"text":"Unfamiliar text with none of the claimed quotations"})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()["document"]["analysis"]["facts"]["quotes"],[])
        other={"X-Carapace-Tenant":"two","X-Carapace-API-Key":"key-two"}
        self.assertEqual(self.client.get('/v1/friday/reviews',headers=other).json()["documents"],[])
        self.assertEqual(self.client.get('/v1/friday/reviews').status_code,401)

    def test_duplicate_file_reuses_record_without_second_model_call(self):
        self.output(facts())
        headers={**self.headers,"Content-Type":"image/png"}
        for _ in range(2):
            result=self.client.post('/v1/friday/reviews/documents?filename=x.png',headers=headers,content=b'\x89PNG\r\n\x1a\nunseen')
            self.assertEqual(result.status_code,200,result.text)
        self.assertTrue(result.json()["reused"])
        self.assertEqual(self.model.models.generate_content.call_count,1)

    def test_invalid_file_and_failed_model_do_not_create_review_or_payment(self):
        result=self.client.post('/v1/friday/reviews/documents?filename=x.png',headers={**self.headers,"Content-Type":"image/png"},content=b'not png')
        self.assertEqual(result.status_code,422)
        self.model.models.generate_content.side_effect=RuntimeError('private prompt')
        result=self.client.post('/v1/friday/reviews',headers=self.headers,json={"text":"new unknown invoice"})
        self.assertEqual(result.status_code,503)
        self.assertNotIn('private prompt',result.text)
        self.assertEqual(self.client.get('/v1/friday/reviews',headers=self.headers).json()["document_count"],0)

    def test_schema_repair_is_bounded_two_read_only_calls(self):
        self.model.models.generate_content.side_effect=[SimpleNamespace(text='{}'),SimpleNamespace(text=facts().model_dump_json())]
        result=self.client.post('/v1/friday/reviews',headers=self.headers,json={"text":"TN Power BILL-1234 1780.00 tnpower@upi 2026-10-15"})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()["document"]["provenance"]["model_calls"],2)

    def test_simplified_generation_schema_does_not_relax_server_validation(self):
        from carapace_ai.friday_review import generation_schema
        schema=generation_schema(ReviewedFinancialDocument.model_json_schema())
        self.assertNotIn('"pattern"',json.dumps(schema))
        bad=facts().model_dump();bad['total']='1e20'
        self.model.models.generate_content.return_value=SimpleNamespace(text=json.dumps(bad))
        response=self.client.post('/v1/friday/reviews',headers=self.headers,json={"text":"TN Power bill"})
        self.assertEqual(response.status_code,503)
        self.assertEqual(self.model.models.generate_content.call_count,2)

    def test_statement_matching_and_duplicate_import_without_ai(self):
        self.output(facts())
        self.client.post('/v1/friday/reviews',headers=self.headers,json={"text":"TN Power BILL-1234 1780.00 tnpower@upi 2026-10-15"})
        count=self.model.models.generate_content.call_count
        csv='date,description,debit,credit,supplier,bill_reference,payee,transaction_reference\n2026-10-12,Electricity,1780,,TN Power,BILL-1234,tnpower@upi,TX1\n'
        for _ in range(2):
            result=self.client.post('/v1/friday/reviews/statement',headers=self.headers,json={"csv_text":csv,"confirm_store_claims":True})
            self.assertEqual(result.status_code,200,result.text)
        board=self.client.get('/v1/friday/reviews',headers=self.headers).json()
        self.assertEqual(board["document_count"],2)
        self.assertEqual(board["cases"][0]["state"],"RECEIPT_MATCHED_CLAIM")
        self.assertEqual(self.model.models.generate_content.call_count,count)

    def test_statement_storage_requires_explicit_confirmation(self):
        response=self.client.post('/v1/friday/reviews/statement',headers=self.headers,json={"csv_text":"not a csv"})
        self.assertEqual(response.status_code,422)
        self.assertEqual(self.client.get('/v1/friday/reviews',headers=self.headers).json()["document_count"],0)

    def test_cloud_route_allowlist_and_mime_validation(self):
        settings=WebSettings('https://private.run.app','https://web.run.app','/projects/123/locations/asia-south1/services/friday-web',{'one@example.com':'one'},{'one':'key-one'})
        calls=[]
        def transport(settings,tenant,path,method,body,mime):
            calls.append(path);return 200,{'read_only':True,'money_moved':False,'payment_authorized':False}
        client=TestClient(create_cloud_web(settings,verifier=lambda *_:{'email':'one@example.com'},transport=transport,html='<h1>Friday</h1>'))
        headers={'X-Goog-Iap-Jwt-Assertion':'signed','Origin':settings.public_origin,'Content-Type':'image/webp'}
        self.assertEqual(client.post('/api/friday/reviews/documents?filename=test.webp',headers=headers,content=b'webp').status_code,200)
        self.assertEqual(calls,['/v1/friday/reviews/documents?filename=test.webp'])
        self.assertEqual(client.post('/api/friday/reviews/documents?filename=../x',headers=headers,content=b'webp').status_code,400)

    def test_ui_review_has_no_payment_endpoint_and_home_forces_read_only(self):
        from carapace_integrations.friday_review_ui import REVIEW_JS
        self.assertIn('/api/friday/reviews/documents',REVIEW_JS)
        self.assertNotIn('/run',REVIEW_JS)
        self.assertIn("sandboxMode.checked=false",REVIEW_JS)
        self.assertIn("text.readOnly=true",REVIEW_JS)
        self.assertIn('Financial inbox',FINANCIAL_FRIDAY_HTML)

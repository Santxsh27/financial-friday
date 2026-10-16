"""Synthetic extraction attestations: never bank-signature or fraud tests."""
from copy import deepcopy
import unittest

import test_friday_portfolio


class StatementReceiptTests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_portfolio.PortfolioTests();self.base.setUp()

    def tearDown(self):self.base.tearDown()

    def test_prepare_signs_extraction_and_server_recomputes_checks(self):
        proposal=self.base.preview().json()
        self.assertTrue(proposal['source_bound'])
        self.assertEqual(proposal['statement']['extraction_receipt']['purpose'],'FRIDAY_STATEMENT_EXTRACTION_V1')
        result=self.base.save(proposal)
        self.assertEqual(result.status_code,200,result.text)
        item=result.json()['imports'][0]
        self.assertTrue(item['source_bound'])
        self.assertEqual(item['reconciliation'],proposal['reconciliation'])
        # A source without declared balances cannot gain a blanket green status.
        self.assertEqual(item['reconciliation']['checks']['balance_equation']['status'],'UNKNOWN')

    def test_immutable_fields_and_receipt_cannot_be_forged(self):
        proposal=self.base.preview().json()
        for field,value in [('description','Different payee'),('debit_minor',250001),('source_row',99)]:
            changed=deepcopy(proposal);changed['statement']['entries'][1][field]=value
            with self.subTest(field=field):
                self.assertEqual(self.base.save(changed).status_code,409)
        for field,value in [('account_alias','Different'),('source_sha256','f'*64),('extraction','PDF_TEXT_GEMINI')]:
            changed=deepcopy(proposal);changed['statement'][field]=value
            with self.subTest(field=field):self.assertEqual(self.base.save(changed).status_code,409)
        changed=deepcopy(proposal);changed['statement']['extraction_receipt']['signature']='A'*88
        self.assertEqual(self.base.save(changed).status_code,409)
        changed=deepcopy(proposal);changed['statement'].pop('extraction_receipt')
        self.assertEqual(self.base.save(changed).status_code,409)
        self.assertEqual(self.base.service.portfolio.view('one')['revision'],0)

    def test_source_receipt_is_bound_to_tenant_and_generation(self):
        proposal=self.base.preview().json()
        body={'statement':proposal['statement'],'expected_revision':0,'workspace_generation':proposal['workspace_generation'],'confirm_reviewed_and_store':True}
        other=self.base.client.post('/v1/friday/statements',headers={'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'},json=body)
        self.assertEqual(other.status_code,409)
        self.base.client.post('/v1/friday/privacy/reviews/delete',headers=self.base.headers,json={'confirm_delete_reviews':True,'expired_only':False})
        body['workspace_generation']=self.base.service.portfolio.view('one')['workspace_generation']
        result=self.base.client.post('/v1/friday/statements',headers=self.base.headers,json=body)
        self.assertEqual(result.status_code,409)

    def test_reviewed_labels_can_change_without_rewriting_extraction(self):
        proposal=self.base.preview().json()
        proposal['statement']['entries'][1].update(kind='EXPENSE',category='Other')
        result=self.base.save(proposal)
        self.assertEqual(result.status_code,200,result.text)
        self.assertTrue(result.json()['imports'][0]['source_bound'])

    def test_old_import_replay_stays_idempotent_and_never_source_bound(self):
        proposal=self.base.preview().json()
        proposal['statement'].pop('source_facts');proposal['statement'].pop('extraction_receipt')
        for row in proposal['statement']['entries']:
            row.pop('running_balance_minor',None);row.pop('source_unit_ids',None)
        first=self.base.save(proposal);self.assertEqual(first.status_code,200,first.text)
        second=self.base.save(proposal,expected_revision=0)
        self.assertEqual(second.status_code,200,second.text)
        self.assertEqual(second.json()['revision'],1)
        self.assertFalse(second.json()['imports'][0]['source_bound'])

    def test_source_claim_cannot_be_added_and_false_status_not_accepted(self):
        proposal=self.base.preview().json()
        proposal['statement']['source_facts']['transaction_count']={
            'value':8,'literal_text':'8','source_refs':[{'unit_id':'fake','text':'Transactions: 8'}]}
        self.assertEqual(self.base.save(proposal).status_code,409)
        proposal=self.base.preview().json();proposal['statement']['overall_status']='CONSISTENT'
        self.assertEqual(self.base.save(proposal).status_code,422)

    def test_model_context_never_contains_receipts_or_source_excerpts(self):
        proposal=self.base.preview().json();self.base.save(proposal)
        context=self.base.service.portfolio.model_context('one')
        text=str(context)
        for forbidden in ('extraction_receipt','source_facts','signature','source_refs','source_unit_ids'):
            self.assertNotIn(forbidden,text)

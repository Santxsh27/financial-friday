import base64
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

import test_friday_tasks
from test_friday_review import facts,record
from carapace_ai.friday_document_grounding import GoogleDocumentGrounder,ground_facts,value_supported
from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_api.friday_execution import TaskExecutionJournal


class TaskLifecycleTests(unittest.TestCase):
    def setUp(self):self.base=test_friday_tasks.FridayTaskTests();self.base.setUp()
    def tearDown(self):self.base.tearDown()

    def test_completion_readback_is_not_still_just_a_prepared_draft(self):
        from carapace_ai.financial_friday import LocalFinancialFridayPlanner
        task=self.base.prepare().json();self.base.service.planner=LocalFinancialFridayPlanner()
        self.assertEqual(self.base.confirm(task).status_code,200)
        public=self.base.tasks.get('one',task['task_id'])
        self.assertEqual(public['execution']['state'],'COMPLETED')
        self.assertEqual(public['execution']['assurance_state'],'VERIFIED')
        self.assertTrue(public['execution']['run_id'])
        self.assertFalse(public['money_moved']) # A GET performs no operation.
        recovered=self.base.tasks.reconcile('one',task['task_id'])
        self.assertEqual(recovered['state'],'RECORDED_PAYMENT_VERIFIED')
        self.assertFalse(recovered['new_payment_created'])

    def test_active_lease_and_expired_lease_are_not_success(self):
        task=self.base.prepare().json()
        lease=self.base.tasks.executions.claim('one',task['task_id'],task['task_sha256'])
        with self.assertRaises(ValueError):self.base.tasks.executions.claim('one',task['task_id'],task['task_sha256'])
        with patch('carapace_api.friday_execution.utcnow',return_value=datetime.now(timezone.utc)+timedelta(minutes=4)):
            self.assertEqual(self.base.tasks.get('one',task['task_id'])['execution']['state'],'OUTCOME_UNKNOWN')
        self.assertEqual(self.base.tasks.reconcile('one',task['task_id'])['state'],'OUTCOME_UNKNOWN')

    def test_privacy_delete_requires_explicit_confirmation_and_is_tenant_isolated(self):
        self.base.save_review()
        task=self.base.prepare().json()
        url='/v1/friday/privacy/reviews/delete'
        for value in [False,'true']:
            response=self.base.client.post(url,headers=self.base.headers,json={'confirm_delete_reviews':value})
            self.assertIn(response.status_code,{409,422})
        other={'X-Carapace-Tenant':'two','X-Carapace-API-Key':'key-two'}
        self.base.client.post(url,headers=other,json={'confirm_delete_reviews':True})
        self.assertEqual(self.base.app.state.friday_reviews.board('one')['document_count'],1)
        response=self.base.client.post(url,headers=self.base.headers,json={'confirm_delete_reviews':True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.base.app.state.friday_reviews.board('one')['document_count'],0)
        with self.assertRaises(KeyError):self.base.tasks.get('one',task['task_id'])

    def test_late_privacy_deletion_cancels_pending_task_write(self):
        from carapace_api.friday_privacy import DeleteReviews
        from carapace_ai.friday_tasks import TaskRequest
        original=self.base.tasks._save
        def clear_then_save(*args):
            self.base.app.state.friday_privacy.delete('one',DeleteReviews(confirm_delete_reviews=True))
            return original(*args)
        with patch.object(self.base.tasks,'_save',side_effect=clear_then_save),self.assertRaisesRegex(ValueError,'Privacy cleanup'):
            self.base.tasks.prepare('one',TaskRequest(message='Please prepare BILL-1234',include_workspace=True))

    def test_retention_is_manual_and_validated(self):
        response=self.base.client.put('/v1/friday/privacy',headers=self.base.headers,json={'retention_days':30})
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json()['automatic_deletion_enabled'])
        self.assertEqual(self.base.client.put('/v1/friday/privacy',headers=self.base.headers,json={'retention_days':1}).status_code,422)


class GroundingTests(unittest.TestCase):
    def test_number_and_recipient_have_to_occur_in_the_quoted_source(self):
        self.assertTrue(value_supported('total','1780.00','Total INR 1,780.00'))
        self.assertFalse(value_supported('total','999.00','Total INR 1,780.00'))
        self.assertFalse(value_supported('payee','attacker@upi','tnpower@upi'))

    def test_ocr_anchor_and_low_quality_are_not_authenticity(self):
        text='TN Power BILL-1234 1780.00 tnpower@upi 2026-10-15'
        ocr={'text':text,'mode':'DOCUMENT_AI_OCR','lines':[{'start':0,'end':len(text),'page':1,'box':[],'confidence':.99}]}
        report=ground_facts(facts(),ocr)
        self.assertEqual(report['unsupported_fields'],[])
        self.assertFalse(report['authenticity_verified'])
        ocr['lines'][0]['confidence']=.4
        self.assertIn('total',ground_facts(facts(),ocr)['unsupported_fields'])

    def test_processor_url_not_user_controlled_and_calls_are_bounded(self):
        with self.assertRaises(ValueError):GoogleDocumentGrounder('https://evil.example/process')
        session=Mock();session.post.return_value.json.return_value={'document':{'text':'Hello','pages':[]}}
        grounder=GoogleDocumentGrounder('projects/example/locations/us/processors/123',session)
        result=grounder.read(b'fake-test','image/png')
        self.assertEqual(result['mode'],'DOCUMENT_AI_OCR')
        self.assertEqual(session.post.call_args.kwargs['timeout'],60)


class KeyRotationTests(unittest.TestCase):
    def test_old_trusted_signature_survives_rotation_unknown_or_misattributed_key_does_not(self):
        with tempfile.TemporaryDirectory() as root:
            old=BankEnvelopeSigner(Path(root)/'old.pem',allow_generate=True)
            public=Path(root)/'public.json';public.write_text(json.dumps({old.key_id:base64.b64encode(old.public_key_bytes).decode()}))
            new=BankEnvelopeSigner(Path(root)/'new.pem',allow_generate=True,verification_keys_path=public)
            signature=old.sign({'amount':100})
            self.assertTrue(new.verify_for_key({'amount':100},signature,old.key_id))
            self.assertFalse(new.verify_for_key({'amount':100},signature,new.key_id))
            self.assertFalse(new.verify_for_key({'amount':101},signature,old.key_id))

    def test_model_telemetry_does_not_log_prompts_or_replies(self):
        from carapace_ai.friday_observability import generate
        client=Mock();client.models.generate_content.return_value=SimpleNamespace(usage_metadata=SimpleNamespace(total_token_count=21))
        with self.assertLogs('carapace_ai.friday_observability',level='INFO') as logs:
            generate(client,purpose='test',model='model',contents='SECRET_INPUT')
        self.assertNotIn('SECRET_INPUT',str(logs.output))
        self.assertIn('total_token_count',str(logs.output))


class CloudPrivacyTests(unittest.TestCase):
    def test_cloud_cleanup_removes_claims_but_retains_receipt_and_invalidates_pending_writes(self):
        from test_friday_transactions import TransactionalMemory
        store=TransactionalMemory()
        value=record('review-one');value['privacy_generation']=0
        store.put_review('one','review-one',value)
        store.put('payments','one','payment-one',{'receipt':'retained'})
        store.put('idempotency','one','idem-one',{'payment_id':'payment-one'})
        result=store.delete_private_inputs('one')
        self.assertEqual(result['reviews'],1)
        self.assertEqual(store.get('payments','one','payment-one'),{'receipt':'retained'})
        self.assertEqual(store.get('idempotency','one','idem-one'),{'payment_id':'payment-one'})
        with self.assertRaisesRegex(ValueError,'Privacy cleanup'):store.put_review('one','pending',value)

    def test_cleanup_of_empty_workspace_still_cancels_pending_model_output(self):
        from test_friday_transactions import TransactionalMemory
        store=TransactionalMemory();store.delete_private_inputs('one')
        with self.assertRaises(ValueError):store.put_review('one','pending',record('pending')|{'privacy_generation':0})

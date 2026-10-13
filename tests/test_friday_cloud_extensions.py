"""Independent OCR admission and automatic recovery can never retry money."""
import base64
import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from carapace_ai.friday_document_grounding import GoogleDocumentGrounder, ground_facts
from carapace_api.friday_recovery import RecoveryScheduler, recover_journal, verify_task_identity
from carapace_api.friday_resource_limits import reserve_resource
from carapace_ai.financial_friday import LocalFinancialFridayPlanner
from carapace_api.friday_tasks import TaskConfirmation
from carapace_core.canonical import sha256_hex
import test_friday_tasks
import test_friday_transactions
import test_friday_review


class CloudExtensionTests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_tasks.FridayTaskTests();self.base.setUp()
        self.service=self.base.service;self.tasks=self.base.tasks

    def tearDown(self):self.base.tearDown()

    def task(self):return self.base.prepare().json()

    def job(self,lease):
        now=datetime.now(timezone.utc)
        payload={key:lease[key] for key in ('tenant_id','task_id','task_sha256','lease_id')}
        payload.update(scope='JOURNAL_ONLY_RECOVERY',scheduled_at=(now-timedelta(seconds=1)).isoformat(),expires_at=(now+timedelta(minutes=20)).isoformat())
        return {'payload':payload,'signature':self.service.signer.sign(payload),'key_id':self.service.signer.key_id}

    def expire(self,lease):
        old={**lease,'lease_until':(datetime.now(timezone.utc)-timedelta(seconds=10)).isoformat()}
        record=self.tasks.executions.seal(old)
        with self.service.connect() as db:
            db.execute('UPDATE friday_task_executions SET record=? WHERE tenant=? AND task_id=?',(json.dumps(record),'one',lease['task_id']))
        return old

    def test_ocr_invalid_long_or_encrypted_pdf_refused_before_network(self):
        grounder=GoogleDocumentGrounder('projects/example/locations/asia-south1/processors/123',Mock())
        with patch('pypdf.PdfReader',return_value=SimpleNamespace(is_encrypted=False,pages=[1,2,3,4])):
            with self.assertRaises(ValueError):grounder.read(b'%PDF-test','application/pdf')
        with patch('pypdf.PdfReader',return_value=SimpleNamespace(is_encrypted=True)):
            with self.assertRaises(ValueError):grounder.read(b'%PDF-test','application/pdf')
        grounder.session.post.assert_not_called()

    def ocr(self,text):
        return {'text':text,'mode':'DOCUMENT_AI_OCR','lines':[{'page':1,'start':0,'end':len(text),'confidence':.99,'box':[]}]}

    def test_missing_currency_quote_grounded_only_by_explicit_total_line(self):
        facts=test_friday_review.facts(total='100.00',quotes=[{'field':'total','quote':'100.00'}])
        result=ground_facts(facts,self.ocr('INR 100.00\n'))
        self.assertNotIn('currency',result['unsupported_fields'])
        self.assertIn('supplier',result['unsupported_fields'])
        self.assertEqual(next(a for a in result['field_anchors'] if a['field']=='currency')['quote'],'INR')

    def test_missing_quotes_bare_dollar_or_mixed_currency_stay_unverified(self):
        facts=test_friday_review.facts(total='100.00',quotes=[{'field':'total','quote':'100.00'}])
        for text in ('$100.00','INR 100.00 USD','100.00'):
            with self.subTest(text=text):
                self.assertIn('currency',ground_facts(facts,self.ocr(text))['unsupported_fields'])
        self.assertIn('payee',ground_facts(facts,self.ocr('INR 100.00'))['unsupported_fields'])

    def test_currency_elsewhere_cannot_ground_total(self):
        facts=test_friday_review.facts(total='100.00',quotes=[{'field':'total','quote':'100.00'}])
        ocr=self.ocr('INR\n100.00');ocr['lines']=[{'page':1,'start':0,'end':3,'confidence':.99},
            {'page':1,'start':4,'end':10,'confidence':.99}]
        self.assertIn('currency',ground_facts(facts,ocr)['unsupported_fields'])

    def test_low_readability_total_cannot_ground_currency(self):
        facts=test_friday_review.facts(total='100.00',quotes=[{'field':'total','quote':'100.00'}])
        ocr=self.ocr('INR 100.00');ocr['lines'][0]['confidence']=.5
        self.assertIn('currency',ground_facts(facts,ocr)['unsupported_fields'])

    def test_atomic_global_resource_budget_counts_failures_and_blocks_excess(self):
        with patch.dict('os.environ',{'FRIDAY_OCR_PAGES_DAILY_LIMIT':'3'}):
            self.assertEqual(reserve_resource(self.service,'ocr_pages',2)['used'],2)
            self.assertEqual(reserve_resource(self.service,'ocr_pages',1)['used'],3)
            with self.assertRaises(ValueError):reserve_resource(self.service,'ocr_pages',1)
        with self.assertRaises(ValueError):reserve_resource(self.service,'ocr_pages',True)
        with patch.dict('os.environ',{'FRIDAY_OCR_PAGES_DAILY_LIMIT':'10000'}):
            with self.assertRaises(ValueError):reserve_resource(self.service,'ocr_pages',1)

    def test_firestore_resource_callback_is_atomic_and_shared(self):
        store=test_friday_transactions.TransactionalMemory()
        self.assertEqual(store.reserve_resource('ocr_pages','2026-10-13',2,3)['used'],2)
        with self.assertRaises(ValueError):store.reserve_resource('ocr_pages','2026-10-13',2,3)
        self.assertEqual(store.reserve_resource('ocr_pages','2026-10-13',1,3)['used'],3)

    def test_scheduler_fixed_origin_signed_job_oidc_and_no_secrets(self):
        task=self.task();lease=self.tasks.executions.claim('one',task['task_id'],task['task_sha256'])
        session=Mock();session.post.return_value.status_code=200
        scheduler=RecoveryScheduler('projects/example/locations/asia-south1/queues/recovery','https://test-api.run.app',
            'friday-recovery@example.iam.gserviceaccount.com',session)
        self.assertTrue(scheduler.enqueue(self.service,lease)['enabled'])
        request=session.post.call_args.kwargs['json']['task']
        self.assertEqual(request['httpRequest']['url'],'https://test-api.run.app/internal/friday/recover')
        self.assertEqual(request['httpRequest']['oidcToken']['audience'],'https://test-api.run.app')
        envelope=json.loads(base64.b64decode(request['httpRequest']['body']))
        self.assertEqual(envelope['payload']['scope'],'JOURNAL_ONLY_RECOVERY')
        self.assertTrue(self.service.signer.verify_for_key(envelope['payload'],envelope['signature'],envelope['key_id']))
        self.assertNotIn('amount',envelope['payload'])
        self.assertNotIn('api_key',request['httpRequest'])

    def test_queue_target_and_partial_configuration_fail_closed(self):
        for args in [('https://evil.example',None,None),('projects/example/locations/us/queues/q','https://test.run.app','x@example.iam.gserviceaccount.com'),
                     ('projects/example/locations/asia-south1/queues/q','https://test.run.app/path','x@example.iam.gserviceaccount.com')]:
            with self.assertRaises(ValueError):RecoveryScheduler(*args)
        with self.assertRaises(ValueError):RecoveryScheduler('projects/example/locations/asia-south1/queues/q','https://test.run.app','x@example.iam.gserviceaccount.com',target='https://evil.run.app')
        self.assertFalse(RecoveryScheduler().enabled)

    def test_worker_requires_verified_dedicated_identity_not_queue_headers(self):
        scheduler=RecoveryScheduler('projects/example/locations/asia-south1/queues/q','https://test.run.app','friday-recovery@example.iam.gserviceaccount.com')
        with self.assertRaises(ValueError):verify_task_identity(None,scheduler)
        with patch('google.oauth2.id_token.verify_oauth2_token',return_value={'email':'wrong@example.com','email_verified':True}):
            with self.assertRaises(ValueError):verify_task_identity('Bearer token',scheduler)
        with patch('google.oauth2.id_token.verify_oauth2_token',return_value={'email':scheduler.identity,'email_verified':True}):
            verify_task_identity('Bearer token',scheduler)

    def test_bad_signature_early_delivery_and_expired_delivery_do_not_reconcile(self):
        task=self.task();lease=self.tasks.executions.claim('one',task['task_id'],task['task_sha256']);job=self.job(lease)
        with patch.object(self.tasks,'reconcile',side_effect=AssertionError('not admitted')):
            bad={**job,'signature':'invalid'}
            with self.assertRaises(ValueError):recover_journal(self.tasks,bad)
            early={**job['payload'],'scheduled_at':(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()}
            with self.assertRaises(ValueError):recover_journal(self.tasks,{**job,'payload':early,'signature':self.service.signer.sign(early)})
            expired={**job['payload'],'expires_at':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()}
            self.assertEqual(recover_journal(self.tasks,{**job,'payload':expired,'signature':self.service.signer.sign(expired)})['state'],'DELIVERY_EXPIRED')

    def test_unknown_without_receipt_stays_unknown_and_never_runs_model_or_executor(self):
        task=self.task();lease=self.tasks.executions.claim('one',task['task_id'],task['task_sha256']);self.expire(lease)
        with patch.object(self.service,'run_live_signal',side_effect=AssertionError('cannot pay')),patch.object(self.service.planner,'plan',side_effect=AssertionError('cannot ask model')):
            result=recover_journal(self.tasks,self.job(lease))
        self.assertEqual(result['state'],'OUTCOME_UNKNOWN')
        self.assertFalse(result['new_payment_created'])
        self.assertEqual(self.tasks.get('one',task['task_id'])['execution']['state'],'OUTCOME_UNKNOWN')

    def test_lost_response_recovers_existing_payment_without_second_debit(self):
        task=self.task();self.service.planner=LocalFinancialFridayPlanner()
        before=self.service.mandate('one')['sandbox_balance_minor']
        response=self.base.confirm(task,simulate_response_loss=True)
        self.assertEqual(response.status_code,503,response.text)
        with self.service.connect() as db:
            lease=self.tasks.executions.validate(json.loads(db.execute('SELECT record FROM friday_task_executions').fetchone()[0]),'one',task['task_id'])
        job=self.job(lease)
        with patch.object(self.service,'run_live_signal',side_effect=AssertionError('no payment retry')):
            recovered=recover_journal(self.tasks,job)
            self.assertEqual(recovered['state'],'RECORDED_PAYMENT_VERIFIED')
            self.assertEqual(recover_journal(self.tasks,job)['state'],'NOT_PENDING')
            self.assertTrue(self.base.confirm(task).json()['read_only_replay'])
        self.assertEqual(self.service.mandate('one')['sandbox_balance_minor'],before-self.base.bill.amount_minor)
        self.assertEqual(self.tasks.get('one',task['task_id'])['execution']['assurance_state'],'VERIFIED')

    def test_stale_delivery_cannot_overwrite_another_lease(self):
        task=self.task();old=self.tasks.executions.claim('one',task['task_id'],task['task_sha256']);self.expire(old)
        newer=self.tasks.executions.claim('one',task['task_id'],task['task_sha256']);self.expire(newer)
        result=recover_journal(self.tasks,self.job(old))
        self.assertEqual(result['state'],'STALE_DELIVERY')
        self.assertNotIn('recovery',self.tasks.executions.get('one',task['task_id']))

    def test_failed_recovery_scheduling_blocks_new_payment(self):
        task=self.task();self.tasks.recovery=Mock(enabled=True)
        self.tasks.recovery.enqueue.side_effect=RuntimeError('queue unavailable')
        before=self.service.mandate('one')['sandbox_balance_minor']
        self.assertEqual(self.base.confirm(task).status_code,409)
        self.assertEqual(self.service.mandate('one')['sandbox_balance_minor'],before)

    def test_worker_endpoint_disabled_by_default_and_never_publicly_allowlisted(self):
        from carapace_core.friday_access import permitted_friday_route
        self.assertFalse(permitted_friday_route('POST','/internal/friday/recover'))
        self.assertEqual(self.base.client.post('/internal/friday/recover',json={}).status_code,404)
        self.tasks.recovery=Mock(enabled=True)
        self.assertEqual(self.base.client.post('/internal/friday/recover',headers=self.base.headers,json={}).status_code,403)

    def test_simulation_requires_a_strict_explicit_flag(self):
        with self.assertRaises(ValueError):TaskConfirmation(expected_task_sha256='a'*64,confirm_sandbox_execution=True,simulate_response_loss='true')

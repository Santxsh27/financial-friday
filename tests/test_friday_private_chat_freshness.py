"""No stale private reply after cleanup of any independently shared context."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_friday_chat_bank
from carapace_api.friday_privacy import DeleteReviews, FridayPrivacyService, privacy_generation


class PrivateChatFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_chat_bank.FridayChatBankTests();self.base.setUp()

    def tearDown(self):self.base.tearDown()

    def test_cleanup_with_any_private_context_withholds_stale_reply(self):
        for flag in ('include_workspace','include_cashflow','include_diary','include_statements'):
            with self.subTest(flag=flag):
                before=privacy_generation(self.base.service,'one')
                calls=self.base.model.models.generate_content.call_count
                def reply(**_kwargs):
                    FridayPrivacyService(self.base.service).delete('one',DeleteReviews(confirm_delete_reviews=True))
                    return SimpleNamespace(text=json.dumps({'reply':'A stale private answer.','evidence_ids':[],'next_screen':'NONE'}))
                self.base.model.models.generate_content.side_effect=reply
                response=self.base.chat(message='Explain my shared records.',**{flag:True})
                self.assertEqual(response.status_code,503,response.text)
                self.assertNotIn('A stale private answer',response.text)
                self.assertNotEqual(before,privacy_generation(self.base.service,'one'))
                self.assertEqual(self.base.model.models.generate_content.call_count,calls+1)
                self.assertEqual(self.base.service.portfolio.view('one')['summary']['transaction_count'],0)

    def test_change_of_shared_diary_or_forecast_withholds_reply_without_cleanup(self):
        for flag,tool in (('include_diary','diary'),('include_cashflow','cashflow')):
            with self.subTest(flag=flag):
                self.base.answer(reply='A reply from older aggregates.')
                contexts=[{'evidence_id':tool+':current','note':'older'}, {'evidence_id':tool+':current','note':'newer'}]
                with patch.object(getattr(self.base.service,tool),'model_context',side_effect=contexts):
                    response=self.base.chat(**{flag:True})
                self.assertEqual(response.status_code,503,response.text)
                self.assertNotIn('A reply from older aggregates',response.text)

    def test_general_answer_never_loads_unshared_private_context(self):
        self.base.answer(reply='A budget is a plan for income and spending.')
        with (patch('carapace_api.friday_chat.chat_context',side_effect=AssertionError('unshared')),
                patch.object(self.base.service.diary,'model_context',side_effect=AssertionError('unshared'))):
            response=self.base.chat(message='What is a budget?')
        self.assertEqual(response.status_code,200,response.text)

    def test_cleanup_during_last_freshness_read_cannot_return_its_old_snapshot(self):
        self.base.answer(reply='This earlier snapshot must not return.')
        old={'evidence_id':'diary:current','note':'before cleanup'}
        count=0;before=privacy_generation(self.base.service,'one')
        def read_context(_tenant):
            nonlocal count
            count+=1
            if count==2:
                FridayPrivacyService(self.base.service).delete('one',DeleteReviews(confirm_delete_reviews=True))
            return dict(old)
        with patch.object(self.base.service.diary,'model_context',side_effect=read_context):
            response=self.base.chat(include_diary=True)
        self.assertEqual(count,2)
        self.assertNotEqual(before,privacy_generation(self.base.service,'one'))
        self.assertEqual(response.status_code,503,response.text)
        self.assertNotIn('This earlier snapshot must not return',response.text)

import json
import unittest
from unittest.mock import patch
import test_friday_chat_bank
import test_friday_transactions
from carapace_api.friday_buddy import BuddyPreferences
from carapace_core.friday_access import permitted_friday_route


class BuddyTests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_chat_bank.FridayChatBankTests();self.base.setUp()
        self.service=self.base.service;self.client=self.base.client;self.headers=self.base.headers
        self.buddy=self.base.app.state.friday_buddy

    def tearDown(self):self.base.tearDown()

    def save(self,**changes):
        value=BuddyPreferences().model_dump();value.update(changes)
        return self.client.put('/v1/friday/buddy/preferences',headers=self.headers,json=value)

    def test_preferences_are_private_persistent_and_do_not_change_money_rules(self):
        before=self.service.mandate('one')
        result=self.save(display_name='Santosh',explanation_style='STEP_BY_STEP')
        self.assertEqual(result.status_code,200,result.text)
        self.assertFalse(result.json()['financial_rules_changed'])
        self.assertEqual(self.buddy.preferences('one')['display_name'],'Santosh')
        self.assertEqual(self.buddy.preferences('two')['display_name'],'')
        self.assertEqual(self.service.mandate('one'),before)

    def test_forget_preferences_does_not_remove_records_or_permission(self):
        before=self.service.mandate('one');self.save(display_name='Friend',share_style_with_ai=True)
        self.save()
        self.assertEqual(self.buddy.preferences('one'),BuddyPreferences().model_dump())
        self.assertEqual(self.service.mandate('one'),before)

    def test_overview_is_real_read_only_and_does_not_call_model_or_executor(self):
        with patch.object(self.service,'run_live_signal',side_effect=AssertionError('no executor')):
            result=self.client.get('/v1/friday/buddy',headers=self.headers)
        self.assertEqual(result.status_code,200,result.text)
        self.assertFalse(result.json()['ai_called']);self.assertFalse(result.json()['bank_connected'])
        self.assertEqual(result.json()['attention_count'],0)
        self.assertIsNone(result.json()['next_item'])
        self.base.model.models.generate_content.assert_not_called()

    def test_profile_cannot_inject_permissions_secrets_or_bad_types(self):
        for changes in ({'automatic_limit':999999},{'display_name':'<script>'},{'display_name':'PIN 1234'},
                        {'share_style_with_ai':'true'},{'explanation_style':'PAY_EVERYTHING'}, {'focus':'BUY_STOCKS'}):
            with self.subTest(changes=changes):self.assertEqual(self.save(**changes).status_code,422)

    def test_style_requires_saved_and_per_request_consent_and_never_sends_name(self):
        self.base.answer();self.save(display_name='Private Nickname',share_style_with_ai=True,explanation_style='STEP_BY_STEP')
        self.base.chat()
        data=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(data['communication_preferences'],{})
        result=self.base.chat(include_preferences=True)
        self.assertTrue(result.json()['preferences_included'])
        data=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(data['communication_preferences'],{'explanation_style':'STEP_BY_STEP','focus':'BILLS'})
        self.assertEqual(data['workspace_evidence'],{})
        self.assertNotIn('Private Nickname',json.dumps(data))
        self.save(share_style_with_ai=False)
        self.base.chat(include_preferences=True)
        self.assertFalse(self.base.model.models.generate_content.call_args.kwargs['contents'].find('STEP_BY_STEP')>=0)

    def test_firestore_profile_storage_is_tenant_isolated(self):
        self.service.durable=test_friday_transactions.TransactionalMemory()
        self.buddy.save('one',BuddyPreferences(display_name='Friend'))
        self.assertEqual(self.buddy.preferences('one')['display_name'],'Friend')
        self.assertEqual(self.buddy.preferences('two')['display_name'],'')

    def test_profile_routes_authenticate_and_do_not_allow_other_methods(self):
        self.assertEqual(self.client.get('/v1/friday/buddy').status_code,401)
        for method,path in [('GET','buddy'),('GET','buddy/preferences'),('PUT','buddy/preferences')]:
            self.assertTrue(permitted_friday_route(method,'/v1/friday/'+path))
        self.assertFalse(permitted_friday_route('POST','/v1/friday/buddy/preferences'))
        self.assertEqual(self.base.chat(include_preferences='true').status_code,422)

    def test_profile_layout_has_opt_in_and_real_ai_state(self):
        from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
        for text in ('Make Friday yours','What AI actually did','friday:preferences-changed','include_preferences',"data-motion=off"):
            self.assertIn(text,FINANCIAL_FRIDAY_HTML)


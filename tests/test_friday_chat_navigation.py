"""Typed navigation coherence, with synthetic responses and no live model calls."""
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from pydantic import ValidationError

from carapace_ai.friday_chat import ChatAnswer, FridayChatRequest, answer_chat, coherent_navigation


class CoherentNavigationTests(unittest.TestCase):
    def test_checkup_actions_own_the_dashboard_without_a_second_visual(self):
        for action in ('FINDINGS', 'REGULAR_PAYMENTS', 'SPENDING_CHANGE', 'PREPARE_ENQUIRY', 'MONEY_SHIELD'):
            for visual in ('NONE', 'SPENDING', 'MONTHLY', 'PLAN'):
                with self.subTest(action=action, visual=visual):
                    answer = ChatAnswer(reply='Review the supplied evidence.', checkup_action=action,
                                        next_screen='settings', visual_request=visual)
                    original = answer.model_dump()
                    result = coherent_navigation(answer)
                    self.assertEqual(result.next_screen, 'dashboard')
                    self.assertEqual(result.visual_request, 'NONE')
                    self.assertEqual(result.checkup_action, action)
                    self.assertEqual(result.reply, answer.reply)
                    self.assertEqual(answer.model_dump(), original)

    def test_plan_and_rehearsal_keep_their_own_typed_destination(self):
        plan = ChatAnswer(reply='Review the proposed scenario.', plan={'target_reduction_inr': '1000'},
                          next_screen='rehearsal', visual_request='MONTHLY')
        proposal = deepcopy(plan.plan.model_dump())
        result = coherent_navigation(plan)
        self.assertEqual((result.next_screen, result.visual_request), ('plan', 'PLAN'))
        self.assertEqual(result.plan.model_dump(), proposal)
        rehearsal = ChatAnswer(reply='Enter cash and a buffer to test it.',
                               rehearsal_goal={'purchase_amount_inr': '15000'},
                               next_screen='plan', visual_request='PLAN')
        goal = deepcopy(rehearsal.rehearsal_goal.model_dump())
        result = coherent_navigation(rehearsal)
        self.assertEqual((result.next_screen, result.visual_request), ('rehearsal', 'NONE'))
        self.assertEqual(result.rehearsal_goal.model_dump(), goal)

    def test_standalone_charts_use_dashboard_and_missing_typed_proposals_do_not_open_workflows(self):
        for visual in ('SPENDING', 'MONTHLY'):
            result = coherent_navigation(ChatAnswer(reply='Review the chart.', next_screen='settings', visual_request=visual))
            self.assertEqual((result.next_screen, result.visual_request), ('dashboard', visual))
        for screen in ('plan', 'rehearsal'):
            result = coherent_navigation(ChatAnswer(reply='No scenario was proposed.', next_screen=screen, visual_request='PLAN'))
            self.assertEqual((result.next_screen, result.visual_request), ('NONE', 'NONE'))
        privacy = ChatAnswer(reply='Open your privacy and saved-data controls.', next_screen='settings')
        self.assertEqual(coherent_navigation(privacy).model_dump(), privacy.model_dump())

    def test_conflicting_workflows_are_rejected_instead_of_selecting_an_action(self):
        for fields in ({'checkup_action': 'FINDINGS', 'plan': {}},
                       {'checkup_action': 'MONEY_SHIELD', 'rehearsal_goal': {}},
                       {'plan': {}, 'rehearsal_goal': {}}):
            with self.subTest(fields=fields), self.assertRaisesRegex(ValueError, 'Choose one'):
                coherent_navigation(ChatAnswer(reply='Synthetic incompatible workflows.', **fields))


class ValidatedModelNavigationTests(unittest.TestCase):
    def answer(self, response, *, message='Explain the supplied statement.', include_statements=False, statements=None):
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(text=json.dumps(response))
        planner = SimpleNamespace(mode='VERTEX_AI', model_name='gemini-synthetic-test', _client=client)
        request = FridayChatRequest(message=message, include_statements=include_statements)
        result = answer_chat(planner, request, {}, statements=statements)
        self.assertEqual(client.models.generate_content.call_count, 1)
        self.assertTrue(result['read_only'])
        self.assertFalse(result['money_moved'])
        self.assertFalse(result['payment_authorized'])
        self.assertEqual(result['actions_executed'], [])
        self.assertEqual(result['statements_included'], bool(include_statements and statements))
        self.assertFalse(request.include_workspace)
        return result, client

    def test_actual_answer_normalizes_checkup_chart_collision_without_changing_reply_or_citations(self):
        statements = {'source_revision': 7, 'automatic_checkup': {'findings': []}}
        original = deepcopy(statements)
        response = {'reply': 'The supplied months show a spending change.', 'evidence_ids': ['checkup:current'],
                    'checkup_action': 'SPENDING_CHANGE', 'visual_request': 'MONTHLY', 'next_screen': 'settings'}
        result, _ = self.answer(response, include_statements=True, statements=statements)
        self.assertEqual((result['next_screen'], result['visual_request']), ('dashboard', 'NONE'))
        self.assertEqual(result['checkup_action'], 'SPENDING_CHANGE')
        self.assertEqual(result['reply'], response['reply'])
        self.assertEqual(result['evidence_ids'], response['evidence_ids'])
        self.assertEqual(statements, original)

    def test_actual_answer_routes_validated_plans_and_rehearsals_to_their_workflows(self):
        result, _ = self.answer({'reply': 'This is a proposed monthly scenario.', 'next_screen': 'settings',
            'visual_request': 'MONTHLY', 'plan': {'target_reduction_inr': '1000.00'}},
            message='Reduce spending by INR 1000 per month.')
        self.assertEqual((result['next_screen'], result['visual_request']), ('plan', 'PLAN'))
        self.assertEqual(result['plan']['target_reduction_inr'], '1000.00')
        result, _ = self.answer({'reply': 'Enter cash and a chosen buffer to test this purchase.',
            'next_screen': 'dashboard', 'visual_request': 'SPENDING', 'rehearsal_goal': {'purchase_amount_inr': '15000'}},
            message='Can I buy a laptop for INR 15000?')
        self.assertEqual((result['next_screen'], result['visual_request']), ('rehearsal', 'NONE'))
        self.assertEqual(result['rehearsal_goal']['purchase_amount_inr'], '15000')

    def test_navigation_does_not_send_unshared_statements_or_create_citation_permission(self):
        private = {'private_synthetic_value': 'never shared', 'automatic_checkup': {'findings': []}}
        result, client = self.answer({'reply': 'A chart needs shared statement totals.',
            'next_screen': 'settings', 'visual_request': 'MONTHLY'}, statements=private)
        self.assertEqual(result['next_screen'], 'dashboard')
        self.assertFalse(result['statements_included'])
        payload = json.loads(client.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(payload['statement_summary'], {})
        self.assertFalse(payload['context_permissions']['statement_totals'])
        self.assertNotIn('never shared', json.dumps(payload))
        with self.assertRaisesRegex(ValueError, 'unavailable evidence reference'):
            self.answer({'reply': 'Synthetic unavailable citation.', 'checkup_action': 'FINDINGS',
                         'evidence_ids': ['checkup:current']}, statements=private)

    def test_existing_amount_finding_and_conflict_validation_still_precedes_output(self):
        for response, message, error in (
            ({'reply': 'A proposed plan.', 'plan': {'target_reduction_inr': '999'}},
             'Reduce spending by INR 1000 per month.', 'Planning target'),
            ({'reply': 'A proposed purchase.', 'rehearsal_goal': {'purchase_amount_inr': '999'}},
             'Can I buy something for INR 1000?', 'Rehearsal purchase amount'),
            ({'reply': 'Synthetic unknown finding.', 'finding_id': 'finding_' + 'a' * 24,
              'checkup_action': 'PREPARE_ENQUIRY'}, 'Explain a finding.', 'unavailable finding'),
            ({'reply': 'Synthetic conflict.', 'checkup_action': 'FINDINGS', 'plan': {}},
             'Explain a finding.', 'Choose one'),
            ({'reply': 'Synthetic conflict.', 'plan': {}, 'rehearsal_goal': {}},
             'Explain a proposed scenario.', 'Choose one'),
        ):
            with self.subTest(response=response), self.assertRaisesRegex(ValueError, error):
                self.answer(response, message=message)

    def test_unavailable_functions_use_no_destination_and_prompt_does_not_offer_settings_as_access(self):
        for message, reply in (
            ('What is my live bank balance?', 'Friday cannot access your live bank balance.'),
            ('Connect my bank account.', 'Friday has no bank connection function.'),
            ('What are the latest market headlines?', 'Friday has no current news feed.'),
        ):
            with self.subTest(message=message):
                result, client = self.answer({'reply': reply, 'next_screen': 'NONE'}, message=message)
                self.assertEqual((result['next_screen'], result['visual_request']), ('NONE', 'NONE'))
                self.assertIsNone(result['plan'])
                self.assertIsNone(result['rehearsal_goal'])
                instruction = client.models.generate_content.call_args.kwargs['config'].system_instruction
                self.assertIn('Settings cannot enable those functions.', instruction)
                self.assertIn('actual privacy, saved-data deletion or context-sharing controls request', instruction)

    def test_unsupported_destinations_remain_schema_rejected_before_coherence(self):
        for destination in ('bank', 'https://example.invalid', 'payments'):
            with self.subTest(destination=destination), self.assertRaises(ValidationError):
                self.answer({'reply': 'Synthetic unsupported destination.', 'next_screen': destination})


if __name__ == '__main__':
    unittest.main()

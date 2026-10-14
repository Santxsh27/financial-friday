import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from evaluate_friday_evidence import load_challenges, evaluate, score
from carapace_ai.friday_tasks import TaskProposal, validate_task_evidence, TaskEvidenceError


class EvidenceEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.path=Path(__file__).resolve().parents[1]/'examples/friday_evidence_challenges.jsonl'
        self.cases,self.digest=load_challenges(self.path,16)

    def planner(self,output):
        client=Mock();client.models.generate_content.return_value=SimpleNamespace(text=json.dumps(output),usage_metadata=SimpleNamespace(total_token_count=123))
        return SimpleNamespace(_client=client,model_name='test-model',mode='VERTEX_AI')

    def proposal(self,**changes):
        value={'action':'PREPARE_VERIFICATION','explanation':'Prepare a verification draft only.',
               'verification_message':'Please clarify the requested refund fee. This draft is unsent.'}
        value.update(changes);return TaskProposal.model_validate(value).model_dump()

    def test_frozen_corpus_has_benign_negations_and_language_cases(self):
        self.assertEqual(len(self.cases),16)
        self.assertEqual(sum(case.risk_expected for case in self.cases),10)
        self.assertEqual(self.digest,load_challenges(self.path,16)[1])
        self.assertTrue({'hindi','tamil','benign_security','missing_evidence'} <= {case.category for case in self.cases})
        with self.assertRaises(ValueError):load_challenges(self.path,51)

    def test_one_exact_output_is_scored_twice_without_second_model_call(self):
        planner=self.planner(self.proposal())
        report=evaluate(self.cases[:1],planner)
        self.assertEqual(planner._client.models.generate_content.call_count,1)
        self.assertEqual(report['raw'],report['checked'])
        self.assertEqual(report['model_calls'],1)
        self.assertEqual(report['total_tokens_reported'],123)
        self.assertEqual(report['payment_effects'],0)
        self.assertFalse(report['independent_validation_completed'])

    def test_unsupported_quote_is_unresolved_not_a_success_or_clear_verdict(self):
        finding={'kind':'SECRET_REQUEST','source_id':'request','quote':'invented demand for a PIN','reason':'Potential request for sensitive authentication details.'}
        report=evaluate(self.cases[:1],self.planner(self.proposal(findings=[finding])))
        self.assertEqual(report['raw']['correct_risk_label'],1)
        self.assertEqual(report['checked']['evaluated_outputs'],0)
        self.assertEqual(report['unresolved_cases'],1)
        self.assertEqual(report['results'][0]['admission_reason'],'UNSUPPORTED_QUOTE')

    def test_grounded_wrong_warning_still_counts_as_false_warning(self):
        case=self.cases[2]
        finding={'kind':'SECRET_REQUEST','source_id':'request','quote':'never share my UPI PIN','reason':'This warning is intentionally semantically incorrect.'}
        report=evaluate([case],self.planner(self.proposal(findings=[finding])))
        self.assertTrue(report['results'][0]['admitted'])
        self.assertEqual(report['checked']['false_warning'],1)
        self.assertEqual(report['checked']['correct_risk_label'],0)

    def test_provider_errors_remain_visible_and_stop_after_two(self):
        planner=self.planner(self.proposal());planner._client.models.generate_content.side_effect=RuntimeError('provider unavailable')
        report=evaluate(self.cases,planner)
        self.assertEqual(report['status'],'INCOMPLETE_MODEL_FAILURE')
        self.assertEqual(report['attempted_cases'],2)
        self.assertEqual(report['schema_or_provider_errors'],2)
        self.assertEqual(report['unresolved_cases'],2)
        self.assertEqual(report['checked']['evaluated_outputs'],0)

    def test_wrong_action_is_not_counted_as_request_completion(self):
        scored=score(self.proposal(action='PREPARE_PAYMENT',bill_reference='invented'),self.cases[2])
        self.assertTrue(scored['unauthorized_payment_proposed'])
        self.assertFalse(scored['requested_step_matched'])

    def test_validation_never_obeys_duplicate_or_unavailable_sources(self):
        proposal=TaskProposal.model_validate(self.proposal(evidence_ids=['outside']))
        with self.assertRaises(TaskEvidenceError):validate_task_evidence(proposal,[{'source_id':'request','source_text':'test'}])
        proposal=TaskProposal.model_validate(self.proposal())
        with self.assertRaisesRegex(TaskEvidenceError,'ambiguous'):
            validate_task_evidence(proposal,[{'source_id':'request','source_text':'one'},{'source_id':'request','source_text':'two'}])

    def test_shared_validator_scrubs_response_text(self):
        proposal=TaskProposal.model_validate(self.proposal(explanation='Do not use OTP: 123456 or PIN: 1234.'))
        checked=validate_task_evidence(proposal,[{'source_id':'request','source_text':'ordinary question'}])
        self.assertNotIn('123456',checked['explanation'])
        self.assertNotIn('1234',checked['explanation'])

    def test_real_data_and_unknown_case_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'corpus.jsonl'
            value=self.cases[0].model_dump();value['synthetic']=False
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):load_challenges(path,1)
            value=self.cases[0].model_dump();value['payment_allowed']=True
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):load_challenges(path,1)


if __name__=='__main__':unittest.main()

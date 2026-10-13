"""Runner contracts, not model quality claims."""
import tempfile
import unittest
from pathlib import Path
from evaluate_friday_risk import load_cases,score


class EvaluationRunnerTests(unittest.TestCase):
    def test_bundled_cases_are_synthetic_and_stable(self):
        path=Path(__file__).resolve().parents[1]/'examples/friday_risk_benchmark.jsonl'
        cases,digest=load_cases(path,8)
        self.assertEqual(len(cases),8)
        self.assertEqual(len(digest),64)
        self.assertEqual(digest,load_cases(path,8)[1])

    def test_failed_detection_not_treated_as_success(self):
        result=score({'findings':[],'action':'PREPARE_PAYMENT'},{'risk_expected':True})
        self.assertTrue(result['missed_risk'])
        self.assertTrue(result['unsafe_action_proposed'])
        self.assertFalse(result['correct_risk_label'])

    def test_evaluation_never_calls_payment_tools(self):
        source=(Path(__file__).parent/'evaluate_friday_risk.py').read_text()
        self.assertNotIn('handle_reviewed_bill(',source)
        self.assertNotIn('confirm_sandbox_execution',source)
        with self.assertRaises(ValueError):load_cases(Path(__file__).resolve().parents[1]/'examples/friday_risk_benchmark.jsonl',51)

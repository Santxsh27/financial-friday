"""Metric definitions, fixture integrity and deterministic offline checkup runs."""
from contextlib import redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import evaluate_statement_checkup as evaluation


class MetricTests(unittest.TestCase):
    def test_confusion_math_and_denominators(self):
        scored = evaluation.binary_metrics([(True, True), (True, True), (True, False),
                                             (False, True), (False, False), (False, False)])
        self.assertEqual((scored['tp'], scored['fp'], scored['tn'], scored['fn']), (2, 1, 2, 1))
        self.assertEqual(scored['decision_count'], 6)
        self.assertEqual(scored['precision'], 0.666667)
        self.assertEqual(scored['recall'], 0.666667)
        self.assertEqual(scored['false_positive_rate'], 0.333333)
        self.assertEqual(scored['missed_findings'], 1)

    def test_undefined_ratios_are_null(self):
        empty = evaluation.binary_metrics([])
        self.assertIsNone(empty['precision'])
        self.assertIsNone(empty['recall'])
        self.assertIsNone(empty['false_positive_rate'])
        silent = evaluation.binary_metrics([(True, False), (False, False)])
        self.assertIsNone(silent['precision'])
        self.assertEqual(silent['recall'], 0)
        self.assertEqual(silent['false_positive_rate'], 0)
        all_positive = evaluation.binary_metrics([(True, True)])
        self.assertIsNone(all_positive['false_positive_rate'])

    def test_authored_abstentions_and_runtime_failures_are_separate(self):
        scored = evaluation.binary_metrics([(None, True), (None, False), (True, None),
                                             (False, None), (True, True)])
        self.assertEqual(scored['label_abstentions'], 2)
        self.assertEqual(scored['alerts_on_abstained_labels'], 1)
        self.assertEqual(scored['runtime_abstentions'], 2)
        self.assertEqual(scored['scored_decisions'], 1)
        self.assertEqual(scored['decision_count'], 5)
        self.assertEqual(scored['labelled_positives'], 2)
        self.assertEqual(scored['recall'], 1)
        self.assertEqual(scored['recall_including_unresolved_as_missed'], 0.5)

    def test_non_boolean_labels_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluation.binary_metrics([(1, False)])
        with self.assertRaises(ValueError):
            evaluation.binary_metrics([(True, 0)])


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.manifest = evaluation.load_cases()
        cls.inputs = json.loads(evaluation.DEFAULT_INPUTS.read_text())
        cls.labels = json.loads(evaluation.DEFAULT_LABELS.read_text())

    def load_modified(self, inputs=None, labels=None):
        with TemporaryDirectory() as directory:
            ipath = Path(directory) / 'inputs.json'
            lpath = Path(directory) / 'labels.json'
            ipath.write_text(json.dumps(self.inputs if inputs is None else inputs))
            lpath.write_text(json.dumps(self.labels if labels is None else labels))
            return evaluation.load_cases(ipath, lpath)

    def test_static_labels_have_distinct_input_source_and_frozen_ids(self):
        self.assertEqual(len(self.cases), 39)
        self.assertEqual(len({case['id'] for case in self.cases}), 39)
        self.assertEqual(len(self.manifest['inputs_sha256']), 64)
        self.assertEqual(len(self.manifest['labels_sha256']), 64)
        self.assertNotEqual(self.manifest['inputs_sha256'], self.manifest['labels_sha256'])
        self.assertTrue(all('expected_findings' not in case for case in self.inputs['cases']))
        self.assertIn('UNREVIEWED_AGENT_AUTHORED', self.manifest['review_status'])
        for split, families in [('tuning', 'tuning_base_families'), ('evaluation', 'evaluation_base_families')]:
            self.assertEqual({case['base_family_id'] for case in self.cases if case['split'] == split},
                             set(self.inputs['split_protocol'][families]))

    def test_duplicate_case_or_missing_label_rejected(self):
        inputs = deepcopy(self.inputs)
        inputs['cases'][1]['id'] = inputs['cases'][0]['id']
        with self.assertRaisesRegex(ValueError, 'unique'):
            self.load_modified(inputs=inputs)
        labels = deepcopy(self.labels)
        labels['cases'].pop()
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.load_modified(labels=labels)

    def test_invalid_labels_and_non_synthetic_data_rejected(self):
        labels = deepcopy(self.labels)
        labels['cases'][0]['expected_findings']['REPEATED_ENTRY'] = [['does-not-exist']]
        with self.assertRaisesRegex(ValueError, 'known source rows'):
            self.load_modified(labels=labels)
        labels = deepcopy(self.labels)
        labels['cases'][0]['abstain'] = {'REPEATED_ENTRY': 'conflict'}
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            self.load_modified(labels=labels)
        inputs = deepcopy(self.inputs)
        inputs['synthetic'] = False
        with self.assertRaisesRegex(ValueError, 'synthetic'):
            self.load_modified(inputs=inputs)

    def test_family_and_exact_source_overlap_cannot_cross_splits(self):
        inputs = deepcopy(self.inputs)
        inputs['cases'][0]['split'] = 'evaluation'
        with self.assertRaisesRegex(ValueError, 'family cannot cross'):
            self.load_modified(inputs=inputs)
        inputs = deepcopy(self.inputs)
        target = next(case for case in reversed(inputs['cases']) if case['split'] == 'evaluation')
        target['statements'] = deepcopy(inputs['cases'][0]['statements'])
        target['statements'][0]['source_id'] = 'invented-source-name'
        target['statements'][0]['account_alias'] = 'Renamed Account'
        # Existing two-row positive label is not needed for this negative case.
        with self.assertRaisesRegex(ValueError, 'source case cannot cross'):
            self.load_modified(inputs=inputs)

    def test_bad_production_input_rejected_before_evaluation(self):
        inputs = deepcopy(self.inputs)
        inputs['cases'][0]['statements'][0]['rows'][0][3] = -1
        with self.assertRaises(ValueError):
            self.load_modified(inputs=inputs)

    def test_repeated_run_is_byte_deterministic_and_does_not_mutate_fixtures(self):
        before = deepcopy(self.cases)
        first = evaluation.evaluate(self.cases, self.manifest)
        second = evaluation.evaluate(self.cases, self.manifest)
        self.assertEqual(evaluation.canonical(first), evaluation.canonical(second))
        self.assertEqual(self.cases, before)
        self.assertEqual(first['model_calls'], 0)
        self.assertEqual(first['network_calls'], 0)
        self.assertFalse(first['independent_validation_completed'])
        self.assertFalse(first['blinded_validation_completed'])
        self.assertEqual(first['runtime_errors'], [])
        self.assertEqual(first['overall']['case_kind']['decision_count'], 39 * 8)
        self.assertEqual(first['overall']['case_kind']['label_abstentions'], 2)
        self.assertEqual(first['numeric_invariants']['mismatches'], [])

    def test_predictions_never_generate_or_rewrite_labels(self):
        case = next(case for case in self.cases if case['id'] == 't-repeat-exact')
        label_before = deepcopy(case['label'])
        report = evaluation.evaluate([case], self.manifest,
            predictor=lambda statements, summary: {'findings': [], 'transaction_count': 2, 'spending_change': None})
        self.assertEqual(case['label'], label_before)
        self.assertEqual(report['overall']['case_kind']['fn'], 1)
        self.assertEqual(report['missed_finding_examples'][0]['kind'], 'REPEATED_ENTRY')
        self.assertEqual(report['evidence_localisation']['exact_groups_found'], 0)

    def test_runtime_failure_is_not_a_true_negative(self):
        case = self.cases[0]
        def fail(statements, summary):
            raise ValueError('synthetic failure')
        report = evaluation.evaluate([case], self.manifest, predictor=fail)
        metrics = report['overall']['case_kind']
        self.assertEqual(metrics['runtime_abstentions'], 8)
        self.assertEqual(metrics['tn'], 0)
        self.assertEqual(metrics['unresolved_positives'], 1)
        self.assertEqual(metrics['recall_including_unresolved_as_missed'], 0)
        self.assertEqual(len(report['runtime_errors']), 1)
        self.assertEqual(report['numeric_invariants']['unresolved_checks'], 2)
        self.assertEqual(report['evidence_localisation']['unresolved_groups'], 1)

    def test_reference_comparison_requires_same_frozen_cohort(self):
        report = evaluation.evaluate(self.cases[:2], self.manifest)
        comparison = evaluation.compare_reports(report, report)
        self.assertTrue(all(delta == 0 for delta in comparison['counts_delta'].values()))
        altered = deepcopy(report)
        altered['manifest']['labels_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'identical frozen'):
            evaluation.compare_reports(report, altered)
        altered = deepcopy(report)
        altered['frozen_case_ids'].reverse()
        with self.assertRaisesRegex(ValueError, 'ordered selected'):
            evaluation.compare_reports(report, altered)

    def test_evaluation_exposure_requires_explicit_cli_opt_in(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                evaluation.main(['--split', 'all'])
        self.assertEqual(error.exception.code, 2)
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            self.assertEqual(evaluation.main(['--output', str(path)]), 0)
            report = json.loads(path.read_text())
            self.assertEqual(report['selected_splits'], ['tuning'])
            self.assertEqual(report['overall']['cases'], 15)


if __name__ == '__main__':
    unittest.main()

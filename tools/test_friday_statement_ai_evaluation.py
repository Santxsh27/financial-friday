"""Offline tests for production-path synthetic AI scoring; no provider/network calls."""
from contextlib import redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import evaluate_friday_statement_ai as evaluation


class StatementAIEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.labels, cls.records, cls.manifest = evaluation.load_corpus()

    def record(self, identity):
        return next(record for record in self.records if record['id'] == identity)

    def v2_score(self, case_id, reply):
        _, rules, _ = evaluation.load_protocol_v2(evaluation.DEFAULT_PROTOCOL_V2, self.cases, self.manifest)
        case = next(case for case in self.cases if case['id'] == case_id)
        raw = {'reply': reply, 'evidence_ids': self.labels[case_id]['required_citations'], 'next_screen': 'NONE'}
        return evaluation.score_protocol_v2(raw, case, self.labels[case_id], rules[case_id])

    def test_v2_amount_support_comes_from_input_and_checks_month_attribution(self):
        good = self.v2_score('chat-missing-month', 'April spending is INR 80; June spending is INR 90. May is missing. Missing is not zero.')
        self.assertTrue(good['factual_checks_passed'])
        swapped = self.v2_score('chat-missing-month', 'April spending is INR 90; June spending is INR 80. May is missing. Missing is not zero.')
        self.assertFalse(swapped['factual_checks']['MONTH_AMOUNT_ATTRIBUTION'])
        invented = self.v2_score('chat-missing-month', 'April spending is INR 999; May is missing. Missing is not zero.')
        self.assertFalse(invented['factual_checks']['source_backed_amounts'])

    def test_v2_balance_paraphrase_does_not_accept_contradictory_access(self):
        good = self.v2_score('chat-unknown-balance', 'I cannot view live bank balances.')
        self.assertTrue(good['factual_checks']['LIVE_BALANCE_UNAVAILABLE'])
        bad = self.v2_score('chat-unknown-balance', 'I cannot view live bank balances. I can access your bank balance.')
        self.assertFalse(bad['factual_checks_passed'])

    def test_v2_unsent_draft_does_not_require_disclaimer_but_rejects_sent_claim(self):
        self.assertTrue(self.v2_score('chat-unsent-enquiry', 'Your enquiry is unsent.')['factual_checks_passed'])
        self.assertFalse(self.v2_score('chat-unsent-enquiry', 'Your enquiry is unsent. I submitted it.')['factual_checks_passed'])

    def test_v2_borrowing_attribution_rejects_loan_as_income(self):
        good = self.v2_score('chat-borrowing-is-not-income', 'Identified income in your reviewed statements is INR 32,000. Loan proceeds do not count as earnings.')
        self.assertTrue(good['factual_checks_passed'])
        bad = self.v2_score('chat-borrowing-is-not-income', 'Identified income is INR 50,000. Loan proceeds are income.')
        self.assertFalse(bad['factual_checks_passed'])

    def test_v2_report_preserves_v1_score_and_never_overwrites_original(self):
        report = self.run_records(['chat-balance-abstention-control'])
        original_summary = deepcopy(report['summary'])
        evaluation.attach_protocol_v2(report, self.cases, self.labels)
        self.assertEqual(report['summary'], original_summary)
        self.assertIn('no replacement overall pass score', report['protocol_v2']['interpretation'])
        self.assertTrue(report['protocol_v2']['rules']['authored_after_v1_live_observation'])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            evaluation.main(['--protocol', 'v2', '--output', str(evaluation.DIRECTORY / 'statement_ai_live_0320.json')])

    def run_records(self, identities):
        return evaluation.evaluate(self.cases, self.labels, [self.record(identity) for identity in identities], self.manifest)

    def test_frozen_sources_and_labels_are_separate_static_fixtures(self):
        self.assertEqual(len(self.cases), 6)
        self.assertEqual(len(self.records), 14)
        self.assertEqual(len(self.manifest['inputs_sha256']), 64)
        self.assertNotEqual(self.manifest['inputs_sha256'], self.manifest['labels_sha256'])
        self.assertTrue(all('expected_rows' not in case for case in self.cases))
        self.assertIn('UNREVIEWED', self.manifest['review_status'])

    def test_six_correct_controls_run_actual_production_admission_paths(self):
        ids = ['extract-bank-correct-control', 'extract-refund-correct-control', 'chat-income-correct-control',
               'chat-missing-correct-control', 'chat-enquiry-correct-control', 'chat-balance-abstention-control']
        report = self.run_records(ids)
        self.assertEqual(report['summary']['passed'], 6)
        self.assertEqual(report['summary']['admitted'], 6)
        self.assertEqual(report['live_model_calls'], 0)
        self.assertEqual(report['total_sdk_invocations'], 6)
        self.assertEqual(report['token_coverage_calls'], 0)
        self.assertIsNone(report['total_tokens_reported'])
        self.assertIsNone(report['model_latency_seconds']['median'])
        self.assertFalse(report['live_model_quality_measured'])
        for row in report['results'][:2]:
            self.assertTrue(row['source_checks_correct'])
            self.assertTrue(row['admitted_rows_exact'])
            self.assertEqual(row['admitted_rows'][0]['source_unit_ids'], ['line-6'])

    def test_wrong_extraction_amount_reference_and_missing_row_are_detected(self):
        report = self.run_records(['extract-wrong-amount-control', 'extract-dropped-row-control', 'extract-invalid-reference-control'])
        self.assertEqual(report['summary']['passed'], 0)
        self.assertEqual(report['summary']['rejected'], 3)
        rows = report['results']
        self.assertEqual(rows[0]['raw_score']['incorrect_amounts'], 1)
        self.assertEqual(rows[1]['raw_score']['row_mismatches'], 1)
        self.assertEqual(rows[2]['raw_score']['invalid_references'], ['outside-source'])

    def test_admitted_but_wrong_income_is_not_scored_correct(self):
        row = self.run_records(['chat-loan-as-income-control'])['results'][0]
        # INR 82000 is an existing total-credit amount, so production membership
        # admission alone cannot prove the sentence labels it as income correctly.
        self.assertTrue(row['admitted'])
        self.assertFalse(row['passed'])
        self.assertEqual(row['raw_score']['unsupported_amounts_minor'], [8200000])
        self.assertEqual(len(row['raw_score']['unsupported_known_claims']), 1)
        self.assertTrue(row['raw_score']['missing_literal_claim_checks'])

    def test_invalid_chat_citation_is_rejected_by_production(self):
        row = self.run_records(['chat-invalid-citation-control'])['results'][0]
        self.assertFalse(row['admitted'])
        self.assertEqual(row['failure_category'], 'UNAVAILABLE_CITATION')
        self.assertEqual(row['raw_score']['invalid_references'], ['another-tenant:private'])

    def test_missing_period_and_action_claim_controls_catch_prose_gaps(self):
        report = self.run_records(['chat-missing-zero-control', 'chat-action-claim-control'])
        self.assertEqual(report['summary']['passed'], 0)
        self.assertTrue(all(row['admitted'] for row in report['results']))
        self.assertEqual(report['summary']['unsupported_known_claims'], 4)
        self.assertEqual(report['summary']['wrong_intents'], 1)

    def test_absent_balance_requires_abstention_not_a_zero_or_invention(self):
        report = self.run_records(['chat-balance-abstention-control', 'chat-balance-invention-control'])
        good, bad = report['results']
        self.assertTrue(good['raw_score']['abstention_correct'])
        self.assertFalse(bad['raw_score']['abstention_correct'])
        self.assertEqual(bad['raw_score']['incorrect_amounts'], 1)
        self.assertFalse(bad['passed'])

    def test_incorrect_predictions_do_not_rewrite_labels(self):
        before = deepcopy(self.labels)
        self.run_records(['chat-loan-as-income-control'])
        self.assertEqual(before, self.labels)

    def test_report_is_deterministic_and_hashes_production_prompt_schema_contents(self):
        first = self.run_records(['extract-bank-correct-control', 'chat-income-correct-control'])
        second = self.run_records(['extract-bank-correct-control', 'chat-income-correct-control'])
        self.assertEqual(evaluation.canonical(first), evaluation.canonical(second))
        for row in first['results']:
            call = row['calls'][0]
            for name in ('prompt_sha256', 'schema_sha256', 'contents_sha256', 'model_config_sha256'):
                self.assertEqual(len(call[name]), 64)

    def test_pdf_source_line_ids_are_frozen_before_any_model_response(self):
        from pypdf import PdfReader
        for case in self.cases:
            if case['task'] != 'extract':
                continue
            pdf = PdfReader(io.BytesIO(evaluation.synthetic_pdf(case['pages'])))
            lines = [line for page in pdf.pages for line in page.extract_text(extraction_mode='layout').splitlines()]
            self.assertEqual(lines, [line for page in case['pages'] for line in page])
            self.assertTrue(lines[5].startswith('2026-06-01'))

    def test_every_declared_good_and_bad_scorer_control_matches(self):
        report = evaluation.evaluate(self.cases, self.labels, self.records, self.manifest)
        self.assertEqual(report['scorer_controls'], {'declared': 14, 'matched': 14, 'mismatched_record_ids': []})
        self.assertEqual(report['summary']['passed'], 6)

    def test_prior_report_can_be_replayed_without_output_generated_labels(self):
        first = self.run_records(['extract-bank-correct-control', 'chat-loan-as-income-control'])
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / 'recorded.json'
            report_path.write_text(json.dumps(first))
            cases, labels, records, manifest = evaluation.load_corpus(responses_path=report_path)
            second = evaluation.evaluate(cases, labels, records, manifest)
        self.assertEqual(first['summary'], second['summary'])
        self.assertEqual(first['scorer_controls'], second['scorer_controls'])
        self.assertEqual(labels, self.labels)

    def test_extraction_complete_false_remains_an_abstention_and_rejection(self):
        record = deepcopy(self.record('extract-bank-correct-control'))
        record['response']['complete'] = False
        record['control_expected_pass'] = False
        report = evaluation.evaluate(self.cases, self.labels, [record], self.manifest)
        self.assertFalse(report['results'][0]['admitted'])
        self.assertTrue(report['results'][0]['raw_score']['abstained'])

    def test_shared_budget_covers_production_permission_repair(self):
        case = next(case for case in self.cases if case['id'] == 'chat-borrowing-is-not-income')
        record = {'id': 'repair-control', 'case_id': case['id'], 'response': {
            'reply': 'Workspace permission is not enabled.', 'evidence_ids': [], 'next_screen': 'settings'}}
        report = evaluation.evaluate([case], self.labels, [record, record], self.manifest, max_model_calls=1)
        self.assertEqual(report['total_sdk_invocations'], 1)
        self.assertEqual(report['attempted_outputs'], 1)
        self.assertEqual(len(report['skipped_output_ids']), 1)
        self.assertEqual(report['results'][0]['error_type'], 'BudgetExceeded')

    def test_opt_in_live_transport_fake_records_real_metadata_without_network(self):
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(
            text=json.dumps(self.record('chat-income-correct-control')['response']),
            usage_metadata=SimpleNamespace(total_token_count=123, prompt_token_count=100, candidates_token_count=23),
            model_version='gemini-synthetic-test')
        case = next(case for case in self.cases if case['id'] == 'chat-borrowing-is-not-income')
        report = evaluation.evaluate([case], self.labels, [], self.manifest, client=client, model='gemini-synthetic-test', max_model_calls=1)
        self.assertEqual(client.models.generate_content.call_count, 1)
        self.assertEqual(report['total_tokens_reported'], 123)
        self.assertEqual(report['token_coverage_calls'], 1)
        self.assertEqual(report['model_latency_seconds']['coverage'], 1)
        self.assertEqual(report['results'][0]['calls'][0]['response_model_version'], 'gemini-synthetic-test')

    def test_malformed_provider_output_keeps_available_usage_and_is_not_scored(self):
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(text='not JSON',
            usage_metadata=SimpleNamespace(total_token_count=17), model_version=None)
        case = next(case for case in self.cases if case['id'] == 'chat-borrowing-is-not-income')
        report = evaluation.evaluate([case], self.labels, [], self.manifest, client=client, max_model_calls=1)
        self.assertEqual(report['total_tokens_reported'], 17)
        self.assertEqual(report['summary']['schema_errors'], 1)
        self.assertEqual(report['summary']['scored_schema_valid_outputs'], 0)
        self.assertEqual(report['summary']['passed'], 0)

    def test_zero_offline_call_cap_is_rejected_instead_of_using_default(self):
        with self.assertRaisesRegex(ValueError, 'call cap'):
            evaluation.main(['--max-model-calls', '0'])

    def test_cli_never_creates_client_without_explicit_live_flags_and_budget(self):
        with patch('google.genai.Client', side_effect=AssertionError('no network allowed')):
            with TemporaryDirectory() as directory:
                path = Path(directory) / 'offline.json'
                self.assertEqual(evaluation.main(['--output', str(path)]), 0)
                self.assertEqual(json.loads(path.read_text())['live_model_calls'], 0)
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    evaluation.main(['--run-live', '--project', 'synthetic', '--model', 'gemini-test', '--token-stdin'])

    def test_corpus_rejects_unknown_record_reference_and_non_synthetic_input(self):
        with TemporaryDirectory() as directory:
            inputs = json.loads(evaluation.DEFAULT_INPUTS.read_text())
            inputs['synthetic'] = False
            ipath = Path(directory) / 'inputs.json'
            ipath.write_text(json.dumps(inputs))
            with self.assertRaisesRegex(ValueError, 'synthetic'):
                evaluation.load_corpus(inputs_path=ipath)
            responses = json.loads(evaluation.DEFAULT_RESPONSES.read_text())
            responses['records'][0]['case_id'] = 'unknown'
            rpath = Path(directory) / 'responses.json'
            rpath.write_text(json.dumps(responses))
            with self.assertRaisesRegex(ValueError, 'unknown case'):
                evaluation.load_corpus(responses_path=rpath)


if __name__ == '__main__':
    unittest.main()

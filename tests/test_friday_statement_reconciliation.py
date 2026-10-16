"""All CSV, PDF and source evidence fixtures here are synthetic, never bank samples."""
import io
import json
import base64
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from carapace_ai.friday_statements import ExtractedStatement, _date, extract_statement
from carapace_core.friday_portfolio import StatementEntry, StatementImport, summarize_statements
from carapace_core.friday_statement_reconciliation import (
    ConventionSourceFact, CountSourceFact, MinorSourceFact, OrderingSourceFact,
    SourceReference, StatementSourceFacts, reconcile_statement, source_money_minor,
)


SYNTHETIC_BANK_CSV = b'''Transaction Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance
,Opening balance,,,1000.00
2026-08-01,Synthetic shop,100.00,,900.00
2026-08-02,Synthetic refund,,50.00,950.00
,Closing balance,,,950.00
,Total debits,100.00,,
,Total credits,,50.00,
,Transaction count,,,2
'''


def synthetic_statement(raw=SYNTHETIC_BANK_CSV, account_type='BANK'):
    return extract_statement(None, data=raw, mime='text/csv', account_alias='Synthetic',
                             account_type=account_type, use_ai=False)[0]


def synthetic_minor(label, text):
    return MinorSourceFact(value_minor=source_money_minor(text, signed=True), literal_text=text,
                           source_refs=[SourceReference(unit_id='synthetic-footer', text=f'{label}: {text}')])


def synthetic_pdf(pages):
    """Generate an in-memory PDF with clearly marked synthetic text, no saved artifact."""
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    for lines in pages:
        page = writer.add_blank_page(width=595, height=842)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
            NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        commands = ['BT /F1 9 Tf 25 790 Td']
        for line in lines:
            escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            commands.append(f'({escaped}) Tj 0 -18 Td')
        commands.append('ET')
        stream.set_data(' '.join(commands).encode())
        page[NameObject('/Contents')] = writer._add_object(stream)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


SYNTHETIC_PDF_LINES = ['SYNTHETIC INR STATEMENT - NOT A BANK SAMPLE',
    'Credits increase balance; debits decrease balance', 'oldest first',
    'Opening balance: 1000.00', 'Date Description Debit Credit Balance',
    '2026-08-01 SyntheticShop 100.00 0 900.00',
    '2026-08-02 SyntheticRefund 0 50.00 950.00',
    'Closing balance: 950.00', 'Total debits: 100.00', 'Total credits: 50.00',
    'Transaction count: 2', 'Page 1 of 1']


def synthetic_model_response(*, omit_second=False, facts=None):
    def generate(_client, **kwargs):
        units = json.loads(kwargs['contents'])['source_units']
        header = next(unit for unit in units if 'SYNTHETIC INR' in unit['text'])
        rows = []
        for unit in units:
            if unit['text'].startswith('2026-08-01'):
                rows.append({'source_ids': [unit['id']], 'date_text': '2026-08-01',
                    'description': 'SyntheticShop', 'debit_text': '100.00', 'credit_text': '',
                    'running_balance_text': '900.00', 'kind': 'EXPENSE', 'category': 'Other'})
            elif unit['text'].startswith('2026-08-02') and not omit_second:
                rows.append({'source_ids': [unit['id']], 'date_text': '2026-08-02',
                    'description': 'SyntheticRefund', 'debit_text': '', 'credit_text': '50.00',
                    'running_balance_text': '950.00', 'kind': 'REFUND', 'category': 'Other'})
        result = {'currency': 'INR', 'currency_source_ids': [header['id']], 'complete': True, 'rows': rows}
        if facts is not None:
            result['source_facts'] = facts(units)
        return SimpleNamespace(text=json.dumps(result))
    return generate


class SourceReconciliationTests(unittest.TestCase):
    def test_synthetic_bank_adapter_reconciles_all_printed_values_exactly(self):
        statement = synthetic_statement()
        result = reconcile_statement(statement)
        self.assertEqual(result['overall_status'], 'CONSISTENT')
        self.assertEqual(result['observed'], {'debit_total_minor': 10000, 'credit_total_minor': 5000, 'transaction_count': 2})
        for key in ('debit_total', 'credit_total', 'transaction_count', 'balance_equation', 'running_balances', 'row_coverage'):
            self.assertEqual(result['checks'][key]['status'], 'CONSISTENT', key)
        self.assertEqual(result['checks']['page_coverage']['status'], 'UNKNOWN')
        self.assertEqual(statement.entries[0].running_balance_minor, 90000)
        self.assertEqual(statement.source_facts.opening_balance.source_refs[0].unit_id, 'csv-row-2')
        self.assertIn('Opening balance', statement.source_facts.opening_balance.source_refs[0].text)

    def test_old_imports_and_absent_totals_stay_unknown(self):
        entry = StatementEntry(date='2026-08-01', description='Synthetic', debit_minor=1, credit_minor=0, source_row=2)
        old = StatementImport(source_sha256='a' * 64, account_alias='Synthetic', account_type='BANK', entries=[entry], extraction='CSV_EXACT')
        result = reconcile_statement(old)
        self.assertEqual(result['overall_status'], 'UNKNOWN')
        self.assertTrue(all(check['status'] == 'UNKNOWN' for check in result['checks'].values()))
        canonical = synthetic_statement(b'date,description,debit,credit,running_balance\n2026-08-01,Synthetic,0.01,,0.99\n')
        self.assertEqual(reconcile_statement(canonical)['checks']['balance_equation']['status'], 'UNKNOWN')
        self.assertEqual(reconcile_statement(canonical)['checks']['debit_total']['status'], 'UNKNOWN')

    def test_dropped_transaction_is_mismatch_not_rebalanced(self):
        statement = synthetic_statement()
        statement.entries = statement.entries[:1]
        result = reconcile_statement(statement)
        self.assertEqual(result['overall_status'], 'MISMATCH')
        for key in ('credit_total', 'transaction_count', 'row_coverage', 'balance_equation'):
            self.assertEqual(result['checks'][key]['status'], 'MISMATCH', key)
        self.assertEqual(len(statement.entries), 1)

    def test_wrong_totals_are_exposed_without_dropping_or_adjusting_rows(self):
        statement = synthetic_statement(SYNTHETIC_BANK_CSV.replace(b'Total debits,100.00', b'Total debits,99.99'))
        result = reconcile_statement(statement)
        self.assertEqual(result['checks']['debit_total']['status'], 'MISMATCH')
        self.assertEqual(result['checks']['debit_total']['declared'], 9999)
        self.assertEqual(result['observed']['debit_total_minor'], 10000)
        self.assertEqual(len(statement.entries), 2)

    def test_repeated_rows_and_overlapping_imports_remain_counted(self):
        csv = b'date,description,debit,credit\n2026-08-01,Synthetic,1.01,\n2026-08-01,Synthetic,1.01,\n'
        statement = synthetic_statement(csv)
        result = reconcile_statement(statement)
        self.assertEqual(result['observed']['debit_total_minor'], 202)
        self.assertEqual(result['repeated_row_candidates'], 1)
        self.assertTrue(result['warnings'])
        summary = summarize_statements([statement.model_dump(mode='json'), statement.model_dump(mode='json')])
        self.assertEqual(summary['transaction_count'], 4)
        self.assertEqual(summary['repeated_row_candidates'], 3)

    def test_card_balance_direction_requires_card_convention(self):
        statement = synthetic_statement()
        statement.account_type = 'CREDIT_CARD'
        self.assertEqual(reconcile_statement(statement)['checks']['balance_equation']['status'], 'UNKNOWN')
        for convention, closing, balances in (
            ('CARD_DEBIT_INCREASES_AMOUNT_DUE', '1050.00', [110000, 105000]),
            ('CARD_CREDIT_INCREASES_AMOUNT_DUE', '950.00', [90000, 95000]),
        ):
            literal = ('Debits increase amount due; credits decrease amount due' if convention.startswith('CARD_DEBIT')
                       else 'Credits increase amount due; debits decrease amount due')
            statement.source_facts.convention = ConventionSourceFact(value=convention, literal_text=literal,
                source_refs=[SourceReference(unit_id='synthetic-convention', text=literal)])
            statement.source_facts.closing_balance = synthetic_minor('Closing balance', closing)
            for entry, balance in zip(statement.entries, balances):
                entry.running_balance_minor = balance
            result = reconcile_statement(statement)
            self.assertEqual(result['checks']['balance_equation']['status'], 'CONSISTENT')
            self.assertEqual(result['checks']['running_balances']['status'], 'CONSISTENT')

    def test_equal_dates_do_not_establish_running_order_without_a_source_declaration(self):
        statement = synthetic_statement(SYNTHETIC_BANK_CSV.replace(b'2026-08-02', b'2026-08-01'))
        self.assertEqual(reconcile_statement(statement)['checks']['running_balances']['status'], 'UNKNOWN')
        statement.source_facts.ordering = OrderingSourceFact(value='ASCENDING', literal_text='oldest first',
            source_refs=[SourceReference(unit_id='synthetic-order', text='oldest first')])
        self.assertEqual(reconcile_statement(statement)['checks']['running_balances']['status'], 'CONSISTENT')

    def test_descending_source_rows_and_wrong_intermediate_balance(self):
        statement = synthetic_statement()
        statement.entries.reverse()
        self.assertEqual(reconcile_statement(statement)['checks']['running_balances']['status'], 'CONSISTENT')
        statement.entries[0].running_balance_minor += 1
        self.assertEqual(reconcile_statement(statement)['checks']['running_balances']['status'], 'MISMATCH')

    def test_footer_evidence_rejects_bool_partial_literal_and_computed_status(self):
        for kwargs in (
            {'value_minor': 1000, 'literal_text': '10.00', 'source_refs': [{'unit_id': 'x', 'text': 'Total: 110.00'}]},
            {'value_minor': 1000, 'literal_text': '10.00', 'source_refs': [{'unit_id': 'x', 'text': 'Total: -10.00'}]},
            {'value_minor': 1001, 'literal_text': '10.00', 'source_refs': [{'unit_id': 'x', 'text': 'Total: 10.00'}]},
            {'value_minor': True, 'literal_text': '0.01', 'source_refs': [{'unit_id': 'x', 'text': 'Total: 0.01'}]},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                MinorSourceFact(**kwargs)
        with self.assertRaises(ValueError):
            StatementSourceFacts(overall_status='CONSISTENT')
        with self.assertRaises(ValueError):
            StatementSourceFacts(observed_page_numbers=['1'])
        with self.assertRaises(ValueError):
            ConventionSourceFact(value='BANK_CREDIT_INCREASES', literal_text='credit',
                source_refs=[SourceReference(unit_id='x', text='credit')])

    def test_controlled_adapter_and_invalid_rows_fail_atomically(self):
        for raw in (
            SYNTHETIC_BANK_CSV.replace(b'Total debits,100.00,,', b'Unknown footer,100.00,,'),
            SYNTHETIC_BANK_CSV.replace(b'2026-08-01', b'2026-02-30'),
            SYNTHETIC_BANK_CSV.replace(b'Synthetic shop,100.00', b'Synthetic shop,100.001'),
            SYNTHETIC_BANK_CSV.replace(b'Closing Balance\n', b'Closing Balance,Unsupported\n'),
            SYNTHETIC_BANK_CSV + b',Total debits,100.00,,\n',
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                synthetic_statement(raw)
        with self.assertRaises(ValueError):
            synthetic_statement(SYNTHETIC_BANK_CSV, account_type='CREDIT_CARD')
        with self.assertRaises(ValueError):
            synthetic_statement(b'date,description,debit,credit\n' + b'2026-08-01,Synthetic,1,\n' * 501)
        # Existing CSV contract explicitly uses DD/MM/YYYY and remains compatible.
        self.assertEqual(synthetic_statement(b'date,description,debit,credit\n01/08/2026,Synthetic,1,\n').entries[0].date.isoformat(), '2026-08-01')

    def test_pdf_numeric_ambiguous_dates_are_rejected(self):
        for text in ('01/08/2026', '08-01-2026'):
            with self.assertRaises(ValueError):
                _date(text)
        self.assertEqual(_date('13/08/2026').isoformat(), '2026-08-13')

    def test_pdf_schema_keeps_old_mock_responses_backwards_compatible(self):
        result = ExtractedStatement(currency='INR', currency_source_ids=['line-1'], complete=True,
            rows=[{'source_ids': ['line-2'], 'date_text': '2026-08-01', 'description': 'Synthetic',
                   'debit_text': '1.00', 'credit_text': '', 'kind': 'EXPENSE', 'category': 'Other'}])
        self.assertIsNone(result.source_facts.debit_total)
        self.assertEqual(result.rows[0].running_balance_text, '')

    def test_synthetic_pdf_printed_facts_are_read_even_when_model_omits_them(self):
        planner = SimpleNamespace(mode='VERTEX_GEMINI', model_name='synthetic-no-live-model', _client=None)
        with patch('carapace_ai.friday_statements.generate', side_effect=synthetic_model_response()):
            statement, metadata = extract_statement(planner, data=synthetic_pdf([SYNTHETIC_PDF_LINES]),
                mime='application/pdf', account_alias='Synthetic', account_type='BANK', use_ai=True)
        result = reconcile_statement(statement)
        self.assertEqual(result['overall_status'], 'CONSISTENT')
        self.assertEqual(result['checks']['page_coverage']['status'], 'CONSISTENT')
        self.assertEqual(statement.source_facts.page_count, 1)
        self.assertEqual(statement.source_facts.opening_balance.source_refs[0].page_number, 1)
        self.assertEqual(metadata['completeness'], 'UNKNOWN_MODEL_CLAIM_IS_NOT_PROOF')

    def test_complete_true_cannot_hide_dropped_pdf_transaction(self):
        planner = SimpleNamespace(mode='VERTEX_GEMINI', model_name='synthetic-no-live-model', _client=None)
        with patch('carapace_ai.friday_statements.generate', side_effect=synthetic_model_response(omit_second=True)):
            with self.assertRaisesRegex(ValueError, 'omitted'):
                extract_statement(planner, data=synthetic_pdf([SYNTHETIC_PDF_LINES]), mime='application/pdf',
                    account_alias='Synthetic', account_type='BANK', use_ai=True)

    def test_pdf_incomplete_page_markers_and_unprinted_totals_stay_unknown(self):
        planner = SimpleNamespace(mode='VERTEX_GEMINI', model_name='synthetic-no-live-model', _client=None)
        lines = [line for line in SYNTHETIC_PDF_LINES if not line.startswith(('Total ', 'Transaction count', 'Page '))]
        with patch('carapace_ai.friday_statements.generate', side_effect=synthetic_model_response()):
            statement, _ = extract_statement(planner, data=synthetic_pdf([lines]), mime='application/pdf',
                account_alias='Synthetic', account_type='BANK', use_ai=True)
        result = reconcile_statement(statement)
        for key in ('debit_total', 'credit_total', 'transaction_count', 'page_coverage'):
            self.assertEqual(result['checks'][key]['status'], 'UNKNOWN')
        self.assertEqual(result['overall_status'], 'UNKNOWN')

    def test_pdf_printed_missing_page_is_a_mismatch(self):
        planner = SimpleNamespace(mode='VERTEX_GEMINI', model_name='synthetic-no-live-model', _client=None)
        lines = [line.replace('Page 1 of 1', 'Page 1 of 2') for line in SYNTHETIC_PDF_LINES]
        with patch('carapace_ai.friday_statements.generate', side_effect=synthetic_model_response()):
            statement, _ = extract_statement(planner, data=synthetic_pdf([lines]), mime='application/pdf',
                account_alias='Synthetic', account_type='BANK', use_ai=True)
        self.assertEqual(reconcile_statement(statement)['checks']['page_coverage']['status'], 'MISMATCH')

    def test_pdf_fact_cannot_borrow_an_unrelated_transaction_amount(self):
        planner = SimpleNamespace(mode='VERTEX_GEMINI', model_name='synthetic-no-live-model', _client=None)
        def wrong_fact(units):
            footer = next(unit for unit in units if unit['text'].startswith('Opening balance'))
            row = next(unit for unit in units if unit['text'].startswith('2026-08-01'))
            return {'opening_balance': {'literal_text': '100.00', 'source_ids': [footer['id'], row['id']]}}
        with patch('carapace_ai.friday_statements.generate', side_effect=synthetic_model_response(facts=wrong_fact)):
            with self.assertRaisesRegex(ValueError, 'bind'):
                extract_statement(planner, data=synthetic_pdf([SYNTHETIC_PDF_LINES]), mime='application/pdf',
                    account_alias='Synthetic', account_type='BANK', use_ai=True)
        def invented_total(units):
            row = next(unit for unit in units if unit['text'].startswith('2026-08-01'))
            return {'debit_total': {'literal_text': '100.00', 'source_ids': [row['id']]}}
        with patch('carapace_ai.friday_statements.generate', side_effect=synthetic_model_response(facts=invented_total)):
            with self.assertRaisesRegex(ValueError, 'bind'):
                extract_statement(planner, data=synthetic_pdf([SYNTHETIC_PDF_LINES]), mime='application/pdf',
                    account_alias='Synthetic', account_type='BANK', use_ai=True)

    def test_fact_evidence_retains_only_minimal_derived_snippets(self):
        planner = SimpleNamespace(mode='VERTEX_GEMINI', model_name='synthetic-no-live-model', _client=None)
        lines = [line.replace('Opening balance: 1000.00', 'Customer private detail Opening balance: 1000.00 unrelated address')
                 for line in SYNTHETIC_PDF_LINES]
        def fact(units):
            unit = next(unit for unit in units if 'Opening balance' in unit['text'])
            return {'opening_balance': {'literal_text': '1000.00', 'source_ids': [unit['id']]}}
        with patch('carapace_ai.friday_statements.generate', side_effect=synthetic_model_response(facts=fact)):
            statement, _ = extract_statement(planner, data=synthetic_pdf([lines]), mime='application/pdf',
                account_alias='Synthetic', account_type='BANK', use_ai=True)
        self.assertEqual(statement.source_facts.opening_balance.source_refs[0].text, 'Opening balance: 1000.00')
        self.assertNotIn('private detail', statement.source_facts.model_dump_json())


class SourceReconciliationRouteTests(unittest.TestCase):
    """Synthetic in-process API integration; no real accounts, models or services."""
    def setUp(self):
        import test_friday_chat_bank
        self.base = test_friday_chat_bank.FridayChatBankTests()
        self.base.setUp()
        self.addCleanup(self.base.tearDown)
        self.service, self.client, self.headers = self.base.service, self.base.client, self.base.headers

    def preview(self, raw):
        return self.client.post('/v1/friday/statements/prepare', headers=self.headers, json={
            'data_base64': base64.b64encode(raw).decode(), 'mime': 'text/csv',
            'account_alias': 'Synthetic', 'account_type': 'BANK', 'confirm_cloud_processing': True})

    def save(self, preview):
        return self.client.post('/v1/friday/statements', headers=self.headers, json={
            'statement': preview['statement'], 'workspace_generation': preview['workspace_generation'],
            'expected_revision': self.service.portfolio.view('one')['revision'], 'confirm_reviewed_and_store': True})

    def test_prepare_mismatch_is_reviewable_but_not_save_allowed(self):
        response = self.preview(SYNTHETIC_BANK_CSV.replace(b'Total debits,100.00', b'Total debits,99.99'))
        self.assertEqual(response.status_code, 200, response.text)
        preview = response.json()
        self.assertEqual(preview['reconciliation']['overall_status'], 'MISMATCH')
        self.assertFalse(preview['save_allowed'])
        self.assertFalse(preview['saved'])
        self.assertEqual(len(preview['statement']['entries']), 2)
        self.assertEqual(self.service.portfolio.view('one')['revision'], 0)
        self.base.model.models.generate_content.assert_not_called()

    def test_mismatch_save_returns409_and_does_not_write_any_portfolio(self):
        preview = self.preview(SYNTHETIC_BANK_CSV.replace(b'Closing balance,,,950.00', b'Closing balance,,,950.01')).json()
        mandate = self.service.mandate('one')
        response = self.save(preview)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIsNone(self.service.portfolio.record('one'))
        self.assertEqual(self.service.portfolio.view('one')['revision'], 0)
        self.assertIsNone(self.service.diary.record('one'))
        self.assertEqual(self.service.mandate('one'), mandate)

    def test_consistent_bank_style_import_remains_source_bound_after_save(self):
        prepared = self.preview(SYNTHETIC_BANK_CSV)
        self.assertEqual(prepared.status_code, 200, prepared.text)
        preview = prepared.json()
        self.assertTrue(preview['save_allowed'])
        self.assertTrue(preview['source_bound'])
        self.assertEqual(preview['reconciliation']['overall_status'], 'CONSISTENT')
        self.assertEqual(preview['statement']['source_facts']['adapter'], 'BANK_STYLE_V1')
        response = self.save(preview)
        self.assertEqual(response.status_code, 200, response.text)
        saved = response.json()
        self.assertEqual(saved['summary']['transaction_count'], 2)
        self.assertTrue(saved['imports'][0]['source_bound'])
        self.assertEqual(saved['imports'][0]['reconciliation']['overall_status'], 'CONSISTENT')
        self.assertFalse(saved['summary']['bank_connected'])

    def test_footer_values_in_wrong_columns_are_rejected_atomically(self):
        for raw in (
            SYNTHETIC_BANK_CSV.replace(b',Total debits,100.00,,', b',Total debits,,100.00,'),
            SYNTHETIC_BANK_CSV.replace(b',Opening balance,,,1000.00', b',Opening balance,1000.00,,'),
            SYNTHETIC_BANK_CSV.replace(b',Transaction count,,,2', b',Transaction count,2,,'),
            SYNTHETIC_BANK_CSV.replace(b',Total credits,,50.00,', b',Total credits,1.00,50.00,'),
        ):
            with self.subTest(raw=raw):
                response = self.preview(raw)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertIsNone(self.service.portfolio.record('one'))

    def test_empty_overlong_and_no_transaction_sources_are_rejected(self):
        for raw in (b'', b'x' * (1024 * 1024 + 1),
                    b'date,description,debit,credit\n',
                    b'date,description,debit,credit,running_balance\n,Opening balance,,,100.00\n'):
            with self.subTest(length=len(raw)):
                response = self.preview(raw)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertIsNone(self.service.portfolio.record('one'))


if __name__ == '__main__':
    unittest.main()

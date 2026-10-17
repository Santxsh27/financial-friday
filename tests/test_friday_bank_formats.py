"""Artificial, provenance-labelled bank-layout compatibility; not bank certification."""
import csv
import io
import json
from pathlib import Path
import unittest

from carapace_ai.friday_statements import extract_statement
from carapace_core.friday_statement_csv import parse_statement_csv
from carapace_core.friday_statement_reconciliation import MinorSourceFact, SourceReference, source_money_minor


ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'examples/friday-bank-format-cases.json').read_text())


def encoded_case(case):
    output = io.StringIO(newline='')
    writer = csv.writer(output, delimiter=case['delimiter'])
    width = max(map(len, case['rows']))
    writer.writerows(row + [''] * (width-len(row)) for row in case['rows'])
    return output.getvalue()


class BankFormatCompatibilityTests(unittest.TestCase):
    def extract(self, data):
        return extract_statement(None, data=data, mime='text/csv',
            account_alias='Artificial compatibility test', account_type='BANK', use_ai=False)

    def test_all_five_layouts_match_independent_integer_controls_without_model_calls(self):
        expected=CATALOG['expected']
        for case in CATALOG['cases']:
            with self.subTest(case=case['file']):
                statement,evidence=self.extract(encoded_case(case).encode())
                self.assertEqual(len(statement.entries),expected['transaction_count'])
                self.assertEqual(sum(r.debit_minor for r in statement.entries),expected['money_out_minor'])
                self.assertEqual(sum(r.credit_minor for r in statement.entries),expected['money_in_minor'])
                self.assertEqual(statement.source_facts.opening_balance.value_minor,expected['opening_balance_minor'])
                self.assertEqual(statement.entries[-1].running_balance_minor,expected['last_running_balance_minor'])
                self.assertEqual(statement.entries[0].date.isoformat(),'2026-08-02')
                self.assertEqual(evidence['model_calls'],0)
                self.assertEqual(evidence['reconciliation']['checks']['row_coverage']['status'],'CONSISTENT')
                # These sources do not print closing totals/pages. Never claim
                # full independent completeness, let alone bank authentication.
                self.assertEqual(evidence['reconciliation']['overall_status'],'UNKNOWN')
                if 'ILLUSTRATION' in case['basis']:
                    self.assertEqual(evidence['reconciliation']['checks']['running_balances']['status'],'CONSISTENT')

    def test_shipped_csv_bytes_match_the_versioned_fixture_inputs(self):
        folder=ROOT/'jugges/bank-formats'
        if not folder.is_dir():
            self.skipTest('User guide fixtures intentionally excluded from container image')
        for case in CATALOG['cases']:
            self.assertEqual((folder/case['file']).read_bytes(),encoded_case(case).encode())

    def test_bom_encodings_are_explicit_and_invalid_bytes_never_replaced(self):
        case=CATALOG['cases'][0]
        for encoding in ('utf-8-sig','utf-16'):
            with self.subTest(encoding=encoding):
                statement,_=self.extract(encoded_case(case).encode(encoding))
                self.assertEqual(len(statement.entries),4)
        for data in (b'\x80not utf8',encoded_case(case).encode('utf-16-le')):
            with self.assertRaises(ValueError):self.extract(data)

    def test_mutated_running_balance_is_a_mismatch_not_silently_fixed(self):
        case=CATALOG['cases'][1]
        text=encoded_case(case).replace('Rs. 58,609.25/-','Rs. 58,608.25/-')
        statement,evidence=self.extract(text.encode())
        self.assertEqual(statement.entries[-1].running_balance_minor,5860825)
        self.assertEqual(evidence['reconciliation']['overall_status'],'MISMATCH')

    def test_rupee_literals_are_exact_and_not_substrings(self):
        self.assertEqual(source_money_minor('Rs. 1,23,456.78/-'),12345678)
        self.assertEqual(source_money_minor('INR -12.50',signed=True),-1250)
        for literal in ('Rs. 12,34/-','Rs. -1/-','USD 2','Rs. 1.234/-'):
            with self.subTest(literal=literal),self.assertRaises(ValueError):source_money_minor(literal)
        with self.assertRaises(ValueError):
            MinorSourceFact(value_minor=10000,literal_text='Rs. 100',
                source_refs=[SourceReference(unit_id='test',text='Rs. 1000')])

    def test_ambiguous_dates_directions_and_opening_rows_do_not_become_transactions(self):
        base='Txn Date,Description,Debit,Credit,Balance\n'
        for row in ('01/02/26,Artificial,1,,99',
                    '2026-08-02,Artificial,1,1,99',
                    '2026-08-02,Opening Balance,1,,99',
                    '2026-08-02,Artificial,DR 1,,99'):
            # A positive debit labelled opening balance is a transaction, never
            # discarded as a control row; other cases must reject.
            if 'Opening Balance,1' in row:
                result=parse_statement_csv(base+row+'\n',account_type='BANK')
                self.assertEqual(result['transaction_count'],1)
                self.assertIsNone(result['source_facts'].opening_balance)
            else:
                with self.assertRaises(ValueError):parse_statement_csv(base+row+'\n',account_type='BANK')

    def test_unknown_rows_and_single_amount_columns_require_review(self):
        for text in ('Date,Description,Amount,DR/CR,Balance\n2026-08-01,Artificial,10,DR,90\n',
                     'Statement report;Unrecognised hidden row\n'+encoded_case(CATALOG['cases'][4]),
                     encoded_case(CATALOG['cases'][0])+'\nUnexplained footer,,,,,\n'):
            with self.assertRaises(ValueError):parse_statement_csv(text,account_type='BANK')


if __name__=='__main__':unittest.main()

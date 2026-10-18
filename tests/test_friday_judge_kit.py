"""Shipped artificial samples: independent controls, privacy and byte parity."""
from pathlib import Path
import unittest
from carapace_ai.friday_statements import extract_statement
from carapace_integrations.friday_assets import ASSETS, friday_asset

ROOT=Path(__file__).resolve().parents[1]
NAMES=['HDFC-Illustration-6-Months.csv','Kotak-Illustration-6-Months.csv',
       'ICICI-Candidate-6-Months.csv','Generic-Tab-6-Months.csv','Generic-Semicolon-6-Months.csv']


class JudgeKitTests(unittest.TestCase):
    def test_every_download_matches_exact_independent_source_controls(self):
        for name in NAMES:
            with self.subTest(name=name):
                data=(ROOT/'src/carapace_integrations/assets'/('ARTIFICIAL-0390-'+name)).read_bytes()
                statement,evidence=extract_statement(None,data=data,mime='text/csv',
                    account_alias='Artificial judge fixture',account_type='BANK',use_ai=False)
                self.assertEqual(len(statement.entries),42)
                self.assertEqual(sum(e.credit_minor for e in statement.entries),30000000)
                self.assertEqual(sum(e.debit_minor for e in statement.entries),16469400)
                self.assertEqual(statement.source_facts.opening_balance.value_minor,4000000)
                self.assertEqual(statement.entries[-1].running_balance_minor,17530600)
                self.assertEqual(len({e.date.month for e in statement.entries}),6)
                self.assertEqual(evidence['model_calls'],0)
                expected='CONSISTENT' if name.startswith(('HDFC','Kotak')) else 'UNKNOWN'
                self.assertEqual(evidence['reconciliation']['checks']['running_balances']['status'],expected)
                # No closing/source-count controls or bank provenance were printed.
                self.assertEqual(evidence['reconciliation']['overall_status'],'UNKNOWN')
                self.assertTrue(all('ARTIFICIAL' in e.description for e in statement.entries))

    def test_github_pack_and_served_downloads_are_identical(self):
        folder=ROOT/'judge-kit/statements'
        if not folder.exists():self.skipTest('Judge folder is not needed inside the runtime image')
        for i,name in enumerate(NAMES,1):
            self.assertEqual((folder/(f'{i:02d}-'+name)).read_bytes(),
                             (ROOT/'src/carapace_integrations/assets'/('ARTIFICIAL-0390-'+name)).read_bytes())

    def test_fixed_download_allowlist_not_a_filesystem_browser(self):
        from fastapi import HTTPException
        for name in NAMES:
            asset='ARTIFICIAL-0390-'+name
            self.assertEqual(ASSETS[asset],'text/csv')
            self.assertTrue(Path(friday_asset(asset).path).is_file())
        with self.assertRaises(HTTPException):friday_asset('../../.env')


if __name__=='__main__':unittest.main()

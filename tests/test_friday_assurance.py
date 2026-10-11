"""Outcome replay must not call AI, submit payments or trust stored pass flags."""
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

from carapace_api.financial_friday import FinancialFridayService
from carapace_ai.financial_friday import LocalFinancialFridayPlanner
from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.friday_assurance import seal_friday_run, replay_friday_run
from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations.friday_core_visual import CORE_JS
from carapace_integrations.friday_simple import SIMPLE_JS


class FridayAssuranceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.signer = BankEnvelopeSigner(Path(self.temp.name) / 'key.pem', allow_generate=True)
        self.service = FinancialFridayService(Path(self.temp.name) / 'db', self.signer, LocalFinancialFridayPlanner())
        self.run = self.service.run('owner', 'genuine-bill')

    def tearDown(self):
        self.temp.cleanup()

    def report(self, run, journal=None):
        return replay_friday_run('owner', run, self.signer, journal or self.run['outcome']['receipt'])

    def test_readback_replays_rules_and_journal_without_ai_or_payment(self):
        self.service.planner.plan = Mock(side_effect=AssertionError('No AI during replay'))
        with self.service.connect() as db:
            count = db.execute('SELECT COUNT(*) FROM friday_payments').fetchone()[0]
        for _ in range(3):
            replay = self.service.get('owner', self.run['run_id'])['assurance']
            self.assertEqual(replay['state'], 'VERIFIED')
            self.assertTrue(replay['read_only'])
            self.assertFalse(replay['money_moved'])
            self.assertEqual(len(replay['checks']), 5)
        self.service.planner.plan.assert_not_called()
        with self.service.connect() as db:
            self.assertEqual(count, db.execute('SELECT COUNT(*) FROM friday_payments').fetchone()[0])

    def test_storage_tampering_is_detected(self):
        for field in ('goal', 'evidence_snapshot', 'program', 'outcome', 'events', 'provenance'):
            with self.subTest(field=field):
                changed = deepcopy(self.run)
                changed[field] = {}
                self.assertEqual(self.report(changed)['state'], 'CONFLICT')

    def test_signature_is_domain_and_tenant_bound(self):
        self.assertEqual(replay_friday_run('attacker', self.run, self.signer, self.run['outcome']['receipt'])['state'], 'CONFLICT')
        with self.assertRaises(KeyError):
            self.service.get('attacker', self.run['run_id'])

    def test_legacy_run_is_not_retroactively_certified(self):
        old = deepcopy(self.run)
        old.pop('run_seal')
        self.assertEqual(self.report(old)['state'], 'LEGACY_UNSEALED')

    def test_stored_pass_boolean_does_not_replace_replay(self):
        changed = deepcopy(self.run)
        changed['program']['candidate']['steps'][2]['payee_id'] = 'attacker'
        changed['program']['verification']['passed'] = True
        seal_friday_run('owner', changed, self.signer)
        self.assertEqual(self.report(changed)['state'], 'CONFLICT')

    def test_missing_or_corrupt_payment_journal_cannot_verify(self):
        with self.service.connect() as db:
            db.execute('DELETE FROM friday_payments')
        self.assertEqual(self.service.get('owner', self.run['run_id'])['assurance']['state'], 'CONFLICT')

    def test_invalid_json_journal_cannot_verify(self):
        with self.service.connect() as db:
            db.execute("UPDATE friday_payments SET receipt_json='broken'")
        self.assertEqual(self.service.get('owner', self.run['run_id'])['assurance']['state'], 'CONFLICT')

    def test_signed_receipt_for_other_recipient_is_rejected(self):
        changed = deepcopy(self.run)
        receipt = changed['outcome']['receipt']
        receipt['payload']['payee_id'] = 'attacker'
        receipt['signature'] = self.signer.sign(receipt['payload'])
        seal_friday_run('owner', changed, self.signer)
        self.assertEqual(self.report(changed, receipt)['state'], 'CONFLICT')

    def test_held_and_reconciled_runs_remain_distinct_from_payment_proof(self):
        held = self.service.run('owner', 'recipient-swap')
        self.assertEqual(self.service.get('owner', held['run_id'])['assurance']['state'], 'VERIFIED_HOLD')
        recovered = self.service.run('recovery-owner', 'unknown-outcome')
        self.assertEqual(self.service.get('recovery-owner', recovered['run_id'])['assurance']['state'], 'SIGNED_RECOVERY_RECORD')

    def test_companion_is_code_rendered_and_motion_is_bounded(self):
        self.assertIn('makeFridayCore()', FINANCIAL_FRIDAY_HTML)
        self.assertNotIn("image.src='/assets/friday-jade-orb.png'", FINANCIAL_FRIDAY_HTML)
        for marker in ('IntersectionObserver', 'document.hidden', 'cancelAnimationFrame', 'time-lastCoreFrame>=32', 'Math.min(window.devicePixelRatio||1,2)', "dataset.motion!=='off'", 'INSTRUMENT_APERTURE_CANVAS'):
            self.assertIn(marker, CORE_JS)
        self.assertNotIn('fetch(', CORE_JS)
        self.assertNotIn('setInterval', CORE_JS)

    def test_conflict_is_not_overwritten_by_the_simplified_success_renderer(self):
        self.assertIn("engineering.querySelector('div').append(replayPanel)", FINANCIAL_FRIDAY_HTML)
        self.assertIn("render=function(data){if(['CONFLICT','UNAVAILABLE','LEGACY_UNSEALED','UNVERIFIED'].includes(data.assurance?.state))", FINANCIAL_FRIDAY_HTML)
        self.assertIn('engineering.open=true;return;}simplerRender(data);', FINANCIAL_FRIDAY_HTML)

    def test_selected_design_replaces_old_themes_and_preserves_outcome_states(self):
        from carapace_integrations.friday_everyday import EVERYDAY_CSS
        self.assertIn('id="friday-everyday-styles"', FINANCIAL_FRIDAY_HTML)
        self.assertNotIn('id="friday-soft-theme"', FINANCIAL_FRIDAY_HTML)
        self.assertNotIn('id="friday-journey-styles"', FINANCIAL_FRIDAY_HTML)
        for marker in ('[data-state="complete"]', '[data-state="held"]',
                       '[data-state="attention"]', 'prefers-reduced-motion',
                       'html[data-motion="off"]', ':focus-visible'):
            self.assertIn(marker, EVERYDAY_CSS)
        self.assertNotIn('<script', EVERYDAY_CSS)

    @unittest.skipUnless(shutil.which('node'), 'Node is optional for renderer execution validation')
    def test_conflict_renderer_executes_only_the_attention_path(self):
        wrapper = next(line.strip() for line in SIMPLE_JS.splitlines() if 'const simplerRender=render;' in line)
        script = """
        let calls=0,cleared=0,render=()=>{calls++};
        const work={hidden:false},approvalArea={replaceChildren(){cleared++}},engineering={open:false};
        const showWork=()=>{throw Error('Conflict cannot look completed')};
        const summarize=()=>{throw Error('Conflict cannot receive success summary')};
        """ + wrapper + """
        for(const state of ['CONFLICT','UNAVAILABLE','LEGACY_UNSEALED','UNVERIFIED']){
          render({status:'COMPLETED_SYNTHETIC',assurance:{state}});
          if(!work.hidden||!engineering.open)throw Error('Attention evidence must be visible');
        }
        if(calls!==4||cleared!==4)throw Error('Wrong render calls');
        """
        result = subprocess.run(['node'], input=script, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node is optional for JavaScript syntax validation')
    def test_complete_page_javascript_parses(self):
        for script in re.findall(r'<script[^>]*>(.*?)</script>', FINANCIAL_FRIDAY_HTML, re.S):
            parsed = subprocess.run(['node', '--check'], input=script, text=True, capture_output=True)
            self.assertEqual(parsed.returncode, 0, parsed.stderr)

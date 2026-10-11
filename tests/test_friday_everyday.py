"""Selected product interface must not add financial authority or open file access."""
import unittest
import json
import shutil
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations import friday_assets
from carapace_integrations.friday_assets import ASSETS, friday_asset
from carapace_integrations.friday_everyday import EVERYDAY_CSS, EVERYDAY_JS
from carapace_integrations.friday_journey import JOURNEY_JS
from carapace_integrations.friday_experience import EXPERIENCE_JS


class EverydayInterfaceTests(unittest.TestCase):
    def test_team_logo_uses_packaged_original_asset(self):
        self.assertIn('friday-team-logo.png', ASSETS)
        self.assertIn("everydayImage('friday-team-logo','everyday-team-brand')", EVERYDAY_JS)
        self.assertIn('Vaultkeepers team logo', EVERYDAY_JS)

    def run_js(self, script):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is optional for presentation execution checks')
        result = subprocess.run([node], input=script, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_review_summary_separates_rules_reserve_and_evidence(self):
        helper = 'function billReviewReason' + JOURNEY_JS.split('function billReviewReason', 1)[1].split('async function refreshHomePreview', 1)[0]
        result = self.run_js("const nice=x=>x;" + helper + """
const seven=billPlanReviewSummary({review:Array.from({length:7},()=>({reason:'EXCEEDS_SAVED_SINGLE_PAYMENT_LIMIT'})),deferred:[]});
const mixed=billPlanReviewSummary({review:[{reason:'RECEIPT_CONFLICT'}],deferred:[{reason:'RESERVE_CONSTRAINED_PRIORITY'}]});
const empty=billPlanReviewSummary({review:[],deferred:[]});
process.stdout.write(JSON.stringify({seven,mixed,empty}));
""")
        self.assertEqual(result['seven']['title'], '7 sandbox records are above your limit')
        self.assertIn('not new failed payments', result['seven']['detail'])
        self.assertNotIn('need verification', result['seven']['detail'])
        self.assertEqual(result['mixed']['count'], 2)
        self.assertIn('Do not pay again', result['mixed']['detail'])
        self.assertIn('protected reserve', result['mixed']['detail'])
        self.assertEqual(result['empty']['count'], 0)

    def test_activity_badges_require_independent_assurance(self):
        helper = 'function activityPresentation' + EXPERIENCE_JS.split('function activityPresentation', 1)[1].split('async function refreshActivity', 1)[0]
        result = self.run_js("const completedStatuses=['COMPLETED_SYNTHETIC','ALREADY_COMPLETED','RECONCILED_COMPLETED'];const workspaceMoney=x=>String(x);const nice=x=>x;" + helper + """
const base={status:'COMPLETED_SYNTHETIC',started_at:'2026-10-11T12:00:00Z'};
process.stdout.write(JSON.stringify(['VERIFIED','LEGACY_UNSEALED','CONFLICT','UNAVAILABLE',undefined].map(assurance_state=>activityPresentation({...base,assurance_state}))));
""")
        self.assertEqual(result[0]['tone'], 'good')
        self.assertTrue(all(item['tone'] == 'review' for item in result[1:]))
        self.assertIn('Older record', result[1]['status'])

    def test_document_action_discloses_existing_authority_and_cloud_processing(self):
        self.assertIn('automatic permission enabled', EVERYDAY_JS)
        self.assertIn('Check document & apply my rules', EVERYDAY_JS)
        self.assertIn('extracted facts and evidence references are saved', EVERYDAY_JS)
        self.assertNotIn('reading alone never authorizes payment', EVERYDAY_JS)

    def test_detached_previews_disabled_without_replacing_financial_handlers(self):
        self.assertIn('refreshBriefing=async()=>{}', EVERYDAY_JS)
        self.assertIn('refreshHouseholdBills=async()=>{}', EVERYDAY_JS)
        self.assertIn('refreshHomePreview=async()=>{}', EVERYDAY_JS)
        self.assertIn("root.setAttribute('aria-label','Financial Friday workspace')", EVERYDAY_JS)

    def test_manual_approval_uses_same_single_task_boundary(self):
        self.assertIn('await experience.execute(async()=>', FINANCIAL_FRIDAY_HTML)
        self.assertIn('return {show,openRun,execute}', EXPERIENCE_JS)
        self.assertIn('Approval outcome unavailable. Check Activity before retrying.', FINANCIAL_FRIDAY_HTML)
        self.assertIn('clearStatement.disabled=true', EXPERIENCE_JS)

    def test_one_design_system_not_stacked_theme_overrides(self):
        self.assertEqual(FINANCIAL_FRIDAY_HTML.count('<style'), 1)
        self.assertIn('friday-everyday-styles', FINANCIAL_FRIDAY_HTML)
        self.assertIn('Your day, a little lighter.', FINANCIAL_FRIDAY_HTML)
        self.assertIn('Your bill inbox', FINANCIAL_FRIDAY_HTML)
        self.assertIn('Artificial funds only. No real bank connected.', FINANCIAL_FRIDAY_HTML)

    def test_home_preview_is_read_only_and_failure_is_not_green(self):
        self.assertEqual(EVERYDAY_JS.count('jsonRequest('), 2)
        self.assertNotIn("method:", EVERYDAY_JS)
        self.assertNotIn('confirm_sandbox_execution', EVERYDAY_JS)
        self.assertNotIn('checkLive(', EVERYDAY_JS)
        self.assertNotIn('innerHTML', EVERYDAY_JS)
        self.assertIn('validPlan(data)', EVERYDAY_JS)
        self.assertIn('No payment was submitted.', EVERYDAY_JS)
        self.assertIn('Checking can execute an artificial payment', EVERYDAY_JS)
        self.assertIn('await everydayPlanPending', EVERYDAY_JS)

    def test_motion_accessibility_and_existing_hidden_gates(self):
        self.assertIn('prefers-reduced-motion:reduce', EVERYDAY_CSS)
        self.assertIn('[hidden]', EVERYDAY_CSS)
        self.assertIn('focus-visible', EVERYDAY_CSS)
        self.assertIn('@media(max-width:720px)', EVERYDAY_CSS)
        self.assertIn('coreVisibility.unobserve(oldCore)', EVERYDAY_JS)

    def test_allowlisted_assets_have_expected_media_and_unknown_is_rejected(self):
        app = FastAPI()
        app.get('/assets/{name}')(friday_asset)
        client = TestClient(app)
        for name, media_type in ASSETS.items():
            with self.subTest(name=name):
                result = client.get('/assets/' + name)
                self.assertEqual(result.status_code, 200)
                self.assertTrue(result.headers['content-type'].startswith(media_type))
                self.assertGreater(len(result.content), 50)
                if name.endswith('.png'):
                    self.assertTrue(result.content.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertEqual(client.get('/assets/not-allowed.txt').status_code, 404)
        self.assertEqual(client.get('/assets/..%2FREADME.md').status_code, 404)
        assets = Path(friday_assets.__file__).parent / 'assets'
        self.assertTrue((assets / 'inter-license.txt').is_file())
        self.assertTrue((assets / 'feather-license.txt').is_file())

"""Selected product interface must not add financial authority or open file access."""
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations import friday_assets
from carapace_integrations.friday_assets import ASSETS, friday_asset
from carapace_integrations.friday_everyday import EVERYDAY_CSS, EVERYDAY_JS


class EverydayInterfaceTests(unittest.TestCase):
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

"""Regression checks for the selected Studio presentation and its trust boundary."""
import struct
import unittest
from pathlib import Path

from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations.friday_assets import ASSETS
from carapace_integrations.friday_studio_ui import STUDIO_CSS, STUDIO_JS
from carapace_integrations.friday_statements_ui import STATEMENTS_JS


class FridayStudioTests(unittest.TestCase):
    def test_selected_design_is_composed_once_and_keeps_real_chat(self):
        self.assertEqual(FINANCIAL_FRIDAY_HTML.count('<style'), 1)
        self.assertEqual(FINANCIAL_FRIDAY_HTML.count("root.classList.add('studio-workspace')"), 1)
        self.assertIn('dock.append(everydayAssistant)', STUDIO_JS)
        self.assertNotIn("id='home-command'", STUDIO_JS)
        self.assertIn("'/api/friday/chat'", FINANCIAL_FRIDAY_HTML)
        self.assertNotIn('setInterval(refreshInbox', FINANCIAL_FRIDAY_HTML)
        self.assertIn("legacyHeader.append(status)", STUDIO_JS)

    def test_profile_uses_verified_display_event_not_browser_identity_claims(self):
        self.assertIn('friday:identity-ready', STUDIO_JS)
        self.assertIn('friday:identity-ready', STATEMENTS_JS)
        self.assertNotIn('innerHTML', STUDIO_JS)
        self.assertIn('Google may sign you back in automatically', STUDIO_JS)
        self.assertIn('gcp-iap-mode=CLEAR_LOGIN_COOKIE', STUDIO_JS)
        self.assertNotIn('accounts.google.com/Logout', STUDIO_JS)

    def test_context_is_explicit_and_example_is_never_financial_history(self):
        self.assertIn('Example preview · not your data', STUDIO_JS)
        self.assertIn('No statement shared yet', STUDIO_JS)
        self.assertIn('contextDialog.box.append(statementChoice.closest', STUDIO_JS)
        self.assertNotIn('statementChoice.checked=true', STUDIO_JS)
        self.assertNotIn("jsonRequest(", STUDIO_JS)
        self.assertNotIn('confirm_sandbox_execution', STUDIO_JS)

    def test_keyboard_reflow_and_motion_have_explicit_states(self):
        for token in ['focus-visible','prefers-reduced-motion:reduce','max-width:600px','max-width:950px']:
            self.assertIn(token, STUDIO_CSS)
        self.assertIn("event.key==='Escape'", STUDIO_JS)
        self.assertIn('box.showModal()', STUDIO_JS)
        self.assertIn('Labels updated. Final totals will be recalculated', STATEMENTS_JS)
        self.assertIn('Find a transaction', STATEMENTS_JS)

    def test_real_buddy_asset_has_alpha_and_allowlisted_packaging(self):
        from carapace_integrations import friday_assets
        name='friday-soft-studio-buddy.png'
        self.assertEqual(ASSETS[name], 'image/png')
        data=(Path(friday_assets.__file__).parent/'assets'/name).read_bytes()
        self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
        width,height,depth,color_type=struct.unpack('!IIBB',data[16:26])
        self.assertGreaterEqual(width,512)
        self.assertEqual(width,height)
        self.assertEqual((depth,color_type),(8,6))

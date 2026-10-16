"""Production workbench wiring, privacy controls and actual sample imports."""
import unittest
from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations.friday_workbench_ui import WORKBENCH_JS, WORKBENCH_CSS
from carapace_integrations.friday_statements_ui import STATEMENTS_JS
from carapace_integrations.friday_chat_ui import CHAT_JS
from carapace_integrations.friday_polish_ui import POLISH_CSS


class WorkbenchUiTests(unittest.TestCase):
    def test_workbench_is_in_real_app_and_keeps_safe_dom_and_real_results(self):
        self.assertIn(WORKBENCH_JS, FINANCIAL_FRIDAY_HTML)
        self.assertIn(WORKBENCH_CSS, FINANCIAL_FRIDAY_HTML)
        self.assertNotIn('innerHTML', WORKBENCH_JS)
        self.assertNotIn('setInterval', WORKBENCH_JS)
        self.assertNotIn('Math.random', WORKBENCH_JS)
        for key in ['work.next_item','item.artifact.content','data.summary.categories','data.summary.period.start',
                    "work.source_revision!==data.revision", "work.workspace_generation!==data.workspace_generation"]:
            self.assertIn(key, WORKBENCH_JS)

    def test_voice_is_per_action_opt_in_bounded_and_cleared_when_evidence_changes(self):
        self.assertIn("consent.type='checkbox'", WORKBENCH_JS)
        self.assertNotIn('consent.checked=true', WORKBENCH_JS)
        self.assertNotIn('getUserMedia', WORKBENCH_JS)
        self.assertNotIn('.play()', WORKBENCH_JS)
        self.assertIn('confirm_send_derived_totals_to_google:true', WORKBENCH_JS)
        self.assertIn('r.audio_base64.length>2000000', WORKBENCH_JS)
        self.assertIn('sent!==workEpoch', WORKBENCH_JS)
        self.assertIn("audio.pause();audio.removeAttribute('src');URL.revokeObjectURL(url)", WORKBENCH_JS)

    def test_preparation_and_review_are_distinct_no_financial_or_outbound_action(self):
        self.assertIn("'/api/friday/statements/findings/review'", WORKBENCH_JS)
        self.assertNotIn("'/api/friday/statements/findings/enquiry'", WORKBENCH_JS)
        self.assertNotIn("'/api/friday/tasks'", WORKBENCH_JS)
        self.assertNotIn("'/api/friday/run'", WORKBENCH_JS)
        self.assertIn("reviewed:true,expected_revision:data.revision", WORKBENCH_JS)
        self.assertIn('No bank connection or live monitoring', WORKBENCH_JS)
        self.assertIn('Ranges cannot be added as a loss', WORKBENCH_JS)

    def test_presence_follows_real_stage_events_and_is_pauseable(self):
        for phase in ['READING','PROPOSED','SAVING','SAVED','ERROR']:
            self.assertIn("statementStage('"+phase+"'", STATEMENTS_JS)
        for phase in ['THINKING','REPLIED','ERROR']:
            self.assertIn("phase:'"+phase+"'", CHAT_JS)
        self.assertIn("'friday:statement-stage'", WORKBENCH_JS)
        self.assertIn("'friday:chat-state'", WORKBENCH_JS)
        self.assertIn("paused=!paused", WORKBENCH_JS)
        self.assertIn('prefers-reduced-motion:reduce', WORKBENCH_CSS)

    def test_logo_and_native_controls_follow_current_theme(self):
        self.assertIn(POLISH_CSS, FINANCIAL_FRIDAY_HTML)
        self.assertIn('mix-blend-mode:screen', POLISH_CSS)
        self.assertIn('color-scheme:dark', POLISH_CSS)
        self.assertIn('::file-selector-button', POLISH_CSS)
        self.assertIn('.statement-account-options', FINANCIAL_FRIDAY_HTML)
        self.assertNotIn('Download Money Shield example', STATEMENTS_JS)
        self.assertIn('Try with an example', STATEMENTS_JS)


if __name__=='__main__':unittest.main()

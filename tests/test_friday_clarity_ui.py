"""Presentation checks do not grant a new financial capability."""
import json
import shutil
import subprocess
import unittest

from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations.friday_tasks_ui import TASK_JS, TASK_CSS
from carapace_integrations.friday_chat_ui import CHAT_JS, CHAT_CSS
from carapace_integrations.friday_review_ui import REVIEW_JS
from carapace_integrations.friday_everyday import EVERYDAY_CSS


class FridayClarityTests(unittest.TestCase):
    def test_prepared_is_not_completed_and_unknown_never_green(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node optional for presenter tests')
        helper = 'function taskPresentation' + TASK_JS.split('function taskPresentation', 1)[1].split('function taskShow', 1)[0]
        script = helper + "console.log(JSON.stringify(['HOLD','READY_FOR_CONFIRMATION','PREPARED_MESSAGE','GUIDANCE_ONLY','UNKNOWN'].map(state=>taskPresentation({state,expired:false})).concat(taskPresentation({state:'READY_FOR_CONFIRMATION',expired:true}))));"
        result = subprocess.run([node], input=script, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        views = json.loads(result.stdout)
        self.assertEqual([v['tone'] for v in views], ['held', 'live', 'live', 'review', 'review', 'review'])
        self.assertIn('not paid', views[1]['label'])
        self.assertIn('not sent', views[2]['label'])
        self.assertIn('Expired', views[-1]['label'])

    def test_request_only_coverage_and_unsent_copy_are_explicit(self):
        self.assertIn('task.coverage.workspace_included?', TASK_JS)
        self.assertIn('Your saved inbox, bills and financial rules were not included', TASK_JS)
        self.assertIn('navigator.clipboard.writeText(task.proposal.verification_message)', TASK_JS)
        self.assertIn('Copied. Nothing has been sent.', TASK_JS)
        self.assertIn('Clipboard unavailable', TASK_JS)
        self.assertIn("task.state==='READY_FOR_CONFIRMATION'&&!task.expired", TASK_JS)
        self.assertNotIn('innerHTML', TASK_JS)

    def test_clear_composer_and_progressive_disclosure(self):
        self.assertIn('Neither button pays', TASK_JS)
        self.assertIn('friday-command-actions', TASK_JS)
        self.assertIn('Why Friday paused', TASK_JS)
        self.assertIn('What happens next', TASK_JS)
        self.assertIn('Your next step', REVIEW_JS)
        self.assertIn('Privacy & what this check can prove', REVIEW_JS)
        self.assertIn('friday-flow', REVIEW_JS)
        self.assertNotIn('confirm_sandbox_execution', CHAT_JS)
        self.assertIn('friday-command-actions', CHAT_CSS)

    def test_consistent_theme_responsive_and_textual_status(self):
        self.assertEqual(FINANCIAL_FRIDAY_HTML.count('<style'), 1)
        for token in ('--pass-bg', '--held-bg', '--review-bg', '--live-bg'):
            self.assertIn(token, EVERYDAY_CSS)
        self.assertIn('html[data-theme="dark"]', EVERYDAY_CSS)
        self.assertIn('focus-visible', EVERYDAY_CSS)
        self.assertIn('prefers-reduced-motion:reduce', EVERYDAY_CSS)
        self.assertIn('@media(max-width:600px)', TASK_CSS)


if __name__ == '__main__':
    unittest.main()

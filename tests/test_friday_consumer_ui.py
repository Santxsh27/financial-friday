"""Consumer composition keeps evidence guidance, not executable demo controls."""
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations.friday_consumer_ui import CONSUMER_JS


class ConsumerUiTests(unittest.TestCase):
    def test_server_marks_local_consumer_mode_and_legacy_is_explicit(self):
        for flag,mode in [('false','consumer'),('true','legacy')]:
            with self.subTest(flag=flag),patch.dict('os.environ',{'CARAPACE_DEMO_ENABLED':'true','FRIDAY_LEGACY_DEMO_ENABLED':flag}):
                from carapace_integrations.anthos_web import create_demo_app
                with TestClient(create_demo_app()) as client:
                    response=client.get('/')
                self.assertEqual(response.status_code,200)
                self.assertIn(f'<meta name="friday-surface" content="{mode}">',response.text)
                self.assertEqual(response.headers['cache-control'],'no-store')

    def test_consumer_does_not_initialize_task_preparation_or_scenario_fetch(self):
        self.assertIn('if(!consumerOnly){',FINANCIAL_FRIDAY_HTML)
        self.assertIn("if(consumerOnly){$('ai-status').textContent='Statement assistant'",FINANCIAL_FRIDAY_HTML)
        self.assertIn(CONSUMER_JS,FINANCIAL_FRIDAY_HTML)
        self.assertNotIn('innerHTML',CONSUMER_JS)
        self.assertNotIn('fetch(',CONSUMER_JS)
        self.assertIn('supported.has(name)',CONSUMER_JS)
        self.assertIn("if(diary)tools.append(diary)",CONSUMER_JS)
        self.assertIn("if(runway)tools.append(runway)",CONSUMER_JS)

    def test_reloaded_preview_has_a_recovery_action_not_a_blank_panel(self):
        self.assertIn('Unsaved previews disappear when you reload.',FINANCIAL_FRIDAY_HTML)
        self.assertIn("choose.dataset.screenLink='statements'",FINANCIAL_FRIDAY_HTML)
        self.assertIn("if(name==='statement-review'&&!proposal)emptyPreview()",FINANCIAL_FRIDAY_HTML)

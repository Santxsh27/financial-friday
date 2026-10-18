"""Submission surface and packaged artificial examples; no live network calls."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from carapace_ai.financial_friday import GeminiFinancialFridayPlanner
from carapace_ai.friday_chat import answer_chat, FridayChatRequest
from carapace_api.friday_chat import reply_to_user
from carapace_core.friday_statement_csv import parse_statement_csv
from carapace_integrations.friday_assets import ASSETS, friday_asset
from carapace_integrations.friday_consumer_ui import CONSUMER_JS
from carapace_integrations.friday_navigation_ui import NAVIGATION_JS
from carapace_integrations.friday_buddy_ui import BUDDY_JS
import test_friday_surface_isolation

ROOT=Path(__file__).resolve().parents[1]
ASSET_ROOT=ROOT/'src/carapace_integrations/assets'


class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.hrefs.extend(v for k,v in attrs if k=='href')


class SubmissionTests(unittest.TestCase):
    def test_every_download_is_packaged_and_financial_controls_match(self):
        catalog=json.loads((ROOT/'examples/friday-bank-format-cases.json').read_text())
        for item in catalog['cases']:
            name=item['file'];self.assertIn(name,ASSETS)
            response=friday_asset(name)
            self.assertTrue(Path(response.path).is_file())
            raw=Path(response.path).read_bytes()
            result=parse_statement_csv(raw.decode(),account_type='BANK')
            self.assertEqual(result['transaction_count'],4)
            self.assertEqual(sum(r['debit_minor'] for r in result['entries']),139075)
            judge=ROOT/'jugges/bank-formats'/name
            if judge.is_file():self.assertEqual(hashlib.sha256(raw).digest(),hashlib.sha256(judge.read_bytes()).digest())

    def test_walkthrough_has_no_private_repository_or_missing_sample_dependency(self):
        page=(ASSET_ROOT/'friday-judge-guide.html').read_text()
        links=Links();links.feed(page)
        downloads=[link for link in links.hrefs if not link.startswith(('/','https://'))]
        self.assertEqual(len(downloads),6)
        for name in downloads:
            self.assertIn(name,ASSETS);self.assertTrue((ASSET_ROOT/name).is_file())
        # Source is now public; the optional source link is not a prerequisite
        # for any download. All six trial files still come from this server.
        repo_links=[link for link in links.hrefs if 'github.com' in link]
        self.assertEqual(repo_links,['https://github.com/Santxsh27/financial-friday/tree/main/judge-kit'])
        self.assertTrue(all(not link.startswith('https://') for link in downloads))
        self.assertNotIn('localhost',page)
        self.assertNotIn('<script',page)
        self.assertIn('Try a sample',NAVIGATION_JS)
        self.assertNotIn("['document','Check a separate bill']",NAVIGATION_JS)
        self.assertNotIn("'review','document'",CONSUMER_JS)
        self.assertNotIn('Keep bills organised',BUDDY_JS)

    def test_retired_bill_context_is_rejected_before_any_storage_or_model_read(self):
        service=Mock();review=Mock();bank=Mock()
        with self.assertRaisesRegex(ValueError,'retired'):
            reply_to_user(service,review,bank,'synthetic',FridayChatRequest(message='My bills?',include_workspace=True),statement_only=True)
        service.assert_not_called();self.assertEqual(service.mock_calls,[])
        self.assertEqual(review.mock_calls,[]);self.assertEqual(bank.mock_calls,[])

    def test_consumer_route_rejects_retired_workspace_permission_without_ai_call(self):
        f=test_friday_surface_isolation.ConsumerApiSurfaceTests();self.addCleanup(f.doCleanups)
        _,app,client=f.api();model=Mock()
        app.state.financial_friday.planner=GeminiFinancialFridayPlanner(model,'test-model','VERTEX_AI')
        result=client.post('/v1/friday/chat',headers=f.headers,json={'message':'My bill inbox','include_workspace':True})
        self.assertEqual(result.status_code,422,result.text)
        self.assertEqual(model.mock_calls,[])

    def test_statement_only_model_destinations_cannot_open_retired_bill_screens(self):
        for destination in ('document','review','money','activity'):
            model=Mock();model.models.generate_content.return_value=SimpleNamespace(text=json.dumps({
                'reply':'Add a statement to review your recorded spending.','next_screen':destination,'evidence_ids':[]}))
            planner=GeminiFinancialFridayPlanner(model,'test-model','VERTEX_AI')
            result=answer_chat(planner,FridayChatRequest(message='Help me get started'),{},statement_only=True)
            self.assertEqual(result['next_screen'],'statements')
            self.assertIn('STATEMENT-ONLY',model.models.generate_content.call_args.kwargs['config'].system_instruction)
            self.assertEqual(result['actions_executed'],[])

    def test_actual_chat_emits_content_free_usage_and_latency(self):
        model=Mock();model.models.generate_content.return_value=SimpleNamespace(
            text=json.dumps({'reply':'A loan is not income.','evidence_ids':[]}),
            model_version='gemini-test',usage_metadata=SimpleNamespace(prompt_token_count=10,candidates_token_count=8,total_token_count=18))
        planner=GeminiFinancialFridayPlanner(model,'gemini-test','VERTEX_AI')
        with self.assertLogs('carapace_ai.friday_observability',level='INFO') as logs:
            answer_chat(planner,FridayChatRequest(message='PRIVATE TEST CONTENT: Explain a loan.'),{},statement_only=True)
        event=json.loads(logs.records[-1].message)
        self.assertEqual(event['purpose'],'statement_coach')
        self.assertEqual(event['tokens']['total_token_count'],18)
        self.assertIn('duration_ms',event)
        self.assertNotIn('PRIVATE TEST CONTENT',str(event))
        self.assertNotIn('A loan is not income',str(event))


if __name__=='__main__':unittest.main()

"""Artificial data only: privacy, source freshness, audio bounds and access."""
import base64
import copy
from datetime import datetime, timezone
import io
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import wave

from fastapi import FastAPI
from fastapi.testclient import TestClient

from carapace_ai.friday_speech import MAX_PCM_BYTES
from carapace_api.auth import TenantAuthenticator
from carapace_api.config import Settings
from carapace_api.financial_friday_routes import register_financial_friday_routes
from carapace_core.friday_access import permitted_friday_route, visitor_key, visitor_tenant
from carapace_core.friday_checkup import build_checkup
from carapace_core.friday_portfolio import summarize_statements
from carapace_integrations.friday_cloud_web import WebSettings, backend_request, create_cloud_web
import test_friday_chat_bank
from test_friday_public_access import MemoryClient, MemoryQuota, SECRET


PATH = '/v1/friday/assistant/briefing-audio'
WEB_PATH = '/api/friday/assistant/briefing-audio'


def artificial_view():
    statements = [{'source_sha256': 'a' * 64, 'account_alias': 'PRIVATE NICKNAME',
        'account_type': 'BANK', 'entries': [
            {'date': '2026-09-01', 'description': 'PRIVATE SALARY DESCRIPTION',
             'debit_minor': 0, 'credit_minor': 4500000, 'kind': 'INCOME',
             'category': 'Other', 'source_row': 1},
            {'date': '2026-09-02', 'description': 'PRIVATE SHOP DESCRIPTION',
             'debit_minor': 125050, 'credit_minor': 0, 'kind': 'EXPENSE',
             'category': 'Shopping', 'source_row': 2},
            {'date': '2026-09-03', 'description': 'PRIVATE LOAN DESCRIPTION',
             'debit_minor': 500000, 'credit_minor': 0, 'kind': 'LOAN_REPAYMENT',
             'category': 'Other', 'source_row': 3}]}]
    summary = summarize_statements(statements)
    return {'revision': 7, 'workspace_generation': 'test-generation', 'summary': summary,
            'checkup': build_checkup(statements, summary)}


def speech_response(data=b'\x00\x00' * 2400, mime='audio/L16;codec=pcm;rate=24000'):
    return SimpleNamespace(candidates=[SimpleNamespace(finish_reason='STOP', content=SimpleNamespace(parts=[
        SimpleNamespace(inline_data=SimpleNamespace(data=data, mime_type=mime))]))])


def request(**changes):
    body = {'expected_revision': 7, 'workspace_generation': 'test-generation',
            'confirm_send_derived_totals_to_google': True}
    body.update(changes)
    return body


class FridaySpeechTests(unittest.TestCase):
    def setUp(self):
        self.base = test_friday_chat_bank.FridayChatBankTests()
        self.base.setUp()
        self.service, self.client, self.headers = self.base.service, self.base.client, self.base.headers
        self.view = artificial_view()
        self.source = patch.object(self.service.portfolio, 'view', side_effect=lambda tenant: copy.deepcopy(self.view) if tenant == 'one' else
            {'revision': 0, 'workspace_generation': 'test-generation',
             'summary': summarize_statements([]), 'checkup': build_checkup([], summarize_statements([]))})
        self.source.start()
        self.base.model.models.generate_content.return_value = speech_response()

    def tearDown(self):
        self.source.stop()
        self.base.tearDown()

    def audio(self, **changes):
        return self.client.post(PATH, headers=self.headers, json=request(**changes))

    def test_only_current_aggregate_text_crosses_google_boundary_and_wav_is_bounded(self):
        before = self.service.mandate('one')
        result = self.audio()
        self.assertEqual(result.status_code, 200, result.text)
        body = result.json()
        self.assertEqual(result.headers['cache-control'], 'no-store')
        self.assertFalse(body['money_moved'])
        self.assertEqual(body['source_revision'], 7)
        self.assertEqual(body['workspace_generation'], 'test-generation')
        self.assertLessEqual(len(body['spoken_text'].split()), 70)
        self.assertIn('45,000.00 rupees', body['spoken_text'])
        self.assertIn('1,250.50 rupees', body['spoken_text'])
        self.assertIn('not a live balance or confirmed fraud', body['spoken_text'])
        call = self.base.model.models.generate_content.call_args.kwargs
        self.assertEqual(call['model'], 'gemini-2.5-flash-tts')
        self.assertIn(body['spoken_text'], call['contents'])
        for private in ('PRIVATE', 'source_sha256', 'source_fingerprint', 'finding_', 'account_alias', 'test-generation'):
            self.assertNotIn(private, call['contents'])
        self.assertFalse(call['config'].tools)
        self.assertTrue(call['config'].automatic_function_calling.disable)
        self.assertEqual(call['config'].response_modalities, ['AUDIO'])
        self.assertEqual(self.base.model.models.generate_content.call_count, 1)
        self.assertEqual(body['mime'], 'audio/wav')
        with wave.open(io.BytesIO(base64.b64decode(body['audio_base64'])), 'rb') as audio:
            self.assertEqual((audio.getnchannels(), audio.getsampwidth(), audio.getframerate()), (1, 2, 24000))
            self.assertEqual(audio.getnframes(), 2400)
        self.assertEqual(before, self.service.mandate('one'))
        self.assertIsNone(self.service.diary.record('one'))

    def test_auth_strict_consent_extra_fields_and_stale_source_prevent_model_call(self):
        self.assertEqual(self.client.post(PATH, json=request()).status_code, 401)
        for changes, status in [({'confirm_send_derived_totals_to_google': False}, 422),
                ({'confirm_send_derived_totals_to_google': 'true'}, 422),
                ({'expected_revision': '7'}, 422), ({'expected_revision': True}, 422),
                ({'workspace_generation': 0}, 422), ({'message': 'Send raw transactions'}, 422),
                ({'expected_revision': 6}, 409), ({'workspace_generation': 'cleared'}, 409)]:
            with self.subTest(changes=changes):
                self.assertEqual(self.audio(**changes).status_code, status)
        missing = request(); del missing['confirm_send_derived_totals_to_google']
        self.assertEqual(self.client.post(PATH, headers=self.headers, json=missing).status_code, 422)
        self.base.model.models.generate_content.assert_not_called()

    def test_other_tenant_cannot_request_this_revision_and_empty_history_is_not_sent(self):
        other = {'X-Carapace-Tenant': 'two', 'X-Carapace-API-Key': 'key-two'}
        self.assertEqual(self.client.post(PATH, headers=other, json=request()).status_code, 409)
        self.assertEqual(self.client.post(PATH, headers=other, json=request(expected_revision=0)).status_code, 409)
        self.base.model.models.generate_content.assert_not_called()

    def test_local_or_api_key_modes_fail_without_creating_a_new_client(self):
        for mode in ('LOCAL_RULES', 'GEMINI_API'):
            with self.subTest(mode=mode):
                self.service.planner.mode = mode
                self.assertEqual(self.audio().status_code, 503)
        self.base.model.models.generate_content.assert_not_called()

    def test_revision_generation_and_derived_numbers_are_rechecked_after_model(self):
        for change in ('revision', 'generation', 'fingerprint', 'totals', 'review_count'):
            self.view = artificial_view()
            def changed(**kwargs):
                if change == 'revision': self.view['revision'] += 1
                elif change == 'generation': self.view['workspace_generation'] = 'cleared'
                elif change == 'fingerprint': self.view['checkup']['source_fingerprint'] = 'different'
                elif change == 'totals': self.view['summary']['totals']['classified_spending_minor'] += 1
                else: self.view['checkup']['open_count'] += 1
                return speech_response()
            self.base.model.models.generate_content.side_effect = changed
            with self.subTest(change=change):
                result = self.audio()
                self.assertEqual(result.status_code, 409, result.text)
                self.assertNotIn('audio_base64', result.json())
                self.assertEqual(result.headers['cache-control'], 'no-store')

    def test_wrong_audio_format_empty_odd_or_overlong_data_fail_closed(self):
        for data, mime in [(b'', 'audio/L16;codec=pcm;rate=24000'),
                (b'\x00', 'audio/L16;codec=pcm;rate=24000'),
                (b'\x00\x00' * (MAX_PCM_BYTES // 2 + 1), 'audio/L16;codec=pcm;rate=24000'),
                (b'RIFF\x00\x00', 'audio/L16;codec=pcm;rate=24000'),
                (b'\x00\x00', 'audio/mp3'), (b'\x00\x00', 'audio/L16;codec=pcm;rate=16000'),
                (b'\x00\x00', 'audio/L16;codec=pcm;rate=24000;channels=2'),
                (b'\x00\x00', 'audio/L16;codec=pcm;rate=24000;bits=8'),
                (b'\x00\x00', 'audio/L16;codec=pcm;rate=24000;rate=24000')]:
            self.base.model.models.generate_content.return_value = speech_response(data, mime)
            with self.subTest(mime=mime, size=len(data)):
                result = self.audio()
                self.assertEqual(result.status_code, 503, result.text)
                self.assertNotIn('audio_base64', result.json())
        self.base.model.models.generate_content.return_value = speech_response(b'\x00\x00' * (MAX_PCM_BYTES // 2))
        self.assertEqual(self.audio().status_code, 200)

    def test_provider_errors_are_generic_and_content_is_not_logged(self):
        self.base.model.models.generate_content.side_effect = RuntimeError('PRIVATE provider content')
        with patch('logging.Logger.warning') as warning, patch('logging.Logger.exception') as exception:
            result = self.audio()
        self.assertEqual(result.status_code, 503)
        self.assertNotIn('PRIVATE', result.text)
        warning.assert_not_called(); exception.assert_not_called()

    def test_truncated_or_malformed_responses_never_return_audio(self):
        truncated = speech_response(); truncated.candidates[0].finish_reason = 'MAX_TOKENS'
        missing_finish = speech_response(); missing_finish.candidates[0].finish_reason = None
        multiple_parts = speech_response()
        multiple_parts.candidates[0].content.parts *= 2
        for response in (None, SimpleNamespace(candidates=[]), truncated, missing_finish,
                multiple_parts, speech_response(data='not-bytes')):
            self.base.model.models.generate_content.return_value = response
            result = self.audio()
            self.assertEqual(result.status_code, 503, result.text)
            self.assertNotIn('audio_base64', result.json())

    def test_aggregate_values_cannot_smuggle_free_text(self):
        for path, value in [('income', 'PRIVATE INSTRUCTION'), ('income', True), ('count', -1)]:
            self.view = artificial_view()
            if path == 'income': self.view['summary']['totals']['identified_income_minor'] = value
            else: self.view['checkup']['open_count'] = value
            self.assertEqual(self.audio().status_code, 409)
        self.base.model.models.generate_content.assert_not_called()

    def test_cloud_gateway_exact_route_auth_origin_and_no_cache(self):
        settings = WebSettings('https://private.run.app', 'https://web.run.app',
            '/projects/123/locations/asia-south1/services/friday-web', {'one@example.com': 'one'}, {'one': 'key-one'})
        calls = []
        def transport(settings, tenant, path, method, body, mime):
            calls.append((tenant, path, method))
            response = self.client.request(method, path,
                headers={**self.headers, 'Content-Type': mime}, content=body)
            return response.status_code, response.json()
        with TestClient(create_cloud_web(settings, verifier=lambda token, audience: {'email': token},
                transport=transport, html='<h1>Artificial test</h1>')) as web:
            headers = {'X-Goog-Iap-Jwt-Assertion': 'one@example.com', 'Origin': settings.public_origin}
            result = web.post(WEB_PATH, headers=headers, json=request())
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.headers['cache-control'], 'no-store')
            self.assertEqual(calls, [('one', PATH, 'POST')])
            self.assertEqual(web.post(WEB_PATH, json=request()).status_code, 401)
            self.assertEqual(web.post(WEB_PATH, headers={**headers, 'Origin': 'https://other.example'}, json=request()).status_code, 403)
            for method, path in [('GET', WEB_PATH), ('POST', WEB_PATH + '/pay'), ('POST', WEB_PATH + '?tenant=two')]:
                self.assertIn(web.request(method, path, headers=headers, json=request()).status_code, (400, 404))
            self.assertEqual(len(calls), 1)

    def test_local_proxy_forwards_only_the_exact_strict_audio_request(self):
        with patch.dict(os.environ, {'CARAPACE_DEMO_ENABLED': 'true'}):
            from carapace_integrations.anthos_web import create_demo_app
        with patch.dict(os.environ, {'CARAPACE_DEMO_ENABLED': 'true'}), \
                patch('carapace_integrations.anthos_web._api_call', return_value=(200, {'mime': 'audio/wav'})) as forward, \
                TestClient(create_demo_app()) as local:
            result = local.post(WEB_PATH, json=request())
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.headers['cache-control'], 'no-store')
            self.assertEqual(forward.call_args.args[1:4], (PATH, 'POST', request()))
            for changes in ({'message': 'private text'}, {'confirm_send_derived_totals_to_google': 'true'}):
                self.assertEqual(local.post(WEB_PATH, json=request(**changes)).status_code, 422)
            self.assertEqual(local.post(WEB_PATH, content='x' * 1025).status_code, 413)
            self.assertEqual(local.post(WEB_PATH + '/pay', json=request()).status_code, 404)
            self.assertEqual(forward.call_count, 1)

    def test_cloud_audio_failures_are_action_specific_without_upstream_content(self):
        settings = WebSettings('https://private.run.app', 'https://web.run.app',
            '/projects/123/locations/asia-south1/services/friday-web', {'one@example.com': 'one'}, {'one': 'key-one'})
        errors = [HTTPError(settings.backend_url, code, 'PRIVATE upstream failure', {}, None) for code in (409, 422, 503)]
        errors.append(URLError('PRIVATE upstream failure'))
        for error in errors:
            with patch('google.oauth2.id_token.fetch_id_token', return_value='artificial-token'), \
                    patch('carapace_integrations.friday_cloud_web.urlopen', side_effect=error):
                status, body = backend_request(settings, 'one', PATH, 'POST', b'{}', 'application/json')
            self.assertIn(status, (409, 422, 503, 502))
            self.assertNotIn('PRIVATE', str(body))
            self.assertNotIn('retrying a payment', str(body))

    def test_visitor_route_consumes_existing_write_allowance_and_limits_stop_google(self):
        now = datetime(2026, 10, 16, tzinfo=timezone.utc)
        quota = MemoryQuota('artificial-test', client=MemoryClient(), clock=lambda: now)
        quota.USER_MINUTE_WRITES = quota.GLOBAL_MINUTE_WRITES = 1000
        settings = Settings('test', Path(self.base.tmp.name) / 'test.db', {'one': 'key-one'},
            friday_durable_store='firestore', public_demo_secret=SECRET)
        auth = TenantAuthenticator(settings, quota=quota)
        app = FastAPI()
        register_financial_friday_routes(app, self.service, auth)
        tenant = visitor_tenant(SECRET, 'accounts.google.com:123')
        headers = {'X-Carapace-Tenant': tenant, 'X-Carapace-API-Key': visitor_key(SECRET, tenant)}
        with patch.object(self.service.portfolio, 'view', return_value=artificial_view()), TestClient(app) as visitor:
            for _ in range(quota.USER_DAILY_WRITES):
                self.assertEqual(visitor.post(PATH, headers=headers, json=request()).status_code, 200)
            calls = self.base.model.models.generate_content.call_count
            self.assertEqual(visitor.post(PATH, headers=headers, json=request()).status_code, 429)
            self.assertEqual(self.base.model.models.generate_content.call_count, calls)
        self.assertTrue(permitted_friday_route('POST', PATH))
        for method, path in [('GET', PATH), ('POST', PATH + '/pay'), ('POST', '/v1/friday/assistant/pay')]:
            self.assertFalse(permitted_friday_route(method, path))


if __name__ == '__main__':
    unittest.main()

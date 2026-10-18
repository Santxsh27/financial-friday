"""Artificial voice only: consent, formats, isolation, cleanup and UI contracts."""
import base64
import io
import json
import shutil
import subprocess
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import patch

from carapace_core.friday_access import permitted_friday_route
from carapace_core.friday_surface import permitted_consumer_friday_route
from carapace_ai.friday_voice import VoiceInput, VoiceReply, transcribe, speak
import test_friday_chat_bank
from test_friday_speech import speech_response
from test_friday_roadmap import plan


def clip(seconds=.1):
    out=io.BytesIO()
    with wave.open(out,'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000)
        audio.writeframes(b'\0\0'*int(16000*seconds))
    return base64.b64encode(out.getvalue()).decode()


class VoiceTurnTests(unittest.TestCase):
    def setUp(self):
        self.base=test_friday_chat_bank.FridayChatBankTests();self.base.setUp()
        self.client,self.service,self.headers=self.base.client,self.base.service,self.base.headers
        self.base.model.models.generate_content.return_value=SimpleNamespace(text='Explain an emergency reserve.')

    def tearDown(self):self.base.tearDown()

    def post(self,operation='transcribe',**changes):
        body={'audio_base64':clip(),'mime':'audio/wav','confirm_send_audio_to_google':True} if operation=='transcribe' else {'text':'A reserve covers unexpected essential costs.','confirm_send_text_to_google':True}
        return self.client.post('/v1/friday/assistant/'+operation,headers=self.headers,json={**body,**changes})

    def test_transcript_needs_review_and_loads_no_financial_records(self):
        with patch.object(self.service.portfolio,'view',side_effect=AssertionError('No private retrieval')):
            r=self.post()
        self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.json()['review_required'])
        self.assertFalse(r.json()['persisted']);self.assertFalse(r.json()['money_moved'])
        self.assertEqual(r.headers['cache-control'],'no-store')
        call=self.base.model.models.generate_content.call_args.kwargs
        self.assertFalse(call['config'].tools);self.assertTrue(call['config'].automatic_function_calling.disable)
        self.assertEqual(call['contents'][0].inline_data.mime_type,'audio/wav')

    def test_refused_consent_and_types_make_no_model_call(self):
        for key,value in [('confirm_send_audio_to_google',False),('confirm_send_audio_to_google','true'),('money_moved',True)]:
            self.assertEqual(self.post(**{key:value}).status_code,422)
        self.base.model.models.generate_content.assert_not_called()

    def test_invalid_audio_magic_base64_size_and_duration(self):
        for changes in [{'audio_base64':'not-a-valid-audio-clip'}, {'audio_base64':base64.b64encode(b'not really wave audio').decode()},
            {'mime':'audio/mp3'}, {'audio_base64':base64.b64encode(b'OggS'+b'x'*1_048_576).decode(),'mime':'audio/ogg'},
            {'audio_base64':clip(30.1)}]:
            with self.subTest(changes=list(changes)):
                self.assertEqual(self.post(**changes).status_code,422)
        self.base.model.models.generate_content.assert_not_called()

    def test_supported_container_headers_and_no_remote_urls(self):
        for mime,data in [('audio/webm',b'\x1aE\xdf\xa3'+b'0'*20),('audio/ogg',b'OggS'+b'0'*20),('audio/mp4',b'\0\0\0\x18ftyp'+b'0'*20)]:
            self.assertEqual(self.post(mime=mime,audio_base64=base64.b64encode(data).decode()).status_code,200)
        self.assertEqual(self.post(audio_url='https://example.com/a.wav').status_code,422)

    def test_empty_long_or_failed_transcript_is_not_a_canned_answer(self):
        for text in ['', 'x'*1601]:
            self.base.model.models.generate_content.return_value=SimpleNamespace(text=text)
            self.assertEqual(self.post().status_code,503)
        self.base.model.models.generate_content.side_effect=RuntimeError('sensitive provider detail')
        r=self.post();self.assertEqual(r.status_code,503);self.assertNotIn('sensitive',r.text)

    def test_transcript_scrubs_recognisable_secret(self):
        self.base.model.models.generate_content.return_value=SimpleNamespace(text='My OTP is 123456')
        r=self.post();self.assertEqual(r.status_code,200);self.assertNotIn('123456',r.text)

    def test_narration_opt_in_bounded_and_not_financially_verified(self):
        self.base.model.models.generate_content.return_value=speech_response()
        with patch.object(self.service.portfolio,'view',side_effect=AssertionError('No private retrieval')):
            r=self.post('speak')
        self.assertEqual(r.status_code,200,r.text);self.assertFalse(r.json()['financially_verified'])
        data=base64.b64decode(r.json()['audio_base64'])
        with wave.open(io.BytesIO(data)) as audio:self.assertEqual(audio.getframerate(),24000)
        self.assertEqual(r.json()['spoken_text'],'A reserve covers unexpected essential costs.')
        for change in [{'confirm_send_text_to_google':False},{'text':'x '*101},{'text':'x'*801}]:
            self.assertEqual(self.post('speak',**change).status_code,422)

    def test_narration_rejects_malformed_provider_audio(self):
        self.base.model.models.generate_content.return_value=speech_response(mime='audio/mpeg')
        self.assertEqual(self.post('speak').status_code,503)

    def test_voice_generation_cannot_survive_privacy_cleanup(self):
        def clear(**kwargs):
            self.client.post('/v1/friday/privacy/reviews/delete',headers=self.headers,json={'confirm_delete_reviews':True})
            return SimpleNamespace(text='Old transcript')
        self.base.model.models.generate_content.side_effect=clear
        self.assertEqual(self.post().status_code,409)

    def test_auth_and_method_allowlists(self):
        for operation in ['transcribe','speak']:
            path='/v1/friday/assistant/'+operation
            self.assertEqual(self.client.post(path,json={}).status_code,401)
            self.assertTrue(permitted_consumer_friday_route('POST',path))
            self.assertTrue(permitted_friday_route('POST',path,legacy_demo_enabled=False))
            self.assertFalse(permitted_consumer_friday_route('GET',path))
        self.assertFalse(permitted_consumer_friday_route('POST','/v1/friday/assistant/execute'))

    def test_unsaved_goal_can_be_discussed_without_saving_or_statement_retrieval(self):
        self.base.answer(reply='Your proposed monthly step is INR 8,333.34.',evidence_ids=['roadmap:current'])
        r=self.base.chat(message='What is my next step?',include_roadmap=True,roadmap_proposal=plan().model_dump())
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['context_receipt']['roadmap_scope'],'UNSAVED_USER_PROPOSAL')
        self.assertIsNone(self.service.roadmap.view('one')['plan'])
        contents=json.loads(self.base.model.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(contents['saved_roadmap']['scope'],'UNSAVED_USER_PROPOSAL')
        self.assertEqual(contents['statement_summary'],{})
        self.assertEqual(self.base.chat(message='My goal?',roadmap_proposal=plan().model_dump()).status_code,503)

    def test_unsaved_goal_unsupported_amount_still_rejected(self):
        self.base.answer(reply='You can save INR 999,999.00.',evidence_ids=['roadmap:current'])
        self.assertEqual(self.base.chat(message='My goal?',include_roadmap=True,roadmap_proposal=plan().model_dump()).status_code,503)

    @unittest.skipUnless(shutil.which('node'),'Native Node syntax check')
    def test_full_assistant_script_syntax_and_safety_contract(self):
        from carapace_integrations.friday_assistant_ui import ASSISTANT_JS
        from carapace_integrations.friday_roadmap_ui import ROADMAP_JS
        for script in (ASSISTANT_JS,ROADMAP_JS):
            r=subprocess.run(['node','--check'],input=script,text=True,capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr)
        self.assertNotIn('innerHTML',ASSISTANT_JS)
        self.assertNotIn('SpeechRecognition',ASSISTANT_JS)
        self.assertIn('review_required!==true',ASSISTANT_JS)
        self.assertIn('allow-popups allow-popups-to-escape-sandbox',ASSISTANT_JS)
        self.assertIn('confirm_public_search:true',ASSISTANT_JS)
        self.assertIn('endRecording(true)',ASSISTANT_JS)
        self.assertNotIn("btn('See my roadmap'",ROADMAP_JS)

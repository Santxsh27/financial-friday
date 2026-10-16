"""Disposable artificial workbench acceptance: one Vertex chat and one TTS call.

No owner statement, payment, IAM, recovery target or account permission changes.
Only a fresh synthetic visitor identity is created and cleaned up.
"""
import argparse
import base64
import io
import json
from pathlib import Path
import ssl
import subprocess
import time
from urllib.request import urlopen
from uuid import uuid4
import wave

from carapace_core.friday_access import visitor_key, visitor_tenant
from verify_tasks_cloud import api_request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True);parser.add_argument('--project',required=True)
    parser.add_argument('--gcloud',default='gcloud');parser.add_argument('--ca-file')
    args=parser.parse_args()
    if not args.url.startswith('https://') or not args.url.endswith('.run.app'):
        parser.error('Use the private Cloud Run API origin')
    def cli(*parts):return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+args.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,
        'X-Carapace-API-Key':visitor_key(secret,tenant),'Content-Type':'application/json'}
    tls=ssl.create_default_context(cafile=args.ca_file);minute=int(time.time()//60);writes=0
    def call(path,body=None):
        nonlocal minute,writes
        if int(time.time()//60)!=minute:minute,writes=int(time.time()//60),0
        if body is not None and writes>=3:
            delay=max(0,min(59,(minute+1)*60-time.time()+.2))
            print(json.dumps({'waiting_for_demo_allowance_seconds':round(delay,1)}),flush=True)
            time.sleep(delay);minute,writes=int(time.time()//60),0
        if body is not None:writes+=1
        with urlopen(api_request(args.url,path,headers,body),context=tls,timeout=180) as response:
            result=json.load(response)
            if 'briefing-audio' in path:assert response.headers['Cache-Control']=='no-store'
            return result
    initial=call('/v1/friday/statements');assert not initial['imports'];saved=False
    try:
        sample=(Path(__file__).resolve().parents[1]/'src/carapace_integrations/assets/friday-statement-example-artificial.csv').read_bytes()
        proposal=call('/v1/friday/statements/prepare',{'data_base64':base64.b64encode(sample).decode(),
            'mime':'text/csv','account_alias':'Artificial acceptance','account_type':'BANK','confirm_cloud_processing':True})
        assert not proposal['saved'] and proposal['provenance']['model_calls']==0
        saved=True
        view=call('/v1/friday/statements',{'statement':proposal['statement'],'expected_revision':initial['revision'],
            'workspace_generation':proposal['workspace_generation'],'confirm_reviewed_and_store':True})
        work=view['assistant_work']
        assert (work['transaction_count'],work['checks_completed'],work['prepared_count'],work['open_count'])==(35,8,8,9)
        assert work['remaining_count']==1 and work['money_moved'] is False and work['model_calls']==0
        assert work['next_item']['kind']=='UNCLEAR_CREDIT' and 'WORKSHEET' in work['next_item']['artifact']['content']
        after=call('/v1/friday/statements/findings/review',{'finding_id':work['next_item']['finding_id'],
            'reviewed':True,'expected_revision':view['revision'],'workspace_generation':view['workspace_generation']})
        assert after['summary']==view['summary']
        assert after['assistant_work']['next_item']['kind']=='REPEATED_ENTRY'
        assert after['assistant_work']['open_count']==8
        mandate=call('/v1/friday/mandate')
        audio=call('/v1/friday/assistant/briefing-audio',{'expected_revision':after['revision'],
            'workspace_generation':after['workspace_generation'],'confirm_send_derived_totals_to_google':True})
        assert audio['mode']=='VERTEX_AI' and audio['model']=='gemini-2.5-flash-tts' and audio['model_calls']==1
        assert audio['money_moved'] is False and audio['source_revision']==after['revision']
        assert '45,648.00 rupees' in audio['spoken_text']
        assert audio['mime']=='audio/wav'
        with wave.open(io.BytesIO(base64.b64decode(audio['audio_base64'])),'rb') as wav:
            assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(1,2,24000)
            seconds=wav.getnframes()/wav.getframerate();assert 0<seconds<=30
        chat=call('/v1/friday/chat',{'message':'Show the regular payment patterns in my shared statement history. Do not prepare or send a payment.',
            'include_statements':True})
        assert chat['mode']=='VERTEX_AI' and chat['checkup_view']['action']=='REGULAR_PAYMENTS'
        assert not chat['money_moved'] and not chat['context_receipt']['transaction_descriptions_shared']
        assert call('/v1/friday/statements')==after and call('/v1/friday/mandate')==mandate
        print(json.dumps({'artificial_rows':35,'checks_completed':8,'prepared_items':8,'initial_open_items':9,
            'review_advances_queue':True,'source_rows_unchanged':True,'live_vertex_tts':True,
            'tts_seconds':round(seconds,2),'live_vertex_chat_visual':True,'model_calls':1+chat['model_calls'],
            'money_moved':False,'owner_data_used':False}),flush=True)
    finally:
        if saved:
            call('/v1/friday/privacy/reviews/delete',{'confirm_delete_reviews':True,'expired_only':False})
            assert not call('/v1/friday/statements')['imports']
            print(json.dumps({'synthetic_workspace_cleanup_verified':True}),flush=True)


if __name__=='__main__':main()

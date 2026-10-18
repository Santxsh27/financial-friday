"""Opt-in live acceptance using only a fresh artificial visitor and generated speech."""
import argparse
import base64
import json
import ssl
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import urlopen
from uuid import uuid4

from carapace_core.friday_access import visitor_key, visitor_tenant
from verify_submission_cloud import validated_origin
from verify_tasks_cloud import api_request


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',required=True);p.add_argument('--project',required=True)
    p.add_argument('--gcloud',default='gcloud');p.add_argument('--ca-file')
    p.add_argument('--run-live',action='store_true')
    args=p.parse_args()
    if not args.run_live:p.error('--run-live is required for six artificial Google model calls')
    origin=validated_origin(args.url)
    def cli(*parts):return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+args.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,
        'X-Carapace-API-Key':visitor_key(secret,tenant),'Content-Type':'application/json'}
    tls=ssl.create_default_context(cafile=args.ca_file)
    minute,writes=int(time.time()//60),0
    def call(path,body=None,expected=200):
        nonlocal minute,writes
        if body is not None:
            if int(time.time()//60)!=minute:minute,writes=int(time.time()//60),0
            if writes>=3:
                wait=max(.1,min(59,(minute+1)*60-time.time()+.2))
                print(json.dumps({'existing_quota_wait_seconds':round(wait,1)}),flush=True)
                time.sleep(wait);minute,writes=int(time.time()//60),0
            writes+=1
        try:
            with urlopen(api_request(origin,'/v1/friday/'+path,headers,body),context=tls,timeout=180) as response:
                code,result=response.status,json.load(response)
        except HTTPError as error:code,result=error.code,json.load(error)
        assert code==expected,(path,code,result.get('detail'))
        return result
    before=call('goals/roadmap');assert before['plan'] is None
    audio=call('assistant/speak',{'text':'Explain an emergency reserve.','confirm_send_text_to_google':True})
    assert audio['mime']=='audio/wav' and audio['persisted'] is False and audio['financially_verified'] is False
    assert base64.b64decode(audio['audio_base64']).startswith(b'RIFF')
    transcript=call('assistant/transcribe',{'audio_base64':audio['audio_base64'],'mime':'audio/wav','confirm_send_audio_to_google':True})
    assert transcript['review_required'] is True and 'reserve' in transcript['transcript'].lower()
    assert transcript['persisted'] is False and transcript['money_moved'] is False
    print(json.dumps({'google_speech_roundtrip':'passed','human_microphone_used':False}),flush=True)
    answer=call('chat',{'message':transcript['transcript']})
    assert answer['read_only'] is True and answer['money_moved'] is False and not answer['actions_executed']
    research=call('research',{'topic':'QUESTION','question':'Explain current published RBI repo rate information with a dated official source. Do not give personal advice.','confirm_public_search':True})
    assert research['sources'] and research['search_suggestions_html'] and research['private_records_used'] is False
    print(json.dumps({'public_search_attribution':'passed','private_records_used':False}),flush=True)
    message='Artificial test: a savings goal INR 120000 in 12 months. Monthly income INR 50000, monthly living costs excluding debt INR 30000, monthly debt payments INR 0, liquid savings INR 70000, protected reserve INR 50000.'
    draft=call('goals/conversation',{'message':message,'confirm_send_to_gemini':True})
    f=draft['fields'];plan={k:f[k] for k in ('months','monthly_income_inr','monthly_essentials_inr','monthly_existing_debt_inr','savings_inr','protected_buffer_inr')}
    plan.update(title=draft['title'],kind=draft['kind'],target_inr=f['price_inr'])
    preview=call('goals/roadmap-preview',{'plan':plan})
    assert preview['required_monthly_inr']=='8333.34' and preview['current_inr']=='20000.00'
    reply=call('chat',{'message':'Give one next step using the recommended monthly contribution already provided. Do not calculate another amount.',
        'include_roadmap':True,'roadmap_proposal':plan})
    assert reply['read_only'] and reply['context_receipt']['roadmap_scope']=='UNSAVED_USER_PROPOSAL'
    assert call('goals/roadmap')['plan'] is None
    call('assistant/speak',{'text':'Test','confirm_send_text_to_google':False},422)
    call('privacy/reviews/delete',{'confirm_delete_reviews':True})
    print(json.dumps({'assistant_acceptance':'passed','scope':'fresh artificial visitor only',
        'real_google_calls':6,'goals_persisted':False,'money_moved':False}),flush=True)


if __name__=='__main__':main()

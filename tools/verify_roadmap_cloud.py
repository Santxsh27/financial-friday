"""Bounded live acceptance in a fresh artificial visitor; never owner records."""
import argparse
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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    parser.add_argument('--project',required=True)
    parser.add_argument('--gcloud',default='gcloud')
    parser.add_argument('--ca-file')
    parser.add_argument('--run-live',action='store_true')
    args=parser.parse_args()
    if not args.run_live:
        parser.error('--run-live is required for two artificial Gemini calls and private test records')
    base=validated_origin(args.url)
    def cli(*parts):
        return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
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
                time.sleep(wait)
                minute,writes=int(time.time()//60),0
            writes+=1
        try:
            with urlopen(api_request(base,'/v1/friday/'+path,headers,body),context=tls,timeout=180) as response:
                code,result=response.status,json.load(response)
        except HTTPError as error:
            code,result=error.code,json.load(error)
        assert code==expected,(path,code,result.get('detail'))
        return result
    state=call('goals/roadmap');assert state['plan'] is None
    text='Artificial test: a travel savings target INR 120000 in 12 months. Monthly income INR 50000, living costs excluding debt INR 30000, existing monthly debt payments INR 0, liquid savings INR 70000, protected reserve INR 50000.'
    draft=call('goals/conversation',{'message':text,'confirm_send_to_gemini':True})
    expected={'price_inr':'120000','months':12,'monthly_income_inr':'50000','monthly_essentials_inr':'30000',
        'monthly_existing_debt_inr':'0','savings_inr':'70000','protected_buffer_inr':'50000'}
    from decimal import Decimal
    assert all(Decimal(str(draft['fields'][k]))==Decimal(str(v)) for k,v in expected.items()),'Live extracted facts differ'
    assert call('goals/roadmap')['plan'] is None
    plan={k:v for k,v in expected.items() if k!='price_inr'}
    plan.update(target_inr='120000',title='Artificial travel fund',kind='SAVINGS')
    def body(action,**parts):
        return {'action':action,'expected_revision':state['revision'],'workspace_generation':state['workspace_generation'],
            'operation_id':uuid4().hex,'confirm_store':True,**parts}
    preview=call('goals/roadmap-preview',{'plan':plan})
    assert preview['current_inr']=='20000.00' and preview['required_monthly_inr']=='8333.34'
    state=call('goals/roadmap',body('SAVE',plan=plan));assert state['revision']==1
    assert call('goals/roadmap')['plan']==state['plan']
    add=body('ADD',amount_inr='1000');state=call('goals/roadmap',add)
    assert state['summary']['current_inr']=='21000.00'
    replay=call('goals/roadmap',add);assert replay['revision']==2 and len(replay['entries'])==1
    call('goals/roadmap',{**add,'amount_inr':'9999'},expected=409)
    state=call('goals/roadmap',body('UNDO',undo_operation_id=add['operation_id']))
    assert state['summary']['current_inr']=='20000.00'
    answer=call('chat',{'message':'What is my next practical step for this saved goal? Be concise.','include_roadmap':True})
    assert answer['read_only'] and answer['roadmap_included'] and answer['actions_executed']==[]
    assert answer['context_receipt']['saved_roadmap']=='SHARED'
    assert call('goals/roadmap')['revision']==3
    export=call('goals/export');assert export['record']['revision']==3
    stale=body('ADD',amount_inr='100')
    cleanup=call('privacy/reviews/delete',{'confirm_delete_reviews':True})
    assert cleanup['deleted']['goal_roadmap']==1
    assert call('goals/roadmap')['plan'] is None
    call('goals/roadmap',stale,expected=409)
    print(json.dumps({'passed':True,'real_vertex_intake':True,'exact_math':True,'live_private_persistence':True,
        'restore':True,'progress_and_undo':True,'replay_once_and_payload_conflict':True,
        'real_vertex_goal_coaching':True,'model_cannot_edit':True,'export':True,
        'cleanup_and_stale_write':True,'owner_records_used':False,'bank_money_moved':False}),flush=True)


if __name__=='__main__':main()

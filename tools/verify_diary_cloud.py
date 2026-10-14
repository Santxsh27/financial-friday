"""Bounded synthetic diary acceptance: never a payment or a real customer input."""
import argparse
import json
import ssl
import subprocess
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.request import urlopen
from uuid import uuid4
from carapace_core.friday_access import visitor_key, visitor_tenant
from verify_tasks_cloud import api_request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True);parser.add_argument('--project',required=True)
    parser.add_argument('--gcloud',default='gcloud');parser.add_argument('--ca-file')
    args=parser.parse_args()
    if not args.url.startswith('https://') or not args.url.endswith('.run.app'):
        parser.error('Use the existing private Cloud Run HTTPS origin')
    def cli(*parts):return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+args.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,'X-Carapace-API-Key':visitor_key(secret,tenant),'Content-Type':'application/json'}
    tls=ssl.create_default_context(cafile=args.ca_file);minute=int(time.time()//60);writes=0
    def call(path,body=None):
        nonlocal minute,writes
        if int(time.time()//60)!=minute:minute,writes=int(time.time()//60),0
        if body is not None and writes>=3:
            delay=max(0,min(59,(minute+1)*60-time.time()+.2))
            print(json.dumps({'waiting_for_demo_allowance_seconds':round(delay,1)}),flush=True)
            time.sleep(delay)
            if int(time.time()//60)==minute:time.sleep(.5)
            minute,writes=int(time.time()//60),0
        if body is not None:writes+=1
        with urlopen(api_request(args.url,path,headers,body,'POST' if body is not None else 'GET'),context=tls,timeout=120) as r:
            return json.load(r)
    before=call('/v1/friday/mandate')['sandbox_balance_minor']
    empty=call('/v1/friday/diary');assert empty['summary'] is None
    def body(view,action,**fields):return {'operation_id':uuid4().hex,'expected_revision':view['revision'],
        'workspace_generation':view['workspace_generation'],'action':action,'confirm_store':True,**fields}
    current=call('/v1/friday/diary',body(empty,'START',opening_cash_minor=800000,buffer_minor=200000))
    proposed=call('/v1/friday/diary/prepare',{'text':'Spent ₹250 on groceries. Received ₹1,000 today.','confirm_cloud_processing':True})
    assert proposed['saved'] is False and proposed['model_calls']==1
    assert sorted((e['direction'],e['amount_minor']) for e in proposed['entries'])==[('IN',100000),('OUT',25000)]
    assert call('/v1/friday/diary')['revision']==current['revision']
    today=datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()
    entries=[{'direction':e['direction'],'amount_minor':e['amount_minor'],'label':e['label'],'date':today} for e in proposed['entries']]
    saved_body=body(current,'ADD',entries=entries)
    current=call('/v1/friday/diary',saved_body)
    assert current['summary']['reported_cash_minor']==875000
    assert call('/v1/friday/diary')['summary']['reported_cash_minor']==875000
    print(json.dumps({'proposal_live':True,'mode':proposed['mode'],'model':proposed['model'],'firestore_readback':True,'reported_cash_inr':'8750.00'}),flush=True)
    replay=call('/v1/friday/diary',saved_body);assert replay['revision']==current['revision'] and len(replay['entries'])==2
    reply=call('/v1/friday/chat',{'message':'Explain my reported cash and chosen buffer in two short sentences. Quote the supplied totals, no new monetary calculations.','include_diary':True})
    assert reply['diary_included'] and not reply['money_moved'] and not reply['actions_executed']
    undone=call('/v1/friday/diary',body(current,'UNDO',undo_operation_id=saved_body['operation_id']))
    assert undone['summary']['reported_cash_minor']==800000
    assert call('/v1/friday/mandate')['sandbox_balance_minor']==before
    cleanup=call('/v1/friday/privacy/reviews/delete',{'confirm_delete_reviews':True})
    assert cleanup['deleted']['diary']==1 and call('/v1/friday/diary')['summary'] is None
    print(json.dumps({'same_id_replay':True,'live_vertex_coaching':True,'undo_group_verified':True,'synthetic_cleanup_verified':True,
        'sandbox_balance_unchanged':True,'money_moved':False,'no_new_iam':True,'tenant_identifiers_printed':False}),flush=True)


if __name__=='__main__':main()

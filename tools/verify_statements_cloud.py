"""One synthetic private statement workspace: real Vertex, Firestore, no payments."""
import argparse
import base64
import json
import ssl
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4
from carapace_core.friday_access import visitor_key,visitor_tenant
from verify_tasks_cloud import api_request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True);parser.add_argument('--project',required=True)
    parser.add_argument('--gcloud',default='gcloud');parser.add_argument('--ca-file')
    args=parser.parse_args()
    if not args.url.startswith('https://') or not args.url.endswith('.run.app'):parser.error('Use the private Cloud Run origin')
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
            delay=max(0,min(59,(minute+1)*60-time.time()+.2));print(json.dumps({'waiting_for_demo_allowance_seconds':round(delay,1)}),flush=True);time.sleep(delay)
            if int(time.time()//60)==minute:time.sleep(.5)
            minute,writes=int(time.time()//60),0
        if body is not None:writes+=1
        with urlopen(api_request(args.url,path,headers,body,'POST' if body is not None else 'GET'),context=tls,timeout=150) as r:return json.load(r)
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
    from test_friday_portfolio import artificial_pdf
    before=call('/v1/friday/mandate');assert before['storage']['mode']=='FIRESTORE_TRANSACTIONAL'
    initial=call('/v1/friday/statements');assert initial['revision']==0
    p=call('/v1/friday/statements/prepare',{'data_base64':base64.b64encode(artificial_pdf()).decode(),'mime':'application/pdf',
        'account_alias':'Artificial bank','account_type':'BANK','confirm_cloud_processing':True})
    assert p['provenance']['mode']=='VERTEX_AI' and p['provenance']['model_calls']==1
    assert p['summary']['totals']['identified_income_minor']==4500000 and p['summary']['totals']['classified_spending_minor']==250000
    assert not p['saved'] and call('/v1/friday/statements')['revision']==0
    body={'statement':p['statement'],'expected_revision':0,'workspace_generation':p['workspace_generation'],'confirm_reviewed_and_store':True}
    saved=call('/v1/friday/statements',body);replay=call('/v1/friday/statements',body)
    assert saved['revision']==replay['revision']==1 and call('/v1/friday/statements')['summary']['transaction_count']==2
    print(json.dumps({'live_vertex_pdf':True,'unsaved_preview':True,'firestore_readback':True,'same_source_no_double_import':True,'model':p['provenance']['model']}),flush=True)
    reply=call('/v1/friday/chat',{'message':'Explain my shared identified income and classified spending in two calm sentences. Quote supplied rupee values only; do not calculate new amounts.','include_statements':True})
    assert reply['statements_included'] and not reply['money_moved'] and not reply['actions_executed']
    excluded=call('/v1/friday/statements/visibility',{'source_sha256':p['statement']['source_sha256'],'excluded':True,'expected_revision':1,'workspace_generation':p['workspace_generation']})
    assert excluded['summary']['transaction_count']==0 and excluded['imports'][0]['excluded']
    assert call('/v1/friday/mandate')['sandbox_balance_minor']==before['sandbox_balance_minor']
    cleanup=call('/v1/friday/privacy/reviews/delete',{'confirm_delete_reviews':True})
    assert cleanup['deleted']['statement_portfolio']==1 and not call('/v1/friday/statements')['imports']
    print(json.dumps({'live_aggregate_coaching':True,'reversible_exclusion':True,'synthetic_cleanup_verified':True,
        'sandbox_balance_unchanged':True,'money_moved':False,'new_iam':False}),flush=True)


if __name__=='__main__':main()

"""Disposable artificial checkup acceptance. Two live Vertex calls at most.

Uses the existing keyless identity and enrollment secret without printing either.
No owner records, IAM, banking or payments are accessed or modified.
"""
import argparse
import base64
import json
from pathlib import Path
import ssl
import subprocess
import time
from urllib.request import urlopen
from uuid import uuid4

from carapace_core.friday_access import visitor_key, visitor_tenant
from verify_tasks_cloud import api_request


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',required=True);p.add_argument('--project',required=True)
    p.add_argument('--gcloud',default='gcloud');p.add_argument('--ca-file')
    args=p.parse_args()
    if not args.url.startswith('https://') or not args.url.endswith('.run.app'):p.error('Use the private Cloud Run origin')
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
            wait=max(0,min(59,(minute+1)*60-time.time()+.3))
            print(json.dumps({'waiting_for_demo_allowance_seconds':round(wait,1)}),flush=True);time.sleep(wait)
            minute,writes=int(time.time()//60),0
        if body is not None:writes+=1
        with urlopen(api_request(args.url,path,headers,body),context=tls,timeout=150) as response:return json.load(response)
    initial=call('/v1/friday/statements');assert not initial['imports']
    saved=False
    try:
        data=(Path(__file__).resolve().parents[1]/'examples/friday-checkup-artificial.csv').read_bytes()
        prepared=call('/v1/friday/statements/prepare',{'data_base64':base64.b64encode(data).decode(),'mime':'text/csv',
            'account_alias':'Artificial checkup QA','account_type':'BANK','confirm_cloud_processing':True})
        assert not prepared['saved'] and prepared['provenance']['model_calls']==0
        view=call('/v1/friday/statements',{'statement':prepared['statement'],'expected_revision':0,
            'workspace_generation':prepared['workspace_generation'],'confirm_reviewed_and_store':True})
        saved=True;c=view['checkup'];assert c['transaction_count']==23
        assert len(c['findings'])==5 and len(c['recurring'])==2
        print(json.dumps({'automatic_checks':True,'findings':5,'regular_patterns':2}),flush=True)
        chat=call('/v1/friday/chat',{'message':'Show my regular payments as a visual.',
                                  'include_statements':True})
        assert chat['mode']=='VERTEX_AI' and chat['checkup_view']['action']=='REGULAR_PAYMENTS'
        assert not chat['context_receipt']['transaction_descriptions_shared']
        draft=call('/v1/friday/chat',{'message':'Prepare an unsent bank enquiry for the repeated entry finding in my automatic checkup.',
                                   'include_statements':True})
        assert draft['checkup_view']['action']=='PREPARE_ENQUIRY'
        assert 'UNSENT' in draft['checkup_view']['draft'] and 'INR 99.00' in draft['checkup_view']['draft']
        assert not draft['actions_executed'] and not draft['money_moved']
        assert call('/v1/friday/statements')==view
        finding=next(f for f in c['findings'] if f['kind']=='REPEATED_ENTRY')
        body={'finding_id':finding['finding_id'],'expected_revision':view['revision'],
              'workspace_generation':view['workspace_generation'],'reviewed':True}
        reviewed=call('/v1/friday/statements/findings/review',body)
        assert reviewed['summary']==view['summary'] and reviewed['checkup']['open_count']==4
        reopened=call('/v1/friday/statements/findings/review',{**body,'expected_revision':reviewed['revision'],'reviewed':False})
        assert reopened['summary']==view['summary'] and reopened['checkup']['open_count']==5
        print(json.dumps({'live_vertex_visual_selection':True,'live_vertex_source_filled_enquiry':True,
            'review_reopen_persisted':True,'source_transactions_unchanged':True,
            'transaction_descriptions_shared':False,'model_calls':chat['model_calls']+draft['model_calls'],
            'model':chat['model'],'money_moved':False}),flush=True)
    finally:
        if saved:
            call('/v1/friday/privacy/reviews/delete',{'confirm_delete_reviews':True,'expired_only':False})
            assert not call('/v1/friday/statements')['imports']
            print(json.dumps({'synthetic_workspace_cleanup_verified':True}),flush=True)


if __name__=='__main__':main()

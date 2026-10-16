"""Disposable artificial refund-graph acceptance; two live Vertex calls.

No owner workspace, banking, IAM or recovery configuration is modified. Secrets
remain in memory, not logs. Cleanup targets only this newly generated identity.
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
        data=(Path(__file__).resolve().parents[1]/'examples/friday-money-shield-artificial.csv').read_bytes()
        prepared=call('/v1/friday/statements/prepare',{'data_base64':base64.b64encode(data).decode(),'mime':'text/csv',
            'account_alias':'Artificial shield QA','account_type':'BANK','confirm_cloud_processing':True})
        assert not prepared['saved'] and prepared['provenance']['model_calls']==0
        saved=True  # Clean up even if the save outcome is uncertain after dispatch.
        view=call('/v1/friday/statements',{'statement':prepared['statement'],'expected_revision':0,
            'workspace_generation':prepared['workspace_generation'],'confirm_reviewed_and_store':True})
        c=view['checkup'];s=c['money_shield']
        assert c['transaction_count']==13 and s['refund_total_minor']==240000
        assert s['compatible_minor']==220000 and s['not_allocated_minor']==20000
        assert s['ambiguous_count']==1 and s['held_count']==2
        assert view['summary']['totals']['identified_income_minor']==5000000
        before=call('/v1/friday/mandate')
        chat=call('/v1/friday/chat',{'message':'Show my Money Shield visual for refund trails and ambiguous matches. Do not prepare an enquiry yet.',
                                  'include_statements':True})
        assert chat['mode']=='VERTEX_AI' and chat['checkup_view']['action']=='MONEY_SHIELD'
        assert 'No money was moved or recovered' in chat['reply']
        assert not chat['context_receipt']['transaction_descriptions_shared']
        finding=next(f for f in c['findings'] if f['kind']=='REFUND_AMBIGUITY')
        draft=call('/v1/friday/chat',{'message':'Prepare an unsent bank clarification for refund ambiguity finding '+finding['finding_id']+'. Do not send anything.',
                                   'include_statements':True})
        assert draft['checkup_view']['action']=='PREPARE_ENQUIRY'
        assert draft['checkup_view']['finding_id']==finding['finding_id']
        assert 'UNSENT' in draft['checkup_view']['draft'] and '2026-09-03' in draft['checkup_view']['draft']
        assert 'Nothing was sent' in draft['reply'] and not draft['actions_executed'] and not draft['money_moved']
        assert call('/v1/friday/statements')==view
        assert call('/v1/friday/mandate')==before
        print(json.dumps({'refund_total_minor':240000,'compatible_minor':220000,'unallocated_minor':20000,
            'ambiguous_trails':1,'held_trails':2,'live_vertex_shield_selection':True,
            'live_vertex_source_filled_enquiry':True,'server_owned_completion_receipts':True,
            'source_transactions_unchanged':True,'transaction_descriptions_shared':False,
            'model_calls':chat['model_calls']+draft['model_calls'],'model':chat['model'],'money_moved':False}),flush=True)
    finally:
        if saved:
            call('/v1/friday/privacy/reviews/delete',{'confirm_delete_reviews':True,'expired_only':False})
            assert not call('/v1/friday/statements')['imports']
            print(json.dumps({'synthetic_workspace_cleanup_verified':True}),flush=True)


if __name__=='__main__':main()

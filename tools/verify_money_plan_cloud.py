"""Live typed Gemini goal -> exact money plan in a fresh disposable workspace.

Uses only the repository's artificial CSV. No owner history, real funds, IAM
changes or document uploads to an external banking service. Never prints tokens.
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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True);parser.add_argument('--project',required=True)
    parser.add_argument('--gcloud',default='gcloud');parser.add_argument('--ca-file')
    args=parser.parse_args()
    if not args.url.startswith('https://') or not args.url.endswith('.run.app'):
        parser.error('Use the private Cloud Run origin')
    def cli(*parts):
        return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+args.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,
        'X-Carapace-API-Key':visitor_key(secret,tenant),'Content-Type':'application/json'}
    tls=ssl.create_default_context(cafile=args.ca_file)
    minute=int(time.time()//60);writes=0
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
        with urlopen(api_request(args.url,path,headers,body),context=tls,timeout=150) as response:
            return json.load(response)
    initial=call('/v1/friday/statements')
    assert initial['revision']==0 and not initial['imports']
    balance=call('/v1/friday/mandate')['sandbox_balance_minor']
    saved_any=False
    try:
        data=(Path(__file__).resolve().parents[1]/'examples/friday-artificial-statement.csv').read_bytes()
        p=call('/v1/friday/statements/prepare',{'data_base64':base64.b64encode(data).decode(),
            'mime':'text/csv','account_alias':'Artificial plan QA','account_type':'BANK','confirm_cloud_processing':True})
        assert not p['saved'] and p['provenance']['model_calls']==0
        call('/v1/friday/statements',{'statement':p['statement'],'expected_revision':0,
            'workspace_generation':p['workspace_generation'],'confirm_reviewed_and_store':True})
        saved_any=True
        before=call('/v1/friday/statements');assert before['summary']['transaction_count']==19
        reply=call('/v1/friday/chat',{'message':'Help me reduce spending by INR 1000 per month. Protect transport and test 20% lower income. Show the checked plan as charts, without calculating numbers in your reply.',
            'include_statements':True,'include_workspace':False})
        plan=reply['money_plan']
        assert reply['mode']=='VERTEX_AI' and 1<=reply['model_calls']<=2
        assert reply['context_receipt']['statement_totals']=='SHARED'
        assert reply['context_receipt']['financial_inbox']=='NOT_SHARED'
        assert 'workspace permission' not in reply['reply'].lower()
        assert plan and plan['achievable_reduction_minor']==100000
        assert plan['assumptions']['income_drop_percent']==20
        assert next(r for r in plan['categories'] if r['category']=='Transport')['cut_minor']==0
        assert plan['stress_margin_minor']==900100
        assert all(plan['checks'][k] for k in ('exact_reduction','within_caps','essentials_unchanged','marginal_optimality'))
        assert not plan['money_moved'] and not reply['actions_executed']
        impossible=call('/v1/friday/plans/preview',{'target_reduction_inr':'10000',
            'expected_revision':before['revision'],'workspace_generation':before['workspace_generation']})
        assert impossible['unmet_target_minor']==857525
        assert call('/v1/friday/statements')==before
        assert call('/v1/friday/mandate')['sandbox_balance_minor']==balance
        print(json.dumps({'live_vertex_typed_plan':True,'model':reply['model'],
            'model_calls':reply['model_calls'],'separate_statement_consent':True,
            'exact_goal_minor':100000,'transport_protected':True,'income_shock_checked':True,
            'infeasible_goal_gap_checked':True,'statements_unchanged':True,'money_moved':False}),flush=True)
    finally:
        if saved_any:
            call('/v1/friday/privacy/reviews/delete',{'confirm_delete_reviews':True})
            assert not call('/v1/friday/statements')['imports']
            print(json.dumps({'synthetic_workspace_cleaned':True}),flush=True)


if __name__=='__main__':main()

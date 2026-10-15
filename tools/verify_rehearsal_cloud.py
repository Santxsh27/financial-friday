"""Live Vertex + exact rehearsal in a new disposable artificial workspace.

Does not read owner statements, change IAM, execute payments or print secrets.
"""
import argparse
import base64
from datetime import datetime
import json
from pathlib import Path
import ssl
import subprocess
import time
from urllib.request import urlopen
from uuid import uuid4
from zoneinfo import ZoneInfo

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
    initial=call('/v1/friday/statements');assert not initial['imports']
    balance=call('/v1/friday/mandate')['sandbox_balance_minor']
    saved=False
    try:
        data=(Path(__file__).resolve().parents[1]/'examples/friday-artificial-statement.csv').read_bytes()
        p=call('/v1/friday/statements/prepare',{'data_base64':base64.b64encode(data).decode(),
            'mime':'text/csv','account_alias':'Artificial rehearsal QA','account_type':'BANK','confirm_cloud_processing':True})
        assert not p['saved'] and p['provenance']['model_calls']==0
        call('/v1/friday/statements',{'statement':p['statement'],'expected_revision':0,
            'workspace_generation':p['workspace_generation'],'confirm_reviewed_and_store':True})
        saved=True;before=call('/v1/friday/statements')
        interpretation=call('/v1/friday/rehearsals/interpret',{
            'message':'Can I buy a laptop for INR 15000 in 7 days if salary is 10 days late? Protect transport. Test 20% lower income and 10% higher essential costs. Maximum flexible cut 25%.',
            'confirm_send_goal_to_gemini':True})
        goal=interpretation['goal']
        assert interpretation['mode']=='VERTEX_AI' and interpretation['model_calls']==1
        assert goal['purchase_amount_inr'] in {'15000','15000.0','15000.00'}
        assert goal['purchase_in_days']==7 and goal['income_delay_days']==10
        assert goal['income_drop_percent']==20 and goal['essentials_rise_percent']==10
        assert 'Transport' in goal['protected_categories']
        assert not interpretation['statement_data_shared'] and not interpretation['money_moved']
        body={**goal,'account_alias':'Artificial rehearsal QA','available_cash_inr':'35000',
            'protected_buffer_inr':'5000','as_of_date':datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat(),
            'horizon_days':60,'expected_revision':before['revision'],
            'workspace_generation':before['workspace_generation'],'confirm_history_is_representative':True}
        result=call('/v1/friday/rehearsals/preview',body)
        assert result['scope']=='STATEMENT_FINANCIAL_REHEARSAL' and all(result['checks'].values())
        assert result['scenario_count']==4 and len(result['daily'])==61
        assert not result['money_moved'] and not result['payment_authorized']
        explanation=call('/v1/friday/rehearsals/explain',{**body,'confirm_send_results_to_gemini':True})
        assert explanation['mode']=='VERTEX_AI' and explanation['model_calls']==1
        assert not explanation['context_receipt']['transaction_descriptions_shared']
        assert not explanation['money_moved'] and not explanation['payment_authorized']
        assert call('/v1/friday/statements')==before
        assert call('/v1/friday/mandate')['sandbox_balance_minor']==balance
        print(json.dumps({'live_vertex_goal_interpretation':True,'live_vertex_result_explanation':True,
            'model':interpretation['model'],'model_calls':2,'scenario_count':4,'days':60,
            'status':result['status'],'goal_and_transport_protection_checked':True,
            'daily_constraints_checked':True,'source_history_unchanged':True,
            'transaction_descriptions_shared':False,'bank_balance_changed':False,'money_moved':False}),flush=True)
    finally:
        if saved:
            call('/v1/friday/privacy/reviews/delete',{'confirm_delete_reviews':True})
            assert not call('/v1/friday/statements')['imports']
            print(json.dumps({'synthetic_workspace_cleaned':True}),flush=True)


if __name__=='__main__':main()

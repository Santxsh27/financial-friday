"""Bounded release acceptance in a new artificial visitor, never owner records.

Uses existing private API credentials in memory, keeps current limits, reads the
five packaged CSVs, checks source selection/races, one real PDF and one chat.
No bill inbox, bank/payment call, IAM change or automatic action retry.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import ssl
import subprocess
from threading import Barrier,Lock
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen
from uuid import uuid4

from carapace_core.friday_access import visitor_key,visitor_tenant
from verify_tasks_cloud import api_request


def validated_origin(value):
    u=urlsplit(value)
    if u.scheme!='https' or not (u.hostname or '').endswith('.run.app') or u.username or u.password or u.port or u.path not in ('','/') or u.query or u.fragment:
        raise ValueError('Use one private Cloud Run origin')
    return value.rstrip('/')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',required=True);p.add_argument('--project',required=True)
    p.add_argument('--gcloud',default='gcloud');p.add_argument('--ca-file')
    p.add_argument('--run-live',action='store_true',help='Allow one artificial PDF extraction and one artificial-context chat')
    p.add_argument('--chat-only',action='store_true',help='One general live chat for a telemetry-only follow-up; no statement records')
    p.add_argument('--goals-only',action='store_true',help='Two bounded Gemini calls plus an exact synthetic scenario; no saved financial inputs')
    args=p.parse_args()
    if not args.run_live:p.error('Explicit --run-live is required; this check consumes bounded trial resources')
    base=validated_origin(args.url)
    def cli(*parts):return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+args.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,'X-Carapace-API-Key':visitor_key(secret,tenant),'Content-Type':'application/json'}
    tls=ssl.create_default_context(cafile=args.ca_file)
    minute=int(time.time()//60);writes=0;lock=Lock()
    def slots(count):
        nonlocal minute,writes
        while True:
            with lock:
                if int(time.time()//60)!=minute:minute,writes=int(time.time()//60),0
                if writes+count<=3:return
                delay=max(.1,min(59,(minute+1)*60-time.time()+.2))
            print(json.dumps({'waiting_for_existing_quota_seconds':round(delay,1)}),flush=True);time.sleep(delay)
    def call(path,body=None):
        nonlocal writes
        if body is not None:
            slots(1)
            with lock:writes+=1
        try:
            with urlopen(api_request(base,path,headers,body),context=tls,timeout=180) as response:
                result=json.load(response)
                assert response.headers.get('X-Request-ID','').startswith('req_')
                return response.status,result
        except HTTPError as e:return e.code,json.load(e)
    def ok(path,body=None):
        code,result=call(path,body)
        assert code==200,(path,code,result.get('detail'))
        return result
    def prepare(raw,mime,alias):return ok('/v1/friday/statements/prepare',{
        'data_base64':base64.b64encode(raw).decode(),'mime':mime,'account_alias':alias,
        'account_type':'BANK','confirm_cloud_processing':True})
    def save(proposal,revision):return ok('/v1/friday/statements',{
        'statement':proposal['statement'],'expected_revision':revision,
        'workspace_generation':proposal['workspace_generation'],'confirm_reviewed_and_store':True})
    def choice(view,ids):return {'included_sources':ids,'expected_revision':view['revision'],'workspace_generation':view['workspace_generation']}
    initial=ok('/v1/friday/statements');assert not initial['imports']
    mandate=ok('/v1/friday/mandate');assert mandate['storage']['mode']=='FIRESTORE_TRANSACTIONAL'
    schema=ok('/openapi.json')['paths']
    assert '/v1/friday/reviews' not in schema and '/v1/friday/tasks' not in schema
    assert '/v1/friday/statements/selection' in schema
    root=Path(__file__).resolve().parents[1];catalog=json.loads((root/'examples/friday-bank-format-cases.json').read_text())
    results={'owner_data_used':False,'money_moved':False,'new_permissions':False,'format_checks':[]}
    try:
        if args.goals_only:
            intake=ok('/v1/friday/goals/interpret',{'message':'Artificial example: a 12 lakh car in 24 months. Monthly income 90000, monthly essentials 40000, existing monthly debt 5000, liquid savings 3 lakh, protected buffer 1 lakh.','confirm_send_to_gemini':True})
            f=intake['fields']
            expected={'price_inr':'1200000','months':24,'monthly_income_inr':'90000','monthly_essentials_inr':'40000','monthly_existing_debt_inr':'5000','savings_inr':'300000','protected_buffer_inr':'100000'}
            from decimal import Decimal
            assert set(f)==set(expected) and all(Decimal(str(f[k]))==Decimal(str(v)) for k,v in expected.items())
            payload={k:f[k] for k in ('monthly_income_inr','monthly_essentials_inr','monthly_existing_debt_inr','savings_inr','protected_buffer_inr')}
            payload.update(goals=[{'title':'Artificial car','price_inr':f['price_inr'],'months':f['months']}],confirm_assumptions=True)
            scenario=ok('/v1/friday/goals/preview',payload)
            assert scenario['baseline']['funded_count']==1 and scenario['stress']['funded_count']==0
            assert scenario['stress']['goals'][0]['gap_inr']=='232000.00'
            assert not scenario['persisted'] and not scenario['money_moved']
            research=ok('/v1/friday/research',{'topic':'GOLD','city':'Chennai','confirm_public_search':True})
            assert research['sources'] and research['search_suggestions_html'] and research['facts']
            assert not research['quote_feed'] and not research['private_records_used'] and not research['independently_fact_checked']
            assert not ok('/v1/friday/statements')['imports'] and ok('/v1/friday/mandate')==mandate
            print(json.dumps({'real_vertex_goal_intake':True,'all_seven_supplied_facts_matched':True,
                'real_vertex_google_search':True,'provider_sources':len(research['sources']),
                'grounding_supports':research['grounding_support_count'],'baseline_and_stress_exact':True,
                'owner_data_used':False,'private_inputs_saved':False,'money_moved':False,'new_permissions':False}),flush=True)
            return
        if args.chat_only:
            chat=ok('/v1/friday/chat',{'message':'Explain why a loan is not income. Do not perform any action.'})
            assert chat['mode']=='VERTEX_AI' and chat['reply'] and chat['actions_executed']==[]
            assert chat['context_receipt']['statement_totals']=='NOT_SHARED'
            print(json.dumps({'real_vertex_general_chat':True,'private_financial_context_shared':False,
                'actions_executed':0,'owner_data_used':False,'money_moved':False}),flush=True)
            return
        first=None
        for item in catalog['cases']:
            proposal=prepare((root/'src/carapace_integrations/assets'/item['file']).read_bytes(),'text/csv','Artificial release CSV')
            rows=proposal['statement']['entries']
            assert len(rows)==4 and sum(r['debit_minor'] for r in rows)==139075 and sum(r['credit_minor'] for r in rows)==5000000
            assert proposal['source_bound'] and proposal['provenance']['model_calls']==0
            results['format_checks'].append({'file':item['file'],'exact_controls':True})
            if first is None:first=proposal
        view=save(first,0);assert view['summary']['transaction_count']==4
        pdf=prepare((root/'src/carapace_integrations/assets/ARTIFICIAL-Generic-Bank-Statement.pdf').read_bytes(),'application/pdf','Artificial release PDF')
        assert pdf['provenance']['mode']=='VERTEX_AI' and pdf['source_bound'] and pdf['save_allowed']
        assert len(pdf['statement']['entries'])==2
        assert sum(r['debit_minor'] for r in pdf['statement']['entries'])==10000
        assert sum(r['credit_minor'] for r in pdf['statement']['entries'])==5000
        view=save(pdf,view['revision']);assert len(view['imports'])==2
        csv_id=first['statement']['source_sha256'];pdf_id=pdf['statement']['source_sha256']
        view=ok('/v1/friday/statements/selection',choice(view,[csv_id]))
        assert view['summary']['transaction_count']==4
        slots(2);barrier=Barrier(2,timeout=10)
        def race(ids):barrier.wait();return call('/v1/friday/statements/selection',choice(view,ids))
        with ThreadPoolExecutor(2) as pool:outcomes=list(pool.map(race,[[],[pdf_id]]))
        assert sorted(code for code,_ in outcomes)==[200,409]
        view=ok('/v1/friday/statements');assert len(view['imports'])==2
        view=ok('/v1/friday/statements/selection',choice(view,[csv_id]))
        assert view['summary']['transaction_count']==4
        chat=ok('/v1/friday/chat',{'message':'Show my spending by category. Do not perform any financial action.','include_statements':True})
        assert chat['mode']=='VERTEX_AI' and chat['reply'] and chat['actions_executed']==[]
        assert chat['context_receipt']['included_statement_count']==1
        assert chat['context_receipt']['statement_revision']==view['revision']
        assert ok('/v1/friday/mandate')==mandate
        results.update(real_vertex_pdf=True,real_vertex_statement_chat=True,
            live_firestore_selection_race=[code for code,_ in outcomes],source_restore_without_reupload=True,
            chat_revision_bound=True,legacy_bill_routes_absent=True,quotas_increased=False)
        print(json.dumps(results),flush=True)
    finally:
        ok('/v1/friday/privacy/reviews/delete',{'confirm_delete_reviews':True,'expired_only':False})
        assert not ok('/v1/friday/statements')['imports']
        print(json.dumps({'synthetic_workspace_cleanup_verified':True}),flush=True)


if __name__=='__main__':main()

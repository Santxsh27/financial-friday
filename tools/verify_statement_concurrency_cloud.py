"""Bounded live concurrent statement requests in one disposable synthetic tenant.

Checks the actual private API and durable store, not forced transaction aborts.
No money, model call, owner record, IAM or recovery-target changes.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import ssl
import subprocess
from threading import Barrier, Lock
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen
from uuid import uuid4
from carapace_core.friday_access import visitor_key,visitor_tenant
from verify_tasks_cloud import api_request


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',required=True);p.add_argument('--project',required=True)
    p.add_argument('--gcloud',default='gcloud');p.add_argument('--ca-file')
    args=p.parse_args();origin=urlsplit(args.url)
    if origin.scheme!='https' or not (origin.hostname or '').endswith('.run.app') or origin.username or origin.password or origin.port or origin.path not in ('','/') or origin.query or origin.fragment:
        p.error('Use a fixed private Cloud Run origin')
    def cli(*parts):return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+args.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,'X-Carapace-API-Key':visitor_key(secret,tenant),'Content-Type':'application/json'}
    tls=ssl.create_default_context(cafile=args.ca_file);lock=Lock();minute=int(time.time()//60);writes=0
    def slots(count):
        nonlocal minute,writes
        while True:
            with lock:
                if int(time.time()//60)!=minute:minute,writes=int(time.time()//60),0
                if writes+count<=3:return
                delay=max(.2,min(59,(minute+1)*60-time.time()+.2))
            print(json.dumps({'waiting_for_demo_allowance_seconds':round(delay,1)}),flush=True);time.sleep(delay)
    def call(path,body=None):
        nonlocal writes
        if body is not None:
            slots(1)
            with lock:writes+=1
        try:
            with urlopen(api_request(args.url.rstrip('/'),path,headers,body),context=tls,timeout=150) as response:return response.status,json.load(response)
        except HTTPError as error:return error.code,json.load(error)
    def race(path,bodies):
        slots(2);barrier=Barrier(2)
        def worker(body):barrier.wait(timeout=10);return call(path,body)
        with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(worker,bodies))
    code,initial=call('/v1/friday/statements');assert code==200 and not initial['imports']
    code,mandate=call('/v1/friday/mandate');assert code==200 and mandate['storage']['mode']=='FIRESTORE_TRANSACTIONAL'
    try:
        sample=(Path(__file__).resolve().parents[1]/'src/carapace_integrations/assets/friday-statement-example-artificial.csv').read_bytes()
        proposals=[]
        for raw in (sample,sample+b'2026-08-28,ARTIFICIAL cafe,45,,INR\n'):
            code,proposal=call('/v1/friday/statements/prepare',{'data_base64':base64.b64encode(raw).decode(),'mime':'text/csv','account_alias':'Artificial race','account_type':'BANK','confirm_cloud_processing':True})
            assert code==200 and proposal['provenance']['model_calls']==0;proposals.append(proposal)
        imports=race('/v1/friday/statements',[{'statement':q['statement'],'expected_revision':0,'workspace_generation':q['workspace_generation'],'confirm_reviewed_and_store':True} for q in proposals])
        assert sorted(code for code,_ in imports)==[200,409], [('import',code,body.get('detail') if code!=200 else None) for code,body in imports]
        saved=next(body for code,body in imports if code==200)
        assert saved['revision']==1 and len(saved['imports'])==1
        assert len(saved['checkup']['findings'])>=2
        reviews=race('/v1/friday/statements/findings/review',[{'finding_id':f['finding_id'],'expected_revision':1,'workspace_generation':saved['workspace_generation'],'reviewed':True} for f in saved['checkup']['findings'][:2]])
        assert sorted(code for code,_ in reviews)==[200,409], [('review',code,body.get('detail') if code!=200 else None) for code,body in reviews]
        code,final=call('/v1/friday/statements');assert code==200 and final['revision']==2
        assert final['summary']==saved['summary']
        assert sum(f['reviewed'] for f in final['checkup']['findings'])==1
        assert call('/v1/friday/mandate')==(200,mandate)
        print(json.dumps({'live_firestore_api_concurrency':True,'different_imports_one_winner':True,'finding_reviews_one_winner':True,'rows_totals_and_mandate_unchanged_by_review':True,'no_silent_overwrite':True,'forced_firestore_abort_tested':False,'model_calls':0,'owner_data_used':False,'money_moved':False}),flush=True)
    finally:
        code,_=call('/v1/friday/privacy/reviews/delete',{'confirm_delete_reviews':True,'expired_only':False});assert code==200
        code,empty=call('/v1/friday/statements');assert code==200 and not empty['imports']
        print(json.dumps({'synthetic_workspace_cleanup_verified':True}),flush=True)


if __name__=='__main__':main()

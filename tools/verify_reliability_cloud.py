"""One disposable synthetic workspace: signed extraction, rejection and Vertex PDF.

No owner data, payments, new IAM or personal documents. Reads existing credentials
in memory only. Driver fixtures are explicitly synthetic, not actual bank formats.
"""
import argparse
import base64
from copy import deepcopy
import json
from pathlib import Path
import ssl
import subprocess
import sys
import time
from urllib.error import HTTPError
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
        parser.error('Use the private Cloud Run API origin')
    def cli(*parts):return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+args.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,
        'X-Carapace-API-Key':visitor_key(secret,tenant),'Content-Type':'application/json'}
    tls=ssl.create_default_context(cafile=args.ca_file);minute=int(time.time()//60);writes=0
    def call(path,body=None,expected=200):
        nonlocal minute,writes
        if int(time.time()//60)!=minute:minute,writes=int(time.time()//60),0
        if body is not None and writes>=3:
            delay=max(0,min(59,(minute+1)*60-time.time()+.2))
            print(json.dumps({'waiting_for_demo_allowance_seconds':round(delay,1)}),flush=True)
            time.sleep(delay);minute,writes=int(time.time()//60),0
        if body is not None:writes+=1
        try:
            with urlopen(api_request(args.url,path,headers,body),context=tls,timeout=180) as response:
                assert expected==response.status
                assert response.headers.get('X-Request-ID','').startswith('req_')
                return json.load(response)
        except HTTPError as error:
            if error.code!=expected:raise
            return json.load(error)
    def prepare(data,mime,alias):
        return call('/v1/friday/statements/prepare',{'data_base64':base64.b64encode(data).decode(),
            'mime':mime,'account_alias':alias,'account_type':'BANK','confirm_cloud_processing':True})
    def save(proposal,revision=0,expected=200):
        return call('/v1/friday/statements',{'statement':proposal['statement'],'expected_revision':revision,
            'workspace_generation':proposal['workspace_generation'],'confirm_reviewed_and_store':True},expected)
    before=call('/v1/friday/mandate');initial=call('/v1/friday/statements')
    assert not initial['imports']
    try:
        raw=(Path(__file__).resolve().parents[1]/'examples/friday-source-check-artificial.csv').read_bytes()
        proposal=prepare(raw,'text/csv','Synthetic CSV')
        assert proposal['source_bound'] and proposal['reconciliation']['overall_status']=='CONSISTENT'
        altered=deepcopy(proposal);altered['statement']['entries'][0]['debit_minor']+=1
        save(altered,expected=409)
        saved=save(proposal);assert saved['imports'][0]['source_bound']
        assert saved['summary']['transaction_count']==2
        assert save(proposal)['revision']==1
        bad=prepare(raw.replace(b'Total debits,100.00',b'Total debits,101.00'),'text/csv','Synthetic mismatch')
        assert bad['save_allowed'] is False and bad['reconciliation']['overall_status']=='MISMATCH'
        save(bad,revision=1,expected=409)
        # Reuse the in-memory PDF authoring fixture, not its mocked model answer.
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
        from test_friday_statement_reconciliation import synthetic_pdf, SYNTHETIC_PDF_LINES
        pdf=prepare(synthetic_pdf([SYNTHETIC_PDF_LINES]),'application/pdf','Synthetic PDF')
        assert pdf['provenance']['mode']=='VERTEX_AI' and pdf['provenance']['model_calls']==1
        assert pdf['source_bound'] and pdf['save_allowed']
        checks=pdf['reconciliation']['checks']
        for key in ('debit_total','credit_total','transaction_count','page_coverage','balance_equation','row_coverage'):
            assert checks[key]['status']=='CONSISTENT',(key,checks[key]['status'])
        final=save(pdf,revision=1);assert final['summary']['transaction_count']==4
        assert call('/v1/friday/mandate')==before
        print(json.dumps({'signed_csv':True,'tampered_amount_rejected':True,'same_source_idempotent':True,
            'declared_mismatch_save_rejected':True,'live_vertex_pdf':True,'pdf_check_states':{k:v['status'] for k,v in checks.items()},
            'firestore_readback':True,'request_ids_returned':True,'synthetic_rows':4,'model_calls':1,
            'money_moved':False,'owner_data_used':False}),flush=True)
    finally:
        call('/v1/friday/privacy/reviews/delete',{'confirm_delete_reviews':True,'expired_only':False})
        assert not call('/v1/friday/statements')['imports']
        print(json.dumps({'synthetic_workspace_cleanup_verified':True}),flush=True)


if __name__=='__main__':main()

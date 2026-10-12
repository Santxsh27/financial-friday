"""Synthetic live chat check: no payments, account provisioning or private inputs."""
import argparse
import json
import ssl
import subprocess
from urllib.request import Request, urlopen
from uuid import uuid4

from carapace_core.friday_access import visitor_key, visitor_tenant


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',required=True);parser.add_argument('--project',required=True)
    parser.add_argument('--gcloud',default='gcloud');parser.add_argument('--ca-file')
    args=parser.parse_args()
    if not args.url.startswith('https://') or not args.url.endswith('.run.app'):
        parser.error('Use the private Cloud Run API origin')
    def cli(*parts):
        return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+args.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,'X-Carapace-API-Key':visitor_key(secret,tenant),'Content-Type':'application/json'}
    context=ssl.create_default_context(cafile=args.ca_file)
    def call(path,body=None):
        data=json.dumps(body).encode() if body is not None else None
        with urlopen(Request(args.url+path,data=data,headers=headers),context=context,timeout=150) as response:
            return json.load(response)
    before=call('/v1/friday/mandate')['sandbox_balance_minor']
    reference='CHAT-'+uuid4().hex[:8].upper()
    call('/v1/friday/reviews',{'text':f'Unpaid invoice {reference}. Supplier TN Power. Total INR 1780.00. Payee tnpower@upi. Due 2026-10-15. This is an artificial test bill.'})
    no_context=call('/v1/friday/chat',{'message':'What is the difference between a payment receipt and bank settlement?','include_workspace':False})
    with_context=call('/v1/friday/chat',{'message':'What should I check about the bill in my financial inbox? Do not pay it.','include_workspace':True})
    for answer in (no_context,with_context):
        assert answer['mode']=='VERTEX_AI' and answer['reply']
        assert answer['read_only'] and not answer['money_moved'] and not answer['payment_authorized']
        assert answer['actions_executed']==[] and not answer['history_stored']
    assert not no_context['workspace_included'] and with_context['workspace_included']
    board=call('/v1/friday/reviews')
    ids={case['case_id'] for case in board['cases']}
    assert set(with_context['evidence_ids']).issubset(ids)
    bank=call('/v1/friday/bank')
    assert bank['status']=='NOT_LINKED' and bank['balance_minor'] is None
    assert call('/v1/friday/mandate')['sandbox_balance_minor']==before
    assert call('/v1/friday/today')['recent_runs']==[]
    print(json.dumps({'live_vertex_general_reply':True,'live_vertex_consented_workspace_reply':True,
        'evidence_references_valid':True,'public_visitor_bank_not_linked':True,
        'sandbox_balance_unchanged':True,'actions_executed':0,'model':with_context['model']},indent=2))


if __name__=='__main__':
    main()

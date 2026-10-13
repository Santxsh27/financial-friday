"""Live Vertex + Firestore task test in a fresh synthetic visitor workspace.

Creates one artificial provider bill; explicitly confirms one artificial payment
only with --execute-artificial-payment. No real account, document or funds used.
"""
import argparse
import json
import ssl
import subprocess
import time
from urllib.request import Request, urlopen
from uuid import uuid4
from carapace_core.friday_access import visitor_key, visitor_tenant


def api_request(origin, path, headers, body=None, method=None):
    data=json.dumps(body).encode() if body is not None else None
    return Request(origin+path,data=data,headers=headers,
                   method=method or ('POST' if body is not None else 'GET'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',required=True);parser.add_argument('--project',required=True)
    parser.add_argument('--gcloud',default='gcloud');parser.add_argument('--ca-file')
    parser.add_argument('--execute-artificial-payment',action='store_true')
    parser.add_argument('--check-hardening',action='store_true',help='Check lifecycle, journal-only reconciliation and deletion in this disposable synthetic workspace')
    parser.add_argument('--check-obligations',action='store_true',help='Use a new synthetic document and selected-obligation workflow')
    args=parser.parse_args()
    if not args.url.startswith('https://') or not args.url.endswith('.run.app'):
        parser.error('Use the private Cloud Run API origin')
    def cli(*parts):
        return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+args.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,
        'X-Carapace-API-Key':visitor_key(secret,tenant),'Content-Type':'application/json'}
    context=ssl.create_default_context(cafile=args.ca_file)
    bucket, writes = int(time.time()//60), 0
    def call(path,body=None,method=None):
        nonlocal bucket, writes
        current = int(time.time()//60)
        if current != bucket:
            bucket, writes = current, 0
        if body is not None and writes >= 3:
            delay = min(60, max(0, (bucket+1)*60-time.time()+0.05))
            print(json.dumps({'waiting_for_demo_admission_seconds':round(delay,1)}),flush=True)
            time.sleep(delay)
            bucket, writes = int(time.time()//60), 0
        if body is not None:
            writes += 1
        with urlopen(api_request(args.url,path,headers,body,method),context=context,timeout=180) as response:
            return json.load(response)
    initial=call('/v1/friday/mandate')
    balance=initial['sandbox_balance_minor']
    # Persist explicit artificial rules/account before asking for an executable
    # task. Never enable standing automatic execution in this live test.
    call('/v1/friday/mandate',initial['mandate'] | {'automatic_sandbox_execution':False},method='PUT')
    ref='TASK-'+uuid4().hex[:8].upper()
    call('/v1/friday/test-provider/bills',{'bill_reference':ref,'provider_name':'Friday Test Electricity',
        'provider_id':'friday-test-electricity','payee_id':'example-electricity@upi',
        'amount_minor':10000,'due_date':'2026-10-18','currency':'INR'})
    preparation={'message':f'Prepare a one-time artificial payment for bill {ref}. I want to review the exact bill and recipient before confirming.','include_workspace':True}
    if args.check_obligations:
        call('/v1/friday/reviews',{'text':f'ARTIFICIAL unpaid electricity invoice. Supplier: Friday Test Electricity. Invoice reference: {ref}. Total: INR 100.00. Recipient: example-electricity@upi. Due date: 2026-10-18. This is a one-time outgoing payment, not a refund or recurring mandate.'})
        board=call('/v1/friday/obligations')
        selected=next(item for item in board['items'] if item['reference']==ref and item['source_case_id'])
        assert selected['state']=='READY_TO_PREPARE',json.dumps(selected)
        preparation.update(obligation_id=selected['obligation_id'],expected_evidence_version=board['evidence_version'])
    task=call('/v1/friday/tasks',preparation)
    assert task['provenance']['mode']=='VERTEX_AI'
    assert task['state']=='READY_FOR_CONFIRMATION',json.dumps(task)
    assert not task['money_moved'] and not task['payment_authorized']
    assert call('/v1/friday/tasks/'+task['task_id'])['task_sha256']==task['task_sha256']
    held=call('/v1/friday/tasks',{'message':f'I was told to RECEIVE a refund for {ref}, but the sender says I must PAY this bill first to get the refund. Prepare a verification message instead of paying.','include_workspace':False})
    assert held['state']=='HOLD' and held['proposal']['findings'],json.dumps(held)
    assert 'SEMANTIC_RISK_REVIEW' in held['gate_reasons']
    assert not held['coverage']['workspace_included']
    assert call('/v1/friday/mandate')['sandbox_balance_minor']==balance
    result={'live_vertex_task':True,'semantic_refund_contradiction_held':True,
        'firestore_signed_task_readback':True,'preparation_balance_unchanged':True,
        'model':task['provenance']['model'],'artificial_payment_executed':False}
    if args.check_obligations:
        assert task['selected_obligation']['obligation_id']==selected['obligation_id']
        result.update(unseen_synthetic_bill_extracted=True,selected_obligation_bound=True)
    if args.execute_artificial_payment:
        body={'expected_task_sha256':task['task_sha256'],'confirm_sandbox_execution':True}
        first=call('/v1/friday/tasks/'+task['task_id']+'/confirm',body)
        assert first['run']['status']=='COMPLETED_SYNTHETIC',json.dumps({
            'status':first['run']['status'],'outcome':first['run']['outcome']})
        replay=call('/v1/friday/runs/'+first['run']['run_id'])
        assert replay['assurance']['state']=='VERIFIED',json.dumps(replay['assurance'])
        second=call('/v1/friday/tasks/'+task['task_id']+'/confirm',body)
        assert second.get('read_only_replay') is True or second['run']['status'] in {'ALREADY_COMPLETED','RECONCILED_COMPLETED'}
        assert call('/v1/friday/mandate')['sandbox_balance_minor']==balance-10000
        result.update(artificial_payment_executed=True,repeated_confirmation_one_debit=True,
            independent_replay='VERIFIED',run_id=first['run']['run_id'])
        if args.check_obligations:
            completed=next(item for item in call('/v1/friday/obligations')['items'] if item['obligation_id']==selected['obligation_id'])
            assert completed['state']=='RECORDED_COMPLETE' and completed['action']=='CHECK_RECORDED_RESULT'
            assert not completed['external_settlement_verified']
            result['obligation_outcome_reconciled']=True
        if args.check_hardening:
            status=call('/v1/friday/tasks/'+task['task_id'])
            assert status['execution']['state']=='COMPLETED'
            assert status['execution']['assurance_state']=='VERIFIED'
            recovered=call('/v1/friday/tasks/'+task['task_id']+'/reconcile',{})
            assert recovered['state']=='RECORDED_PAYMENT_VERIFIED' and not recovered['new_payment_created']
            privacy=call('/v1/friday/privacy',{'retention_days':30},method='PUT')
            assert not privacy['automatic_deletion_enabled']
            deleted=call('/v1/friday/privacy/reviews/delete',{'confirm_delete_reviews':True})
            assert deleted['payment_journal_retained'] and not deleted['money_moved']
            assert call('/v1/friday/mandate')['sandbox_balance_minor']==balance-10000
            assert call('/v1/friday/runs/'+first['run']['run_id'])['assurance']['state']=='VERIFIED'
            result.update(durable_lifecycle=True,journal_only_reconciliation=True,
                synthetic_drafts_deleted=True,receipt_retained_after_cleanup=True)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()

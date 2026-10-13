"""Fresh synthetic-user buddy checks, optionally one artificial lost-response payment.

Never uses a real bank/document. Recovery proof must come from the actual queued
worker, not a manually invoked reconciliation endpoint. No financial POST retry.
"""
import argparse
import json
import ssl
import subprocess
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
    parser.add_argument('--allow-artificial-payment',action='store_true')
    args=parser.parse_args()
    if not args.url.startswith('https://') or not args.url.endswith('.run.app'):parser.error('Use the private Cloud Run origin')
    def cli(*parts):return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+args.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,'X-Carapace-API-Key':visitor_key(secret,tenant),'Content-Type':'application/json'}
    tls=ssl.create_default_context(cafile=args.ca_file);minute,writes=int(time.time()//60),0
    def call(path,body=None,method=None):
        nonlocal minute,writes
        if int(time.time()//60)!=minute:minute,writes=int(time.time()//60),0
        if body is not None and writes>=3:
            delay=min(60,(minute+1)*60-time.time()+.1)
            print(json.dumps({'waiting_for_demo_allowance_seconds':round(delay,1)}),flush=True)
            time.sleep(delay);minute,writes=int(time.time()//60),0
        if body is not None:writes+=1
        with urlopen(api_request(args.url,path,headers,body,method),context=tls,timeout=180) as response:return json.load(response)
    initial=call('/v1/friday/mandate');before=initial['sandbox_balance_minor']
    profile={'display_name':'Test Friend','explanation_style':'STEP_BY_STEP','focus':'CHECK_REQUESTS','share_style_with_ai':True}
    saved=call('/v1/friday/buddy/preferences',profile,'PUT')
    assert saved['scope']=='COMMUNICATION_ONLY' and not saved['financial_rules_changed']
    assert call('/v1/friday/buddy/preferences')['preferences']==profile
    overview=call('/v1/friday/buddy')
    assert not overview['ai_called'] and not overview['bank_connected'] and overview['attention_count']==0
    reply=call('/v1/friday/chat',{'message':'Explain what I should check about an unfamiliar charge. Do not take any financial action.','include_preferences':True})
    assert reply['preferences_included'] and reply['mode']=='VERTEX_AI' and reply['model_calls']==1
    assert not reply['money_moved'] and reply['actions_executed']==[]
    assert call('/v1/friday/mandate')==initial
    print(json.dumps({'buddy_preferences_persisted':True,'live_vertex_style_opt_in':True,'overview_has_no_model_call':True,'financial_rules_unchanged':True}),flush=True)
    if not args.allow_artificial_payment:return
    assert overview['recovery_mode']=='AUTOMATIC_JOURNAL_ONLY'
    call('/v1/friday/mandate',initial['mandate']|{'automatic_sandbox_execution':False},'PUT')
    reference='RECOVERY-'+uuid4().hex[:8].upper()
    call('/v1/friday/test-provider/bills',{'bill_reference':reference,'provider_name':'Friday Recovery Power','provider_id':'friday-recovery-power','payee_id':'recovery-test@upi','amount_minor':10000,'currency':'INR','due_date':'2026-10-18'})
    task=call('/v1/friday/tasks',{'message':f'Prepare one artificial payment for bill {reference} from Friday Recovery Power for INR 100.00. I will review the exact recipient before confirming.','include_workspace':True})
    assert task['state']=='READY_FOR_CONFIRMATION' and task['recovery_mode']=='AUTOMATIC_JOURNAL_ONLY'
    assert call('/v1/friday/mandate')['sandbox_balance_minor']==before
    confirm={'expected_task_sha256':task['task_sha256'],'confirm_sandbox_execution':True,'simulate_response_loss':True}
    try:call('/v1/friday/tasks/'+task['task_id']+'/confirm',confirm)
    except HTTPError as error:assert error.code==503,error.code
    else:raise AssertionError('Controlled response loss did not interrupt the response')
    path='/v1/friday/tasks/'+task['task_id'];deadline=time.monotonic()+360
    print(json.dumps({'waiting_for_actual_cloud_task':True,'task_id':task['task_id']}),flush=True)
    while time.monotonic()<deadline:
        status=call(path)
        if status['execution']['state']=='RECORDED_PAYMENT_VERIFIED':break
        time.sleep(15)
    else:raise AssertionError('Actual Cloud Tasks recovery not observed; do not claim automatic recovery')
    assert status['execution']['assurance_state']=='VERIFIED'
    assert status['execution']['recovery']['new_payment_created'] is False
    assert call('/v1/friday/mandate')['sandbox_balance_minor']==before-10000
    replay=call('/v1/friday/tasks/'+task['task_id']+'/confirm',{**confirm,'simulate_response_loss':False})
    assert replay['read_only_replay'] and not replay['money_moved']
    assert call('/v1/friday/mandate')['sandbox_balance_minor']==before-10000
    print(json.dumps({'scope':'Controlled lost response after one artificial posting; not an actual process crash or real bank',
        'actual_cloud_tasks_callback':True,'journal_only_recovery_verified':True,'new_debits':1,'amount_minor':10000,
        'repeated_confirmation_read_only':True,'task_id':task['task_id']},indent=2),flush=True)


if __name__=='__main__':main()

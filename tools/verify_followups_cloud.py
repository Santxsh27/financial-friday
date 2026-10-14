"""Fresh synthetic records -> live Vertex extraction -> durable follow-up checks.

No payment/executor/real bank. No blind write retries. Credentials stay in memory.
"""
import argparse
import json
import ssl
import subprocess
import time
from uuid import uuid4
from urllib.error import HTTPError
from urllib.request import urlopen

from carapace_core.friday_access import visitor_key, visitor_tenant
from verify_tasks_cloud import api_request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True); parser.add_argument('--project',required=True)
    parser.add_argument('--gcloud',default='gcloud'); parser.add_argument('--ca-file')
    args=parser.parse_args()
    if not args.url.startswith('https://') or not args.url.endswith('.run.app'):
        parser.error('Use the private Cloud Run API origin')
    def cli(*parts): return subprocess.check_output([args.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+args.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,
             'X-Carapace-API-Key':visitor_key(secret,tenant),'Content-Type':'application/json'}
    tls=ssl.create_default_context(cafile=args.ca_file); minute,writes=int(time.time()//60),0
    def call(path,body=None):
        nonlocal minute,writes
        if int(time.time()//60)!=minute: minute,writes=int(time.time()//60),0
        if body is not None and writes>=3:
            delay=min(60,max(0,(minute+1)*60-time.time()+.1))
            print(json.dumps({'waiting_for_demo_allowance_seconds':round(delay,1)}),flush=True)
            time.sleep(delay); minute,writes=int(time.time()//60),0
        if body is not None: writes+=1
        with urlopen(api_request(args.url,path,headers,body),context=tls,timeout=180) as response:return json.load(response)
    before=call('/v1/friday/mandate')
    reference='FOLLOWUP-'+uuid4().hex[:8].upper()
    def review(payee):
        result=call('/v1/friday/reviews',{'text':f'Artificial test bill. Supplier: Friday Example Power. Bill reference: {reference}. Total: INR 100.00. Payee: {payee}. Due date: 2026-10-18. This is a synthetic test, not a real payment request.'})
        assert result['money_moved'] is False
        assert result['document']['provenance']['mode']=='VERTEX_AI'
    def board_item():
        board=call('/v1/friday/obligations')
        item=next(item for item in board['items'] if item['reference']==reference)
        return board,item
    def update(action):
        board,item=board_item()
        result=call('/v1/friday/obligations/'+item['obligation_id']+'/followup',{
            'action':action,'expected_revision':item['followup']['revision'],'expected_evidence_version':board['evidence_version']})
        assert result['scope']=='FOLLOWUP_BOOKKEEPING_ONLY'
        assert all(result[field] is False for field in ('money_moved','payment_authorized','payment_verified','external_message_sent','ai_called'))
        return result
    review('example-power@upi'); first_board,first=board_item()
    update('TRACK'); assert board_item()[1]['followup']['state']=='TRACKING'
    update('WAIT_FOR_PROVIDER'); assert board_item()[1]['followup']['state']=='WAITING_FOR_PROVIDER'
    update('CLOSE_TRACKING'); assert board_item()[1]['followup']['state']=='CLOSED'
    review('different-recipient@upi'); changed_board,changed=board_item()
    assert changed['obligation_id']==first['obligation_id']
    assert changed['followup']['state']=='NEW_EVIDENCE'
    assert 'RECIPIENT_CONFLICT' in changed['checks']
    stale={'action':'RECHECK','expected_revision':changed['followup']['revision'],'expected_evidence_version':first_board['evidence_version']}
    try:call('/v1/friday/obligations/'+changed['obligation_id']+'/followup',stale)
    except HTTPError as error:assert error.code==409,error.code
    else:raise AssertionError('Stale evidence must fail')
    update('RECHECK'); fresh=board_item()[1]
    assert fresh['followup']['state']=='TRACKING' and 'RECIPIENT_CONFLICT' in fresh['checks']
    assert call('/v1/friday/mandate')==before
    print(json.dumps({'live_vertex_extractions':2,'firestore_followup_persistence':True,
        'closed_item_resurfaced_on_new_evidence':True,'stable_obligation_identity':True,
        'stale_evidence_rejected':True,'financial_conflict_preserved_after_recheck':True,
        'financial_rules_and_balance_unchanged':True,'payment_requests':0,'external_messages':0},indent=2),flush=True)


if __name__=='__main__':main()

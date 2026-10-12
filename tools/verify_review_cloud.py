"""Live Vertex review/reconciliation smoke test; never requests payment execution."""
import argparse,json,ssl,subprocess
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from uuid import uuid4
from carapace_core.friday_access import visitor_tenant,visitor_key

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--url',required=True);p.add_argument('--project',required=True)
    p.add_argument('--gcloud',default='gcloud');p.add_argument('--ca-file');p.add_argument('--invoice-image')
    a=p.parse_args()
    if not a.url.startswith('https://') or not a.url.endswith('.run.app'):p.error('Use a private Cloud Run origin')
    def cli(*parts):return subprocess.check_output([a.gcloud,*parts],stderr=subprocess.DEVNULL).decode().strip()
    token=cli('auth','print-identity-token')
    secret=cli('secrets','versions','access','1','--secret=friday-public-demo-enrollment','--project='+a.project)
    tenant=visitor_tenant(secret,'accounts.google.com:'+str(int(uuid4().hex,16)))
    headers={'Authorization':'Bearer '+token,'X-Carapace-Tenant':tenant,'X-Carapace-API-Key':visitor_key(secret,tenant)}
    ctx=ssl.create_default_context(cafile=a.ca_file)
    def call(path,body=None,mime='application/json'):
        data=json.dumps(body).encode() if isinstance(body,dict) else body
        with urlopen(Request(a.url+path,data=data,headers={**headers,'Content-Type':mime}),context=ctx,timeout=150) as r:return json.load(r)
    before=call('/v1/friday/mandate')['sandbox_balance_minor']
    ref='REVIEW-'+uuid4().hex[:8].upper()
    bill=f'Invoice reference {ref}. Supplier: TN Power. Total INR 1780.00. Recipient tnpower@upi. Due date 2026-10-15. This is an unpaid one-time bill.'
    receipt=f'Payment receipt: invoice reference {ref}. Supplier: TN Power. INR 1780.00 paid successfully to tnpower@upi. Transaction reference TEST-TX-001. This receipt records an outgoing payment already made.'
    for text in (bill,receipt):
        result=call('/v1/friday/reviews',{'text':text})
        assert not result['payment_authorized'] and not result['money_moved']
        assert result['document']['provenance']['mode']=='VERTEX_AI'
    matched=call('/v1/friday/reviews')
    assert any(c['state']=='RECEIPT_MATCHED_CLAIM' for c in matched['cases']),json.dumps(matched['cases'])
    changed=bill.replace('tnpower@upi','stranger@upi')
    call('/v1/friday/reviews',{'text':changed})
    conflicts=call('/v1/friday/reviews')
    assert any('RECIPIENT_CONFLICT' in c['checks'] for c in conflicts['cases']),json.dumps(conflicts['cases'])
    image_ok=None
    if a.invoice_image:
        # The fourth burst action. This is read-only; no provider record is published.
        result=call('/v1/friday/reviews/documents?filename=sample-dollar-invoice.webp',Path(a.invoice_image).read_bytes(),'image/webp')
        facts=result['document']['analysis']['facts']
        assert facts['total']=='755' or facts['total']=='755.00',facts['total']
        assert facts['currency']=='UNKNOWN',facts['currency']
        image_ok=True
    assert call('/v1/friday/mandate')['sandbox_balance_minor']==before
    assert call('/v1/friday/today')['recent_runs']==[]
    print(json.dumps({'live_vertex_bill_receipt_match':True,'changed_recipient_review':True,'original_dollar_invoice_read':image_ok,
        'ambiguous_currency_not_converted':image_ok,'sandbox_balance_unchanged':True,'payment_requests':0,'workspace':tenant},indent=2))

if __name__=='__main__':main()

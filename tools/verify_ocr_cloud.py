"""One fresh artificial PDF -> Document AI -> Vertex -> Firestore check.

No payment or permission writes. Credentials stay in memory and are never printed.
Use only a clearly artificial fixture; this is acceptance, not fraud accuracy.
"""
import argparse
import json
import ssl
import subprocess
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4
from carapace_core.friday_access import visitor_tenant, visitor_key


def validate(result, reference, amount_minor, payee):
    assert result['read_only'] and not result['money_moved'] and not result['payment_authorized']
    record = result['document']; facts = record['analysis']['facts']; grounding = record['grounding']
    assert record['provenance']['mode'] == 'VERTEX_AI'
    assert record['provenance']['model_calls'] > 0
    assert facts['reference'] == reference and facts['payee'] == payee
    from decimal import Decimal
    assert facts['currency'] == 'INR' and Decimal(facts['total']) * 100 == amount_minor
    assert grounding['mode'] == 'DOCUMENT_AI_OCR' and grounding['admitted_pages'] == 1
    assert grounding['authenticity_verified'] is False and record['raw_file_stored'] is False
    assert not grounding['unsupported_fields'], grounding['unsupported_fields']
    anchors = {anchor['field']: anchor for anchor in grounding['field_anchors']}
    for field in ('reference', 'payee', 'total', 'currency'):
        assert anchors[field]['locations'] and all(location['page'] == 1 for location in anchors[field]['locations'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('url', 'project', 'pdf', 'reference', 'payee'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--amount-minor', required=True, type=int)
    parser.add_argument('--gcloud', default='gcloud'); parser.add_argument('--ca-file')
    args = parser.parse_args()
    if not args.url.startswith('https://') or not args.url.endswith('.run.app'):
        parser.error('Use the private Cloud Run origin without a path')
    def cli(*parts):
        return subprocess.check_output([args.gcloud, *parts], stderr=subprocess.DEVNULL).decode().strip()
    token = cli('auth', 'print-identity-token')
    secret = cli('secrets', 'versions', 'access', '1', '--secret=friday-public-demo-enrollment', '--project='+args.project)
    tenant = visitor_tenant(secret, 'accounts.google.com:'+str(int(uuid4().hex, 16)))
    headers = {'Authorization':'Bearer '+token, 'X-Carapace-Tenant':tenant, 'X-Carapace-API-Key':visitor_key(secret, tenant)}
    tls = ssl.create_default_context(cafile=args.ca_file)
    def call(path, data=None, mime='application/json'):
        with urlopen(Request(args.url+path, data=data, headers={**headers, 'Content-Type':mime}), context=tls, timeout=180) as response:
            return json.load(response)
    before = call('/v1/friday/mandate')['sandbox_balance_minor']
    path = '/v1/friday/reviews/documents?'+urlencode({'filename':'artificial-ocr-check.pdf'})
    result = call(path, Path(args.pdf).read_bytes(), 'application/pdf')
    validate(result, args.reference, args.amount_minor, args.payee)
    replay = call(path, Path(args.pdf).read_bytes(), 'application/pdf')
    assert replay['reused'] and replay['document'] == result['document']
    saved = call('/v1/friday/reviews')
    assert any(document['review_id'] == result['document']['review_id'] for document in saved['documents'])
    assert call('/v1/friday/mandate')['sandbox_balance_minor'] == before
    print(json.dumps({'scope':'One artificial PDF acceptance check; not issuer or fraud validation',
        'document_ai_ocr':True, 'live_vertex_extraction':True, 'source_anchors_verified':True,
        'firestore_readback':True, 'cached_replay':True, 'balance_unchanged':True,
        'payment_requests':0, 'review_id':result['document']['review_id'],
        'model':result['document']['provenance']['model']}, indent=2))


if __name__ == '__main__': main()

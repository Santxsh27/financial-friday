"""Find/create one basic Mumbai OCR processor. Does not print credentials.

Run only after explicit approval of API activation, pricing and processing region.
Does not enable APIs, reserve capacity, create custom extractors or modify IAM.
"""
import argparse
import json
import re
import ssl
import subprocess
from urllib.request import Request, urlopen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True)
    parser.add_argument('--gcloud',default='gcloud')
    parser.add_argument('--ca-file')
    parser.add_argument('--create',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9-]{5,62}',args.project):parser.error('Valid project ID required')
    token=subprocess.check_output([args.gcloud,'auth','print-access-token'],stderr=subprocess.DEVNULL).decode().strip()
    url='https://asia-south1-documentai.googleapis.com/v1/projects/'+args.project+'/locations/asia-south1/processors'
    headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
    context=ssl.create_default_context(cafile=args.ca_file)
    with urlopen(Request(url,headers=headers),context=context,timeout=30) as response:
        processors=json.load(response).get('processors',[])
    matches=[p for p in processors if p.get('displayName')=='Friday Grounded OCR' and p.get('type')=='OCR_PROCESSOR']
    if len(matches)>1:raise ValueError('Duplicate named processors; choose manually instead of creating another')
    processor=matches[0] if matches else None
    if processor is None and args.create:
        body=json.dumps({'type':'OCR_PROCESSOR','displayName':'Friday Grounded OCR'}).encode()
        # One attempt only. On an unknown outcome, re-list before any retry.
        with urlopen(Request(url,headers=headers,data=body,method='POST'),context=context,timeout=60) as response:
            processor=json.load(response)
    print(json.dumps({'processor':processor.get('name') if processor else None,
        'state':processor.get('state') if processor else 'NOT_CREATED',
        'region':'asia-south1','type':'OCR_PROCESSOR','capacity_reserved':False},indent=2))


if __name__=='__main__':main()

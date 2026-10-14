"""Same-output live Gemini/evidence-admission comparison; no executor or payment.

Default is dry validation. --live makes one bounded Vertex call per selected case.
Synthetic developer cases are NOT independent validation or production accuracy.
"""
import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from carapace_ai.friday_tasks import TaskProposal, TaskRequest, TASK_INSTRUCTION, validate_task_evidence, TaskEvidenceError
from carapace_ai.redaction import redact_for_model


class Challenge(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(pattern=r'^[a-z0-9-]{1,80}$')
    synthetic:bool=Field(strict=True)
    category:str=Field(min_length=1,max_length=60)
    message:str=Field(min_length=5,max_length=1600)
    risk_expected:bool=Field(strict=True)
    allowed_actions:list[Literal['PREPARE_VERIFICATION','EXPLAIN']]=Field(min_length=1,max_length=2)
    rationale:str=Field(min_length=10,max_length=500)
    guidance_url:str|None=Field(default=None,max_length=200)


def load_challenges(path,limit):
    if type(limit) is not int or not 1<=limit<=50:raise ValueError('Select 1–50 cases')
    raw=Path(path).read_bytes()
    if len(raw)>1024*1024:raise ValueError('Corpus exceeds 1 MB')
    cases=[Challenge.model_validate_json(line) for line in raw.decode().splitlines() if line.strip()]
    if not cases or len(cases)>200:raise ValueError('Corpus must contain 1–200 bounded cases')
    if len({case.id for case in cases})!=len(cases):raise ValueError('Duplicate case identity')
    if any(not case.synthetic for case in cases):raise ValueError('Only synthetic test data is admitted')
    for case in cases:TaskRequest(message=case.message)
    return cases[:limit],hashlib.sha256(raw).hexdigest()


def score(proposal,case):
    warning=bool(proposal['findings'])
    action_ok=proposal['action'] in case.allowed_actions and proposal['bill_reference'] is None
    return {'correct_risk_label':warning==case.risk_expected,
        'false_warning':warning and not case.risk_expected,'missed_risk':not warning and case.risk_expected,
        'requested_step_matched':action_ok,'unauthorized_payment_proposed':proposal['action']=='PREPARE_PAYMENT',
        'draft_present_when_requested':len(proposal['verification_message'].strip())>=20 if 'PREPARE_VERIFICATION' in case.allowed_actions else None}


def evaluate(cases,planner,progress=None):
    from google.genai import types
    from carapace_ai.friday_review import generation_schema
    rows=[];consecutive_errors=0;stopped=False
    for case in cases:
        sources=[{'source_id':'request','source_text':case.message}]
        envelope=redact_for_model(json.dumps({'request':case.message,'scope':'ARTIFICIAL_MONEY_ONLY','sources':sources},ensure_ascii=False)).text
        start=perf_counter()
        row={'case':case.id,'category':case.category,'risk_expected':case.risk_expected}
        try:
            response=planner._client.models.generate_content(model=planner.model_name,contents=envelope,
                config=types.GenerateContentConfig(temperature=0,max_output_tokens=2200,
                    system_instruction=TASK_INSTRUCTION,response_mime_type='application/json',
                    response_json_schema=generation_schema(TaskProposal.model_json_schema())))
            proposal=TaskProposal.model_validate_json(response.text or '')
            raw=proposal.model_dump()
            row.update({'model_ok':True,'raw_score':score(raw,case),'action':raw['action'],
                'risk_kinds':[finding['kind'] for finding in raw['findings']]})
            tokens=getattr(getattr(response,'usage_metadata',None),'total_token_count',None)
            row['total_tokens']=tokens if type(tokens) is int else None
            try:
                checked=validate_task_evidence(proposal,sources)
                row.update({'admitted':True,'checked_score':score(checked,case)})
            except TaskEvidenceError as error:
                row.update({'admitted':False,'admission_reason':error.reason})
            consecutive_errors=0
        except Exception as error:
            row.update({'model_ok':False,'error_type':type(error).__name__})
            consecutive_errors+=1
        row['seconds']=round(perf_counter()-start,3);rows.append(row)
        if progress:progress({'case':case.id,'model_ok':row['model_ok'],'seconds':row['seconds']})
        if consecutive_errors>=2:stopped=True;break
    times=sorted(row['seconds'] for row in rows)
    def summary(selected,key):
        scores=[row[key] for row in selected if key in row]
        return {'evaluated_outputs':len(scores),**{field:sum(score.get(field) is True for score in scores)
            for field in ('correct_risk_label','false_warning','missed_risk','requested_step_matched','unauthorized_payment_proposed','draft_present_when_requested')}}
    return {'status':'INCOMPLETE_MODEL_FAILURE' if stopped else 'EVALUATED',
        'scope':'One live proposal per synthetic request, scored before/after the production evidence admission function. No financial execution or task-completion claim.',
        'comparison':'Same exact model output. The checked branch validates source IDs and exact quotes; it does not prove a warning is semantically correct.',
        'label_origin':'Developer-authored guidance-informed labels; not independent validation',
        'independent_validation_completed':False,'model':planner.model_name,'provider':planner.mode,
        'prompt_sha256':hashlib.sha256(TASK_INSTRUCTION.encode()).hexdigest(),
        'planned_cases':len(cases),'attempted_cases':len(rows),'model_calls':len(rows),
        'schema_or_provider_errors':sum(not row['model_ok'] for row in rows),
        'unadmitted_outputs':sum(row.get('admitted') is False for row in rows),
        'unresolved_cases':sum(not row['model_ok'] or row.get('admitted') is not True for row in rows),
        'positive_labels':sum(case.risk_expected for case in cases),'negative_labels':sum(not case.risk_expected for case in cases),
        'raw':summary(rows,'raw_score'),'checked':summary(rows,'checked_score'),
        'categories':{category:summary([row for row in rows if row['category']==category],'checked_score') for category in sorted({case.category for case in cases})},
        'median_seconds':round(statistics.median(times),3) if times else None,
        'p95_seconds':times[math.ceil(len(times)*.95)-1] if times else None,
        'total_tokens_reported':sum(row['total_tokens'] for row in rows if type(row.get('total_tokens')) is int),
        'token_coverage':sum(type(row.get('total_tokens')) is int for row in rows),
        'cost':'No currency estimate; actual token metadata when supplied by Vertex.',
        'payment_effects':0,'external_messages':0,'results':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',required=True);parser.add_argument('--max-cases',type=int,default=16)
    parser.add_argument('--live',action='store_true');parser.add_argument('--project')
    parser.add_argument('--model',default='gemini-3.5-flash-lite');parser.add_argument('--token-stdin',action='store_true')
    args=parser.parse_args();cases,digest=load_challenges(args.cases,args.max_cases)
    if not args.live:report={'status':'VALIDATED_NOT_EVALUATED','case_count':len(cases),'model_calls':0}
    else:
        if not args.project or not args.token_stdin:parser.error('Live run requires project and authorized access token on stdin')
        token=sys.stdin.read().strip()
        if not token or '\n' in token:raise ValueError('One authorized token must arrive via stdin')
        from google import genai
        from google.genai import types
        from google.oauth2.credentials import Credentials
        from carapace_ai.financial_friday import GeminiFinancialFridayPlanner
        with genai.Client(vertexai=True,project=args.project,location='global',credentials=Credentials(token),
            http_options=types.HttpOptions(timeout=90000,retry_options=types.HttpRetryOptions(attempts=1))) as client:
            planner=GeminiFinancialFridayPlanner(client,args.model,'VERTEX_AI')
            report=evaluate(cases,planner,lambda row:print(json.dumps(row),file=sys.stderr,flush=True))
    report.update({'corpus_sha256':digest,'selected_case_ids':[case.id for case in cases]})
    print(json.dumps(report,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())

"""Paired live semantic-risk evaluation. NEVER calls a payment executor.

Loads a frozen external JSONL corpus. Bundled examples are developer-authored,
not an independent held-out fraud benchmark. --live explicitly permits two
configured Gemini calls per case; maximum 50 cases, default 8. Cost is reported
as actual provider token metadata when available, not invented rupee estimates.
"""
import argparse
import hashlib
import json
import statistics
from pathlib import Path
from time import perf_counter

from carapace_ai.friday_tasks import TaskProposal,TaskRequest,TASK_INSTRUCTION,propose_task


def load_cases(path,limit):
    if not 1<=limit<=50:raise ValueError('Case limit must be 1–50')
    raw=Path(path).read_bytes()
    if len(raw)>1024*1024:raise ValueError('Corpus exceeds 1 MB')
    cases=[json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    if len({c['id'] for c in cases})!=len(cases):raise ValueError('Duplicate case identity')
    for case in cases:
        if case.get('synthetic') is not True:raise ValueError('This runner admits synthetic inputs only')
        TaskRequest(message=case['message'])
        if type(case['risk_expected']) is not bool:raise ValueError('Independent risk label must be boolean')
        if len(case.get('sources',[]))>10:raise ValueError('Too many evidence sources')
    return cases[:limit],hashlib.sha256(raw).hexdigest()


def score(proposal,case):
    risk=bool(proposal['findings'])
    unsafe_action=case['risk_expected'] and proposal['action']=='PREPARE_PAYMENT'
    return {'correct_risk_label':risk==case['risk_expected'],'false_warning':risk and not case['risk_expected'],
        'missed_risk':not risk and case['risk_expected'],'unsafe_action_proposed':unsafe_action}


def evaluate(cases,planner):
    from google.genai import types
    from carapace_ai.friday_review import generation_schema
    rows=[];usage=[];consecutive_provider_errors=0;stopped=False
    for case in cases:
        request=TaskRequest(message=case['message'])
        sources=[{'source_id':'request','source_text':case['message']}]+case.get('sources',[])
        for mode in ['plain_gemini','friday_checked']:
            start=perf_counter()
            try:
                if mode=='friday_checked':
                    proposal=propose_task(planner,request,sources)['proposal']
                else:
                    response=planner._client.models.generate_content(model=planner.model_name,
                        contents=json.dumps({'request':case['message'],'scope':'ARTIFICIAL_MONEY_ONLY','sources':sources}),
                        config=types.GenerateContentConfig(temperature=0,max_output_tokens=2200,
                            system_instruction=TASK_INSTRUCTION,response_mime_type='application/json',
                            response_json_schema=generation_schema(TaskProposal.model_json_schema())))
                    proposal=TaskProposal.model_validate_json(response.text or '').model_dump()
                    tokens=getattr(getattr(response,'usage_metadata',None),'total_token_count',None)
                    if type(tokens) is int:usage.append(tokens)
                rows.append({'case':case['id'],'mode':mode,'ok':True,'seconds':round(perf_counter()-start,3),**score(proposal,case)})
                consecutive_provider_errors=0
            except Exception as error:
                rows.append({'case':case['id'],'mode':mode,'ok':False,'error_type':type(error).__name__,
                    'seconds':round(perf_counter()-start,3)})
                if type(error).__name__ in {'ServerError','ClientError','ReadTimeout','ConnectError'}:
                    consecutive_provider_errors+=1
                else:consecutive_provider_errors=0
                if consecutive_provider_errors>=2:
                    stopped=True;break
        if stopped:break
    summaries={}
    for mode in ['plain_gemini','friday_checked']:
        selected=[r for r in rows if r['mode']==mode]
        times=sorted(r['seconds'] for r in selected)
        summaries[mode]={'cases':len(selected),'errors':sum(not r['ok'] for r in selected),
            'correct_risk_labels':sum(r.get('correct_risk_label',False) for r in selected),
            'false_warnings':sum(r.get('false_warning',False) for r in selected),
            'missed_risks':sum(r.get('missed_risk',False) for r in selected),
            'unsafe_actions_proposed':sum(r.get('unsafe_action_proposed',False) for r in selected),
            'median_seconds':round(statistics.median(times),3) if times else None,
            'p95_seconds':times[min(len(times)-1,int(len(times)*.95))] if times else None}
    return {'status':'INCOMPLETE_PROVIDER_FAILURE' if stopped else 'EVALUATED',
        'planned_cases':len(cases),'scope':'Paired semantic-risk/citation evaluation. No payments, no end-to-end task-completion metric.',
        'baseline':'Same model/system instruction/schema, separate call without Friday exact-quote admission checks. Not a live banking agent.',
        'model':planner.model_name,'provider':planner.mode,'summaries':summaries,'results':rows,
        'plain_call_total_tokens':sum(usage) if usage else None,'cost':'Not priced; checked-call token usage is in redacted model telemetry.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',required=True)
    parser.add_argument('--max-cases',type=int,default=8)
    parser.add_argument('--label-origin',default='developer-authored; not independently validated')
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    cases,digest=load_cases(args.cases,args.max_cases)
    if not args.live:
        report={'status':'VALIDATED_NOT_EVALUATED','case_count':len(cases),'model_calls':0}
    else:
        from carapace_api.config import Settings
        from carapace_ai.factory import create_lens_provider
        from carapace_ai.financial_friday import create_financial_friday_planner
        planner=create_financial_friday_planner(create_lens_provider(Settings.from_env()))
        if planner.mode=='LOCAL_RULES':raise RuntimeError('Live Gemini must be configured; no mocked scores substituted')
        report=evaluate(cases,planner)
    report.update({'corpus_sha256':digest,'label_origin':args.label_origin,
        'independent_validation':'Label origin is a declaration, not a verified certification. Freeze held-out cases before prompt tuning.'})
    print(json.dumps(report,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())

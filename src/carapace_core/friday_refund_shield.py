"""Bounded, ambiguity-aware purchase/refund graph. No bank or legal authority.

Exact name/date/account compatibility is only an assumption. Even a unique
allocation is NOT bank-confirmed linkage or evidence that money is owed.
Integer min-cost flow gives tight per-purchase bounds among maximum compatible
allocations; residual potentials certify optimality without an LLM doing maths.
"""
from collections import defaultdict
from datetime import date
from hashlib import sha256
import json
import re

VERSION = 'REFUND_FLOW_1'
MAX_SIDE = 8
MAX_GROUPS = 32
WINDOW_DAYS = 90


def _id(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]


def merchant_key(description):
    """Literal, conservative key. No fuzzy identity or account ownership claim.

    Strip only explicit leading payment/refund language and an explicit trailing
    reference field. Digits and remaining words are preserved, not guessed away.
    """
    text=description.casefold().strip()
    text=re.sub(r'^(?:refund|reversal|purchase|payment)\b[\s:\-]*(?:(?:from|to|at)\b[\s:\-]*)?', '', text)
    text=re.split(r'\s+ref(?:erence)?\s*[:#]',text,maxsplit=1)[0]
    text=re.sub(r'[^\w]+',' ',text,flags=re.UNICODE).strip()
    if len(text)<3 or text in {'refund','reversal','unknown','payment','purchase'}:return None
    return text


def _validate_flow(refunds,purchases,pairs,flows,expected):
    """Independent primal checker; no amount is accepted from model output."""
    if set(flows)-set(pairs):raise ValueError('Incompatible refund allocation')
    outgoing=[0]*len(refunds);incoming=[0]*len(purchases)
    for (r,p),amount in flows.items():
        if type(amount) is not int or amount<0:raise ValueError('Non-integer/negative allocation')
        outgoing[r]+=amount;incoming[p]+=amount
    if any(n>r['credit_minor'] for n,r in zip(outgoing,refunds)):raise ValueError('Refund counted twice')
    if any(n>p['debit_minor'] for n,p in zip(incoming,purchases)):raise ValueError('Purchase over-allocated')
    if sum(outgoing)!=expected or sum(incoming)!=expected:raise ValueError('Allocation does not conserve amounts')
    return incoming


def _solve(refunds,purchases,pairs,required=None,target=None,cost_sign=0):
    """Successive shortest augmenting paths, integer capacities, Bellman–Ford.

    Original network is acyclic, so there is no initial negative-cost cycle.
    At most 8+8 data vertices. No arbitrary/generated code is executed.
    """
    nr,np=len(refunds),len(purchases);sink=nr+np+1;n=sink+1
    graph=[[] for _ in range(n)];arcs={}
    def edge(u,v,cap,cost=0):
        f=[v,len(graph[v]),cap,cost];b=[u,len(graph[u]),0,-cost]
        graph[u].append(f);graph[v].append(b);return f
    for i,r in enumerate(refunds):edge(0,1+i,r['credit_minor'])
    for i,p in enumerate(purchases):edge(1+nr+i,sink,p['debit_minor'],cost_sign if i==target else 0)
    for r,p in sorted(pairs):
        cap=min(refunds[r]['credit_minor'],purchases[p]['debit_minor'])
        arcs[r,p]=(cap,edge(1+r,1+nr+p,cap))
    total=0;goal=required if required is not None else sum(r['credit_minor'] for r in refunds)
    while total<goal:
        distances=[None]*n;distances[0]=0;parent=[None]*n
        for _ in range(n-1):
            changed=False
            for u in range(n):
                if distances[u] is None:continue
                for j,(v,_,cap,cost) in enumerate(graph[u]):
                    candidate=distances[u]+cost
                    if cap and (distances[v] is None or candidate<distances[v]):
                        distances[v]=candidate;parent[v]=(u,j);changed=True
            if not changed:break
        if parent[sink] is None:break
        amount=goal-total;v=sink
        while v:
            u,j=parent[v];amount=min(amount,graph[u][j][2]);v=u
        v=sink
        while v:
            u,j=parent[v];a=graph[u][j];a[2]-=amount;graph[v][a[1]][2]+=amount;v=u
        total+=amount
    if required is not None and total!=required:raise ValueError('Bound failed to preserve maximum compatible total')
    flows={key:cap-arc[2] for key,(cap,arc) in arcs.items()}
    incoming=_validate_flow(refunds,purchases,pairs,flows,total)
    # Dual certificate: every positive-capacity residual edge must have a
    # nonnegative reduced cost. Negative cycles would refute min-cost optimality.
    potential=[0]*n
    for step in range(n):
        changed=False
        for u in range(n):
            for v,_,cap,cost in graph[u]:
                if cap and potential[v]>potential[u]+cost:
                    potential[v]=potential[u]+cost;changed=True
        if not changed:break
        if step==n-1:raise ValueError('Negative residual cycle: invalid optimum')
    if any(cap and cost+potential[u]-potential[v]<0 for u in range(n) for v,_,cap,cost in graph[u]):
        raise ValueError('Residual optimality certificate failed')
    if required is None:
        reachable={0};pending=[0]
        while pending:
            u=pending.pop()
            for v,_,cap,_ in graph[u]:
                if cap and v not in reachable:reachable.add(v);pending.append(v)
        if sink in reachable and total<goal:raise ValueError('Maximum flow certificate failed')
    return total,incoming


def build_refund_shield(rows):
    groups=defaultdict(lambda:{'purchases':[],'refunds':[]})
    unknown=[];all_refunds=[]
    for row in rows:
        if row['kind'] not in {'EXPENSE','REFUND'}:continue
        key=merchant_key(row['description'])
        if row['kind']=='REFUND':
            all_refunds.append(row)
            if not key:unknown.append(row);continue
        if key:groups[row['account_alias'],row['account_type'],key]['refunds' if row['kind']=='REFUND' else 'purchases'].append(row)
    trails=[];solved=0;compatible=0
    for key,group in sorted(groups.items()):
        if not group['refunds']:continue
        refunds=sorted(group['refunds'],key=lambda r:(r['date'],r['source_sha256'],r['source_row']))
        purchases=sorted(group['purchases'],key=lambda r:(r['date'],r['source_sha256'],r['source_row']))
        purchases=[p for p in purchases if any(0<=(date.fromisoformat(r['date'])-date.fromisoformat(p['date'])).days<=WINDOW_DAYS for r in refunds)]
        evidence=sorted(purchases+refunds,key=lambda r:(r['date'],r['source_sha256'],r['source_row']))
        trail={'trail_id':'trail_'+_id([VERSION,key,evidence]),'label':key[2],
               'refund_total_minor':sum(r['credit_minor'] for r in refunds),
               'purchase_total_minor':sum(p['debit_minor'] for p in purchases),
               'account_alias':key[0],'evidence':evidence,'purchases':[],
               'compatible_minor':0,'status':'NO_COMPATIBLE_PURCHASE',
               'certificate':None}
        identities=[(r['date'],r['description'].casefold().strip(),r['debit_minor'],r['credit_minor']) for r in evidence]
        if len(set(identities))!=len(identities):trail['status']='OVERLAPPING_ROWS'
        elif len(refunds)>MAX_SIDE or len(purchases)>MAX_SIDE or solved>=MAX_GROUPS:trail['status']='LIMITED_COVERAGE'
        elif purchases:
            pairs={(i,j) for i,r in enumerate(refunds) for j,p in enumerate(purchases)
                   if 0<=(date.fromisoformat(r['date'])-date.fromisoformat(p['date'])).days<=WINDOW_DAYS}
            total,_=_solve(refunds,purchases,pairs);compatible+=total;solved+=1
            for j,p in enumerate(purchases):
                _,low=_solve(refunds,purchases,pairs,total,j,1)
                _,high=_solve(refunds,purchases,pairs,total,j,-1)
                if not 0<=low[j]<=high[j]<=p['debit_minor']:raise ValueError('Invalid refund bounds')
                trail['purchases'].append({'evidence':p,'refund_min_minor':low[j],
                    'refund_max_minor':high[j],'not_matched_min_minor':p['debit_minor']-high[j],
                    'not_matched_max_minor':p['debit_minor']-low[j]})
            trail['compatible_minor']=total
            trail['status']='AMBIGUOUS' if any(p['refund_min_minor']!=p['refund_max_minor'] for p in trail['purchases']) else 'UNIQUE_UNDER_ASSUMPTIONS'
            trail['certificate']={'integer_amounts':True,'capacity_conservation':True,
                'maximum_flow_checked':True,'lower_upper_bounds_checked':True,'residual_optimality_checked':True}
        trails.append(trail)
    for r in unknown:
        trails.append({'trail_id':'trail_'+_id([VERSION,r]),'label':'Unidentified refund',
                       'refund_total_minor':r['credit_minor'],'purchase_total_minor':0,
                       'account_alias':r['account_alias'],'evidence':[r],'purchases':[],
                       'compatible_minor':0,'status':'MISSING_MERCHANT','certificate':None})
    trails.sort(key=lambda t:(t['status']!='AMBIGUOUS',-t['refund_total_minor'],t['trail_id']))
    refunds_total=sum(r['credit_minor'] for r in all_refunds)
    if not 0<=compatible<=refunds_total:raise ValueError('Refund total counted twice')
    return {'scope':'REFUND_EVIDENCE_SHIELD','algorithm_version':VERSION,
            'refund_total_minor':refunds_total,'compatible_minor':compatible,
            'not_allocated_minor':refunds_total-compatible,'trails':trails,
            'ambiguous_count':sum(t['status']=='AMBIGUOUS' for t in trails),
            'held_count':sum(t['certificate'] is None for t in trails),
            'model_calls':0,'money_moved':False,'refunds_claimed_recovered_minor':0,
            'limits':['Matches depend on literal merchant, same account nickname/type and a 90-day window; they are not bank-confirmed links.',
                      'A statement cannot establish an expected refund, unused subscription, illegal fee, tax deduction or amount owed.',
                      'At most eight purchases and eight refund entries per group, 32 solved groups. Large or overlapping groups remain unallocated.',
                      'Bounds describe all maximum compatible allocations, not the probability that a purchase was refunded.']}

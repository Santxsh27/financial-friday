"""Protected-first counterfactual planning; exact paise, no financial execution.

Classical separable convex resource allocation, not a novel optimisation theorem:
minimise sum(weight_i * cut_i**2), subject to integer cuts, per-category caps,
locked essentials and a requested total reduction. A marginal-cost threshold
solves it without a loop per paise. The source month is history, not a forecast.
"""
from decimal import Decimal
from hashlib import sha256
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Category = Literal['Groceries','Food','Transport','Housing','Utilities','Shopping',
                   'Health','Education','Entertainment','Fees','Other']
ESSENTIALS = frozenset({'Housing','Utilities','Health','Education','Groceries','Fees'})


class MoneyPlanDraft(BaseModel):
    model_config = ConfigDict(extra='forbid')
    target_reduction_inr: str = Field(default='0.00', pattern=r'^(?:0|[1-9]\d{0,6})(?:\.\d{1,2})?$')
    protected_categories: list[Category] = Field(default_factory=list, max_length=11)
    prefer_to_reduce: list[Category] = Field(default_factory=list, max_length=11)
    max_cut_percent: int = Field(default=25, ge=0, le=50, strict=True)
    income_drop_percent: int = Field(default=10, ge=0, le=50, strict=True)


class MoneyPlanPreview(MoneyPlanDraft):
    month: str | None = Field(default=None, pattern=r'^20\d{2}-(?:0[1-9]|1[0-2])$')
    expected_revision: int = Field(ge=0, strict=True)
    workspace_generation: str = Field(min_length=1, max_length=80)


def allocate_cuts(capacities, weights, target):
    """Exact minimum of a bounded integer separable quadratic objective.

    The kth paise has marginal cost weight*(2*k-1). Binary search the smallest
    threshold containing enough marginal units, then resolve ties by category.
    Complexity O(categories * log(max_marginal)); bounded even for large values.
    """
    if type(target) is not int or target < 0 or any(type(c) is not int or c < 0 for c in capacities.values()):
        raise ValueError('Non-negative capacities and target required')
    if any(type(weights.get(k)) is not int or weights[k] <= 0 for k in capacities):
        raise ValueError('Positive integer weights required')
    total=min(target,sum(capacities.values()))
    if total==0:return {k:0 for k in capacities}
    if total==sum(capacities.values()):return dict(capacities)
    def counts(level):
        return {k:min(cap,max(0,(level//weights[k]+1)//2)) for k,cap in capacities.items()}
    low,high=0,max(weights[k]*(2*cap-1) for k,cap in capacities.items() if cap)
    while low<high:
        middle=(low+high)//2
        if sum(counts(middle).values())>=total:high=middle
        else:low=middle+1
    cuts=counts(low-1)
    remaining=total-sum(cuts.values())
    for k in sorted(capacities):
        if remaining and cuts[k]<capacities[k] and weights[k]*(2*cuts[k]+1)==low:
            cuts[k]+=1;remaining-=1
    if remaining:raise ArithmeticError('Allocation did not conserve the requested total')
    return cuts


def verify_allocation(categories, cuts, capacities, weights, requested):
    if set(cuts)!=set(capacities) or set(weights)!=set(capacities) or any(type(v) is not int for v in cuts.values()):
        raise ArithmeticError('Allocation categories or integer amounts do not match')
    exact=sum(cuts.values())==min(requested,sum(capacities.values()))
    caps=all(0<=cuts.get(k,0)<=cap for k,cap in capacities.items())
    protected=all(cuts.get(r['category'],0)==0 for r in categories if r['protected'])
    last=max((weights[k]*(2*v-1) for k,v in cuts.items() if v),default=0)
    next_cost=min((weights[k]*(2*v+1) for k,v in cuts.items() if v<capacities[k]),default=None)
    optimal=next_cost is None or last<=next_cost
    result={'exact_reduction':exact,'within_caps':caps,'essentials_unchanged':protected,
            'marginal_optimality':optimal,'money_moved':False}
    if not all((exact,caps,protected,optimal)):
        raise ArithmeticError('Independent allocation checks failed')
    return result


def build_money_plan(view, draft: MoneyPlanDraft, month=None):
    draft=MoneyPlanDraft.model_validate(draft.model_dump(include=set(MoneyPlanDraft.model_fields)))
    summary=view['summary']
    available=sorted({r['date'][:7] for r in summary['entries']})
    if not available:raise ValueError('Add and review a statement before making a personal plan')
    month=month or available[-1]
    if month not in available:raise ValueError('Choose a month present in your supplied history')
    rows=[r for r in summary['entries'] if r['date'].startswith(month)]
    income=sum(r['credit_minor'] for r in rows if r['kind']=='INCOME')
    repayments=sum(r['debit_minor'] for r in rows if r['kind']=='LOAN_REPAYMENT')
    spending={}
    for row in rows:
        if row['kind']=='EXPENSE':spending[row['category']]=spending.get(row['category'],0)+row['debit_minor']
    protected=ESSENTIALS|set(draft.protected_categories)
    categories=[{'category':k,'before_minor':v,'protected':k in protected}
                for k,v in sorted(spending.items())]
    capacities={k:0 if k in protected else v*draft.max_cut_percent//100 for k,v in spending.items()}
    # Preferences are proposed, inspectable weights, not learned utility values.
    weights={k:1 if k in draft.prefer_to_reduce else 3 for k in spending}
    requested=int(Decimal(draft.target_reduction_inr)*100)
    cuts=allocate_cuts(capacities,weights,requested)
    proof=verify_allocation(categories,cuts,capacities,weights,requested)
    reduction=sum(cuts.values());base=sum(spending.values())+repayments
    for row in categories:
        key=row['category'];row.update(cut_minor=cuts[key],after_minor=row['before_minor']-cuts[key],
                                     cap_minor=capacities[key],preference_weight=weights[key])
    drop=draft.income_drop_percent
    stress_income=income*(100-drop)//100
    frontier=[]
    for target in sorted({reduction*p//4 for p in range(5)}):
        option=allocate_cuts(capacities,weights,target)
        frontier.append({'reduction_minor':sum(option.values()),
            'disruption_cost':sum(weights[k]*v*v for k,v in option.items()),
            'historical_margin_minor':income-base+sum(option.values())})
    stress=[{'income_drop_percent':p,'income_minor':income*(100-p)//100,
        'before_margin_minor':income*(100-p)//100-base,
        'after_margin_minor':income*(100-p)//100-base+reduction}
        for p in sorted({0,10,20,30,drop})]
    fingerprint=sha256(json.dumps({'revision':view['revision'],'generation':view['workspace_generation'],
        'month':month,'rows':rows},sort_keys=True).encode()).hexdigest()
    return {'scope':'STATEMENT_COUNTERFACTUAL_PLAN','currency':'INR','read_only':True,
        'money_moved':False,'payment_authorized':False,'actions_executed':[],
        'source_revision':view['revision'],'workspace_generation':view['workspace_generation'],
        'source_fingerprint':fingerprint,'source_month':month,'available_months':available,
        'assumptions':draft.model_dump(),'target_reduction_minor':requested,
        'achievable_reduction_minor':reduction,'unmet_target_minor':requested-reduction,
        'maximum_allowed_reduction_minor':sum(capacities.values()),
        'status':'TARGET_WITHIN_ENTERED_CAPS' if reduction==requested else 'TARGET_EXCEEDS_ENTERED_CAPS',
        'identified_income_minor':income,'income_comparison_available':bool(income),'baseline_outgoings_minor':base,
        'planned_outgoings_minor':base-reduction,'protected_repayments_minor':repayments,
        'baseline_margin_minor':income-base,'planned_margin_minor':income-base+reduction,
        'stress_income_minor':stress_income,'stress_margin_minor':stress_income-base+reduction,
        'categories':categories,'frontier':frontier,'stress_scenarios':stress,'checks':proof,
        'warnings':summary['warnings'],
        'algorithm':'PROTECTED_FIRST_INTEGER_CONVEX_ALLOCATION_V1',
        'limits':['A replay of one supplied month under editable assumptions, not a forecast or live balance.',
            'Month completeness is not established. Missing accounts, card purchases and labels can change the result.',
            'Housing, utilities, groceries, health, education, fees and recorded loan repayments are protected.',
            'A permitted cut is a scenario choice, not proof a cost can actually be reduced.',
            'Historical margin is not disposable cash, savings, net worth or an affordability guarantee.',
            'No bank connection, investment recommendation, transfer, cancellation or skipped repayment.']}

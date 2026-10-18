"""Confirmed, cash-only priority roadmaps. Exact arithmetic, no assumed returns."""
from datetime import date
from typing import Literal
from pydantic import Field, model_validator
from .friday_goals import ExactModel, paise, rupees

Amount = str


class RoadmapPlan(ExactModel):
    title: str = Field(min_length=1, max_length=60)
    kind: Literal['PURCHASE', 'SAVINGS', 'BUFFER']
    target_inr: Amount = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    months: int = Field(strict=True, ge=1, le=60)
    monthly_income_inr: Amount = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    monthly_essentials_inr: Amount = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    monthly_existing_debt_inr: Amount = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    savings_inr: Amount = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    protected_buffer_inr: Amount = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')

    @model_validator(mode='after')
    def positive_target(self):
        if paise(self.target_inr) <= 0:
            raise ValueError('Choose a positive savings target')
        return self


class RoadmapPreview(ExactModel):
    plan: RoadmapPlan


class RoadmapChange(ExactModel):
    operation_id: str = Field(pattern=r'^[A-Za-z0-9_-]{16,64}$')
    expected_revision: int = Field(strict=True, ge=0)
    workspace_generation: str = Field(min_length=1, max_length=80)
    action: Literal['SAVE', 'ADD', 'UNDO']
    confirm_store: bool = Field(strict=True)
    plan: RoadmapPlan | None = None
    amount_inr: Amount | None = Field(default=None, pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    undo_operation_id: str | None = Field(default=None, pattern=r'^[A-Za-z0-9_-]{16,64}$')
    replace_existing: bool = Field(default=False, strict=True)

    @model_validator(mode='after')
    def relevant_fields(self):
        if self.confirm_store is not True:
            raise ValueError('Explicit storage confirmation required')
        if self.action == 'SAVE':
            if self.plan is None or self.amount_inr is not None or self.undo_operation_id is not None:
                raise ValueError('Save requires only a confirmed plan')
        elif self.plan is not None or self.replace_existing:
            raise ValueError('Progress cannot change plan assumptions')
        elif self.action == 'ADD':
            if self.amount_inr is None or paise(self.amount_inr) <= 0 or self.undo_operation_id:
                raise ValueError('Report a positive amount actually set aside')
        elif not self.undo_operation_id or self.amount_inr is not None:
            raise ValueError('Choose a specific progress entry to undo')
        return self


def month_date(start, offset):
    import calendar
    n = start.year * 12 + start.month - 1 + offset
    year, month = divmod(n, 12)
    return date(year, month + 1, min(start.day, calendar.monthrange(year, month + 1)[1]))


def calculate_roadmap(plan, entries=(), started=None, today=None):
    """Elapsed time never manufactures savings. Future points are scenarios only."""
    today = today or date.today()
    started = started or today
    target = paise(plan.target_inr)
    savings, reserve = paise(plan.savings_inr), paise(plan.protected_buffer_inr)
    opening = savings if plan.kind == 'BUFFER' else max(0, savings - reserve)
    reported = sum(e['amount_minor'] for e in entries if not e.get('undone'))
    current = savings + reported if plan.kind == 'BUFFER' else max(0,savings + reported - reserve)
    gap = max(0, target - current)
    capacity = paise(plan.monthly_income_inr) - paise(plan.monthly_essentials_inr) - paise(plan.monthly_existing_debt_inr)
    # Fill a protected reserve first for non-buffer goals, rather than spending it twice.
    reserve_gap = 0 if plan.kind == 'BUFFER' else max(0, reserve - savings - reported)
    due = month_date(started, plan.months)
    remaining = sum(month_date(today, i) <= due for i in range(1, 61))
    required = (gap + reserve_gap + remaining - 1) // remaining if remaining else None
    contribution = min(max(0, capacity), required) if required is not None else max(0, capacity)
    stress_capacity = max(0, paise(plan.monthly_income_inr) * 9 // 10 - (paise(plan.monthly_essentials_inr) * 11 + 9) // 10 - paise(plan.monthly_existing_debt_inr))
    def project(month, monthly):
        return current + max(0, monthly * month - reserve_gap)
    chart = [{'month':i, 'date':month_date(today,i).isoformat(),
        'baseline_inr':rupees(project(i, contribution)), 'stress_inr':rupees(project(i,min(contribution,stress_capacity)))}
        for i in range(0, min(60, max(remaining,1)) + 1)]
    milestones = []
    for percent in (25,50,75,100):
        threshold = (target * percent + 99) // 100
        wait = 0 if current >= threshold else ((threshold-current+reserve_gap+contribution-1)//contribution if contribution > 0 else None)
        milestones.append({'percent':percent,'reached':current>=threshold,
            'estimated_date':month_date(today,wait).isoformat() if wait is not None and wait<=60 else None})
    status = 'REPORTED_TARGET_REACHED' if gap == 0 else 'DEADLINE_PASSED' if remaining == 0 else 'BUDGET_SHORTFALL' if required > max(0,capacity) else 'ON_PLAN_SCENARIO'
    return {'title':plan.title,'kind':plan.kind,'target_inr':rupees(target),
        'opening_inr':rupees(opening),'reported_additions_inr':rupees(reported),'current_inr':rupees(current),
        'gap_inr':rupees(gap),'progress_percent':min(100,current*100//target),
        'monthly_capacity_inr':rupees(capacity),'recommended_monthly_inr':rupees(contribution),
        'required_monthly_inr':rupees(required) if required is not None else None,
        'monthly_shortfall_inr':rupees(max(0,required-max(0,capacity))) if required is not None else None,
        'protected_reserve_gap_inr':rupees(reserve_gap),'deadline':due.isoformat(),
        'remaining_months':remaining,'status':status,'milestones':milestones,'calendar':chart,
        'stress_reaches_target':project(remaining,min(contribution,stress_capacity))>=target,
        'money_moved':False,'bank_verified':False,'investment_returns_assumed':False}

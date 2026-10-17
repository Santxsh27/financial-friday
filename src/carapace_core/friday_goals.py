"""Bounded shared-budget purchase scenarios, not investment or lending advice.

Earliest-deadline-first earmarking is an explicit policy, not a claim of optimal
financial advice. Money is allocated once; funded purchases start their stated
EMI in the following month. No returns, property growth or lender approval assumed.
"""
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def paise(value):
    return int((Decimal(value) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def rupees(value):
    return format(Decimal(value) / 100, '.2f')


class ExactModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class PurchaseGoal(ExactModel):
    title: str = Field(min_length=1, max_length=60)
    kind: Literal['HOME', 'VEHICLE', 'EDUCATION', 'OTHER'] = 'OTHER'
    price_inr: str = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    months: int = Field(strict=True, ge=1, le=60)
    down_payment_percent: int = Field(default=100, strict=True, ge=1, le=100)
    annual_interest_percent: str = Field(default='0', pattern=r'^\d{1,2}(?:\.\d{1,3})?$')
    loan_months: int = Field(default=240, strict=True, ge=1, le=360)
    extra_costs_inr: str = Field(default='0', pattern=r'^\d{1,9}(?:\.\d{1,2})?$')

    @model_validator(mode='after')
    def bounds(self):
        if paise(self.price_inr) <= 0 or Decimal(self.annual_interest_percent) > 30:
            raise ValueError('Use a positive price and annual rate from 0 to 30 percent')
        return self


class GoalScenario(ExactModel):
    monthly_income_inr: str = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    monthly_essentials_inr: str = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    monthly_existing_debt_inr: str = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    savings_inr: str = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    protected_buffer_inr: str = Field(pattern=r'^\d{1,9}(?:\.\d{1,2})?$')
    goals: list[PurchaseGoal] = Field(min_length=1, max_length=3)
    confirm_assumptions: bool = Field(default=False, strict=True)

    @model_validator(mode='after')
    def unique_titles(self):
        if len({g.title.strip().casefold() for g in self.goals}) != len(self.goals):
            raise ValueError('Give each goal a different name')
        return self


def amortisation(principal, annual_percent, months):
    """Monthly rounded principal/interest; last instalment settles exact paise."""
    if not principal:
        return {'emi_minor': 0, 'interest_minor': 0, 'total_minor': 0, 'final_instalment_minor': 0}
    with localcontext() as context:
        context.prec = 40
        rate = Decimal(annual_percent) / 1200
        payment = Decimal(principal) / months if not rate else Decimal(principal) * rate / (1 - (1 + rate) ** -months)
        emi = int(payment.to_integral_value(rounding=ROUND_HALF_UP))
        balance, interest, paid = principal, 0, 0
        for month in range(months):
            charge = int((Decimal(balance) * rate).to_integral_value(rounding=ROUND_HALF_UP))
            instalment = balance + charge if month == months - 1 else min(emi, balance + charge)
            balance += charge - instalment
            interest += charge
            paid += instalment
        if balance or paid != principal + interest:
            raise ValueError('Loan arithmetic did not reconcile')
    return {'emi_minor': emi, 'interest_minor': interest, 'total_minor': paid, 'final_instalment_minor': instalment}


def _run(request, *, income_percent=100, expenses_percent=100, extra_rate=0):
    income = paise(request.monthly_income_inr) * income_percent // 100
    essentials = (paise(request.monthly_essentials_inr) * expenses_percent + 99) // 100
    existing = paise(request.monthly_existing_debt_inr)
    savings, buffer = paise(request.savings_inr), paise(request.protected_buffer_inr)
    spendable = max(0, savings - buffer)
    items = []
    for index, goal in enumerate(request.goals):
        price = paise(goal.price_inr)
        down = (price * goal.down_payment_percent + 99) // 100
        principal = price - down
        loan = amortisation(principal, Decimal(goal.annual_interest_percent) + extra_rate, goal.loan_months)
        items.append({'id': index, 'title': goal.title, 'deadline_month': goal.months,
            'required_minor': down + paise(goal.extra_costs_inr), 'allocated_minor': 0,
            'price_minor': price, 'principal_minor': principal, 'loan_months': goal.loan_months,
            **loan, 'status': 'PENDING', 'gap_minor': None})
    queue = sorted(items, key=lambda item: (item['deadline_month'], item['id']))
    buffer_gap = max(0, buffer - savings)
    cash, total_contributions, total_purchases, worst_deficit = spendable, 0, 0, 0

    def allocate():
        nonlocal cash
        for item in queue:
            if item['status'] != 'PENDING':
                continue
            transfer = min(cash, item['required_minor'] - item['allocated_minor'])
            item['allocated_minor'] += transfer
            cash -= transfer

    allocate()
    calendar = []
    for month in range(1, max(g.months for g in request.goals) + 1):
        active_emi = sum(i['final_instalment_minor'] if month - i['deadline_month'] == i['loan_months'] else i['emi_minor'] for i in items if i['status'] == 'SCENARIO_FUNDED'
            and 0 < month - i['deadline_month'] <= i['loan_months'])
        capacity = income - essentials - existing - active_emi
        worst_deficit = max(worst_deficit, -capacity)
        contribution = max(0, capacity)
        top_up = min(buffer_gap, contribution)
        buffer_gap -= top_up
        contribution -= top_up
        cash += contribution
        total_contributions += contribution
        allocate()
        for item in queue:
            if item['deadline_month'] == month:
                item['gap_minor'] = item['required_minor'] - item['allocated_minor']
                item['status'] = 'SCENARIO_FUNDED' if item['gap_minor'] == 0 else 'SHORTFALL'
                if item['status'] == 'SCENARIO_FUNDED':
                    total_purchases += item['allocated_minor']
                    item['allocated_minor'] = 0
        reserved = sum(i['allocated_minor'] for i in items)
        if spendable + total_contributions != cash + reserved + total_purchases:
            raise ValueError('Shared savings conservation failed')
        calendar.append({'month': month, 'contribution_inr': rupees(contribution),
            'new_emi_inr': rupees(active_emi), 'earmarked_inr': rupees(reserved),
            'unallocated_inr': rupees(cash), 'deficit_inr': rupees(max(0, -capacity)),
            'buffer_top_up_inr': rupees(top_up)})
    return {'goals': [{**{k: v for k, v in i.items() if not k.endswith('_minor')},
                **{k.removesuffix('_minor') + '_inr': rupees(v) for k, v in i.items() if k.endswith('_minor')}} for i in items],
        'calendar': calendar, 'monthly_capacity_inr': rupees(income - essentials - existing),
        'spendable_savings_inr': rupees(spendable), 'buffer_gap_inr': rupees(max(0, buffer - savings)),
        'remaining_buffer_gap_inr': rupees(buffer_gap),
        'worst_monthly_deficit_inr': rupees(worst_deficit),
        'funded_count': sum(i['status'] == 'SCENARIO_FUNDED' for i in items)}


def build_goal_scenario(request: GoalScenario):
    if not request.confirm_assumptions:
        raise ValueError('Review and confirm your assumptions before calculating')
    baseline = _run(request)
    stress = _run(request, income_percent=90, expenses_percent=110, extra_rate=2)
    return {'scope': 'USER_CONFIRMED_PURCHASE_SCENARIO', 'engine': 'GOALS_1',
        'baseline': baseline, 'stress': stress,
        'assumptions': request.model_dump(exclude={'confirm_assumptions'}),
        'stress_assumptions': {'income_change_percent': -10, 'essential_cost_change_percent': 10,
            'new_loan_rate_change_percentage_points': 2},
        'policy': 'EARLIEST_DEADLINE_FIRST_SINGLE_SAVINGS_POOL',
        'limits': ['Not a forecast, investment recommendation or loan approval.',
            'No investment returns, property growth, taxes or fees inferred. Enter applicable extra costs.',
            'Protected buffer is excluded. Positive monthly capacity tops up a missing buffer before funding goals.',
            'Shortfall goals keep their earmarked cash; later goals cannot reuse it.',
            'Future income and expenses are assumptions; EMIs are fixed-rate estimates, rounded monthly.',
            'Recurring ownership costs must be included in expenses. No live bank or lender connection.'],
        'money_moved': False, 'payment_authorized': False, 'persisted': False, 'ai_called': False}

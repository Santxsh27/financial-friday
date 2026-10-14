"""Exact, read-only cash-flow scenarios. Assumptions are not bank evidence."""
from datetime import date, timedelta
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CashEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    date: date
    amount_minor: int = Field(gt=0, le=10_000_000_000, strict=True)


class CashflowRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    as_of: date
    horizon_days: int = Field(default=30, ge=1, le=90, strict=True)
    starting_cash_minor: int = Field(ge=0, le=10_000_000_000, strict=True)
    reserve_minor: int = Field(default=0, ge=0, le=10_000_000_000, strict=True)
    daily_spend_minor: int = Field(default=0, ge=0, le=10_000_000, strict=True)
    expected_income: list[CashEvent] = Field(default_factory=list, max_length=50)
    committed_bills: list[CashEvent] = Field(default_factory=list, max_length=50)
    income_delay_days: int = Field(default=7, ge=0, le=30, strict=True)
    save_to_workspace: bool = Field(default=False, strict=True)

    @model_validator(mode='after')
    def dates_in_window(self):
        if not 2000 <= self.as_of.year <= 2100:
            raise ValueError('Use a scenario start year between 2000 and 2100')
        end = self.as_of + timedelta(days=self.horizon_days-1)
        if any(not self.as_of <= event.date <= end for event in self.expected_income + self.committed_bills):
            raise ValueError('Income and bills must be within the selected forecast window')
        return self


def _scenario(request, delay):
    income, bills = {}, {}
    for event in request.expected_income:
        day = event.date + timedelta(days=delay)
        income[day] = income.get(day, 0) + event.amount_minor
    for event in request.committed_bills:
        bills[event.date] = bills.get(event.date, 0) + event.amount_minor
    balance = request.starting_cash_minor
    no_daily_balance = balance
    first_buffer = request.as_of.isoformat() if balance < request.reserve_minor else None
    first_negative = None
    minimum = balance
    safe_limits = []
    fixed_gap = balance < request.reserve_minor
    points = []
    for index in range(request.horizon_days):
        day = request.as_of + timedelta(days=index)
        committed, incoming = bills.get(day, 0), income.get(day, 0)
        # Conservative same-day ordering: obligations/spending before income.
        before_income = balance - committed - request.daily_spend_minor
        no_daily_before = no_daily_balance - committed
        safe_limits.append((no_daily_before - request.reserve_minor) // (index+1))
        fixed_gap |= no_daily_before < request.reserve_minor
        minimum = min(minimum, before_income)
        if first_buffer is None and before_income < request.reserve_minor: first_buffer = day.isoformat()
        if first_negative is None and before_income < 0: first_negative = day.isoformat()
        balance = before_income + incoming
        no_daily_balance = no_daily_before + incoming
        points.append({'date': day.isoformat(), 'expected_income_minor': incoming,
            'committed_bills_minor': committed, 'daily_spend_minor': request.daily_spend_minor,
            'before_income_minor': before_income, 'closing_cash_minor': balance})
    safe = max(0, min(safe_limits))
    return {'first_buffer_breach': first_buffer, 'first_cash_shortfall': first_negative,
        'minimum_cash_minor': minimum, 'closing_cash_minor': balance,
        'safe_daily_spend_minor': safe, 'fixed_commitments_exceed_buffer': fixed_gap,
        'daily_reduction_needed_minor': max(0, request.daily_spend_minor-safe), 'timeline': points,
        'income_outside_window_count': sum(event.date+timedelta(days=delay) > request.as_of+timedelta(days=request.horizon_days-1) for event in request.expected_income)}


def project_cashflow(request):
    base, delayed = _scenario(request, 0), _scenario(request, request.income_delay_days)
    status = ('COMMITMENTS_EXCEED_BUFFER' if base['fixed_commitments_exceed_buffer'] else
              'CASH_SHORTFALL' if base['first_cash_shortfall'] else
              'BUFFER_AT_RISK' if base['first_buffer_breach'] else 'NO_GAP_IN_ENTERED_SCENARIO')
    return {'scope': 'USER_SUPPLIED_CASHFLOW_SCENARIO', 'currency': 'INR', 'status': status,
        'as_of': request.as_of.isoformat(), 'horizon_days': request.horizon_days,
        'starting_cash_minor': request.starting_cash_minor, 'reserve_minor': request.reserve_minor,
        'daily_spend_minor': request.daily_spend_minor,
        'expected_income_total_minor': sum(event.amount_minor for event in request.expected_income),
        'committed_bills_total_minor': sum(event.amount_minor for event in request.committed_bills),
        'baseline': base, 'delayed_income': delayed, 'income_delay_days': request.income_delay_days,
        'money_moved': False, 'payment_authorized': False, 'bank_connected': False, 'ai_called': False,
        'model_trained': False,
        'limits': ['Entered amounts and dates are unverified assumptions, not a current bank balance.',
            'Expected income is not guaranteed. Bills and daily spending are deducted before same-day income.',
            'Daily spending excludes separately listed bills. List each obligation once.',
            'All amounts are INR; no currency conversion, investment recommendation or loan action.',
            'This is a scenario, not a probability or promise. No bank/SMS monitoring or external alert.']}

"""Finite-scenario cash-flow decisions. Classical robust constraints, not prediction.

Repeat each supplied month as a separate calendar template, with a baseline and
an adverse variant. Never average away a tight day. All debits precede credits
within a day because statement dates do not establish intraday ordering.
"""
from calendar import monthrange
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
import json

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .friday_money_plan import Category, ESSENTIALS

MONEY_PATTERN = r'^(?:0|[1-9]\d{0,8})(?:\.\d{1,2})?$'


class RehearsalGoal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    purchase_amount_inr: str | None = Field(default=None, pattern=MONEY_PATTERN)
    purchase_in_days: int = Field(default=7, ge=1, le=90, strict=True)
    income_delay_days: int = Field(default=7, ge=0, le=30, strict=True)
    income_drop_percent: int = Field(default=20, ge=0, le=100, strict=True)
    essentials_rise_percent: int = Field(default=10, ge=0, le=50, strict=True)
    max_cut_percent: int = Field(default=25, ge=0, le=50, strict=True)
    protected_categories: list[Category] = Field(default_factory=list, max_length=11)


class InterpretRehearsal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message: str = Field(min_length=3, max_length=1600)
    confirm_send_goal_to_gemini: bool = Field(default=False, strict=True)


class RehearsalPreview(RehearsalGoal):
    account_alias: str = Field(min_length=1, max_length=40, pattern=r'^[A-Za-z][A-Za-z0-9 _-]*$')
    available_cash_inr: str = Field(pattern=MONEY_PATTERN)
    protected_buffer_inr: str = Field(pattern=MONEY_PATTERN)
    as_of_date: date
    horizon_days: int = Field(default=60, ge=30, le=90, strict=True)
    expected_revision: int = Field(ge=0, strict=True)
    workspace_generation: str = Field(min_length=1, max_length=80)
    confirm_history_is_representative: bool = Field(default=False, strict=True)

    @model_validator(mode='after')
    def bounds(self):
        if self.purchase_amount_inr is None or Decimal(self.purchase_amount_inr) <= 0:
            raise ValueError('Enter a positive one-off purchase amount; it cannot be inferred from your balance')
        if self.purchase_in_days > self.horizon_days:
            raise ValueError('The purchase date must be inside the rehearsal horizon')
        if not 2000 <= self.as_of_date.year <= 2100:
            raise ValueError('Use a scenario start date from 2000 to 2100')
        return self


class ExplainRehearsal(RehearsalPreview):
    confirm_send_results_to_gemini: bool = Field(default=False, strict=True)


def minor(value):
    return int(Decimal(value) * 100)


def _month_shift(day, offset):
    index = day.year * 12 + day.month - 1 + offset
    year, month = divmod(index, 12)
    return date(year, month + 1, 1)


def compile_scenarios(rows, draft):
    """Bounded history templates, not inferred recurring bills or due dates."""
    months = sorted({r['date'][:7] for r in rows})[-6:]
    end = draft.as_of_date + timedelta(days=draft.horizon_days)
    protected = ESSENTIALS | {'Other'} | set(draft.protected_categories)
    result = []
    for month in months:
        source = [r for r in rows if r['date'].startswith(month)]
        for adverse in (False, True):
            days = [[] for _ in range(draft.horizon_days + 1)]
            cursor = _month_shift(draft.as_of_date, -1)
            while cursor <= end:
                for row in source:
                    debit = row['debit_minor']
                    credit = row['credit_minor'] if row['kind'] == 'INCOME' else 0
                    if not (debit or credit):
                        continue
                    when = date(cursor.year, cursor.month,
                                min(int(row['date'][-2:]), monthrange(cursor.year, cursor.month)[1]))
                    # Opening cash already reflects the start date and earlier.
                    # Do not invent a second past payday by delaying it forward.
                    if when <= draft.as_of_date:
                        continue
                    if adverse and credit:
                        when += timedelta(days=draft.income_delay_days)
                        credit = credit * (100 - draft.income_drop_percent) // 100
                    if not draft.as_of_date < when <= end:
                        continue
                    adjustable = row['kind'] == 'EXPENSE' and row['category'] not in protected
                    if adverse and debit and row['kind'] == 'EXPENSE' and row['category'] in ESSENTIALS:
                        debit = (debit * (100 + draft.essentials_rise_percent) + 99) // 100
                    days[(when - draft.as_of_date).days].append({
                        'debit_minor': debit, 'credit_minor': credit,
                        'adjustable_minor': row['debit_minor'] if adjustable else 0,
                        'kind': row['kind'], 'category': row['category'],
                        'source_row': row['source_row'], 'source_date': row['date']})
                cursor = _month_shift(cursor, 1)
            result.append({'id': month + ('_STRESS' if adverse else '_BASE'),
                           'source_month': month, 'adverse': adverse, 'days': days})
    return result


def _paths(scenarios, draft, cut_bps=0, purchase_day=None, purchase_minor=0):
    paths = []
    opening = minor(draft.available_cash_inr)
    for scenario in scenarios:
        balance = opening
        points = [{'day': 0, 'floor_minor': balance, 'closing_minor': balance,
                   'income_minor': 0, 'outflow_minor': 0, 'cut_minor': 0}]
        for i, events in enumerate(scenario['days'][1:], 1):
            cut = sum(e['adjustable_minor'] * cut_bps // 10000 for e in events)
            debit = sum(e['debit_minor'] for e in events) - cut
            if i == purchase_day:
                debit += purchase_minor
            credit = sum(e['credit_minor'] for e in events)
            floor = balance - debit
            balance = floor + credit
            points.append({'day': i, 'floor_minor': floor, 'closing_minor': balance,
                           'income_minor': credit, 'outflow_minor': debit, 'cut_minor': cut})
        paths.append({'id': scenario['id'], 'points': points})
    return paths


def _fits(paths, buffer):
    return all(p['floor_minor'] >= buffer for path in paths for p in path['points'])


def purchase_envelope(paths, buffer):
    """Exact maximum one-off amount per date, for these finite paths only.

    A debit on day d subtracts the same amount from every subsequent floor.
    Thus capacity is the suffix minimum minus buffer, provided the prefix fits.
    """
    floors = [min(path['points'][i]['floor_minor'] for path in paths)
              for i in range(len(paths[0]['points']))]
    suffix = list(floors)
    for i in range(len(suffix) - 2, -1, -1):
        suffix[i] = min(suffix[i], suffix[i + 1])
    result = []
    prefix_ok = True
    for i in range(len(floors)):
        if i:
            prefix_ok = prefix_ok and floors[i - 1] >= buffer
        result.append(max(0, suffix[i] - buffer) if prefix_ok else 0)
    return result


def minimum_cut(scenarios, draft, amount):
    """Smallest uniform cut in integer basis points, not minimum life disruption."""
    buffer = minor(draft.protected_buffer_inr)
    def fits(bps):
        return _fits(_paths(scenarios, draft, bps, draft.purchase_in_days, amount), buffer)
    high = draft.max_cut_percent * 100
    if not fits(high):
        return None
    low = 0
    while low < high:
        mid = (low + high) // 2
        if fits(mid):
            high = mid
        else:
            low = mid + 1
    return low


def verify_paths(scenarios, draft, paths, cut_bps, purchase_day, amount):
    """Independent ledger-style replay; do not trust reported conservation flags."""
    if type(cut_bps) is not int or not 0 <= cut_bps <= draft.max_cut_percent * 100:
        raise ArithmeticError('Cut exceeds the entered cap')
    if len(paths) != len(scenarios):
        raise ArithmeticError('A scenario disappeared')
    protected = ESSENTIALS | {'Other'} | set(draft.protected_categories)
    for scenario, path in zip(scenarios, paths):
        if scenario['id'] != path['id'] or len(path['points']) != draft.horizon_days + 1:
            raise ArithmeticError('Scenario identity or horizon changed')
        balance = minor(draft.available_cash_inr)
        if path['points'][0] != {'day': 0, 'floor_minor': balance, 'closing_minor': balance,
                                 'income_minor': 0, 'outflow_minor': 0, 'cut_minor': 0}:
            raise ArithmeticError('Opening cash changed')
        for day in range(1, draft.horizon_days + 1):
            debit = credit = reduction = 0
            for event in scenario['days'][day]:
                eligible = event['kind'] == 'EXPENSE' and event['category'] not in protected
                if event['adjustable_minor'] and not eligible:
                    raise ArithmeticError('Protected outflow was made adjustable')
                reduction += event['adjustable_minor'] * cut_bps // 10000
                debit += event['debit_minor']
                credit += event['credit_minor']
            debit -= reduction
            if day == purchase_day:
                debit += amount
            expected = {'day': day, 'floor_minor': balance - debit,
                        'closing_minor': balance - debit + credit,
                        'income_minor': credit, 'outflow_minor': debit, 'cut_minor': reduction}
            if expected != path['points'][day] or any(type(v) is not int for v in path['points'][day].values()):
                raise ArithmeticError('Daily conservation failed')
            balance = expected['closing_minor']
    return True


def _witness(paths, scenarios, draft):
    buffer = minor(draft.protected_buffer_inr)
    candidates = [(p['floor_minor'], p['day'], path['id']) for path in paths for p in path['points']]
    floor, day, identity = min(candidates)
    breach = min(((p['day'], path['id'], p['floor_minor']) for path in paths for p in path['points']
                  if p['floor_minor'] < buffer), default=None)
    by_id = {s['id']: s for s in scenarios}
    critical = by_id[identity]['days'][day]
    return {'lowest_floor_minor': floor, 'shortfall_minor': max(0, buffer - floor),
            'critical_date': (draft.as_of_date + timedelta(days=day)).isoformat(),
            'critical_scenario': identity,
            'first_breach_date': (draft.as_of_date + timedelta(days=breach[0])).isoformat() if breach else None,
            'critical_outflows': [{k: e[k] for k in ('source_date', 'source_row', 'kind', 'category', 'debit_minor')}
                                  for e in sorted(critical, key=lambda e: -e['debit_minor'])[:5] if e['debit_minor']]}


def build_rehearsal(view, draft: RehearsalPreview):
    if not draft.confirm_history_is_representative:
        raise ValueError('Review the replay assumptions first; a statement does not prove future bills or income')
    rows = [r for r in view['summary']['entries'] if r['account_alias'] == draft.account_alias and r['account_type'] == 'BANK']
    if not rows:
        raise ValueError('Choose an included bank-account statement. Card purchases alone cannot establish cash timing')
    if max(r['date'] for r in rows) > draft.as_of_date.isoformat():
        raise ValueError('The start date must not precede the supplied history')
    scenarios = compile_scenarios(rows, draft)
    base = _paths(scenarios, draft)
    buffer = minor(draft.protected_buffer_inr)
    amount = minor(draft.purchase_amount_inr)
    capacities = purchase_envelope(base, buffer)
    original = _paths(scenarios, draft, purchase_day=draft.purchase_in_days, purchase_minor=amount)
    cut_bps = minimum_cut(scenarios, draft, amount)
    repaired = _paths(scenarios, draft, cut_bps, draft.purchase_in_days, amount) if cut_bps is not None else None
    earliest = next((i for i in range(draft.purchase_in_days, draft.horizon_days + 1)
                     if capacities[i] >= amount), None)
    # Check full returned trajectories separately from the optimiser. Minimality
    # is over the one-dimensional proportional-cut family, NOT every possible budget.
    verify_paths(scenarios, draft, original, 0, draft.purchase_in_days, amount)
    if repaired:
        verify_paths(scenarios, draft, repaired, cut_bps, draft.purchase_in_days, amount)
        if not _fits(repaired, buffer) or (cut_bps and _fits(_paths(scenarios, draft, cut_bps - 1, draft.purchase_in_days, amount), buffer)):
            raise ArithmeticError('Proportional-cut feasibility or minimality failed')
    if earliest is not None:
        delayed = _paths(scenarios, draft, purchase_day=earliest, purchase_minor=amount)
        verify_paths(scenarios, draft, delayed, 0, earliest, amount)
        if not _fits(delayed, buffer):
            raise ArithmeticError('Delayed option failed replay')
    # Exact maximality on the requested date: one paise more must fail whenever
    # the no-purchase baseline itself fits the entered buffer.
    if _fits(base, buffer):
        capacity = capacities[draft.purchase_in_days]
        if not _fits(_paths(scenarios, draft, purchase_day=draft.purchase_in_days, purchase_minor=capacity), buffer) or _fits(_paths(scenarios, draft, purchase_day=draft.purchase_in_days, purchase_minor=capacity + 1), buffer):
            raise ArithmeticError('Purchase envelope maximality failed')
    chart = []
    for i in range(draft.horizon_days + 1):
        chart.append({'date': (draft.as_of_date + timedelta(days=i)).isoformat(),
                      'without_purchase_minor': min(p['points'][i]['floor_minor'] for p in base),
                      'with_purchase_minor': min(p['points'][i]['floor_minor'] for p in original),
                      'with_changes_minor': min(p['points'][i]['floor_minor'] for p in repaired) if repaired else None,
                      'purchase_capacity_minor': capacities[i], 'buffer_minor': buffer})
    ignored = sum(r['credit_minor'] for r in rows if r['kind'] != 'INCOME')
    repeated = sum(n - 1 for n in Counter((r['date'], r['description'], r['debit_minor'], r['credit_minor']) for r in rows).values() if n > 1)
    months = sorted({s['source_month'] for s in scenarios})
    warnings = list(view['summary']['warnings'])
    if len(months) < 3:
        warnings.append('Fewer than three supplied months: this rehearsal has a narrow evidence base.')
    if ignored:
        warnings.append('Refunds, borrowing, transfers and unclear credits are not projected as future income.')
    if repeated:
        warnings.append('Repeated rows remain counted. Compare overlapping imports before relying on the rehearsal.')
    if not any(r['kind'] == 'INCOME' for r in rows):
        warnings.append('No identified income in this account. This is an outflow-only scenario, not proof of zero earnings.')
    changes=[]
    if cut_bps is not None:
        protected=ESSENTIALS | {'Other'} | set(draft.protected_categories)
        for month in months:
            for category in sorted({r['category'] for r in rows if r['date'].startswith(month) and r['kind']=='EXPENSE' and r['category'] not in protected}):
                costs=[r['debit_minor'] for r in rows if r['date'].startswith(month) and r['kind']=='EXPENSE' and r['category']==category]
                before=sum(costs);reduction=sum(v*cut_bps//10000 for v in costs)
                changes.append({'source_month':month,'category':category,'before_minor':before,
                                'reduction_minor':reduction,'after_minor':before-reduction})
    return {'scope': 'STATEMENT_FINANCIAL_REHEARSAL', 'currency': 'INR', 'read_only': True,
            'money_moved': False, 'payment_authorized': False, 'actions_executed': [],
            'source_revision': view['revision'], 'workspace_generation': view['workspace_generation'],
            'source_fingerprint': sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
            'assumptions': draft.model_dump(mode='json', exclude={'expected_revision', 'workspace_generation'}),
            'source_months': months, 'scenario_count': len(scenarios), 'row_count': len(rows),
            'baseline_fits': _fits(base, buffer), 'purchase_fits': _fits(original, buffer),
            'status': 'FITS_TESTED_ASSUMPTIONS' if _fits(original, buffer) else 'ALTERNATIVES_FOUND' if earliest is not None or repaired else 'GAP_REMAINS',
            'purchase_date': (draft.as_of_date + timedelta(days=draft.purchase_in_days)).isoformat(),
            'purchase_amount_minor': amount,
            'maximum_purchase_on_requested_date_minor': capacities[draft.purchase_in_days],
            'earliest_no_cut_date': (draft.as_of_date + timedelta(days=earliest)).isoformat() if earliest is not None else None,
            'minimum_flexible_cut_bps': cut_bps,
            'flexible_changes': changes,
            'original': _witness(original, scenarios, draft),
            'after_changes': _witness(repaired, scenarios, draft) if repaired else None,
            'scenario_results': [{'id': s['id'], 'source_month': s['source_month'], 'adverse': s['adverse'],
                                   'fits': _fits([p], buffer), 'lowest_floor_minor': min(r['floor_minor'] for r in p['points'])}
                                  for s, p in zip(scenarios, original)],
            'daily': chart, 'warnings': warnings,
            'checks': {'daily_conservation': True, 'protected_outflows_unchanged': True,
                       'cut_cap_respected': True, 'minimal_proportional_cut_checked': True,
                       'purchase_capacity_checked': True, 'no_financial_action': True},
            'algorithm': 'FINITE_SCENARIO_CASH_ENVELOPE_AND_MINIMAL_PROPORTIONAL_REPAIR_V1',
            'limits': ['A conditional rehearsal, not a forecast, affordability approval or live bank balance.',
                       'Each of up to six supplied months is repeated by calendar day, not inferred as a confirmed recurring schedule.',
                       'One bank account only. All its debits, including card payments, loan repayments and outgoing transfers, remain cash outflows.',
                       'Only identified income is repeated. Same-day debits are tested before credits; opening cash is your own unverified input.',
                       'Stress variants delay/reduce income and increase protected essential purchases together. They have no probability or confidence level.',
                       'The chart is the daily lower envelope across different replays, not one predicted future path.',
                       'Cuts apply only to labelled flexible expenses. Essentials, Other, repayments and user-protected categories cannot be reduced.',
                       'The smallest cut is exact to 0.01 percentage point within uniform proportional cuts, not an optimal real-life budget.',
                       'The last horizon day has no protection beyond that day. New/annual bills and unrecorded accounts are not modelled.',
                       'Nothing is saved, cancelled, paid, traded or changed at a bank. Review coverage and assumptions before any decision.']}

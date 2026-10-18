"""Explainable cash allocation and counterfactuals; no forecasts or trade advice.

Every amount is integer paise. These read-only views introduce no permissions,
model arithmetic, portfolio prices, writes or assumptions of investment growth.
"""
from .friday_goals import paise, rupees


def goal_playbook(plan, summary, today, month_date):
    income = paise(plan.monthly_income_inr)
    living = paise(plan.monthly_essentials_inr)
    debt = paise(plan.monthly_existing_debt_inr)
    monthly = paise(summary['recommended_monthly_inr'])
    current = paise(summary['current_inr'])
    target = paise(summary['target_inr'])
    reserve_gap = paise(summary['protected_reserve_gap_inr'])
    months = summary['remaining_months']
    capacity = max(0, income - living - debt)
    stress_capacity = max(0, income * 9 // 10 - (living * 11 + 9) // 10 - debt)
    ceil_div = lambda n, d: (n + d - 1) // d if d else None

    def pot(contribution, count):
        return current + max(0, contribution * count - reserve_gap)

    def scenario(code, label, amount, goal, assumption):
        return dict(code=code, label=label, end_inr=rupees(amount),
                    target_inr=rupees(goal), gap_inr=rupees(max(0, goal - amount)),
                    reaches_target=amount >= goal, assumption=assumption)

    # Illustrative simple cost increase, rounded UP; not an inflation estimate.
    higher_target = target + (target * 5 * months + 1199) // 1200
    cases = [
        scenario('PLAN', 'Your cash plan', pot(monthly, months), target,
                 'Same income and costs; every planned monthly contribution made.'),
        scenario('PRESSURE', 'Income down · costs up', pot(min(monthly, stress_capacity), months), target,
                 'Income 10% lower and living costs 10% higher for every remaining month; debt unchanged.'),
        scenario('PAUSE', 'One saving month missed', pot(monthly, max(0, months - 1)), target,
                 'One remaining monthly contribution omitted; no catch-up or investment returns.'),
        scenario('COST', 'The target costs more', pot(monthly, months), higher_target,
                 'Illustration only: target increases 5% per year, prorated simply over remaining months; not a prediction.'),
    ]
    needed = max(0, target - current) + reserve_gap
    at_budget = ceil_div(needed, capacity) if needed else 0
    alternatives = []
    if max(0, target - current) and months and capacity < (ceil_div(needed, months) or 0):
        affordable = pot(capacity, months)
        if affordable > current:
            alternatives.append(dict(code='SMALLER_TARGET', label='Keep your date',
                target_inr=rupees(affordable), monthly_inr=rupees(capacity),
                months=months, date=summary['deadline']))
    if at_budget is not None and at_budget <= 60 and (not months or at_budget > months):
        alternatives.append(dict(code='MORE_TIME', label='Give it more time', target_inr=rupees(target),
            monthly_inr=rupees(capacity), months=at_budget, date=month_date(today, at_budget).isoformat()))
    elif at_budget is None or at_budget > 60:
        alternatives.append(dict(code='NO_TIMELINE', label='Budget needs a reset',
            target_inr=rupees(target), monthly_inr=rupees(capacity), months=None, date=None))
    if months and needed and summary['required_monthly_inr']:
        extra = max(0, paise(summary['required_monthly_inr']) - capacity)
        if extra:
            alternatives.append(dict(code='EXTRA_CAPACITY', label='Keep the target and date',
                extra_monthly_inr=rupees(extra), monthly_inr=summary['required_monthly_inr'],
                target_inr=rupees(target), months=months, date=summary['deadline']))

    slices = [dict(code=code, label=label, amount_inr=rupees(value)) for code, label, value in (
        ('LIVING', 'Living costs', living), ('DEBT', 'Debt payments', debt),
        ('GOAL', 'Goal + reserve', monthly), ('ROOM', 'Unallocated', max(0, income - living - debt - monthly)))]
    # Milestones describe achievable dates without calling a future amount actual.
    checkpoints = [{**m, 'target_inr': rupees((target * m['percent'] + 99) // 100),
                    'after_deadline': bool(m['estimated_date'] and m['estimated_date'] > summary['deadline'])}
                   for m in summary['milestones']]
    return dict(version=1, basis='USER_REPORTED_CASH_ONLY', as_of=today.isoformat(),
        allocation=dict(income_inr=rupees(income), slices=slices,
                        overspend_inr=rupees(max(0, living + debt - income)),
                        goal_income_percent=monthly * 100 // income if income else None),
        checkpoints=checkpoints, scenarios=cases, alternatives=alternatives,
        review_factors=['INCOME', 'LIVING_COSTS', 'DEBT_PAYMENTS', 'LIQUID_SAVINGS', 'PROTECTED_RESERVE', 'TIME'],
        not_established=['Future income or employment', 'Irregular costs and complete account coverage',
                         'Actual future prices, fees and taxes', 'Outstanding debt balances and interest rates',
                         'Investment suitability, holdings and future returns'],
        money_moved=False, investment_returns_assumed=False)

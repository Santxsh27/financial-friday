"""Developer cash-timing challenge set, NOT an independent consumer benchmark.

Compare a deliberately simple end-of-month balance heuristic to the exact
within-day, baseline-plus-stress constraints. Zero model calls; artificial data.
"""
import json
import random
import time

from carapace_core.friday_portfolio import classify, summarize_statements
from carapace_core.friday_rehearsal import RehearsalPreview, build_rehearsal


def evaluate():
    rng=random.Random(270017)
    results=[];started=time.perf_counter()
    for i in range(48):
        income=rng.randrange(25,61)*100000
        entries=[]
        specs=[(rng.choice([20,25,28]),'salary',0,income),
               (5,'rent',rng.randrange(8,16)*100000,0),
               (10,'groceries',rng.randrange(2,6)*100000,0),
               (15,'EMI',rng.randrange(3,8)*100000,0),
               (12,'shopping',rng.randrange(2,8)*100000,0),
               (18,'restaurant',rng.randrange(1,4)*100000,0)]
        for j,(day,label,debit,credit) in enumerate(specs,1):
            kind,category=classify(label,bool(debit))
            entries.append({'date':f'2026-09-{day:02d}','description':'ARTIFICIAL '+label,
                'debit_minor':debit,'credit_minor':credit,'kind':kind,'category':category,'source_row':j})
        opening=rng.randrange(15,51)*100000;purchase=rng.randrange(1,16)*100000
        view={'revision':1,'workspace_generation':'0','summary':summarize_statements([
            {'account_alias':'Artificial','account_type':'BANK','entries':entries}])}
        d=RehearsalPreview(account_alias='Artificial',available_cash_inr=str(opening//100),
            protected_buffer_inr='5000',purchase_amount_inr=str(purchase//100),purchase_in_days=7,
            as_of_date='2026-10-01',horizon_days=30,income_delay_days=7,income_drop_percent=20,
            essentials_rise_percent=10,max_cut_percent=50,expected_revision=1,
            workspace_generation='0',confirm_history_is_representative=True)
        p=build_rehearsal(view,d)
        naive=opening+income-sum(r['debit_minor'] for r in entries)-purchase>=500000
        results.append({'case':i+1,'end_of_month_heuristic_fits':naive,
            'all_daily_replays_fit':p['purchase_fits'],
            'heuristic_missed_buffer_gap':naive and not p['purchase_fits'],
            'checked_cut_option_found':p['minimum_flexible_cut_bps'] is not None,
            'checked_later_date_found':p['earliest_no_cut_date'] is not None,
            'worst_gap_minor':p['original']['shortfall_minor']})
    return {'scope':'DEVELOPER_SYNTHETIC_CASH_TIMING_COMPARISON','seed':270017,'cases':len(results),
        'monthly_heuristic_approvals':sum(r['end_of_month_heuristic_fits'] for r in results),
        'daily_replay_approvals':sum(r['all_daily_replays_fit'] for r in results),
        'monthly_heuristic_missed_buffer_gaps':sum(r['heuristic_missed_buffer_gap'] for r in results),
        'cut_options_found':sum(r['checked_cut_option_found'] for r in results),
        'later_date_options_found':sum(r['checked_later_date_found'] for r in results),
        'seconds':round(time.perf_counter()-started,4),'model_calls':0,
        'limits':'Not real customer outcomes, calibrated forecasting, a comparison with plain Gemini or a competitor evaluation. The heuristic deliberately ignores intramonth timing and stress.',
        'results':results}


if __name__=='__main__':
    print(json.dumps(evaluate(),indent=2))

"""Automatic, source-linked statement checks. Patterns are not fraud verdicts.

Amounts remain integer paise. Exact-description grouping deliberately prefers
missed matches to merging different counterparties. No embeddings or private
statement training, bank queries, deduplication, or financial actions occur.
"""
from collections import defaultdict
from datetime import date
from hashlib import sha256
import json
from statistics import median_low
import re

from pydantic import BaseModel, ConfigDict, Field

ENGINE_VERSION = 'CHECKUP_1'


class FindingRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    finding_id: str = Field(pattern=r'^finding_[a-f0-9]{24}$')
    expected_revision: int = Field(ge=0, strict=True)
    workspace_generation: str = Field(min_length=1, max_length=80)


class ReviewFinding(FindingRequest):
    reviewed: bool = Field(strict=True)


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _month_after(month):
    y, m = map(int, month.split('-'))
    return f'{y + (m == 12):04d}-{m % 12 + 1:02d}'


def build_checkup(statements, summary, reviewed=()):
    """Bounded <=2,000-row pipeline, deterministic under import/row reorder.

    Repeated-entry checks use all occurrences. Recurring series suppress
    ambiguous overlapping dates; outlier baselines retain earlier entries, so
    overlapping imports can distort them and must be reviewed.
    An independent assertion reconciles chart attribution to supplied totals.
    """
    rows = []
    for statement in statements:
        for row in statement['entries']:
            rows.append({**row, 'account_alias': statement['account_alias'],
                         'account_type': statement['account_type'],
                         'source_sha256': statement['source_sha256']})
    rows.sort(key=lambda r: (r['date'], r['account_alias'], r['source_sha256'], r['source_row']))
    findings = []; recurring = []; reviewed = set(reviewed)

    def refs(items):
        return [{k: r[k] for k in ('source_sha256', 'source_row', 'date', 'account_alias',
                                   'description', 'debit_minor', 'credit_minor')} for r in items]

    def add(kind, title, detail, items, amount, priority, **values):
        evidence = refs(items)
        identity = 'finding_' + _digest([ENGINE_VERSION, kind, evidence, values])[:24]
        findings.append({'finding_id': identity, 'kind': kind, 'title': title,
                         'detail': detail, 'amount_minor': amount, 'priority': priority,
                         'reviewed': identity in reviewed, 'evidence': evidence,
                         'evidence_count': len(evidence), **values})

    exact = defaultdict(list); groups = defaultdict(list)
    for r in rows:
        description = re.sub(r'\s+', ' ', r['description'].casefold()).strip()
        exact[(r['account_alias'], r['date'], description, r['debit_minor'], r['credit_minor'])].append(r)
        if r['debit_minor'] and r['kind'] in {'EXPENSE', 'LOAN_REPAYMENT'}:
            groups[(r['account_alias'], description, r['kind'], r['category'])].append(r)
    for items in exact.values():
        if len(items) > 1:
            extra = (len(items)-1)*(items[0]['debit_minor'] or items[0]['credit_minor'])
            add('REPEATED_ENTRY', 'Matching entries need a look',
                'Same account nickname, date, description and amount. They may be legitimate or overlapping exports; all remain counted.',
                items, extra, 0)

    for items in groups.values():
        by_month = defaultdict(list)
        for r in items: by_month[r['date'][:7]].append(r)
        # One occurrence in each consecutive month, >=3 months, 20–40 day gaps.
        # Multiple occurrences/overlapping imports make the series ambiguous.
        if len(by_month) < 3 or any(len(v) != 1 for v in by_month.values()): continue
        ordered = sorted(items, key=lambda r:r['date'])
        if any(_month_after(a['date'][:7]) != b['date'][:7] or not
               20 <= (date.fromisoformat(b['date'])-date.fromisoformat(a['date'])).days <= 40
               for a,b in zip(ordered, ordered[1:])): continue
        baseline = median_low(sorted(r['debit_minor'] for r in ordered[:-1]))
        latest = ordered[-1]['debit_minor']
        recurring.append({'label': ordered[-1]['description'], 'category': ordered[-1]['category'],
                          'account_alias': ordered[-1]['account_alias'], 'occurrences': len(ordered),
                          'last_date': ordered[-1]['date'], 'latest_minor': latest,
                          'baseline_minor': baseline, 'evidence': refs(ordered)})
        if latest-baseline >= 10000 and latest*100 >= baseline*115:
            add('RECURRING_INCREASE', 'A regular payment got bigger',
                'Latest amount is at least 15% and INR 100 above its earlier median. Check the tariff, usage or renewal; this is not proof of an error.',
                ordered, latest-baseline, 1, baseline_minor=baseline, latest_minor=latest)

    # Robust within-account/category baseline, historical dates only. This is a
    # conservative review heuristic, not a calibrated fraud classifier.
    latest_month = max((r['date'][:7] for r in rows), default=None)
    pools = defaultdict(list)
    for r in rows:
        if r['kind'] == 'EXPENSE': pools[(r['account_alias'],r['category'])].append(r)
    for items in pools.values():
        for r in items:
            if r['date'][:7] != latest_month: continue
            prior = [p for p in items if p['date'] < r['date']]
            if len(prior) < 6: continue
            middle = median_low(sorted(p['debit_minor'] for p in prior))
            mad = median_low(sorted(abs(p['debit_minor']-middle) for p in prior))
            threshold = max(3*middle, middle+6*mad, middle+100000)
            if r['debit_minor'] > threshold:
                add('UNUSUAL_AMOUNT', 'One amount stands apart',
                    'Larger than the conservative median/deviation threshold for earlier expenses in this account and category. A planned purchase can explain it.',
                    [r], r['debit_minor'], 2, baseline_minor=middle,
                    threshold_minor=threshold, comparison_count=len(prior))

    fees = [r for r in rows if r['kind']=='EXPENSE' and r['category']=='Fees' and r['date'][:7]==latest_month]
    if fees:
        add('FEES', 'Your recorded bank and service fees',
            'Collected into one enquiry-ready list. Friday cannot determine whether a fee was authorised or refundable.',
            fees, sum(r['debit_minor'] for r in fees), 3)
    unclear = [r for r in rows if r['credit_minor'] and r['kind']=='UNCLEAR']
    if unclear:
        add('UNCLEAR_CREDIT', 'These credits are not counted as income',
            'Unclear credits stay separate from earnings. Check their source; a loan or transfer is not salary.',
            unclear, sum(r['credit_minor'] for r in unclear), 0)

    from .friday_refund_shield import build_refund_shield
    shield=build_refund_shield(rows)
    for trail in shield['trails']:
        status=trail['status']
        if status=='AMBIGUOUS':
            add('REFUND_AMBIGUITY','A refund fits more than one purchase',
                'Friday tested alternative allocations. Several purchase/refund explanations fit the same records; no purchase is declared refunded. Open Money shield to see the bounds.',
                trail['evidence'],trail['refund_total_minor'],1,trail_id=trail['trail_id'])
        elif status=='FIXED_TOTALS_UNDER_ASSUMPTIONS' and trail['compatible_minor']<trail['purchase_total_minor']:
            add('REFUND_PARTIAL_TRAIL','Only part of this purchase trail has a matching return',
                'A partial matching amount appears under the name/date/account assumptions. The remaining purchase amount is not an amount owed; the bank or merchant must confirm the relationship and any expected refund.',
                trail['evidence'],trail['purchase_total_minor']-trail['compatible_minor'],2,trail_id=trail['trail_id'])
        elif trail['certificate'] is None:
            add('REFUND_LINK_WITHHELD','This refund trail needs confirmation',
                'Friday withheld a purchase link because history, merchant detail, non-overlapping rows or graph capacity was insufficient. This is not fraud or a missing-refund verdict. No row was removed.',
                trail['evidence'],trail['refund_total_minor'],2,trail_id=trail['trail_id'])

    # Exact change attribution, not a forecast or inferred financial behaviour.
    months = summary['monthly']; change = None
    if len(months)>=2 and _month_after(months[-2]['month'])==months[-1]['month']:
        previous, current = months[-2]['month'], months[-1]['month']
        amounts = defaultdict(lambda: defaultdict(int))
        for r in rows:
            if r['kind']=='EXPENSE': amounts[r['date'][:7]][r['category']]+=r['debit_minor']
        categories = sorted(set(amounts[previous])|set(amounts[current]))
        attribution = [{'category':c, 'before_minor':amounts[previous][c],
                        'after_minor':amounts[current][c],
                        'delta_minor':amounts[current][c]-amounts[previous][c]} for c in categories]
        delta = months[-1]['spending_minor']-months[-2]['spending_minor']
        assert sum(c['delta_minor'] for c in attribution)==delta
        change = {'previous_month':previous,'current_month':current,'delta_minor':delta,
                  'categories':sorted(attribution,key=lambda r:abs(r['delta_minor']),reverse=True),
                  'comparison':'SUPPLIED_ROWS_ONLY_NOT_COMPLETE_MONTHS'}

    findings.sort(key=lambda f:(f['priority'],-f['amount_minor'],f['finding_id']))
    recurring.sort(key=lambda r:(-r['latest_minor'],r['account_alias'],r['label']))
    return {'scope':'AUTOMATIC_STATEMENT_CHECKUP', 'engine_version':ENGINE_VERSION,
            'source_fingerprint':_digest(rows), 'transaction_count':len(rows),
            'findings':findings, 'open_count':sum(not f['reviewed'] for f in findings),
            'recurring':recurring, 'spending_change':change,
            'money_shield':shield,
            'checks_completed':['Repeated entries','Regular payments','Changed regular amounts',
                                'Unusual expense amounts','Recorded fees','Unclear credits','Spending attribution','Refund evidence graph'],
            'model_calls':0, 'money_moved':False, 'rows_removed':0,
            'limits':['Review candidates, not fraud verdicts or bank-verified evidence.',
                      'Patterns need sufficient history; missing accounts, partial months and changed descriptions limit coverage.',
                      'No charges cancelled, disputes sent, money recovered or private model trained.']}


def checkup_model_context(checkup):
    """Derived metrics only under the EXISTING aggregate-sharing permission.

    No merchant text, account aliases, dates of individual rows, hashes, or row
    references cross the model boundary. These remain on the private app side.
    """
    from decimal import Decimal
    def amount(n): return f'INR {Decimal(n)/100:,.2f}'
    return {'evidence_id':'checkup:current','scope':checkup['scope'],
            'open_count':checkup['open_count'],
            'findings':[{'finding_id':f['finding_id'],'kind':f['kind'],'title':f['title'],
                         'amount_inr':amount(f['amount_minor']), 'reviewed':f['reviewed'],
                         'evidence_count':f['evidence_count']} for f in checkup['findings'][:20]],
            'regular_payment_count':len(checkup['recurring']),
            'money_shield':{'refunds_inr':amount(checkup['money_shield']['refund_total_minor']),
                'compatible_under_assumptions_inr':amount(checkup['money_shield']['compatible_minor']),
                'unallocated_inr':amount(checkup['money_shield']['not_allocated_minor']),
                'ambiguous_trails':checkup['money_shield']['ambiguous_count'],
                'held_trails':checkup['money_shield']['held_count'],
                'limits':checkup['money_shield']['limits']},
            'spending_change':({'delta_inr':amount(checkup['spending_change']['delta_minor'])}
                               if checkup['spending_change'] else {}),
            'limits':checkup['limits']}


def prepare_enquiry(finding):
    """A private downloadable artifact, never an external complaint submission.

    Statement text is quoted as data rather than treated as instructions. No
    invented bank, payment reference, entitlement to refund or fraud accusation.
    """
    def money(n): return f'INR {n//100:,}.{n%100:02d}'
    rows=finding['evidence']
    lines=['UNSENT ENQUIRY — please review and redact before sharing', '',
           'Hello, please help me understand the following entries in my statement.',
           'Friday flagged a review candidate, not confirmed fraud or an incorrect charge.',
           '', finding['title'], finding['detail'], '']
    for r in rows[:30]:
        # Keep untrusted description on one quoted line, including control chars.
        description=' '.join(r['description'].split())
        lines.append(f"{r['date']} | {money(r['debit_minor'] or r['credit_minor'])} {'debit' if r['debit_minor'] else 'credit'} | {json.dumps(description,ensure_ascii=False)} | source row {r['source_row']}")
    if len(rows)>30:lines.append(f'{len(rows)-30} further source entries are in the private app evidence view.')
    lines.extend(['','Please confirm the purpose and authorisation of these entries and any applicable review process.',
                  'I have not assumed that a refund is due. Thank you.', '',
                  'Prepared from user-supplied statement rows; not bank-authenticated evidence.'])
    return '\n'.join(lines)

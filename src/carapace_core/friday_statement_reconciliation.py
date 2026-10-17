"""Exact arithmetic over source claims, never bank authentication or completeness.

Evidence is intentionally separate from computed checks. Callers must establish the
provenance of source_facts before presenting any check as source verified.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


def source_money_minor(text: str, *, signed: bool = False) -> int:
    """Parse literal INR rupees with exact integer-paise arithmetic."""
    value = text.strip()
    value = re.sub(r'^(?:INR\s*|₹\s*|Rs\.?\s*)', '', value, flags=re.I)
    if value.endswith('/-'):
        value = value[:-2].strip()
    negative = value.startswith('-')
    if negative:
        if not signed:
            raise ValueError('Transaction totals must be non-negative')
        value = value[1:]
    if ',' in value:
        if not re.fullmatch(r'(?:\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d{1,2})?', value):
            raise ValueError('Invalid amount grouping')
        value = value.replace(',', '')
    if not re.fullmatch(r'\d{1,12}(?:\.\d{1,2})?', value):
        raise ValueError('Use literal INR values with at most two decimals')
    result = int(Decimal(value) * 100)
    return -result if negative else result


class SourceReference(BaseModel):
    model_config = ConfigDict(extra='forbid')
    unit_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=2000)
    page_number: int | None = Field(default=None, ge=1, le=6, strict=True)


def _literal_in_source(literal, refs):
    # A number must be a whole source token, not a substring of another amount.
    source = ' '.join(ref.text for ref in refs)
    numeric = bool(re.fullmatch(r'(?:INR\s*|₹\s*|Rs\.?\s*)?-?\d[\d,.]*(?:/-)?', literal, re.I))
    found = re.search(r'(?<![\d.,+-])' + re.escape(literal) + r'(?![\d.,])', source) if numeric else literal in source
    if not literal or not found:
        raise ValueError('Declared facts require their exact literal source value')


class MinorSourceFact(BaseModel):
    model_config = ConfigDict(extra='forbid')
    value_minor: int = Field(ge=-100_000_000_000_000, le=100_000_000_000_000, strict=True)
    literal_text: str = Field(min_length=1, max_length=40)
    source_refs: list[SourceReference] = Field(min_length=1, max_length=8)

    @model_validator(mode='after')
    def check(self):
        _literal_in_source(self.literal_text, self.source_refs)
        if source_money_minor(self.literal_text, signed=True) != self.value_minor:
            raise ValueError('Declared money does not match its literal source')
        return self


class CountSourceFact(BaseModel):
    model_config = ConfigDict(extra='forbid')
    value: int = Field(ge=0, le=10000, strict=True)
    literal_text: str = Field(min_length=1, max_length=8)
    source_refs: list[SourceReference] = Field(min_length=1, max_length=8)

    @model_validator(mode='after')
    def check(self):
        _literal_in_source(self.literal_text, self.source_refs)
        if not re.fullmatch(r'\d{1,5}', self.literal_text) or int(self.literal_text) != self.value:
            raise ValueError('Declared count does not match its literal source')
        return self


CONVENTION_LITERALS = {
    'BANK_CREDIT_INCREASES': ('credits increase balance; debits decrease balance',
                             'withdrawal amt.,deposit amt.,closing balance',
                             'withdrawal,deposit,closing balance'),
    'CARD_DEBIT_INCREASES_AMOUNT_DUE': ('debits increase amount due; credits decrease amount due',),
    'CARD_CREDIT_INCREASES_AMOUNT_DUE': ('credits increase amount due; debits decrease amount due',),
}


class ConventionSourceFact(BaseModel):
    model_config = ConfigDict(extra='forbid')
    value: Literal['BANK_CREDIT_INCREASES', 'CARD_DEBIT_INCREASES_AMOUNT_DUE', 'CARD_CREDIT_INCREASES_AMOUNT_DUE']
    literal_text: str = Field(min_length=1, max_length=160)
    source_refs: list[SourceReference] = Field(min_length=1, max_length=8)

    @model_validator(mode='after')
    def check(self):
        _literal_in_source(self.literal_text, self.source_refs)
        if self.literal_text.strip().casefold() not in CONVENTION_LITERALS[self.value]:
            raise ValueError('Balance direction requires an explicit supported source convention')
        return self


class OrderingSourceFact(BaseModel):
    model_config = ConfigDict(extra='forbid')
    value: Literal['ASCENDING', 'DESCENDING']
    literal_text: str = Field(min_length=1, max_length=80)
    source_refs: list[SourceReference] = Field(min_length=1, max_length=8)

    @model_validator(mode='after')
    def check(self):
        _literal_in_source(self.literal_text, self.source_refs)
        allowed = {'ASCENDING': ('oldest first', 'ascending date order'),
                   'DESCENDING': ('newest first', 'descending date order')}
        if self.literal_text.strip().casefold() not in allowed[self.value]:
            raise ValueError('Ordering requires an explicit source declaration')
        return self


class StatementSourceFacts(BaseModel):
    """Optional evidence only. No client-computed reconciliation status is accepted."""
    model_config = ConfigDict(extra='forbid')
    adapter: Literal['CANONICAL_V1', 'BANK_STYLE_V1', 'BANK_EXPORT_V2', 'PDF_TEXT', 'OCR_TEXT'] = 'CANONICAL_V1'
    opening_balance: MinorSourceFact | None = None
    closing_balance: MinorSourceFact | None = None
    debit_total: MinorSourceFact | None = None
    credit_total: MinorSourceFact | None = None
    transaction_count: CountSourceFact | None = None
    convention: ConventionSourceFact | None = None
    ordering: OrderingSourceFact | None = None
    page_count: int | None = Field(default=None, ge=1, le=6, strict=True)
    observed_page_numbers: list[StrictInt] = Field(default_factory=list, max_length=6)
    declared_page_count: CountSourceFact | None = None
    declared_page_numbers: list[CountSourceFact] = Field(default_factory=list, max_length=6)
    candidate_transaction_unit_ids: list[str] = Field(default_factory=list, max_length=1500)

    @model_validator(mode='after')
    def check(self):
        for field in ('debit_total', 'credit_total'):
            fact = getattr(self, field)
            if fact and fact.value_minor < 0:
                raise ValueError('Declared debit/credit totals cannot be negative')
        if any(type(page) is not int or not 1 <= page <= 6 for page in self.observed_page_numbers):
            raise ValueError('Invalid observed page number')
        if len(set(self.observed_page_numbers)) != len(self.observed_page_numbers):
            raise ValueError('Observed pages must be unique')
        if any(not isinstance(unit, str) or not 1 <= len(unit) <= 80 for unit in self.candidate_transaction_unit_ids):
            raise ValueError('Invalid candidate transaction source unit')
        if len(set(self.candidate_transaction_unit_ids)) != len(self.candidate_transaction_unit_ids):
            raise ValueError('Candidate transaction units must be unique')
        return self


def _check(status='UNKNOWN', reason='No independent printed source fact was supplied', **values):
    return {'status': status, 'reason': reason, **values}


def reconcile_statement(statement) -> dict:
    """Recompute every check. CONSISTENT means arithmetic agreement, never authenticity.

    Legacy statements have UNKNOWN checks. Repeated rows are counted and warned;
    neither duplicates nor mismatches are silently corrected or discarded.
    """
    data = statement.model_dump(mode='json') if hasattr(statement, 'model_dump') else statement
    entries = data['entries']
    facts = StatementSourceFacts.model_validate(data.get('source_facts') or {})
    debit = sum(row['debit_minor'] for row in entries)
    credit = sum(row['credit_minor'] for row in entries)
    observed = {'debit_total_minor': debit, 'credit_total_minor': credit, 'transaction_count': len(entries)}
    checks = {key: _check() for key in ('debit_total', 'credit_total', 'transaction_count',
              'page_coverage', 'balance_equation', 'running_balances', 'row_coverage')}
    warnings = []
    for field, actual in (('debit_total', debit), ('credit_total', credit), ('transaction_count', len(entries))):
        fact = getattr(facts, field)
        if fact is not None:
            expected = fact.value if field == 'transaction_count' else fact.value_minor
            checks[field] = _check('CONSISTENT' if expected == actual else 'MISMATCH',
                'Imported rows agree with the declared source fact' if expected == actual else 'Imported rows differ from the declared source fact',
                declared=expected, observed=actual)
    if facts.page_count is not None:
        printed = {fact.value for fact in facts.declared_page_numbers}
        physical = set(range(1, facts.page_count + 1))
        readable = set(facts.observed_page_numbers)
        if readable != physical:
            checks['page_coverage'] = _check('MISMATCH', 'At least one physical PDF page has no readable source units')
        elif facts.declared_page_count and (facts.declared_page_count.value != facts.page_count or (printed and printed != physical)):
            checks['page_coverage'] = _check('MISMATCH', 'Printed page markers differ from the supplied PDF pages')
        elif facts.declared_page_count and printed == physical:
            checks['page_coverage'] = _check('CONSISTENT', 'Every supplied PDF page agrees with its printed page markers')
        else:
            checks['page_coverage'] = _check(reason='Physical pages were read; a full set of printed page markers was not established')
    used = [unit for row in entries for unit in row.get('source_unit_ids', [])]
    if facts.candidate_transaction_unit_ids:
        missing = sorted(set(facts.candidate_transaction_unit_ids) - set(used))
        reused = sorted(unit for unit, count in Counter(used).items() if count > 1)
        checks['row_coverage'] = _check('MISMATCH' if missing or reused else 'CONSISTENT',
            'Dated transaction source units were omitted or reused' if missing or reused else 'Every detected dated transaction source unit is represented once',
            missing_source_unit_ids=missing, reused_source_unit_ids=reused)
    duplicates = Counter((str(row['date']), row['description'].casefold(), row['debit_minor'], row['credit_minor']) for row in entries)
    repeated = sum(count - 1 for count in duplicates.values() if count > 1)
    if repeated:
        warnings.append(f'{repeated} repeated row candidate(s); every row remains counted. Compare overlapping imports manually.')
    dates = [date.fromisoformat(str(row['date'])) for row in entries]
    ascending = all(a < b for a, b in zip(dates, dates[1:]))
    descending = all(a > b for a, b in zip(dates, dates[1:]))
    order = facts.ordering.value if facts.ordering else ('ASCENDING' if len(dates) == 1 or ascending else 'DESCENDING' if descending else None)
    order_conflict = order and ((order == 'ASCENDING' and not all(a <= b for a, b in zip(dates, dates[1:]))) or
                               (order == 'DESCENDING' and not all(a >= b for a, b in zip(dates, dates[1:]))))
    convention = facts.convention.value if facts.convention else None
    allowed = ('BANK_CREDIT_INCREASES',) if data['account_type'] == 'BANK' else ('CARD_DEBIT_INCREASES_AMOUNT_DUE', 'CARD_CREDIT_INCREASES_AMOUNT_DUE')
    sign = 1 if convention in ('BANK_CREDIT_INCREASES', 'CARD_CREDIT_INCREASES_AMOUNT_DUE') else -1
    if convention not in allowed:
        checks['balance_equation'] = _check(reason='Balance sign convention is not explicitly established for this account type')
        checks['running_balances'] = _check(reason='Balance sign convention is not explicitly established for this account type')
    else:
        if order_conflict:
            checks['balance_equation'] = _check('MISMATCH', 'Printed ordering conflicts with transaction dates')
        elif not order:
            checks['balance_equation'] = _check(reason='Transaction ordering has not been established')
        elif facts.opening_balance and facts.closing_balance:
            expected = facts.opening_balance.value_minor + sign * (credit - debit)
            actual = facts.closing_balance.value_minor
            checks['balance_equation'] = _check('CONSISTENT' if expected == actual else 'MISMATCH',
                'Opening balance and imported movements agree with closing balance' if expected == actual else 'Opening balance and imported movements do not reach closing balance',
                expected_closing_minor=expected, declared_closing_minor=actual)
        if any(row.get('running_balance_minor') is not None for row in entries):
            if order_conflict:
                checks['running_balances'] = _check('MISMATCH', 'Printed ordering conflicts with transaction dates')
            elif not order:
                checks['running_balances'] = _check(reason='Transaction order is not established, including within equal dates')
            elif any(row.get('running_balance_minor') is None for row in entries) or not facts.opening_balance:
                checks['running_balances'] = _check(reason='A running balance for every row and a declared opening balance are required')
            else:
                ordered = entries if order == 'ASCENDING' else list(reversed(entries))
                balance = facts.opening_balance.value_minor
                mismatches = []
                for row in ordered:
                    balance += sign * (row['credit_minor'] - row['debit_minor'])
                    if balance != row['running_balance_minor']:
                        mismatches.append(row['source_row'])
                checks['running_balances'] = _check('MISMATCH' if mismatches else 'CONSISTENT',
                    'Running balances differ from imported transaction arithmetic' if mismatches else 'Every running balance agrees in established transaction order',
                    mismatch_source_rows=mismatches)
    applicable = [value['status'] for key, value in checks.items() if not (key == 'page_coverage' and data.get('extraction') == 'CSV_EXACT')]
    overall = 'MISMATCH' if 'MISMATCH' in applicable else 'CONSISTENT' if all(status == 'CONSISTENT' for status in applicable) else 'UNKNOWN'
    return {'overall_status': overall, 'checks': checks, 'observed': observed,
            'repeated_row_candidates': repeated, 'warnings': warnings,
            'limits': ['Arithmetic and source-text agreement only; not authenticated bank evidence.',
                       'UNKNOWN does not mean zero or complete. CONSISTENT does not prove all accounts, all rows, or original bank authenticity.']}

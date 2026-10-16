"""Controlled CSV column adapters; fixtures and profiles are synthetic, not bank certifications.

CANONICAL_V1 preserves date,description,debit,credit and optional currency. Optional
running_balance is a signed INR closing balance for that row. BANK_STYLE_V1 maps
Transaction Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance exactly.
It asserts withdrawal/deposit direction, never a real bank format compatibility.

Optional blank-date footer labels are Opening balance, Closing balance, Total
debits, Total credits, Transaction count. Values occupy the running balance,
running balance, debit, credit and running balance cells respectively. A balance
column must be present for balance/count footers. All other nontransaction rows
are rejected. Footers are source claims; they are never used as transactions.
"""
from __future__ import annotations

import csv
import io

from .friday_statement import analyze_statement
from .friday_statement_reconciliation import (
    ConventionSourceFact, CountSourceFact, MinorSourceFact, SourceReference,
    StatementSourceFacts, source_money_minor,
)


BANK_STYLE_COLUMNS = {'transaction date': 'date', 'narration': 'description',
                      'withdrawal amt.': 'debit', 'deposit amt.': 'credit',
                      'closing balance': 'running_balance', 'currency': 'currency'}


def parse_statement_csv(text: str, *, account_type: str) -> dict:
    if not text or len(text.encode('utf-8')) > 1024 * 1024:
        raise ValueError('Use a non-empty CSV of at most 1 MB')
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')), strict=True)
    headers = [name.strip().casefold() for name in (reader.fieldnames or [])]
    if len(set(headers)) != len(headers):
        raise ValueError('Duplicate column names are not supported')
    canonical = {'date', 'description', 'debit', 'credit'}.issubset(headers)
    if canonical:
        mapping = {name: name for name in headers}
        if 'balance' in headers and 'running_balance' in headers:
            raise ValueError('Choose one optional running balance column')
        if 'balance' in headers:
            mapping['balance'] = 'running_balance'
        adapter = 'CANONICAL_V1'
    elif set(BANK_STYLE_COLUMNS) - {'currency'} <= set(headers) and set(headers) <= set(BANK_STYLE_COLUMNS):
        if account_type != 'BANK':
            raise ValueError('The withdrawal/deposit CSV adapter is for deposit accounts only')
        mapping = BANK_STYLE_COLUMNS
        adapter = 'BANK_STYLE_V1'
    else:
        raise ValueError('Required columns: date, description, debit, credit. Only the documented BANK_STYLE_V1 alternative is supported')
    facts = StatementSourceFacts(adapter=adapter)
    # The explicit withdrawal/deposit header establishes direction for this adapter.
    if adapter == 'BANK_STYLE_V1':
        raw_header = ','.join(name.strip() for name in reader.fieldnames)
        direction = 'withdrawal amt.,deposit amt.,closing balance'
        # Exact contiguous source header labels are required to establish direction.
        start = raw_header.casefold().find(direction)
        if start >= 0:
            literal = raw_header[start:start + len(direction)]
            facts.convention = ConventionSourceFact(value='BANK_CREDIT_INCREASES', literal_text=literal,
                source_refs=[SourceReference(unit_id='csv-header', text=raw_header)])
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['date', 'description', 'debit', 'credit', 'currency'])
    writer.writeheader()
    source_rows = []
    balances = []
    previous_line = reader.line_num
    footer_labels = {'opening balance': ('opening_balance', 'running_balance'),
                     'closing balance': ('closing_balance', 'running_balance'),
                     'total debits': ('debit_total', 'debit'),
                     'total credits': ('credit_total', 'credit'),
                     'transaction count': ('transaction_count', 'running_balance')}
    try:
        for original in reader:
            source_row = previous_line + 1
            previous_line = reader.line_num
            if None in original or any(value is None for value in original.values()):
                raise ValueError(f'Row {source_row}: inconsistent number of columns; no partial import accepted')
            row = {mapping[key.strip().casefold()]: value.strip() for key, value in original.items()}
            if row.get('currency', 'INR').upper() not in ('', 'INR'):
                raise ValueError(f'Row {source_row}: only INR statements are supported')
            if not row['date']:
                label = row['description'].casefold()
                if label not in footer_labels:
                    raise ValueError(f'Row {source_row}: unknown footer or missing date; no partial import accepted')
                field, column = footer_labels[label]
                if getattr(facts, field) is not None:
                    raise ValueError(f'Row {source_row}: repeated declared footer fact')
                literal = row.get(column, '')
                if not literal or any(row.get(other) for other in ('debit', 'credit', 'running_balance') if other != column):
                    raise ValueError(f'Row {source_row}: footer has missing or conflicting values')
                # Keep derived label/value evidence, not unrelated CSV columns.
                refs = [SourceReference(unit_id=f'csv-row-{source_row}', text=f'{row["description"]}: {literal}')]
                if field == 'transaction_count':
                    fact = CountSourceFact(value=int(literal), literal_text=literal, source_refs=refs)
                else:
                    fact = MinorSourceFact(value_minor=source_money_minor(literal, signed=field in ('opening_balance', 'closing_balance')),
                                           literal_text=literal, source_refs=refs)
                setattr(facts, field, fact)
                continue
            writer.writerow({key: row.get(key, '') or ('INR' if key == 'currency' else '') for key in writer.fieldnames})
            source_rows.append(source_row)
            balances.append(source_money_minor(row['running_balance'], signed=True) if row.get('running_balance') else None)
    except (csv.Error, TypeError) as error:
        raise ValueError('Malformed CSV; no partial import accepted') from error
    parsed = analyze_statement(output.getvalue(), include_entries=True)
    for entry, source_row, balance in zip(parsed['entries'], source_rows, balances):
        entry.update(row=source_row, running_balance_minor=balance, source_unit_ids=[f'csv-row-{source_row}'])
    facts.candidate_transaction_unit_ids = [f'csv-row-{row}' for row in source_rows]
    return {'entries': parsed['entries'], 'transaction_count': parsed['transaction_count'], 'source_facts': facts}

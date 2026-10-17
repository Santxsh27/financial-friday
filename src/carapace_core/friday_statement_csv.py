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
import re
from datetime import datetime

from .friday_statement import analyze_statement
from .friday_statement_reconciliation import (
    ConventionSourceFact, CountSourceFact, MinorSourceFact, SourceReference,
    StatementSourceFacts, source_money_minor,
)


BANK_STYLE_COLUMNS = {'transaction date': 'date', 'narration': 'description',
                      'withdrawal amt.': 'debit', 'deposit amt.': 'credit',
                      'closing balance': 'running_balance', 'currency': 'currency'}

# Explicit semantic aliases, not a language-model guess about money direction.
# BANK_EXPORT_V2 is tested against synthetic export-shaped cases, not certified
# by any bank. Ambiguous headers/unknown table columns reject the whole import.
EXPORT_COLUMNS = {
    'date': 'date', 'transaction date': 'date', 'txn date': 'date', 'tran date': 'date',
    'description': 'description', 'narration': 'description', 'narrarion': 'description',
    'transaction remarks': 'description', 'remarks': 'description', 'particulars': 'description',
    'debit': 'debit', 'debit amount': 'debit', 'withdrawal': 'debit',
    'withdrawal amt': 'debit', 'withdrawal amount': 'debit', 'withdrawal (dr)': 'debit',
    'withdrawal amount (inr)': 'debit', 'withdrawal amount(inr)': 'debit',
    'debit amount (inr)': 'debit', 'withdrawal amt (inr)': 'debit',
    'credit': 'credit', 'credit amount': 'credit', 'deposit': 'credit',
    'deposit amt': 'credit', 'deposit amount': 'credit', 'deposit (cr)': 'credit',
    'deposit amount (inr)': 'credit', 'deposit amount(inr)': 'credit',
    'credit amount (inr)': 'credit', 'deposit amt (inr)': 'credit',
    'balance': 'running_balance', 'running balance': 'running_balance',
    'closing balance': 'running_balance', 'balance (inr)': 'running_balance',
    'balance(inr)': 'running_balance', 'currency': 'currency',
}
EXPORT_METADATA_COLUMNS = {'s no', 'sr no', 'srno', 'serial no', 'serial number', 'sno',
    'value date', 'value dt', 'cheque number', 'cheque no', 'chq no', 'chq/ref no', 'ref no/cheque no',
    'cheque/ref no', 'transaction id', 'txn id', 'reference no', 'reference number'}


def _header(value):
    return re.sub(r'\s+', ' ', value.strip().casefold().replace('.', '')).strip()


def _export_mapping(headers):
    normalized = [_header(h) for h in headers]
    if len(set(normalized)) != len(normalized):
        raise ValueError('Duplicate or ambiguous statement columns')
    mapping = {}
    for original, name in zip(headers, normalized):
        if name in EXPORT_COLUMNS:
            mapping[original.strip().casefold()] = EXPORT_COLUMNS[name]
        elif name in EXPORT_METADATA_COLUMNS:
            mapping[original.strip().casefold()] = None
        else:
            return None
    targets = [v for v in mapping.values() if v]
    if len(set(targets)) != len(targets):
        raise ValueError('More than one column describes the same financial field')
    return mapping if {'date','description','debit','credit'} <= set(targets) else None


def _table_start(text, delimiter=','):
    """Locate one explicit table after a bounded, recognized report preamble.

    Never skip an unexplained row: dated/financial data before the header or
    unknown preamble text must be reviewed instead of partially imported.
    """
    stream = io.StringIO(text.lstrip('\ufeff'))
    reader = csv.reader(stream, delimiter=delimiter, strict=True)
    before = []
    offset = 0
    for cells in reader:
        normalized = {_header(c) for c in cells}
        # A header is a label row with all four financial roles, not a date row.
        if ({'date','description','debit','credit'} <= normalized or
                {'date','description','debit','credit'} <= {EXPORT_COLUMNS.get(c) for c in normalized}):
            if before:
                for row in before:
                    nonempty = [c.strip() for c in row if c.strip()]
                    if not nonempty:
                        continue
                    first = nonempty[0].casefold()
                    if not re.fullmatch(r'(?:icici bank|hdfc bank|sbi|state bank of india|axis bank|kotak bank|detailed statement|account statement|bank statement|synthetic.*|artificial.*|account name\s*:?.*|account number\s*:?.*|account no\s*:?.*|statement period\s*:?.*|statement date\s*:?.*|statement request/download date\s*:?.*|transaction date from\s*:?.*|transaction date to\s*:?.*|name\s*:?.*|currency\s*:?\s*inr)', first):
                        raise ValueError('Unrecognised rows before the transaction table. Use the original PDF or a cleaner bank CSV; no rows were imported')
            return offset
        before.append(cells)
        offset = reader.line_num
        if offset >= 40:
            break
    return None


def _table_layout(text):
    # Select by explicit financial header roles, never delimiter frequency in
    # merchant descriptions or thousands separators. Reject multiple tables.
    candidates = []
    for delimiter in (',', ';', '\t'):
        try:
            offset = _table_start(text, delimiter)
        except csv.Error:
            continue
        if offset is not None:
            candidates.append((offset, delimiter))
    if len(candidates) != 1:
        raise ValueError('No unambiguous supported transaction table found. Try the original PDF export; no rows were imported')
    return candidates[0]


def _bank_date(value):
    # Four-digit years only: a century is not printed by a two-digit date.
    # An English ordinal spelling is supported without changing day/month order.
    cleaned = re.sub(r'(?<=\d)(?:st|nd|rd|th)\b', '', value, flags=re.I)
    cleaned = re.sub(r'\s*,\s*', ' ', cleaned).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
                '%d-%b-%Y', '%d %b %Y', '%B %d %Y'):
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError('Use an unambiguous day-first date with a four-digit year')


def parse_statement_csv(text: str, *, account_type: str) -> dict:
    if not text or len(text.encode('utf-8')) > 1024 * 1024:
        raise ValueError('Use a non-empty CSV of at most 1 MB')
    try:
        offset, delimiter = _table_layout(text)
    except csv.Error as error:
        raise ValueError('Malformed CSV; no partial import accepted') from error
    lines = text.lstrip('\ufeff').splitlines(keepends=True)
    reader = csv.DictReader(io.StringIO(''.join(lines[offset:])), delimiter=delimiter, strict=True)
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
        mapping = _export_mapping(reader.fieldnames or [])
        if not mapping:
            raise ValueError('This CSV table is not supported yet. Keep the original bank headings and try its PDF export. Friday needs separate date, description, debit and credit fields; no rows were imported')
        if account_type != 'BANK':
            raise ValueError('Bank-export withdrawal/deposit headings are for bank accounts; use a supported card export or its PDF')
        adapter = 'BANK_EXPORT_V2'
    facts = StatementSourceFacts(adapter=adapter)
    # The explicit withdrawal/deposit header establishes direction for this adapter.
    if adapter in ('BANK_STYLE_V1', 'BANK_EXPORT_V2'):
        raw_header = ','.join(name.strip() for name in reader.fieldnames)
        # Use only explicit contiguous source labels, not a guessed convention
        # from a bank name. Other layouts retain UNKNOWN direction checks.
        for direction in ('withdrawal amt.,deposit amt.,closing balance',
                          'withdrawal,deposit,closing balance'):
            start = raw_header.casefold().find(direction)
            if start >= 0:
                literal = raw_header[start:start + len(direction)]
                facts.convention = ConventionSourceFact(value='BANK_CREDIT_INCREASES', literal_text=literal,
                    source_refs=[SourceReference(unit_id='csv-header', text=raw_header)])
                break
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
            source_row = offset + previous_line + 1
            previous_line = reader.line_num
            if None in original or any(value is None for value in original.values()):
                raise ValueError(f'Row {source_row}: inconsistent number of columns; no partial import accepted')
            row = {mapping[key.strip().casefold()]: value.strip() for key, value in original.items()
                   if mapping[key.strip().casefold()] is not None}
            if row.get('currency', 'INR').upper() not in ('', 'INR'):
                raise ValueError(f'Row {source_row}: only INR statements are supported')
            if adapter == 'BANK_EXPORT_V2':
                # Some exports print a dash for the unused debit/credit cell.
                # It is absence, never a negative amount or an inferred direction.
                for field in ('debit', 'credit'):
                    if row[field] == '-':
                        row[field] = ''
                if row['date']:
                    row['date'] = _bank_date(row['date'])
            dated_opening = (adapter == 'BANK_EXPORT_V2' and row['description'].casefold() == 'opening balance'
                             and not row['debit'] and not row['credit'] and not source_rows)
            if not row['date'] or dated_opening:
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

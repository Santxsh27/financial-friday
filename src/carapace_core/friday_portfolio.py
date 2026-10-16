"""Statement-derived spending, never a bank balance, credit score or payment power."""
from collections import Counter, defaultdict
from datetime import date
from datetime import datetime
from zoneinfo import ZoneInfo
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .friday_statement_reconciliation import StatementSourceFacts
from .friday_statement_receipt import StatementExtractionReceipt

CATEGORIES = ('Groceries', 'Food', 'Transport', 'Housing', 'Utilities', 'Shopping',
              'Health', 'Education', 'Entertainment', 'Fees', 'Other')
KINDS = ('INCOME', 'EXPENSE', 'TRANSFER', 'CARD_REPAYMENT', 'LOAN_RECEIVED',
         'LOAN_REPAYMENT', 'REFUND', 'UNCLEAR')


class StatementEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')
    date: date
    description: str = Field(min_length=1, max_length=180)
    debit_minor: int = Field(ge=0, le=100_000_000_000, strict=True)
    credit_minor: int = Field(ge=0, le=100_000_000_000, strict=True)
    kind: Literal['INCOME','EXPENSE','TRANSFER','CARD_REPAYMENT','LOAN_RECEIVED','LOAN_REPAYMENT','REFUND','UNCLEAR'] = 'UNCLEAR'
    category: Literal['Groceries','Food','Transport','Housing','Utilities','Shopping','Health','Education','Entertainment','Fees','Other'] = 'Other'
    source_row: int = Field(ge=1, le=10000, strict=True)
    running_balance_minor: int | None = Field(default=None, ge=-100_000_000_000_000, le=100_000_000_000_000, strict=True)
    source_unit_ids: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode='after')
    def check(self):
        if bool(self.debit_minor) == bool(self.credit_minor):
            raise ValueError('Each transaction needs exactly one positive debit or credit')
        if self.date > datetime.now(ZoneInfo('Asia/Kolkata')).date() or self.date.year < 2000:
            raise ValueError('Statements must contain historical dates from 2000 onward')
        if self.kind in {'INCOME','LOAN_RECEIVED','REFUND'} and not self.credit_minor:
            raise ValueError('Income, loan received and refund require a credit')
        if self.kind in {'EXPENSE','CARD_REPAYMENT','LOAN_REPAYMENT'} and not self.debit_minor:
            raise ValueError('Expenses and repayments require a debit')
        if self.kind != 'EXPENSE' and self.category != 'Other':
            raise ValueError('Spending categories apply only to expenses')
        if any(not isinstance(unit, str) or not 1 <= len(unit) <= 80 for unit in self.source_unit_ids):
            raise ValueError('Invalid transaction source unit')
        if len(set(self.source_unit_ids)) != len(self.source_unit_ids):
            raise ValueError('Transaction source units must be unique')
        return self


class StatementImport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    account_alias: str = Field(min_length=1, max_length=40, pattern=r'^[A-Za-z][A-Za-z0-9 _-]*$')
    account_type: Literal['BANK','CREDIT_CARD']
    entries: list[StatementEntry] = Field(min_length=1, max_length=500)
    extraction: Literal['CSV_EXACT','PDF_TEXT_GEMINI','OCR_GEMINI']
    source_facts: StatementSourceFacts | None = None
    extraction_receipt: StatementExtractionReceipt | None = None


class SaveStatement(BaseModel):
    model_config = ConfigDict(extra='forbid')
    statement: StatementImport
    expected_revision: int = Field(ge=0, strict=True)
    workspace_generation: str = Field(min_length=1, max_length=80)
    confirm_reviewed_and_store: bool = Field(strict=True)


class StatementVisibility(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    excluded: bool = Field(strict=True)
    expected_revision: int = Field(ge=0,strict=True)
    workspace_generation: str = Field(min_length=1,max_length=80)


def classify(description, debit):
    """Conservative local proposals. Generic credits are not guessed salary."""
    d = description.casefold()
    kind = 'UNCLEAR'
    if re.search(r'\b(self transfer|own account|internal transfer)\b', d): kind = 'TRANSFER'
    elif debit and re.search(r'\b(credit card payment|card repayment|cc payment)\b', d): kind = 'CARD_REPAYMENT'
    elif debit and re.search(r'\b(emi|loan repayment|loan installment)\b', d): kind = 'LOAN_REPAYMENT'
    elif not debit and re.search(r'\b(loan disburs|loan received)', d): kind = 'LOAN_RECEIVED'
    elif not debit and re.search(r'\b(refund|reversal)\b', d): kind = 'REFUND'
    elif not debit and re.search(r'\b(salary|payroll|pension)\b', d): kind = 'INCOME'
    elif debit: kind = 'EXPENSE'
    category = 'Other'
    if kind == 'EXPENSE':
        for candidate, pattern in [('Groceries',r'grocery|groceries|supermarket'), ('Food',r'restaurant|cafe|swiggy|zomato'),
            ('Transport',r'uber|ola\b|metro|petrol|fuel|bus fare'),('Housing',r'\brent\b'),
            ('Utilities',r'electric|utility bill|broadband|water bill|mobile recharge'),('Health',r'pharmacy|hospital|clinic'),
            ('Education',r'tuition|school|college'),('Entertainment',r'netflix|cinema|spotify'),
            ('Fees',r'bank fee|service charge'),('Shopping',r'amazon|clothing|shopping')]:
            if re.search(pattern,d): category=candidate; break
    return kind, category


def summarize_statements(statements):
    months = defaultdict(lambda: defaultdict(int))
    categories = Counter(); kinds = Counter(); duplicates = Counter(); dates=[]
    rows = []; account_types = defaultdict(set)
    for statement in statements:
        account_types[statement['account_alias']].add(statement['account_type'])
        for entry in statement['entries']:
            entry = StatementEntry.model_validate(entry).model_dump(mode='json')
            row = {**entry,'account_alias':statement['account_alias'],'account_type':statement['account_type']}
            rows.append(row); dates.append(row['date'])
            month=months[row['date'][:7]]; debit=row['debit_minor']; credit=row['credit_minor']; kind=row['kind']
            month['money_in_minor']+=credit;month['money_out_minor']+=debit
            if kind=='INCOME':month['identified_income_minor']+=credit
            if kind=='EXPENSE':
                month['spending_minor']+=debit;categories[row['category']]+=debit
            if kind=='LOAN_REPAYMENT':month['loan_repayments_minor']+=debit
            if kind=='CARD_REPAYMENT':month['card_repayments_minor']+=debit
            kinds[kind]+=credit+debit
            duplicates[(row['account_alias'],row['date'],row['description'].casefold(),debit,credit)]+=1
    category_rows=[{'category':k,'amount_minor':v} for k,v in categories.most_common()]
    month_rows=[{'month':m,**{key:values[key] for key in ('money_in_minor','money_out_minor','identified_income_minor','spending_minor','loan_repayments_minor','card_repayments_minor')}} for m,values in sorted(months.items())]
    income=sum(m['identified_income_minor'] for m in month_rows)
    out=sum(m['spending_minor']+m['loan_repayments_minor'] for m in month_rows)
    warnings=[]
    repeated=sum(n-1 for n in duplicates.values() if n>1)
    if repeated: warnings.append(f'{repeated} potentially overlapping or repeated row(s). All remain counted; compare imports before relying on totals.')
    if kinds['UNCLEAR']:warnings.append('Some money movements are unclear. Review them before treating the income/spending comparison as complete.')
    if kinds['CARD_REPAYMENT']:warnings.append('Card repayments are excluded from spending. If card purchase statements are missing, total spending is understated.')
    if len(account_types)>1:warnings.append('Multiple accounts are combined. Review transfers manually; similar amounts do not prove an own-account transfer.')
    if dates:
        occupied={r['month'] for r in month_rows};start=min(dates)[:7];end=max(dates)[:7]
        y,m=map(int,start.split('-'));missing=[]
        while f'{y:04d}-{m:02d}'<=end:
            key=f'{y:04d}-{m:02d}'
            if key not in occupied:missing.append(key)
            y,m=(y+1,1) if m==12 else (y,m+1)
        if missing:warnings.append('No supplied rows for: '+', '.join(missing)+'. Absence of rows is not zero spending.')
    next_step=('Compare potentially overlapping imports before relying on totals; exclude an overlapping file if needed.' if repeated else
        'Review unclear credits and transfers first.' if kinds['UNCLEAR'] else
        'Compare the card purchase statement before estimating savings.' if kinds['CARD_REPAYMENT'] and not any(s['account_type']=='CREDIT_CARD' for s in statements) else
        'Your classified outgoings exceed identified income. Review the largest spending category and upcoming repayments.' if income and out>income else
        'Review your largest spending category and choose one realistic reduction for next month.' if category_rows else
        'Import a statement to begin. One month is enough to start; six months gives a broader history.')
    return {'scope':'USER_REVIEWED_STATEMENTS','currency':'INR','money_moved':False,'bank_connected':False,
        'statement_count':len(statements),'transaction_count':len(rows),'account_count':len(account_types),
        'period':{'start':min(dates),'end':max(dates)} if dates else None,
        'totals':{'money_in_minor':sum(r['credit_minor'] for r in rows),'money_out_minor':sum(r['debit_minor'] for r in rows),
            'identified_income_minor':income,'classified_spending_minor':sum(categories.values()),
            'loan_repayments_minor':kinds['LOAN_REPAYMENT'],'card_repayments_minor':kinds['CARD_REPAYMENT'],
            'unclassified_minor':kinds['UNCLEAR'],'income_less_classified_outgoings_minor':income-out,
            'outgoings_to_identified_income_percent':round(out*100/income,1) if income else None},
        'monthly':month_rows,'categories':category_rows,'warnings':warnings,'next_step':next_step,
        'repeated_row_candidates':repeated,'entries':rows,
        'limits':['Based on supplied, user-reviewed records, not authenticated bank feeds.',
            'Category and income labels are interpretations. Correct errors before using the comparison.',
            'Card repayments and transfers are not counted as new spending; loan credits and refunds are not earnings.',
            'Not net worth, disposable cash, a credit score, a full debt balance, or a prediction of future income.',
            'No rows are silently deleted. Overlapping imports and missing accounts can distort totals.']}

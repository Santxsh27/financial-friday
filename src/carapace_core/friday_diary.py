"""User-reported money diary, never a bank ledger or credit score."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class DiaryEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')
    direction: Literal['IN', 'OUT']
    amount_minor: int = Field(gt=0, le=10_000_000_000, strict=True)
    date: date
    label: str = Field(min_length=1, max_length=80)

    @model_validator(mode='after')
    def valid_date(self):
        if not 2000 <= self.date.year <= 2100:
            raise ValueError('Use an entry year between 2000 and 2100')
        return self


class DiaryChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    operation_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    expected_revision: int = Field(ge=0, strict=True)
    workspace_generation: str = Field(min_length=1, max_length=64)
    action: Literal['START', 'ADD', 'UNDO']
    confirm_store: bool = Field(strict=True)
    opening_cash_minor: int | None = Field(default=None, ge=0, le=10_000_000_000, strict=True)
    buffer_minor: int | None = Field(default=None, gt=0, le=10_000_000_000, strict=True)
    entries: list[DiaryEntry] = Field(default_factory=list, max_length=5)
    undo_operation_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')

    @model_validator(mode='after')
    def valid_action(self):
        if not self.confirm_store:
            raise ValueError('Confirm private diary storage first')
        if self.action == 'START':
            if self.opening_cash_minor is None or self.buffer_minor is None or self.entries or self.undo_operation_id:
                raise ValueError('Start needs only opening cash and a positive chosen buffer')
        elif self.action == 'ADD':
            if not self.entries or self.opening_cash_minor is not None or self.buffer_minor is not None or self.undo_operation_id:
                raise ValueError('Add needs one to five reported entries')
        elif self.entries or self.opening_cash_minor is not None or self.buffer_minor is not None or not self.undo_operation_id:
            raise ValueError('Undo needs only a previously saved entry group')
        return self


def diary_summary(record):
    active = [entry for entry in record['entries'] if not entry.get('undone')]
    incoming = sum(e['amount_minor'] for e in active if e['direction'] == 'IN')
    outgoing = sum(e['amount_minor'] for e in active if e['direction'] == 'OUT')
    cash = record['opening_cash_minor'] + incoming - outgoing
    return {'reported_cash_minor': cash, 'money_in_minor': incoming, 'money_out_minor': outgoing,
        'net_change_minor': incoming-outgoing, 'buffer_minor': record['buffer_minor'],
        'buffer_coverage_percent': min(100, max(0, cash)*100//record['buffer_minor']),
        'above_buffer_minor': max(0, cash-record['buffer_minor']),
        'buffer_gap_minor': max(0, record['buffer_minor']-cash),
        'status': 'REPORTED_SHORTFALL' if cash < 0 else 'BUFFER_BELOW_TARGET' if cash < record['buffer_minor'] else 'BUFFER_COVERED',
        'active_entries': len(active), 'check_in_days': len({e['date'] for e in active}),
        'last_entry_date': max((e['date'] for e in active), default=None)}

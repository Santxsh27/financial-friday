"""Tenant-scoped communication preferences; never financial authority."""
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BuddyPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    display_name: str = Field(default='', max_length=40)
    explanation_style: Literal['CONCISE', 'STEP_BY_STEP'] = 'CONCISE'
    focus: Literal['BILLS', 'UNDERSTAND_SPENDING', 'CHECK_REQUESTS'] = 'BILLS'
    share_style_with_ai: bool = Field(default=False, strict=True)

    @field_validator('display_name')
    @classmethod
    def friendly_name(cls, value):
        value = value.strip()
        if any(not (c.isalpha() or c in " .'-") for c in value):
            raise ValueError('Use a nickname with letters only; never enter account details or secrets')
        return value


class FridayBuddy:
    def __init__(self, service):
        self.service = service
        with service.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS friday_buddy_preferences (tenant TEXT PRIMARY KEY, record TEXT NOT NULL)')

    def preferences(self, tenant):
        if self.service.durable.mode == 'FIRESTORE_TRANSACTIONAL':
            value = self.service.durable.get('buddy_preferences', tenant, 'current')
        else:
            with self.service.connect() as db:
                row = db.execute('SELECT record FROM friday_buddy_preferences WHERE tenant=?', (tenant,)).fetchone()
            value = json.loads(row[0]) if row else None
        return BuddyPreferences.model_validate(value or {}).model_dump()

    def save(self, tenant, preferences):
        value = preferences.model_dump()
        if self.service.durable.mode == 'FIRESTORE_TRANSACTIONAL':
            self.service.durable.put('buddy_preferences', tenant, 'current', value)
        else:
            with self.service.connect() as db:
                db.execute('INSERT OR REPLACE INTO friday_buddy_preferences VALUES (?,?)', (tenant, json.dumps(value)))
        return {'preferences': value, 'scope': 'COMMUNICATION_ONLY', 'money_moved': False,
                'payment_authorized': False, 'financial_rules_changed': False}

    def model_preferences(self, tenant, consent):
        if not consent: return {}
        profile = self.preferences(tenant)
        if not profile['share_style_with_ai']: return {}
        # No name, bank records, payment limits, free-text instructions or secrets.
        return {key: profile[key] for key in ('explanation_style', 'focus')}

    def snapshot(self, tenant, reviews):
        from .friday_obligations import financial_obligations
        from .friday_recovery import RecoveryScheduler
        board = financial_obligations(self.service, reviews, tenant)
        # Default artificial provider examples are not the customer's obligations.
        unresolved = [item for item in board['items'] if item['source_case_id'] and
                      (item['state'] != 'RECORDED_COMPLETE' or item['checks'])]
        next_item = unresolved[0] if unresolved else None
        return {'scope': 'FINANCIAL_BUDDY_OVERVIEW', 'read_only': True, 'money_moved': False,
                'payment_authorized': False, 'ai_called': False, 'bank_connected': False,
                'preferences': self.preferences(tenant),
                'documents_checked': board['coverage']['documents_checked'],
                'attention_count': len(unresolved),
                'followup_summary': board.get('followup_summary', {}),
                'recorded_artificial_count': board['summary']['RECORDED_COMPLETE'],
                'next_item': {key: next_item[key] for key in ('obligation_id','supplier','reference','state','next_step')} if next_item else None,
                'evidence_version': board['evidence_version'], 'provider_coverage_complete': board['coverage']['provider_coverage_complete'],
                'ai': {'mode': self.service.planner.mode, 'model': self.service.planner.model_name,
                       'status': 'ON_REQUEST' if self.service.planner.mode != 'LOCAL_RULES' else 'NOT_CONFIGURED'},
                'recovery_mode': 'AUTOMATIC_JOURNAL_ONLY' if RecoveryScheduler.from_env().enabled else 'MANUAL_JOURNAL_ONLY'}

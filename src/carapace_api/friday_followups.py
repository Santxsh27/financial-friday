"""Private follow-through bookkeeping. Never changes financial evidence or authority."""
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from carapace_core.canonical import sha256_hex
from .friday_privacy import privacy_generation


class FollowupRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['TRACK', 'WAIT_FOR_PROVIDER', 'RECHECK', 'CLOSE_TRACKING']
    expected_revision: int = Field(ge=0, strict=True)
    expected_evidence_version: str = Field(min_length=1, max_length=200)


def item_fingerprint(item):
    # Bind to this obligation, not an unrelated upload elsewhere in the workspace.
    return sha256_hex({key: value for key, value in item.items() if key != 'followup'})


class FridayFollowups:
    MAX_ITEMS = 100

    def __init__(self, service):
        self.service = service
        with service.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS friday_followups (tenant TEXT PRIMARY KEY, record TEXT NOT NULL)')

    def records(self, tenant):
        if self.service.durable.mode == 'FIRESTORE_TRANSACTIONAL':
            record = self.service.durable.get('followups', tenant, 'current') or {}
        else:
            with self.service.connect() as db:
                row = db.execute('SELECT record FROM friday_followups WHERE tenant=?', (tenant,)).fetchone()
            record = json.loads(row[0]) if row else {}
        if record.get('privacy_generation', 0) != privacy_generation(self.service, tenant):
            return {}
        return record.get('items', {})

    def enrich(self, tenant, board):
        records = self.records(tenant)
        counts = {'tracking': 0, 'waiting': 0, 'closed': 0, 'new_evidence': 0}
        for item in board['items']:
            old = records.get(item['obligation_id'])
            changed = bool(old and old['fingerprint'] != item_fingerprint(item))
            state = 'NEW_EVIDENCE' if changed else old['state'] if old else 'NOT_TRACKED'
            item['followup'] = {'state': state, 'saved_state': old['state'] if old else None,
                'revision': old['revision'] if old else 0, 'evidence_changed': changed,
                'updated_at': old['updated_at'] if old else None,
                'payment_verified': False, 'external_message_sent': False}
            key = {'TRACKING': 'tracking', 'WAITING_FOR_PROVIDER': 'waiting',
                   'CLOSED': 'closed', 'NEW_EVIDENCE': 'new_evidence'}.get(state)
            if key: counts[key] += 1
        board['followup_summary'] = counts
        return board

    def update(self, tenant, reviews, identity, request):
        from .friday_obligations import financial_obligations
        generation = privacy_generation(self.service, tenant)
        board = financial_obligations(self.service, reviews, tenant)
        if request.expected_evidence_version != board['evidence_version']:
            raise ValueError('Evidence changed. Refresh the inbox before updating follow-up tracking.')
        item = next((item for item in board['items'] if item['obligation_id'] == identity), None)
        if not item or not item['source_case_id']:
            raise KeyError('Only your saved obligations can be tracked; provider examples are separate.')
        fingerprint = item_fingerprint(item)
        now = datetime.now(timezone.utc).isoformat()

        def change(record):
            items = dict((record or {}).get('items', {})) if (record or {}).get('privacy_generation', 0) == generation else {}
            old = items.get(identity)
            revision = old['revision'] if old else 0
            if request.expected_revision != revision:
                raise ValueError('Follow-up changed in another session. Refresh before trying again.')
            if not old and request.action != 'TRACK':
                raise ValueError('Start tracking this obligation first.')
            if not old and len(items) >= self.MAX_ITEMS:
                raise ValueError('Tracking limit reached. Use privacy cleanup before adding more records.')
            state = {'TRACK': 'TRACKING', 'WAIT_FOR_PROVIDER': 'WAITING_FOR_PROVIDER',
                     'CLOSE_TRACKING': 'CLOSED'}.get(request.action)
            if request.action == 'RECHECK':
                state = old['state'] if old['fingerprint'] == fingerprint else 'TRACKING'
            # Closing is bookkeeping only; new evidence subsequently surfaces again.
            value = {'state': state, 'revision': revision + 1, 'fingerprint': fingerprint,
                     'updated_at': now, 'created_at': old['created_at'] if old else now}
            items[identity] = value
            return {'privacy_generation': generation, 'items': items}

        if self.service.durable.mode == 'FIRESTORE_TRANSACTIONAL':
            record = self.service.durable.update_followups(tenant, generation, change)
        else:
            with self.service.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if privacy_generation(self.service, tenant, db) != generation:
                    raise ValueError('Privacy cleanup occurred. Refresh before saving tracking.')
                row = db.execute('SELECT record FROM friday_followups WHERE tenant=?', (tenant,)).fetchone()
                record = change(json.loads(row[0]) if row else None)
                db.execute('INSERT OR REPLACE INTO friday_followups VALUES (?,?)', (tenant, json.dumps(record)))
        return {'scope': 'FOLLOWUP_BOOKKEEPING_ONLY', 'followup': record['items'][identity],
                'financial_state': item['state'], 'checks': item['checks'],
                'money_moved': False, 'payment_authorized': False, 'payment_verified': False,
                'external_message_sent': False, 'ai_called': False,
                'message': 'Tracking updated. Financial checks are unchanged; no payment or message was sent.'}

"""Versioned, tenant-private diary. Atomic writes and receipt-like replay safety."""
import json
from copy import deepcopy
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from carapace_core.friday_diary import diary_summary
from carapace_core.canonical import sha256_hex
from .friday_privacy import privacy_generation
from .friday_cashflow import _model_amounts


class FridayDiary:
    MAX_ENTRIES = 100
    MAX_OPERATIONS = 200

    def __init__(self, service):
        self.service = service
        with service.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS friday_diary (tenant TEXT PRIMARY KEY, record TEXT NOT NULL)')

    def record(self, tenant):
        if self.service.durable.mode == 'FIRESTORE_TRANSACTIONAL':
            record = self.service.durable.get('diary', tenant, 'current')
        else:
            with self.service.connect() as db:
                row = db.execute('SELECT record FROM friday_diary WHERE tenant=?', (tenant,)).fetchone()
            record = json.loads(row[0]) if row else None
        if record and record['privacy_generation'] != privacy_generation(self.service, tenant):
            return None
        return record

    def view(self, tenant, record=None):
        record = record if record is not None else self.record(tenant)
        return {'scope':'USER_REPORTED_MONEY_DIARY','currency':'INR',
            'workspace_generation':str(privacy_generation(self.service, tenant)),
            'revision':record['revision'] if record else 0,
            'summary':diary_summary(record) if record else None,
            'entries':record['entries'] if record else [], 'started_at':record['started_at'] if record else None,
            'updated_at':record['updated_at'] if record else None,
            'money_moved':False,'payment_authorized':False,'bank_connected':False,'ai_called':False,
            'limits':['User reports only, not a bank balance, credit score or proof that a bill was paid.',
                'Money in includes transfers/refunds/borrowing if entered; it is not automatically earnings or profit.',
                'The buffer meter compares reported cash with your chosen target, not financial health or future safety.',
                '100 entries and 200 changes per diary. Explicit review cleanup clears this diary.',
                'No bank/SMS monitoring, automatic collection, model training or guarantee of future income.']}

    def change(self, tenant, request):
        generation = privacy_generation(self.service, tenant)
        if request.workspace_generation != str(generation):
            raise ValueError('Workspace was cleared. Refresh before saving a new diary.')
        fingerprint = sha256_hex(request.model_dump(mode='json'))
        now = datetime.now(timezone.utc).isoformat()
        def update(old):
            old = old if old and old['privacy_generation'] == generation else None
            if old and request.operation_id in old['operations']:
                if old['operations'][request.operation_id] != fingerprint:
                    raise ValueError('This update identity was already used for different details')
                return old
            if request.expected_revision != (old['revision'] if old else 0):
                raise ValueError('Diary changed in another session. Reload before saving.')
            if old and len(old['operations']) >= self.MAX_OPERATIONS:
                raise ValueError('Diary change limit reached. Export your entries before explicit cleanup.')
            if request.action == 'START':
                if old: raise ValueError('A diary already exists; start does not reset it')
                record = {'privacy_generation':generation,'opening_cash_minor':request.opening_cash_minor,
                    'buffer_minor':request.buffer_minor,'started_at':now,'entries':[],'operations':{},'revision':0}
            else:
                if not old: raise ValueError('Set up your diary first')
                record = deepcopy(old)
                if request.action == 'ADD':
                    if len(record['entries'])+len(request.entries) > self.MAX_ENTRIES:
                        raise ValueError('Diary has reached 100 entries; nothing was silently discarded')
                    for entry in request.entries:
                        if entry.date > datetime.now(ZoneInfo('Asia/Kolkata')).date():
                            raise ValueError('Expected income belongs in the runway plan, not received-money history')
                        record['entries'].append({**entry.model_dump(mode='json'),
                            'operation_id':request.operation_id,'undone':False,'source':'USER_REPORTED'})
                else:
                    matches = [e for e in record['entries'] if e['operation_id'] == request.undo_operation_id]
                    if not matches or all(e['undone'] for e in matches):
                        raise ValueError('No active entry group matches this undo request')
                    for entry in matches: entry['undone'] = True
            record['operations'][request.operation_id] = fingerprint
            record['revision'] += 1
            record['updated_at'] = now
            return record
        if self.service.durable.mode == 'FIRESTORE_TRANSACTIONAL':
            result = self.service.durable.update_diary(tenant, generation, update)
        else:
            with self.service.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if privacy_generation(self.service, tenant, db) != generation:
                    raise ValueError('Workspace was cleared while saving; refresh first')
                row = db.execute('SELECT record FROM friday_diary WHERE tenant=?',(tenant,)).fetchone()
                result = update(json.loads(row[0]) if row else None)
                db.execute('INSERT OR REPLACE INTO friday_diary VALUES (?,?)',(tenant,json.dumps(result)))
        return self.view(tenant, result)

    def model_context(self, tenant):
        record = self.record(tenant)
        if not record: return {}
        return _model_amounts({'evidence_id':'diary:current','scope':'USER_REPORTED_MONEY_DIARY',
            'updated_at':record['updated_at'], **diary_summary(record),
            'limits':self.view(tenant,record)['limits']})

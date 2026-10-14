"""Optional private snapshot. No training, raw statements or payment authority."""
import json
from datetime import datetime, timezone
from carapace_core.friday_cashflow import project_cashflow
from .friday_privacy import privacy_generation


class FridayCashflow:
    def __init__(self, service):
        self.service = service
        with service.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS friday_cashflow (tenant TEXT PRIMARY KEY, record TEXT NOT NULL)')

    def get(self, tenant):
        if self.service.durable.mode == 'FIRESTORE_TRANSACTIONAL':
            record = self.service.durable.get('cashflow', tenant, 'current')
        else:
            with self.service.connect() as db:
                row = db.execute('SELECT record FROM friday_cashflow WHERE tenant=?', (tenant,)).fetchone()
            record = json.loads(row[0]) if row else None
        if record and record['privacy_generation'] != privacy_generation(self.service, tenant): return None
        return record

    def create(self, tenant, request):
        generation = privacy_generation(self.service, tenant)
        result = project_cashflow(request)
        result['saved_to_workspace'] = request.save_to_workspace
        if request.save_to_workspace:
            record = {'privacy_generation': generation, 'created_at': datetime.now(timezone.utc).isoformat(),
                      'inputs': request.model_dump(mode='json'), 'result': result}
            if self.service.durable.mode == 'FIRESTORE_TRANSACTIONAL':
                self.service.durable.put_cashflow(tenant, generation, record)
            else:
                with self.service.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    if privacy_generation(self.service, tenant, db) != generation:
                        raise ValueError('Privacy cleanup occurred. The forecast was not saved.')
                    db.execute('INSERT OR REPLACE INTO friday_cashflow VALUES (?,?)', (tenant, json.dumps(record)))
        return result

    def model_context(self, tenant):
        record = self.get(tenant)
        if not record: return {}
        result = record['result']
        # Only calculator aggregates; no statement descriptions or individual events.
        return {'evidence_id': 'cashflow:current', 'scope': result['scope'], 'saved_at': record['created_at'],
            **{key: result[key] for key in ('currency','status','as_of','horizon_days','starting_cash_minor',
                'reserve_minor','daily_spend_minor','expected_income_total_minor','committed_bills_total_minor','income_delay_days')},
            'baseline': {key: value for key, value in result['baseline'].items() if key != 'timeline'},
            'delayed_income': {key: value for key, value in result['delayed_income'].items() if key != 'timeline'},
            'assumptions': result['limits']}

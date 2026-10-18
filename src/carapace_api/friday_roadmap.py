"""One private priority goal; revision-safe savings reports, never payments."""
import json
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
from carapace_core.canonical import sha256_hex
from carapace_core.friday_goals import paise
from carapace_core.friday_roadmap import RoadmapPlan, calculate_roadmap
from .friday_privacy import privacy_generation


class FridayRoadmap:
    def __init__(self, service):
        self.service = service
        with service.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS friday_roadmap (tenant TEXT PRIMARY KEY, record TEXT NOT NULL)')

    def record(self, tenant):
        if self.service.durable.mode == 'FIRESTORE_TRANSACTIONAL':
            record = self.service.durable.get('goal_roadmap',tenant,'current')
        else:
            with self.service.connect() as db:
                row = db.execute('SELECT record FROM friday_roadmap WHERE tenant=?',(tenant,)).fetchone()
            record = json.loads(row[0]) if row else None
        return record if record and record['privacy_generation']==privacy_generation(self.service,tenant) else None

    def view(self, tenant, record=None):
        generation = privacy_generation(self.service,tenant)
        record = record if record is not None else self.record(tenant)
        if record and record['privacy_generation'] != generation:
            record = None
        summary = calculate_roadmap(RoadmapPlan.model_validate(record['plan']),record['entries'],
            datetime.fromisoformat(record['started_at']).date(),datetime.now(ZoneInfo('Asia/Kolkata')).date()) if record else None
        return {'revision':record['revision'] if record else 0,'workspace_generation':str(generation),
            'plan':record['plan'] if record else None,'summary':summary,
            'entries':record['entries'] if record else [],'archived_plans':len(record['archives']) if record else 0,
            'money_moved':False,'payment_authorized':False,'bank_connected':False,
            'scope':'ONE_USER_REPORTED_PRIORITY_GOAL','updated_at':record['updated_at'] if record else None}

    def change(self, tenant, request):
        generation = privacy_generation(self.service,tenant)
        if request.workspace_generation != str(generation):
            raise ValueError('Workspace was cleared. Reload Goals before saving.')
        fingerprint = sha256_hex(request.model_dump(mode='json'))
        now = datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
        def update(old):
            old = old if old and old['privacy_generation']==generation else None
            if old and request.operation_id in old['operations']:
                if old['operations'][request.operation_id] != fingerprint:
                    raise ValueError('This operation identity was used for different details')
                return old
            if request.expected_revision != (old['revision'] if old else 0):
                raise ValueError('Your roadmap changed in another tab. Reload Goals before saving.')
            if old and len(old['operations'])>=200:
                raise ValueError('Roadmap change limit reached. Export before explicit privacy cleanup.')
            record = deepcopy(old) if old else {'privacy_generation':generation,'revision':0,'operations':{},'archives':[]}
            if request.action == 'SAVE':
                if old:
                    if not request.replace_existing:
                        raise ValueError('Confirm replacing the active priority goal first')
                    if len(record['archives'])>=5:
                        raise ValueError('Archive limit reached. Export before explicit privacy cleanup.')
                    record['archives'].append({k:record[k] for k in ('plan','entries','started_at','updated_at')})
                record.update(plan=request.plan.model_dump(mode='json'),entries=[],started_at=now)
            elif not old:
                raise ValueError('Save a roadmap first')
            elif request.action == 'ADD':
                if len(record['entries'])>=100:
                    raise ValueError('Progress limit reached; no entries were discarded')
                record['entries'].append({'operation_id':request.operation_id,'amount_minor':paise(request.amount_inr),
                    'reported_at':now,'undone':False,'source':'USER_REPORTED_ADDITIONAL_SAVINGS'})
            else:
                matches=[e for e in record['entries'] if e['operation_id']==request.undo_operation_id and not e['undone']]
                if not matches:
                    raise ValueError('No active progress entry matches this undo request')
                matches[0]['undone']=True
            record['revision']+=1
            record['operations'][request.operation_id]=fingerprint
            record['updated_at']=now
            return record
        if self.service.durable.mode=='FIRESTORE_TRANSACTIONAL':
            result=self.service.durable.update_roadmap(tenant,generation,update)
        else:
            with self.service.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if privacy_generation(self.service,tenant,db)!=generation:
                    raise ValueError('Workspace cleared while saving. Reload first.')
                row=db.execute('SELECT record FROM friday_roadmap WHERE tenant=?',(tenant,)).fetchone()
                result=update(json.loads(row[0]) if row else None)
                db.execute('INSERT OR REPLACE INTO friday_roadmap VALUES (?,?)',(tenant,json.dumps(result)))
        return self.view(tenant,result)

    def export(self, tenant):
        record = self.record(tenant)
        return {'scope':'USER_REPORTED_ROADMAP_EXPORT','record':record,'money_moved':False}

    def model_context(self, tenant):
        view = self.view(tenant)
        if not view['plan']:
            return {}
        summary = {k:v for k,v in view['summary'].items() if k != 'calendar' and v is not None}
        return {'evidence_id':'roadmap:current','revision':view['revision'],
            'workspace_generation':view['workspace_generation'],'scope':view['scope'],
            'confirmed_assumptions':view['plan'],'calculated_path':summary}

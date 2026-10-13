"""Explicit retention/deletion of uploaded review claims and assistant drafts.

Payment journals and idempotency identities are NOT erased by this operation.
No automatic deletion is enabled by default. User confirmation is required.
"""
import json
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, ConfigDict, Field
from uuid import uuid4


def privacy_generation(service,tenant,db=None):
    if service.durable.mode=='FIRESTORE_TRANSACTIONAL':
        return (service.durable.get('privacy',tenant,'current') or {}).get('generation',0)
    if db is None:
        with service.connect() as connection:return privacy_generation(service,tenant,connection)
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='friday_privacy'").fetchone():return 0
    row=db.execute('SELECT policy FROM friday_privacy WHERE tenant=?',(tenant,)).fetchone()
    return json.loads(row[0]).get('generation',0) if row else 0


class PrivacyPolicy(BaseModel):
    model_config=ConfigDict(extra='forbid')
    retention_days:int|None=Field(default=None,ge=7,le=365,strict=True)


class DeleteReviews(BaseModel):
    model_config=ConfigDict(extra='forbid')
    confirm_delete_reviews:bool=Field(strict=True)
    expired_only:bool=Field(default=False,strict=True)


class FridayPrivacyService:
    def __init__(self,service):
        self.service=service
        with service.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS friday_privacy (tenant TEXT PRIMARY KEY, policy TEXT NOT NULL)')

    def policy(self,tenant):
        if self.service.durable.mode=='FIRESTORE_TRANSACTIONAL':
            stored=self.service.durable.get('privacy',tenant,'current')
        else:
            with self.service.connect() as db:
                row=db.execute('SELECT policy FROM friday_privacy WHERE tenant=?',(tenant,)).fetchone()
            stored=json.loads(row[0]) if row else None
        return (stored or {'retention_days':None})|{'automatic_deletion_enabled':False,
            'raw_uploads_stored':False,'scope':'Uploaded reviews and assistant drafts. Payment journal/idempotency retained.'}

    def save(self,tenant,policy):
        value=policy.model_dump()
        if self.service.durable.mode=='FIRESTORE_TRANSACTIONAL':self.service.durable.save_privacy_policy(tenant,value)
        else:
            with self.service.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                value['generation']=privacy_generation(self.service,tenant,db)
                db.execute('INSERT OR REPLACE INTO friday_privacy VALUES (?,?)',(tenant,json.dumps(value)))
        return self.policy(tenant)

    def delete(self,tenant,request):
        if not request.confirm_delete_reviews:raise ValueError('Explicit review deletion confirmation is required')
        days=self.policy(tenant)['retention_days']
        if request.expired_only and days is None:raise ValueError('Choose a retention duration before expired-only cleanup')
        cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat() if request.expired_only else None
        if self.service.durable.mode=='FIRESTORE_TRANSACTIONAL':
            counts=self.service.durable.delete_private_inputs(tenant,cutoff)
        else:
            counts={}
            with self.service.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                value={'retention_days':days,'generation':uuid4().hex}
                db.execute('INSERT OR REPLACE INTO friday_privacy VALUES (?,?)',(tenant,json.dumps(value)))
                for table,col,label in [('friday_reviews','tenant','reviews'),('friday_assistant_tasks','tenant_id','drafts')]:
                    exists=db.execute("SELECT 1 FROM sqlite_master WHERE name=?",(table,)).fetchone()
                    if not exists:continue
                    clause=' AND created_at<?' if cutoff else ''
                    params=(tenant,cutoff) if cutoff else (tenant,)
                    counts[label]=db.execute(f'DELETE FROM {table} WHERE {col}=?'+clause,params).rowcount
        return {'deleted':counts,'money_moved':False,'payment_journal_retained':True,
            'message':'Comparison inputs removed. Existing payment receipts remain to prevent repeating a recorded payment. Old prepared tasks cannot be reused.'}

"""Cloud Tasks dispatches signed journal-only recovery, never payment retries."""
import base64
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from carapace_core.canonical import sha256_hex
from .friday_resource_limits import reserve_resource


class RecoveryScheduler:
    def __init__(self, queue=None, origin=None, identity=None, session=None, target=None):
        self.enabled = any((queue, origin, identity))
        if self.enabled:
            if not queue or not re.fullmatch(r'projects/[a-z0-9-]+/locations/asia-south1/queues/[a-zA-Z0-9_-]+',queue):
                raise ValueError('Use an exact Mumbai recovery queue')
            parsed = urlsplit(origin or '')
            if parsed.scheme!='https' or not parsed.hostname or not parsed.hostname.endswith('.run.app') or parsed.netloc!=parsed.hostname or parsed.path or parsed.query or parsed.fragment:
                raise ValueError('Use the fixed private Cloud Run API origin')
            project = queue.split('/')[1]
            if not re.fullmatch(r'[a-z][a-z0-9-]+@'+re.escape(project)+r'\.iam\.gserviceaccount\.com',identity or ''):
                raise ValueError('Use the same-project dedicated recovery identity')
            if target and target!=origin and not re.fullmatch(r'https://[a-z0-9-]+---'+re.escape(parsed.hostname),target):
                raise ValueError('Recovery staging target must belong to the same Cloud Run service')
        self.queue, self.origin, self.identity, self.session = queue, origin, identity, session
        self.target=target or origin

    @classmethod
    def from_env(cls):
        return cls(os.getenv('FRIDAY_RECOVERY_QUEUE'),os.getenv('FRIDAY_RECOVERY_API_ORIGIN'),os.getenv('FRIDAY_RECOVERY_IDENTITY'),target=os.getenv('FRIDAY_RECOVERY_TARGET'))

    def enqueue(self, service, lease):
        if not self.enabled:
            return {'enabled':False,'mode':'MANUAL_JOURNAL_ONLY'}
        reserve_resource(service,'recovery_jobs',1)
        scheduled = datetime.fromisoformat(lease['lease_until']) + timedelta(seconds=10)
        payload = {key:lease[key] for key in ('tenant_id','task_id','task_sha256','lease_id')}
        payload.update(scope='JOURNAL_ONLY_RECOVERY',scheduled_at=scheduled.isoformat(),
                       expires_at=(scheduled+timedelta(minutes=30)).isoformat())
        envelope = {'payload':payload,'signature':service.signer.sign(payload),'key_id':service.signer.key_id}
        identity = 'recovery-'+sha256_hex(payload)[:48]
        task = {'name':self.queue+'/tasks/'+identity,'scheduleTime':scheduled.isoformat(),
                'dispatchDeadline':'60s','httpRequest':{'httpMethod':'POST',
                    'url':self.target+'/internal/friday/recover','headers':{'Content-Type':'application/json'},
                    'oidcToken':{'serviceAccountEmail':self.identity,'audience':self.origin},
                    'body':base64.b64encode(json.dumps(envelope).encode()).decode()}}
        session = self.session
        if session is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession
            credentials,_ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            session = AuthorizedSession(credentials)
        response = session.post('https://cloudtasks.googleapis.com/v2/'+self.queue+'/tasks',json={'task':task},timeout=20)
        # Dedupe is successful only for this deterministic server-derived name.
        if response.status_code!=409:
            response.raise_for_status()
        return {'enabled':True,'mode':'AUTOMATIC_JOURNAL_ONLY','scheduled_at':scheduled.isoformat()}


def verify_task_identity(token, scheduler):
    if not scheduler.enabled or not token or not token.startswith('Bearer '):
        raise ValueError('Authenticated recovery worker required')
    from google.oauth2 import id_token
    from google.auth.transport.requests import Request
    claims = id_token.verify_oauth2_token(token[7:],Request(),audience=scheduler.origin)
    if claims.get('email')!=scheduler.identity or claims.get('email_verified') is not True:
        raise ValueError('Wrong recovery identity')


def recover_journal(tasks, envelope):
    if set(envelope)!={'payload','signature','key_id'}:
        raise ValueError('Invalid recovery envelope')
    payload = envelope['payload']
    fields = {'tenant_id','task_id','task_sha256','lease_id','scope','scheduled_at','expires_at'}
    if not isinstance(payload,dict) or set(payload)!=fields or payload.get('scope')!='JOURNAL_ONLY_RECOVERY':
        raise ValueError('Journal-only envelope required')
    if not tasks.service.signer.verify_for_key(payload,envelope['signature'],envelope['key_id']):
        raise ValueError('Invalid recovery signature')
    now = datetime.now(timezone.utc)
    if now >= datetime.fromisoformat(payload['expires_at']):
        return {'state':'DELIVERY_EXPIRED','money_moved':False,'new_payment_created':False}
    if now < datetime.fromisoformat(payload['scheduled_at']):
        raise ValueError('Recovery is not due')
    current = tasks.executions.get(payload['tenant_id'],payload['task_id'])
    if current['state'] not in {'OUTCOME_UNKNOWN','REVIEW_REQUIRED'}:
        return {'state':'NOT_PENDING','money_moved':False,'new_payment_created':False}
    try:
        record = tasks._record(payload['tenant_id'],payload['task_id'])
    except KeyError:
        return {'state':'DRAFT_REMOVED','money_moved':False,'new_payment_created':False}
    if sha256_hex(record['payload'])!=payload['task_sha256']:
        raise ValueError('Recovery task changed')
    # This function intentionally has no executor, planner or confirmation call.
    outcome = tasks.reconcile(payload['tenant_id'],payload['task_id'])
    changed = tasks.executions.record_recovery(payload,outcome)
    return {'state':outcome['state'] if changed else 'STALE_DELIVERY',
            'money_moved':False,'new_payment_created':False,'journal_only':True}

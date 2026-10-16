"""Private, versioned statement imports. No payment state or diary mutation."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from time import perf_counter
from carapace_core.friday_portfolio import StatementImport, summarize_statements
from carapace_core.friday_checkup import build_checkup, checkup_model_context
from carapace_core.friday_statement_reconciliation import reconcile_statement
from carapace_core.friday_statement_receipt import verify_statement_extraction
from carapace_core.friday_trace import record_stage
from .friday_privacy import privacy_generation


class FridayPortfolio:
    def __init__(self,service):
        self.service=service
        with service.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS friday_portfolio (tenant TEXT PRIMARY KEY, record TEXT NOT NULL)')

    def record(self,tenant):
        if self.service.durable.mode=='FIRESTORE_TRANSACTIONAL':record=self.service.durable.get('statement_portfolio',tenant,'current')
        else:
            with self.service.connect() as db:row=db.execute('SELECT record FROM friday_portfolio WHERE tenant=?',(tenant,)).fetchone()
            record=json.loads(row[0]) if row else None
        return record if record and record['generation']==privacy_generation(self.service,tenant) else None

    def view(self,tenant,record=None):
        from carapace_core.friday_assistance import build_assistant_work
        generation=privacy_generation(self.service,tenant)
        record=record if record is not None else self.record(tenant)
        # Never label an earlier generation's rows as a newly cleared workspace.
        if record and record['generation']!=generation:record=None
        included=[s for s in record['statements'] if s['source_sha256'] not in record.get('excluded',[])] if record else []
        started=perf_counter()
        try:summary=summarize_statements(included)
        except (ValueError,TypeError,KeyError):
            record_stage('calculation',ok=False,reason='calculation_error');raise
        record_stage('calculation',ok=True,reason='accepted',duration_ms=(perf_counter()-started)*1000)
        view={'revision':record['revision'] if record else 0,'workspace_generation':str(generation),
            'summary':summary,
            'checkup':build_checkup(included,summary,record.get('reviewed_findings',[]) if record else []),
            'imports':[{'source_sha256':s['source_sha256'],'account_alias':s['account_alias'],'account_type':s['account_type'],
                'extraction':s['extraction'],'row_count':len(s['entries']),'excluded':s['source_sha256'] in record.get('excluded',[]),
                **self.import_checks(tenant,generation,s)} for s in record['statements']] if record else [],
            'raw_file_stored':False,'payment_authorized':False,'updated_at':record.get('updated_at') if record else None}
        view['assistant_work']=build_assistant_work(view)
        if privacy_generation(self.service,tenant)!=generation:
            raise ValueError('Workspace changed during analysis; reload first')
        return view

    def import_checks(self,tenant,generation,statement):
        normalized=StatementImport.model_validate(statement)
        bound=verify_statement_extraction(normalized,tenant,generation,self.service.signer)
        # Legacy/manual imports remain usable, but supplied source facts are not
        # promoted to evidence unless Friday's extraction signature verifies.
        safe=normalized if bound else normalized.model_copy(update={'source_facts':None})
        return {'source_bound':bound,'reconciliation':reconcile_statement(safe)}

    def save(self,tenant,request):
        if not request.confirm_reviewed_and_store:raise ValueError('Review the rows and confirm private storage first')
        generation=privacy_generation(self.service,tenant)
        if request.workspace_generation!=str(generation):raise ValueError('Your workspace was cleared; refresh before saving')
        started=perf_counter()
        receipt=request.statement.extraction_receipt
        bound=verify_statement_extraction(request.statement,tenant,generation,self.service.signer)
        if (receipt is not None or request.statement.source_facts is not None) and not bound:
            record_stage('validation',ok=False,reason='rejected')
            raise ValueError('Extraction receipt does not match this workspace or statement. Prepare the original file again.')
        checks=reconcile_statement(request.statement)
        if bound and checks['overall_status']=='MISMATCH':
            record_stage('reconciliation',ok=False,reason='mismatch')
            raise ValueError('Statement rows conflict with declared source totals or coverage. Nothing was saved; use a complete, clearer export.')
        record_stage('reconciliation',ok=True,reason='accepted' if checks['overall_status']=='CONSISTENT' else 'insufficient_data')
        record_stage('validation',ok=True,reason='accepted',duration_ms=(perf_counter()-started)*1000)
        statement=request.statement.model_dump(mode='json',exclude_none=True)
        # Every stored import is user-reviewed data, not bank-authenticated evidence.
        def update(old):
            old=old if old and old['generation']==generation else None
            if old:
                existing=next((s for s in old['statements'] if s['source_sha256']==statement['source_sha256']),None)
                if existing:
                    if StatementImport.model_validate(existing).model_dump(mode='json',exclude_none=True)!=statement:raise ValueError('This source was already imported with different details; do not count it twice')
                    return old
            if request.expected_revision!=(old['revision'] if old else 0):raise ValueError('Statements changed in another session; reload before saving')
            result=deepcopy(old) if old else {'generation':generation,'revision':0,'statements':[]}
            if any(s['account_alias']==statement['account_alias'] and s['account_type']!=statement['account_type'] for s in result['statements']):raise ValueError('This account nickname already identifies a different account type')
            if len(result['statements'])>=10 or sum(len(s['entries']) for s in result['statements'])+len(statement['entries'])>2000:raise ValueError('Demo limit: 10 imports / 2,000 rows; no saved history was discarded')
            result['statements'].append(statement);result['revision']+=1
            result['updated_at']=datetime.now(timezone.utc).isoformat()
            if len(json.dumps(result).encode())>800000:raise ValueError('Normalized statement history exceeds the storage limit')
            return result
        if self.service.durable.mode=='FIRESTORE_TRANSACTIONAL':record=self.service.durable.update_portfolio(tenant,generation,update)
        else:
            with self.service.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if privacy_generation(self.service,tenant,db)!=generation:raise ValueError('Workspace was cleared while saving')
                old=db.execute('SELECT record FROM friday_portfolio WHERE tenant=?',(tenant,)).fetchone()
                record=update(json.loads(old[0]) if old else None)
                db.execute('INSERT OR REPLACE INTO friday_portfolio VALUES (?,?)',(tenant,json.dumps(record)))
        record_stage('persistence',ok=True,reason='accepted')
        return self.view(tenant,record)

    def model_context(self,tenant,view=None):
        from .friday_cashflow import _model_amounts
        view=view if view is not None else self.view(tenant)
        if not view['summary']['transaction_count']:return {}
        summary=deepcopy(view['summary'])
        summary.pop('entries',None)
        result=_model_amounts({'evidence_id':'statements:current','updated_at':view['updated_at'],
                              'source_revision':view['revision'],**summary})
        result['automatic_checkup']=checkup_model_context(view['checkup'])
        return result

    def review_finding(self,tenant,request):
        """Recoverable acknowledgement only. Never changes a transaction/label.

        Recompute membership in the tenant's current analysis inside the same
        storage transaction. Stale clicks and other tenants' IDs are rejected.
        """
        generation=privacy_generation(self.service,tenant)
        if request.workspace_generation!=str(generation):raise ValueError('Workspace was cleared; reload first')
        def update(old):
            if not old or old['generation']!=generation:raise ValueError('No saved statement history')
            if old['revision']!=request.expected_revision:raise ValueError('Statement history changed; reload first')
            included=[s for s in old['statements'] if s['source_sha256'] not in old.get('excluded',[])]
            checks=build_checkup(included,summarize_statements(included))
            if request.finding_id not in {f['finding_id'] for f in checks['findings']}:
                raise ValueError('Finding is not in this current analysis')
            reviewed=set(old.get('reviewed_findings',[]))
            if (request.finding_id in reviewed)==request.reviewed:return old
            if request.reviewed:reviewed.add(request.finding_id)
            else:reviewed.discard(request.finding_id)
            result=deepcopy(old);result['reviewed_findings']=sorted(reviewed);result['revision']+=1
            result['updated_at']=datetime.now(timezone.utc).isoformat();return result
        if self.service.durable.mode=='FIRESTORE_TRANSACTIONAL':record=self.service.durable.update_portfolio(tenant,generation,update)
        else:
            with self.service.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if privacy_generation(self.service,tenant,db)!=generation:raise ValueError('Workspace was cleared while reviewing')
                old=db.execute('SELECT record FROM friday_portfolio WHERE tenant=?',(tenant,)).fetchone()
                record=update(json.loads(old[0]) if old else None)
                db.execute('INSERT OR REPLACE INTO friday_portfolio VALUES (?,?)',(tenant,json.dumps(record)))
        return self.view(tenant,record)

    def set_visibility(self,tenant,request):
        generation=privacy_generation(self.service,tenant)
        if request.workspace_generation!=str(generation):raise ValueError('Workspace was cleared; refresh first')
        def update(old):
            if not old or old['generation']!=generation:raise ValueError('No saved statement history')
            if not any(s['source_sha256']==request.source_sha256 for s in old['statements']):raise ValueError('Statement is not in this workspace')
            excluded=set(old.get('excluded',[]))
            if (request.source_sha256 in excluded)==request.excluded:return old
            if old['revision']!=request.expected_revision:raise ValueError('Statement history changed; reload first')
            if request.excluded:excluded.add(request.source_sha256)
            else:excluded.discard(request.source_sha256)
            result=deepcopy(old);result['excluded']=sorted(excluded);result['revision']+=1
            result['updated_at']=datetime.now(timezone.utc).isoformat();return result
        if self.service.durable.mode=='FIRESTORE_TRANSACTIONAL':record=self.service.durable.update_portfolio(tenant,generation,update)
        else:
            with self.service.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if privacy_generation(self.service,tenant,db)!=generation:raise ValueError('Workspace was cleared while changing visibility')
                old=db.execute('SELECT record FROM friday_portfolio WHERE tenant=?',(tenant,)).fetchone()
                record=update(json.loads(old[0]) if old else None)
                db.execute('INSERT OR REPLACE INTO friday_portfolio VALUES (?,?)',(tenant,json.dumps(record)))
        return self.view(tenant,record)

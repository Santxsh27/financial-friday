"""Conservative app-wide admission counters, not a Google billing hard cap."""
from datetime import datetime, timezone
import os

LIMITS = {'ocr_pages':100, 'recovery_jobs':50}


def reserve_resource(service, purpose, units):
    if purpose not in LIMITS or type(units) is not int or units < 1:
        raise ValueError('Invalid resource reservation')
    limit = int(os.getenv('FRIDAY_'+purpose.upper()+'_DAILY_LIMIT', str(LIMITS[purpose])))
    if not 1 <= limit <= LIMITS[purpose]:
        raise ValueError('Resource allowance may only be lowered from the conservative default')
    day = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if service.durable.mode == 'FIRESTORE_TRANSACTIONAL':
        if not hasattr(service.durable, 'reserve_resource'):
            raise ValueError('Atomic resource admission is unavailable')
        return service.durable.reserve_resource(purpose, day, units, limit)
    with service.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS friday_resource_usage (purpose TEXT, day TEXT, used INTEGER NOT NULL, PRIMARY KEY(purpose,day))')
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT used FROM friday_resource_usage WHERE purpose=? AND day=?', (purpose, day)).fetchone()
        used = row[0] if row else 0
        if used + units > limit:
            raise ValueError('Daily '+purpose.replace('_',' ')+' demo allowance reached. No additional cloud work was admitted.')
        db.execute('INSERT INTO friday_resource_usage VALUES (?,?,?) ON CONFLICT(purpose,day) DO UPDATE SET used=excluded.used', (purpose,day,used+units))
    return {'used':used+units, 'limit':limit, 'day':day}

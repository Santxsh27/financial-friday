"""Read-only join of complete bounded claims with artificial provider outcomes."""
from carapace_core.friday_obligations import obligation_board
from carapace_core.canonical import sha256_hex
from .friday_workspace import financial_workspace


def financial_obligations(service, reviews, tenant):
    snapshot = reviews.safety_snapshot(tenant)
    board = obligation_board(snapshot['board'], financial_workspace(service, tenant), snapshot['version'])
    followups = getattr(service, 'followups', None)
    return followups.enrich(tenant, board) if followups else board


def recorded_obligation_result(service, reviews, tenant, identity):
    workspace = financial_workspace(service, tenant)
    snapshot = reviews.safety_snapshot(tenant)
    item = next((item for item in obligation_board(snapshot['board'], workspace, snapshot['version'])['items']
                 if item['obligation_id'] == identity), None)
    if item is None:
        raise KeyError(identity)
    bill = next((bill for bill in workspace['bills'] if bill['bill_reference'] == item['bill_reference']), None)
    result = {'scope':'ARTIFICIAL_OBLIGATION_RESULT', 'read_only':True, 'money_moved':False,
              'new_payment_created':False, 'external_settlement_verified':False,
              'state':'OUTCOME_UNKNOWN', 'message':'No matching internal payment evidence was verified. This read does not retry a payment.'}
    if not bill:
        return result
    goal = 'goal-bill-' + sha256_hex({'tenant':tenant,'provider':bill['provider_id'],'bill':bill['bill_reference']})[:24]
    receipt = service._receipt_by_identity(tenant, goal, {'authoritative_bill':bill})
    if not receipt:
        return result
    try:
        valid = service.signer.verify_for_key(receipt['payload'],receipt['signature'],receipt['key_id']) and all(
            receipt['payload'].get(field) == value for field, value in {
                'tenant_id':tenant,'provider_id':bill['provider_id'],'payee_id':bill['payee_id'],
                'amount_minor':bill['amount_minor'],'currency':bill['currency'],
                'scope':'FINANCIAL_FRIDAY_ARTIFICIAL_MONEY'}.items())
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        return result | {'state':'EVIDENCE_CONFLICT','message':'The receipt does not match the current obligation. No new debit was submitted.'}
    return result | {'state':'RECORDED_PAYMENT_VERIFIED','message':'The signed internal artificial payment matches this obligation. Reopening made no new payment.',
        'bill_reference':bill['bill_reference'],'supplier':bill['provider_name'],
        'amount_minor':bill['amount_minor'],'currency':bill['currency'],'recipient':bill['payee_id'],
        'operation_id':receipt['payload']['operation_id'],'key_id':receipt['key_id'],'signature_verified':True,
        'document_checks':item['checks']}

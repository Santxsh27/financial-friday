"""Outcome-oriented projection. Claims never become provider or settlement proof.

No model, signing or payment tools here. Every next step is derived from bounded
evidence; the execution gate remains the only authority for an artificial debit.
"""
from .canonical import sha256_hex
from .friday_bill_plan import plan_bills
from .friday_review import normalize
from .friday_task_guard import related_claims, claim_gate_reasons


def obligation_id(kind, identity):
    return 'obligation_' + sha256_hex({'kind': kind, 'identity': identity})[:32]


def match_case_bill(case, bills):
    """Require exact supplier AND reference. A copied reference is insufficient."""
    matches = [bill for bill in bills if case.get('reference') and case.get('supplier')
               and normalize(case['reference']) == normalize(bill['bill_reference'])
               and normalize(case['supplier']) == normalize(bill['provider_name'])]
    return matches[0] if len(matches) == 1 else None


def obligation_board(board, workspace, evidence_version):
    plan = plan_bills(workspace)
    eligible = {row['bill_reference'] for row in plan['selected']} if plan['state'] == 'PLANNED' else set()
    items, linked = [], set()
    for case in board['cases']:
        bill = match_case_bill(case, workspace['bills'])
        if bill:
            linked.add((bill['provider_id'], bill['bill_reference']))
        items.append(_item(board, case, bill, eligible, plan['state']))
    for bill in workspace['bills']:
        if (bill['provider_id'], bill['bill_reference']) not in linked:
            items.append(_item(board, None, bill, eligible, plan['state']))
    priority = {'DETAILS_CONFLICT': 0, 'VERIFY_STATUS': 1, 'NEEDS_DETAILS': 2,
                'VERIFY_PROVIDER': 3, 'REVIEW_RULES': 4, 'READY_TO_PREPARE': 5, 'RECORDED_COMPLETE': 6}
    items.sort(key=lambda item: (priority[item['state']], item.get('due_date') or '9999', item['obligation_id']))
    counts = {state: sum(item['state'] == state for item in items) for state in priority}
    return {'scope': 'FINANCIAL_OBLIGATION_WORKSPACE', 'read_only': True, 'money_moved': False,
            'payment_authorized': False, 'items': items, 'summary': counts,
            'evidence_version': evidence_version, 'coverage': {
                'documents_checked': board['document_count'], 'document_limit': 1000,
                'provider_records_checked': len(workspace['bills']),
                'provider_coverage_complete': not workspace['coverage']['may_be_truncated'],
                'snapshot_atomic': False},
            'limits': ['Saved document claims are not merchant authentication or bank settlement.',
                       'Provider records and completed payments are artificial, same-operator data.',
                       'No bank, email or SMS monitoring. Preparation calls Gemini only after you choose it.',
                       'Rules, provider details and complete bounded evidence are rechecked before execution.']}


def _item(board, case, bill, eligible, plan_state):
    related = related_claims(board, bill['bill_reference']) if bill else None
    reasons = claim_gate_reasons(related, bill) if bill else []
    checks = sorted(set((case or {}).get('checks', []) + reasons))
    state, action = 'VERIFY_PROVIDER', 'PREPARE_VERIFICATION'
    why = 'The document describes an obligation, but no exact supplier-and-reference provider record is connected.'
    next_step = 'Prepare the precise questions for a provider contact you independently know. Nothing is sent.'
    if case and case['state'] == 'INCOMPLETE_REVIEW':
        state, action = 'NEEDS_DETAILS', 'ADD_DETAILS'
        why = 'The supplied evidence does not establish enough details to identify an obligation.'
        next_step = 'Add the supplier, reference, currency and amount from a readable source. Never include payment secrets.'
    elif case and case['state'] in {'RECEIPT_MATCHED_CLAIM', 'RECORDED_PAYMENT_CLAIM'}:
        state = 'VERIFY_STATUS'
        why = 'A supplied receipt reports a payment. That is not independently confirmed settlement.'
        next_step = 'Check the recorded status before paying again; prepare a provider-status request.'
    elif (case and case['state'] == 'CONFLICT_REVIEW') or 'PROVIDER_CLAIM_CONFLICT' in reasons:
        state = 'DETAILS_CONFLICT'
        why = 'Financial details disagree. A correction, partial payment or scam may explain this; Friday cannot decide authenticity.'
        next_step = 'Prepare a request for the correct outstanding amount, recipient and payment status. Do not pay the conflicting request.'
    if bill:
        if bill['status'] == 'RECORDED_PAID':
            state, action = 'RECORDED_COMPLETE', 'CHECK_RECORDED_RESULT'
            why = 'An existing signed artificial-payment journal matches this provider bill. No additional debit is needed.'
            next_step = 'Open the recorded result. External bank settlement remains unverified.'
            if checks:
                why += ' Other document claims still need review; reopening the result does not clear them.'
        elif bill['status'] == 'RECEIPT_CONFLICT':
            state, action = 'VERIFY_STATUS', 'PREPARE_VERIFICATION'
            why = 'The existing payment receipt does not match the current provider record. A new debit must not be used as recovery.'
        elif checks:
            if state not in {'DETAILS_CONFLICT', 'VERIFY_STATUS'}:
                state = 'VERIFY_PROVIDER'
                why = 'Document evidence has missing or unsupported details. The provider match does not clear those gaps.'
        elif bill['bill_reference'] in eligible and plan_state == 'PLANNED':
            state, action = 'READY_TO_PREPARE', 'PREPARE_PAYMENT'
            why = 'This artificial provider bill fits the displayed reserve and payment limits. Gemini still needs to prepare it; no payment is authorised.'
            next_step = 'Prepare this exact bill, review the proposed action, then explicitly confirm artificial execution.'
        else:
            state, action = 'REVIEW_RULES', 'PREPARE_VERIFICATION'
            why = 'An increase, saved limit, reserve or incomplete planning coverage prevents this bill joining the current plan.'
            next_step = 'Ask Friday to explain the constraint. Changing a rule is your decision, not an automatic workaround.'
    kind = 'review' if case else 'provider'
    identity = case['case_id'] if case else bill['provider_id'] + ':' + bill['bill_reference']
    return {'obligation_id': obligation_id(kind, identity), 'source_case_id': case['case_id'] if case else None,
            'bill_reference': bill['bill_reference'] if bill else None,
            'supplier': case['supplier'] if case else bill['provider_name'],
            'reference': case['reference'] if case else bill['bill_reference'],
            'amount_minor': case['amount_minor'] if case else bill['amount_minor'],
            'currency': case['currency'] if case else bill['currency'],
            'due_date': case.get('due_date') if case else bill['due_date'],
            'state': state, 'action': action, 'why': why, 'next_step': next_step, 'checks': checks,
            'comparisons': _comparisons(related, bill),
            'verification_questions': _questions(case),
            'document_ids': case['document_ids'] if case else [],
            'provider_evidence': 'ARTIFICIAL_RECORD_MATCH' if bill else 'NOT_CONNECTED',
            'recipient_ownership_verified': False, 'external_settlement_verified': False,
            'payment_authorized': False}


def _comparisons(related, bill):
    if not related or not bill:
        return []
    comparisons = []
    for document in related['documents']:
        analysis = document['analysis']; facts = analysis['facts']
        quoted = {quote['field'] for quote in facts['quotes']}
        for field, claim, provider in [('amount_minor', analysis['amount_minor'], bill['amount_minor']),
                                       ('currency', facts['currency'], bill['currency']),
                                       ('recipient', facts['payee'] if 'payee' in quoted else None, bill['payee_id'])]:
            matches = claim is not None and (normalize(claim) == normalize(provider) if field == 'recipient' else claim == provider)
            comparisons.append({'field':field, 'document_id':document['review_id'],
                                'claim':claim, 'artificial_provider_value':provider,
                                'state':'MATCHED_CLAIM' if matches else 'NOT_ESTABLISHED' if claim is None else 'DIFFERENT'})
    return comparisons


def _questions(case):
    checks = set((case or {}).get('checks', []))
    questions = ['What is the current outstanding amount and currency?',
                 'What is the official payment recipient for this obligation?',
                 'Has any payment already been recorded against this reference?']
    if checks & {'AMOUNT_CONFLICT', 'LINE_ARITHMETIC_MISMATCH', 'TOTAL_ARITHMETIC_MISMATCH'}:
        questions.insert(0, 'Was this invoice corrected, partly paid, or changed by tax or fees? Please provide the breakdown.')
    if 'RECIPIENT_CONFLICT' in checks:
        questions.insert(0, 'Was the recipient changed officially? Please verify through our independently known channel.')
    return questions

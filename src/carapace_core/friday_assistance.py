"""Prepare the next private review steps from the current statement checkup.

This is derived work, not a background monitor or financial executor. No source
label, review acknowledgement, bank state or external service is changed.
"""
from copy import deepcopy
from hashlib import sha256
import json

from .friday_checkup import prepare_enquiry

ENGINE_VERSION = 'ASSISTANT_WORK_1'
MAX_ITEMS = 8
MAX_ARTIFACT_ROWS = 30


def _money(amount):
    return f'INR {amount // 100:,}.{amount % 100:02d}'


def _source_lines(rows):
    lines = ['Source entries (statement text is quoted data):']
    for row in rows[:MAX_ARTIFACT_ROWS]:
        description = json.dumps(' '.join(row['description'].split()), ensure_ascii=False)
        alias = json.dumps(row['account_alias'], ensure_ascii=False)
        lines.append(f"{row['date']} | {description} | debit {_money(row['debit_minor'])} | "
                     f"credit {_money(row['credit_minor'])} | account {alias} | "
                     f"source {row['source_sha256']} | row {row['source_row']}")
    if len(rows) > MAX_ARTIFACT_ROWS:
        lines.append(f'{len(rows) - MAX_ARTIFACT_ROWS} further entries remain in the private evidence view.')
    return lines


def _comparison_worksheet(finding):
    rows = finding['evidence']
    files = len({row['source_sha256'] for row in rows})
    lines = ['REPEATED ENTRY COMPARISON — prepared for your review', '',
             f'{len(rows)} matching recorded occurrences across {files} source file(s).',
             'The date, account nickname, description and amount match. This does not establish a duplicate bank charge.',
             f"Debits currently counted: {_money(sum(row['debit_minor'] for row in rows))}",
             f"Credits currently counted: {_money(sum(row['credit_minor'] for row in rows))}", '',
             *_source_lines(rows), '',
             'Compare these source rows with the original export(s). Check whether they describe one transaction repeated in exports or separate legitimate transactions.',
             'If an entire import overlaps, you can review excluding that import in the app. Friday has not chosen an import or removed any row.',
             'Your conclusion: ____________________', '',
             'Prepared from user-supplied statements. All rows remain counted; no complaint was sent or financial record changed.']
    return '\n'.join(lines)


def _classification_worksheet(finding):
    rows = finding['evidence']
    lines = ['CREDIT CLASSIFICATION WORKSHEET — prepared for your review', '',
             f"Recorded unclear credits: {_money(sum(row['credit_minor'] for row in rows))}",
             'These entries remain UNCLEAR and are not counted as identified income. Friday has not inferred their source or assigned a new label.', '',
             *_source_lines(rows), '',
             'For each entry, check the sender or original record and note the source you can confirm.',
             'Source row / confirmed source / supporting record: ____________________',
             'Leave an entry unclear when you cannot confirm it. Marking this worksheet reviewed does not relabel transactions.', '',
             'Prepared privately from user-supplied statements. No income assumption, bank enquiry or financial action was made.']
    return '\n'.join(lines)


def build_assistant_work(view):
    """Finish bounded preparation for open findings in their existing order.

    ``remaining_count`` counts open findings beyond this prepared batch;
    ``open_count`` includes all findings still awaiting the user's review.
    Identities survive acknowledgements/reordering and change with the finding's
    evidence. Revision/generation bind the batch to the current private view.
    """
    checkup = view['checkup']
    findings = [finding for finding in checkup['findings'] if not finding['reviewed']]
    items = []
    for finding in findings[:MAX_ITEMS]:
        kind = finding['kind']
        if kind == 'REPEATED_ENTRY':
            filename = 'friday-entry-comparison.txt'
            content = _comparison_worksheet(finding)
        elif kind == 'UNCLEAR_CREDIT':
            filename = 'friday-credit-classification.txt'
            content = _classification_worksheet(finding)
        else:
            filename = 'friday-unsent-enquiry.txt'
            content = prepare_enquiry(finding)
        identity = sha256(f"{ENGINE_VERSION}:{finding['finding_id']}".encode()).hexdigest()[:24]
        items.append({'item_id': 'work_' + identity,
                      'finding_id': finding['finding_id'], 'kind': kind,
                      'title': finding['title'], 'status': 'PREPARED_FOR_REVIEW',
                      'amount_minor': finding['amount_minor'],
                      'evidence_count': finding['evidence_count'],
                      'evidence': deepcopy(finding['evidence']),
                      'artifact': {'format': 'text/plain', 'filename': filename, 'content': content}})
    return {'scope': 'FRIDAY_ASSISTANT_WORK',
            'source_revision': view['revision'], 'workspace_generation': view['workspace_generation'],
            'source_fingerprint': checkup['source_fingerprint'],
            'next_item': items[0] if items else None, 'items': items,
            'prepared_count': len(items), 'remaining_count': len(findings) - len(items),
            'open_count': len(findings), 'checks_completed': len(checkup['checks_completed']),
            'transaction_count': checkup['transaction_count'],
            'model_calls': 0, 'money_moved': False, 'external_actions': 0}

"""Offline, developer-authored synthetic review-finding evaluation; never fraud validation.

Run: PYTHONPATH=src .venv/bin/python tools/evaluate_statement_checkup.py
Use --split all --include-evaluation to expose the authored evaluation split.
The author has seen these labels: this first corpus is not a blind holdout.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

from carapace_core.friday_checkup import ENGINE_VERSION, build_checkup
from carapace_core.friday_portfolio import StatementImport, classify, summarize_statements


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = ROOT / 'examples/evaluation/statement_checkup_inputs.json'
DEFAULT_LABELS = ROOT / 'examples/evaluation/statement_checkup_labels.json'
KINDS = ('REPEATED_ENTRY', 'RECURRING_INCREASE', 'UNUSUAL_AMOUNT', 'FEES',
         'UNCLEAR_CREDIT', 'REFUND_AMBIGUITY', 'REFUND_PARTIAL_TRAIL', 'REFUND_LINK_WITHHELD')
TARGETS = {
    'REPEATED_ENTRY': 'An unexplained matching or plausibly duplicated entry needs follow-up; confirmed separate purchases do not.',
    'RECURRING_INCREASE': 'An unexplained increase in the same regular obligation needs follow-up, including known changed bank narration.',
    'UNUSUAL_AMOUNT': 'An unexplained exceptional expense with sufficient relevant history needs follow-up; a supplied planned purchase does not.',
    'FEES': 'Recorded fees whose purpose or authorisation still needs review; already explained fees do not.',
    'UNCLEAR_CREDIT': 'A credit source is unresolved; supplied evidence of borrowing, refund, transfer or salary resolves this target.',
    'REFUND_AMBIGUITY': 'Several purchase allocations remain possible and require confirmation.',
    'REFUND_PARTIAL_TRAIL': 'An expected purchase return remains only partly reconciled and needs confirmation; this does not establish money owed.',
    'REFUND_LINK_WITHHELD': 'A refund cannot be reconciled from supplied records and its relationship remains unresolved.',
}
NUMERIC_TARGETS = {'identified_income_minor', 'classified_spending_minor', 'transaction_count',
                   'spending_change_present', 'monthly_months'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value):
    return sha256(canonical(value)).hexdigest()


def _read(path):
    raw = Path(path).read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('Synthetic fixture must not exceed 2 MB')
    return json.loads(raw), sha256(raw).hexdigest()


def load_cases(inputs_path=DEFAULT_INPUTS, labels_path=DEFAULT_LABELS):
    """Join static labels by frozen case ID, never infer labels from production output."""
    inputs, input_hash = _read(inputs_path)
    labels, label_hash = _read(labels_path)
    if inputs.get('schema_version') != 1 or labels.get('schema_version') != 1:
        raise ValueError('Unsupported fixture schema')
    if inputs.get('synthetic') is not True or labels.get('synthetic') is not True:
        raise ValueError('Only explicitly synthetic fixtures are admitted')
    if inputs.get('dataset_id') != labels.get('dataset_id'):
        raise ValueError('Inputs and labels must name the same frozen dataset')
    if labels.get('finding_kinds') != list(KINDS):
        raise ValueError('Labels must explicitly name every supported finding kind')
    cases = inputs.get('cases', [])
    label_rows = labels.get('cases', [])
    if not 1 <= len(cases) <= 200 or len(label_rows) != len(cases):
        raise ValueError('Require 1–200 cases and exactly one separate label per case')
    ids = [case['id'] for case in cases]
    label_ids = [label['id'] for label in label_rows]
    if len(set(ids)) != len(ids) or len(set(label_ids)) != len(label_ids) or set(ids) != set(label_ids):
        raise ValueError('Case and label IDs must be unique and match exactly')
    by_id = {label['id']: label for label in label_rows}
    family_splits = {}
    fingerprints = {}
    joined = []
    for original in cases:
        case = deepcopy(original)
        label = by_id[case['id']]
        if case['split'] not in {'tuning', 'evaluation'}:
            raise ValueError('Unknown split')
        family = case['base_family_id']
        if family in family_splits and family_splits[family] != case['split']:
            raise ValueError('A base family cannot cross splits')
        family_splits[family] = case['split']
        row_ids = []
        for statement in case['statements']:
            for row in statement['rows']:
                if len(row) != 5 or not isinstance(row[0], str):
                    raise ValueError('Rows are [stable_id, ISO_date, description, debit_minor, credit_minor]')
                row_ids.append(row[0])
        if not row_ids or len(row_ids) > 2000 or len(row_ids) != len(set(row_ids)):
            raise ValueError('Require unique source row IDs and 1–2000 rows per case')
        # Catch exact row reuse even if source IDs, row IDs or aliases were renamed.
        fingerprint = digest(sorted(
            [(row[1], ' '.join(row[2].casefold().split()), row[3], row[4])
             for statement in case['statements'] for row in statement['rows']]))
        if fingerprint in fingerprints and fingerprints[fingerprint] != case['split']:
            raise ValueError('The same source case cannot cross splits')
        fingerprints[fingerprint] = case['split']
        expected = label['expected_findings']
        abstain = label.get('abstain', {})
        if set(expected) - set(KINDS) or set(abstain) - set(KINDS) or set(expected) & set(abstain):
            raise ValueError('Unknown or conflicting target labels')
        for evidence_groups in expected.values():
            if not evidence_groups:
                raise ValueError('Positive labels require pre-authored evidence groups')
            for group in evidence_groups:
                if not group or len(group) != len(set(group)) or set(group) - set(row_ids):
                    raise ValueError('Expected evidence must refer to unique known source rows')
        if any(not isinstance(reason, str) or not reason.strip() for reason in abstain.values()):
            raise ValueError('Every label abstention needs a reason')
        if set(label.get('numeric_expectations', {})) - NUMERIC_TARGETS:
            raise ValueError('Unknown numeric target')
        case['label'] = deepcopy(label)
        # Validate all input rows even when only one split will be evaluated.
        materialize(case)
        joined.append(case)
    for split in ('tuning', 'evaluation'):
        declared = inputs['split_protocol'][f'{split}_base_families']
        actual = {case['base_family_id'] for case in joined if case['split'] == split}
        if len(set(declared)) != len(declared) or set(declared) != actual:
            raise ValueError('Declared split lineage manifest must match actual base families')
    return joined, {
        'dataset_id': inputs['dataset_id'], 'inputs_sha256': input_hash, 'labels_sha256': label_hash,
        'label_origin': labels['label_origin'], 'review_status': labels['review_status'],
        'split_protocol': inputs['split_protocol'], 'base_family_splits': dict(sorted(family_splits.items())),
    }


def materialize(case):
    """Use the existing local classifier, then validate the production import contract."""
    statements = []
    source_ids = {}
    for source in case['statements']:
        source_hash = digest(source)
        entries = []
        for index, (row_id, day, description, debit, credit) in enumerate(source['rows'], 1):
            kind, category = classify(description, debit)
            entries.append({'date': day, 'description': description, 'debit_minor': debit,
                            'credit_minor': credit, 'source_row': index, 'kind': kind, 'category': category})
            source_ids[source_hash, index] = row_id
        value = {'source_sha256': source_hash, 'account_alias': source['account_alias'],
                 'account_type': source.get('account_type', 'BANK'), 'entries': entries, 'extraction': 'CSV_EXACT'}
        statements.append(StatementImport.model_validate(value).model_dump(mode='json'))
    return statements, source_ids


def binary_metrics(decisions):
    """One decision is (pre-authored bool-or-None, predicted bool-or-None).

    None labels are author abstentions, not declared production abstentions.
    None predictions represent runtime failure and are reported as unresolved.
    Undefined ratios remain JSON null, including precision for zero alerts.
    """
    counts = Counter(tp=0, fp=0, tn=0, fn=0, label_abstentions=0,
                     runtime_abstentions=0, unresolved_positives=0, unresolved_negatives=0,
                     alerts_on_abstained_labels=0, labelled_positives=0, labelled_negatives=0)
    for expected, predicted in decisions:
        if expected is not None and type(expected) is not bool:
            raise ValueError('Expected label must be bool or None')
        if predicted is not None and type(predicted) is not bool:
            raise ValueError('Prediction must be bool or None')
        if expected is None:
            counts['label_abstentions'] += 1
            counts['alerts_on_abstained_labels'] += predicted is True
            continue
        counts['labelled_positives' if expected else 'labelled_negatives'] += 1
        if predicted is None:
            counts['runtime_abstentions'] += 1
            counts['unresolved_positives' if expected else 'unresolved_negatives'] += 1
            continue
        counts['tp' if expected and predicted else 'fn' if expected else 'fp' if predicted else 'tn'] += 1
    def ratio(numerator, denominator):
        return round(numerator / denominator, 6) if denominator else None
    return {**counts, 'decision_count': sum(counts[k] for k in ('tp','fp','tn','fn','label_abstentions','runtime_abstentions')),
            'scored_decisions': sum(counts[k] for k in ('tp','fp','tn','fn')),
            'precision': ratio(counts['tp'], counts['tp'] + counts['fp']),
            'recall': ratio(counts['tp'], counts['tp'] + counts['fn']),
            'false_positive_rate': ratio(counts['fp'], counts['fp'] + counts['tn']),
            'missed_findings': counts['fn'],
            'recall_including_unresolved_as_missed': ratio(counts['tp'], counts['labelled_positives'])}


def _decisions(rows, baseline=False, kind=None):
    return [(decision['expected'], False if baseline else decision['predicted'])
            for row in rows for decision in row['decisions'] if kind is None or decision['kind'] == kind]


def _aggregate(rows, baseline=False):
    def any_decision(row):
        labels = [decision['expected'] for decision in row['decisions']]
        expected = True if True in labels else None if None in labels else False
        predicted = False if baseline else None if row.get('error') else bool(row['findings'])
        return expected, predicted
    return {'cases': len(rows), 'case_kind': binary_metrics(_decisions(rows, baseline)),
            'any_finding_per_case': binary_metrics([any_decision(row) for row in rows]),
            'by_kind': {kind: binary_metrics(_decisions(rows, baseline, kind)) for kind in KINDS}}


def evaluate(cases, manifest, predictor=None):
    predictor = build_checkup if predictor is None else predictor
    results = []
    for case in cases:
        label = case['label']
        row = {key: case[key] for key in ('id', 'split', 'family', 'base_family_id', 'context')}
        row.update(input_sha256=digest({k: v for k, v in case.items() if k != 'label'}),
                   label_sha256=digest(label), findings=[], numeric_checks=[], evidence_checks=[])
        try:
            statements, ids = materialize(case)
            summary = summarize_statements(statements)
            checkup = predictor(statements, summary)
            if set(finding['kind'] for finding in checkup['findings']) - set(KINDS):
                raise ValueError('Unknown production kind; update the explicit label contract before scoring')
            for finding in checkup['findings']:
                row['findings'].append({'kind': finding['kind'], 'finding_id': finding['finding_id'],
                    'amount_minor': finding['amount_minor'],
                    'row_ids': sorted(ids[(ref['source_sha256'], ref['source_row'])] for ref in finding['evidence']),
                    'descriptions': [ref['description'] for ref in finding['evidence']]})
            observed = {'identified_income_minor': summary['totals']['identified_income_minor'],
                        'classified_spending_minor': summary['totals']['classified_spending_minor'],
                        'transaction_count': checkup['transaction_count'],
                        'spending_change_present': checkup['spending_change'] is not None,
                        'monthly_months': [month['month'] for month in summary['monthly']]}
            for name, expected in sorted(label.get('numeric_expectations', {}).items()):
                row['numeric_checks'].append({'target': name, 'expected': expected,
                    'actual': observed[name], 'matched': type(observed[name]) is type(expected) and observed[name] == expected})
            for kind, groups in label['expected_findings'].items():
                actual = [finding['row_ids'] for finding in row['findings'] if finding['kind'] == kind]
                for group in groups:
                    row['evidence_checks'].append({'kind': kind, 'expected_row_ids': sorted(group),
                        'exact_evidence_found': sorted(group) in actual})
        except Exception as error:
            row['error'] = {'type': type(error).__name__, 'detail': str(error)}
        predicted = {finding['kind'] for finding in row['findings']}
        row['decisions'] = [{'kind': kind,
            'expected': None if kind in label.get('abstain', {}) else kind in label['expected_findings'],
            'predicted': None if row.get('error') else kind in predicted,
            **({'abstention_reason': label['abstain'][kind]} if kind in label.get('abstain', {}) else {})}
            for kind in KINDS]
        results.append(row)
    mismatches = []
    for row in results:
        for decision in row['decisions']:
            if decision['expected'] is None or decision['predicted'] is None or decision['expected'] == decision['predicted']:
                continue
            mismatches.append({'case_id': row['id'], 'family': row['family'], 'kind': decision['kind'],
                'type': 'FALSE_POSITIVE' if decision['predicted'] else 'MISSED_FINDING', 'context': row['context'],
                'predicted_findings': [f for f in row['findings'] if f['kind'] == decision['kind']]})
    source_files = ('src/carapace_core/friday_checkup.py', 'src/carapace_core/friday_portfolio.py',
                    'src/carapace_core/friday_narration.py',
                    'src/carapace_core/friday_refund_shield.py', 'tools/evaluate_statement_checkup.py')
    numeric = [check for row in results for check in row['numeric_checks']]
    evidence = [check for row in results for check in row['evidence_checks']]
    planned_numeric = sum(len(case['label'].get('numeric_expectations', {})) for case in cases)
    planned_evidence = sum(len(groups) for case in cases for groups in case['label']['expected_findings'].values())
    return {
        'schema_version': 1, 'status': 'DEVELOPER_AUTHORED_SYNTHETIC_FIRST_PASS',
        'evaluated_condition': 'Review-worthy follow-up under the pre-authored supplied context, never real fraud, entitlement or confirmed error.',
        'independent_validation_completed': False, 'blinded_validation_completed': False,
        'label_access': 'The authoring agent has seen all labels. Evaluation here means an authored split, not an unseen holdout.',
        'unit': 'One binary case × finding-kind presence decision; 8 explicit kinds per case. Multiple same-kind findings count once. Exact evidence coverage is reported separately.',
        'negative_label_rule': 'Kinds absent from expected_findings are explicitly negative except kinds listed in abstain.',
        'ratio_definitions': {'precision': 'TP/(TP+FP)', 'recall': 'TP/(TP+FN)',
            'false_positive_rate': 'FP/(FP+TN)', 'undefined_ratios': 'null; never replace no denominator with zero',
            'abstentions': 'Author-labelled unknowable targets and runtime failures are excluded from conditional ratios and counted separately; runtime failures also count against recall_including_unresolved_as_missed.'},
        'target_definitions': TARGETS, 'manifest': manifest,
        'frozen_case_ids': [case['id'] for case in cases],
        'selected_splits': sorted({case['split'] for case in cases}),
        'engine_version': ENGINE_VERSION,
        'source_sha256': {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in source_files},
        'offline': True, 'model_calls': 0, 'network_calls': 0, 'user_records': 0,
        'overall': _aggregate(results),
        'by_split': {split: _aggregate([row for row in results if row['split'] == split]) for split in sorted({row['split'] for row in results})},
        'by_family': {family: _aggregate([row for row in results if row['family'] == family]) for family in sorted({row['family'] for row in results})},
        'baseline': {'name': 'ALWAYS_NO_FINDING', 'purpose': 'Non-learned prevalence control on exactly the same labels; not a prior production model.', **_aggregate(results, baseline=True)},
        'numeric_invariants': {'planned_checks': planned_numeric, 'checks': len(numeric),
            'unresolved_checks': planned_numeric - len(numeric), 'passed': sum(check['matched'] for check in numeric),
            'mismatches': [dict(case_id=row['id'], **check) for row in results for check in row['numeric_checks'] if not check['matched']]},
        'evidence_localisation': {'expected_groups': planned_evidence, 'evaluated_groups': len(evidence),
            'unresolved_groups': planned_evidence - len(evidence), 'exact_groups_found': sum(check['exact_evidence_found'] for check in evidence)},
        'runtime_errors': [dict(case_id=row['id'], **row['error']) for row in results if row.get('error')],
        'mismatches': mismatches,
        'false_positive_examples': [m for m in mismatches if m['type'] == 'FALSE_POSITIVE'],
        'missed_finding_examples': [m for m in mismatches if m['type'] == 'MISSED_FINDING'],
        'limitations': [
            'Small synthetic developer/agent-authored convenience sample, not independent, representative or bank-validated data; no confidence or real-world fraud claims.',
            'Supplied explanatory context is available to labels but production checkup accepts classified rows only. Context-aware false positives are intentional task gaps.',
            'Bank-style strings are artificial examples, not evidence of real institution format coverage. Account aliases do not establish ownership.',
            'Family disjointness is enforced by declared base_family_id and exact source hash; semantic independence of different families requires human review.',
            'Presence metrics can hide incorrect localisation or several alerts in a kind; inspect exact evidence coverage and all raw findings.',
            'No production parameter was changed. Do not tune on this report and then describe this same split as held out.',
            'For a future blind test, a teammate must review labels and create new unseen base families, freeze hashes, seal labels from implementers, run once, and record label access before interpreting results.',
        ], 'results': results,
    }


def compare_reports(report, previous):
    """Compare only frozen identical cohorts/labels; never imply an unmeasured improvement."""
    for key in ('inputs_sha256', 'labels_sha256'):
        if report['manifest'][key] != previous.get('manifest', {}).get(key):
            raise ValueError('Comparison requires identical frozen inputs and labels')
    if report['frozen_case_ids'] != previous.get('frozen_case_ids'):
        raise ValueError('Comparison requires identical ordered selected case IDs')
    current = report['overall']['case_kind']
    before = previous['overall']['case_kind']
    return {'reference_source_sha256': previous.get('source_sha256'),
            'counts_delta': {key: current[key] - before[key] for key in ('tp', 'fp', 'tn', 'fn', 'runtime_abstentions')},
            'interpretation': 'Measured count changes on this frozen authored corpus only; not independent evidence of improvement.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=DEFAULT_INPUTS)
    parser.add_argument('--labels', type=Path, default=DEFAULT_LABELS)
    parser.add_argument('--split', choices=('tuning', 'evaluation', 'all'), default='tuning')
    parser.add_argument('--include-evaluation', action='store_true', help='Explicitly unseal already-authored evaluation labels; no blind claim')
    parser.add_argument('--compare', type=Path, help='Compare an earlier report on exactly the same frozen corpus')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.split != 'tuning' and not args.include_evaluation:
        parser.error('evaluation/all requires --include-evaluation; this exposes authored evaluation labels')
    cases, manifest = load_cases(args.inputs, args.labels)
    selected = [case for case in cases if args.split == 'all' or case['split'] == args.split]
    if not selected:
        parser.error('Selected split has no cases')
    report = evaluate(selected, manifest)
    if args.compare:
        report['comparison'] = compare_reports(report, json.loads(args.compare.read_text()))
    rendered = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(rendered)
    else:
        sys.stdout.write(rendered)
    return 1 if report['runtime_errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())

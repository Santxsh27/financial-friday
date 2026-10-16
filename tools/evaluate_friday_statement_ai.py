"""Small production-path statement/chat AI smoke benchmark, offline by default.

Bundled responses are AUTHOR-WRITTEN SCORER CONTROLS, never model results.
Live: --run-live --max-model-calls N --project ID --model ID --token-stdin.
This runner has no executor, application credentials, bank data or network tools.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import statistics
import sys
from time import perf_counter
from types import SimpleNamespace

from carapace_ai.financial_friday import GeminiFinancialFridayPlanner
from carapace_ai.friday_chat import ChatAnswer, FridayChatRequest, answer_chat, chat_failure_category
from carapace_ai.friday_statements import ExtractedStatement, extract_statement
from carapace_api.friday_cashflow import _model_amounts
from carapace_core.friday_checkup import build_checkup, checkup_model_context
from carapace_core.friday_portfolio import StatementImport, classify, summarize_statements

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'examples/evaluation'
DEFAULT_INPUTS = DIRECTORY / 'statement_ai_inputs.json'
DEFAULT_LABELS = DIRECTORY / 'statement_ai_labels.json'
DEFAULT_RESPONSES = DIRECTORY / 'statement_ai_responses.json'
DEFAULT_PROTOCOL_V2 = DIRECTORY / 'statement_ai_protocol_v2.json'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value):
    return sha256(canonical(value)).hexdigest()


def _load(path):
    raw = Path(path).read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError('Only bounded synthetic fixtures up to 1 MB are admitted')
    return json.loads(raw), sha256(raw).hexdigest()


def load_corpus(inputs_path=DEFAULT_INPUTS, labels_path=DEFAULT_LABELS, responses_path=DEFAULT_RESPONSES):
    inputs, ihash = _load(inputs_path)
    labels, lhash = _load(labels_path)
    responses, rhash = _load(responses_path)
    if 'results' in responses and 'manifest' in responses:
        # A prior report is itself a frozen replay source. Only its raw final
        # outputs are replayed; expected labels still come from labels_path.
        responses = {'schema_version': responses['schema_version'], 'synthetic': responses.get('synthetic'),
            'dataset_id': responses['manifest']['dataset_id'], 'provenance': responses['response_provenance'],
            'model': responses['model'], 'records': [
                {'id': row['record_id'], 'case_id': row['case_id'],
                 'response': row['calls'][-1].get('response') if row['calls'] else None,
                 **({'control_expected_pass': row['control_expected_pass']} if 'control_expected_pass' in row else {})}
                for row in responses['results']]}
    for value in (inputs, labels, responses):
        if value.get('schema_version') != 1 or value.get('synthetic') is not True:
            raise ValueError('Version 1 explicitly synthetic fixtures are required')
        if value.get('dataset_id') != inputs.get('dataset_id'):
            raise ValueError('Frozen dataset IDs must match')
    cases = inputs['cases']
    label_rows = labels['cases']
    ids = [case['id'] for case in cases]
    label_ids = [label['id'] for label in label_rows]
    if not 1 <= len(cases) <= 20 or len(set(ids)) != len(ids) or set(ids) != set(label_ids) or len(label_ids) != len(ids):
        raise ValueError('Require unique case IDs with exactly one separate label each')
    by_id = {label['id']: label for label in label_rows}
    for case in cases:
        if case['task'] not in {'extract', 'chat'} or 'label' in case or 'expected_rows' in case:
            raise ValueError('Inputs must be extraction/chat cases without runtime-generated labels')
        label = by_id[case['id']]
        if label['task'] != case['task']:
            raise ValueError('Input and label task differ')
        if case['task'] == 'extract':
            if not 1 <= len(case['pages']) <= 6 or any(not page for page in case['pages']):
                raise ValueError('Require 1–6 nonempty synthetic PDF pages')
            if not label.get('expected_rows'):
                raise ValueError('Extraction requires pre-authored expected rows')
            source_ids = {f'line-{i}' for i in range(1, sum(len(page) for page in case['pages']) + 1)}
            if any(set(row['source_unit_ids']) - source_ids for row in label['expected_rows']):
                raise ValueError('Expected row cites an unknown frozen source unit')
        else:
            FridayChatRequest.model_validate(case['request'])
            statement_context(case)
            for pattern in label.get('required_claim_patterns', []) + label.get('forbidden_claim_patterns', []) + label.get('abstention_patterns', []):
                re.compile(pattern, re.I)
    records = responses['records']
    if not records or len(records) > 60 or len({record['id'] for record in records}) != len(records):
        raise ValueError('Require 1–60 unique recorded control IDs')
    if any(record['case_id'] not in by_id for record in records):
        raise ValueError('Recorded output references an unknown case')
    if responses.get('provenance') not in {'AUTHOR_WRITTEN_SCORER_CONTROLS_NOT_MODEL_OUTPUT', 'RECORDED_SYNTHETIC_MODEL_OUTPUT'}:
        raise ValueError('Recorded response provenance must identify authored controls or recorded synthetic model output')
    if any('control_expected_pass' in record and type(record['control_expected_pass']) is not bool for record in records):
        raise ValueError('A declared scorer-control expectation must be boolean')
    return cases, by_id, records, {
        'dataset_id': inputs['dataset_id'], 'inputs_sha256': ihash, 'labels_sha256': lhash,
        'responses_sha256': rhash, 'label_origin': labels['label_origin'], 'review_status': labels['review_status'],
        'response_provenance': responses['provenance'], 'recorded_model': responses.get('model')}


def synthetic_pdf(pages):
    """Render known text to in-memory PDF; extraction still reads it with production pypdf."""
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    for lines in pages:
        page = writer.add_blank_page(width=595, height=842)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        commands = ['BT /F1 9 Tf 25 790 Td']
        for line in lines:
            escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            commands.append(f'({escaped}) Tj 0 -10 Td')
        commands.append('ET')
        stream.set_data(' '.join(commands).encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def statement_context(case):
    imports = []
    for source in case.get('statements', []):
        entries = []
        for index, (day, description, debit, credit) in enumerate(source['rows'], 1):
            kind, category = classify(description, debit)
            entries.append(dict(date=day, description=description, debit_minor=debit, credit_minor=credit,
                                kind=kind, category=category, source_row=index))
        imports.append(StatementImport(source_sha256=digest(source), account_alias=source['account_alias'],
            account_type=source.get('account_type', 'BANK'), extraction='CSV_EXACT', entries=entries).model_dump(mode='json'))
    if not imports:
        return {}
    summary = summarize_statements(imports)
    checkup = build_checkup(imports, summary)
    summary.pop('entries', None)
    result = _model_amounts({'evidence_id': 'statements:current', 'source_revision': 1, **summary})
    result['automatic_checkup'] = checkup_model_context(checkup)
    return result


class BudgetExceeded(RuntimeError):
    pass


class CapturedClient:
    """Intercept the real SDK boundary, including production chat repair attempts."""
    def __init__(self, model, limit, *, client=None, output_cap=4096):
        self.models = self
        self.model = model
        self.limit = limit
        self.client = client
        self.output_cap = output_cap
        self.calls = []
        self.recorded = None

    def generate_content(self, **kwargs):
        if len(self.calls) >= self.limit:
            raise BudgetExceeded('Explicit total model-call budget exhausted')
        config = kwargs['config']
        if self.client is not None:
            config.max_output_tokens = min(config.max_output_tokens or self.output_cap, self.output_cap)
        call = {'model': kwargs['model'], 'contents_sha256': sha256(kwargs['contents'].encode()).hexdigest(),
                'prompt_sha256': digest(config.system_instruction), 'schema_sha256': digest(config.response_json_schema),
                'config_sha256': digest(config.model_dump(mode='json', exclude_none=True)),
                'model_config_sha256': digest({'model': kwargs['model'], 'config': config.model_dump(mode='json', exclude_none=True)}),
                'model_latency_seconds': None, 'tokens': None, 'response_model_version': None}
        self.calls.append(call)
        start = perf_counter()
        try:
            response = self.client.models.generate_content(**kwargs) if self.client is not None else SimpleNamespace(text=json.dumps(self.recorded), usage_metadata=None)
            call['response_sha256'] = sha256((response.text or '').encode()).hexdigest()
            if self.client is not None:
                call['model_latency_seconds'] = round(perf_counter() - start, 4)
                usage = getattr(response, 'usage_metadata', None)
                call['tokens'] = {key: value for key in ('prompt_token_count', 'candidates_token_count', 'total_token_count', 'cached_content_token_count')
                    if type(value := getattr(usage, key, None)) is int and value >= 0} or None
                version = getattr(response, 'model_version', None)
                call['response_model_version'] = version if isinstance(version, str) and re.fullmatch(r'[A-Za-z0-9._/-]{1,120}', version) else None
            try:
                call['response'] = json.loads(response.text or '{}')
            except (ValueError, TypeError):
                call['response'] = None
                call['malformed_response'] = True
            # Let production perform schema admission, including malformed JSON.
            return response
        except Exception as error:
            call['error_type'] = type(error).__name__
            if self.client is not None:
                call['model_latency_seconds'] = round(perf_counter() - start, 4)
            raise


def quoted_amounts(reply):
    text = reply.replace('−', '-')
    marker = r'(?:₹|\bINR\b|\bRs\.?|\brupees?\b)'
    number = r'(-?\d[\d,]*(?:\.\d{1,2})?)'
    values = re.findall(marker + r'\s*' + number, text, re.I)
    values += re.findall(number + r'\s*' + marker, text, re.I)
    from decimal import Decimal
    return sorted({int(Decimal(value.replace(',', '')) * 100) for value in values})


def score_raw(raw, case, label):
    if case['task'] == 'extract':
        try:
            value = ExtractedStatement.model_validate(raw)
        except ValueError:
            return {'schema_valid': False, 'passed': False}
        by_id = {f'line-{index}': line for index, line in enumerate([line for page in case['pages'] for line in page], 1)}
        invalid = [identity for row in value.rows for identity in row.source_ids if identity not in by_id]
        invalid += [identity for identity in value.currency_source_ids if identity not in by_id]
        from carapace_ai.friday_statements import _date
        from carapace_core.friday_statement import _money
        normalized = []
        numeric_errors = 0
        for row in value.rows:
            try:
                normalized.append({'date': _date(row.date_text).isoformat(), 'description': row.description,
                    'debit_minor': _money(row.debit_text), 'credit_minor': _money(row.credit_text),
                    'kind': row.kind, 'category': row.category, 'source_unit_ids': row.source_ids})
            except ValueError:
                numeric_errors += 1
        expected = label['expected_rows']
        wrong_rows = sum(actual != wanted for actual, wanted in zip(normalized, expected)) + abs(len(normalized) - len(expected))
        incorrect_amounts = numeric_errors + sum(
            any(actual[key] != wanted[key] for key in ('debit_minor', 'credit_minor'))
            for actual, wanted in zip(normalized, expected))
        return {'schema_valid': True, 'row_mismatches': wrong_rows, 'incorrect_amounts': incorrect_amounts,
            'invalid_references': invalid, 'abstained': not value.complete, 'normalized_rows': normalized,
            'passed': not wrong_rows and not incorrect_amounts and not invalid and value.complete}
    try:
        value = ChatAnswer.model_validate(raw)
    except ValueError:
        return {'schema_valid': False, 'passed': False}
    allowed = set(label['allowed_citations'])
    cited = set(value.evidence_ids)
    amounts = quoted_amounts(value.reply)
    forbidden = [pattern for pattern in label.get('forbidden_claim_patterns', []) if re.search(pattern, value.reply, re.I)]
    missing_claims = [pattern for pattern in label.get('required_claim_patterns', []) if not re.search(pattern, value.reply, re.I)]
    abstained = any(re.search(pattern, value.reply, re.I) for pattern in label['abstention_patterns'])
    intents = {key: getattr(value, key) == expected for key, expected in label['expected_intent'].items()}
    incorrect = sorted(set(amounts) - set(label['allowed_amounts_minor']))
    missing_amounts = sorted(set(label['required_amounts_minor']) - set(amounts))
    missing_citations = sorted(set(label['required_citations']) - cited)
    invalid_citations = sorted(cited - allowed)
    return {'schema_valid': True, 'intent_fields': intents, 'intent_correct': all(intents.values()),
        'quoted_amounts_minor': amounts, 'incorrect_amounts': len(incorrect), 'unsupported_amounts_minor': incorrect,
        'missing_required_amounts_minor': missing_amounts, 'invalid_references': invalid_citations,
        'missing_required_citations': missing_citations, 'unsupported_known_claims': forbidden,
        'missing_literal_claim_checks': missing_claims, 'abstained': abstained,
        'abstention_correct': abstained == label['abstention_expected'],
        'passed': all(intents.values()) and not any((incorrect, missing_amounts, invalid_citations, missing_citations, forbidden, missing_claims)) and abstained == label['abstention_expected']}


def load_protocol_v2(path, cases, manifest):
    rules, fingerprint = _load(path)
    if rules.get('protocol_version') != 2 or rules.get('synthetic') is not True:
        raise ValueError('Require explicitly synthetic protocol v2 rules')
    for key, expected in (('dataset_id', manifest['dataset_id']), ('inputs_sha256', manifest['inputs_sha256']),
                          ('v1_labels_sha256', manifest['labels_sha256'])):
        if rules.get(key) != expected:
            raise ValueError('Protocol v2 is bound to the original frozen inputs and v1 labels')
    by_id = {rule['id']: rule for rule in rules['cases']}
    if len(by_id) != len(rules['cases']) or set(by_id) != {case['id'] for case in cases}:
        raise ValueError('Protocol v2 rules must match frozen cases exactly')
    for case in cases:
        rule = by_id[case['id']]
        if rule['task'] != case['task']:
            raise ValueError('Protocol v2 task mismatch')
        for fact in rule.get('input_facts', []):
            row = case['statements'][fact['statement']]['rows'][fact['row']]
            if fact['column'] not in {'debit', 'credit'} or row[2 if fact['column'] == 'debit' else 3] != fact['value_minor']:
                raise ValueError('Protocol v2 expected facts must agree with frozen input rows')
        if rule.get('missing_month') and any(row[0].startswith(rule['missing_month'])
                for statement in case['statements'] for row in statement['rows']):
            raise ValueError('Protocol v2 missing-period target contradicts supplied input rows')
    return rules, by_id, fingerprint


def _source_amounts(case):
    """Input-derived shared context only, independent of any model output."""
    from decimal import Decimal
    supported = {}
    def visit(value, path):
        if isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f'{path}[{index}]')
        elif isinstance(value, dict):
            for key, item in value.items():
                if key.endswith('_inr') and isinstance(item, str):
                    minor = int(Decimal(item.removeprefix('INR ').replace(',', '')) * 100)
                    supported.setdefault(minor, []).append(f'{path}.{key}')
                elif isinstance(item, (dict, list)):
                    visit(item, f'{path}.{key}')
    visit(statement_context(case), 'statement_summary')
    return [{'value_minor': value, 'support_paths': sorted(paths)} for value, paths in sorted(supported.items())]


_MONEY_TOKEN = r'(?:₹|\bINR\b|\bRs\.?)\s*(-?\d[\d,]*(?:\.\d{1,2})?)(?![\d,]|\.\d)'
_MONTH_NAMES = {'04': r'Apr(?:il)?', '05': r'May', '06': r'Jun(?:e)?'}


def _attributed_amounts(reply, subject):
    """Finite subject/amount binding; a value allowlist alone cannot detect swaps."""
    from decimal import Decimal
    found = []
    money = list(re.finditer(_MONEY_TOKEN, reply, re.I))
    subjects = list(re.finditer(subject, reply, re.I))
    for match in subjects:
        before = next((amount for amount in reversed(money) if amount.end() <= match.start()), None)
        if before:
            gap = reply[before.end():match.start()]
            if re.fullmatch(r'\s*(?:in|for|during|is|was|represents|is your|is the)\s+(?:the\s+)?', gap, re.I):
                found.append(int(Decimal(before[1].replace(',', '')) * 100))
                continue
        after = next((amount for amount in money if amount.start() >= match.end()), None)
        if after:
            gap = reply[match.end():after.start()]
            if len(gap) <= 90 and not re.search(r'[;!?\n]|\.(?!\d)|\b(?:not|never)\b', gap, re.I) and not re.search(subject, gap, re.I):
                found.append(int(Decimal(after[1].replace(',', '')) * 100))
    return sorted(set(found))


def _known_contradictions(reply):
    """Conservative finite affirmative-claim checks, not a prose truth oracle."""
    patterns = {
        'EXTERNAL_ACTION_CLAIM': r'\bI\s+(?:have\s+)?(?:sent|submitted|filed|cancelled|recovered|corrected)\b|\b(?:your|the)\s+(?:enquiry|dispute)\s+(?:has been|was|is)\s+(?:sent|submitted|filed)\b',
        'UNSUPPORTED_INNOCENCE': r'\bthere is no fraud\b|\b(?:it|this|the charge)\s+is\s+(?:not fraud|legitimate|safe)\b',
        'BORROWING_AS_EARNINGS': r'\bloan(?:s| proceeds| credits| receipts)?\s+(?:are|is|count as|counts as)\s+(?:income|earnings|salary)\b|\bloans?[^.!?;]{0,35}\bnot excluded from (?:income|earnings)\b',
        'BANK_CONNECTED': r'\b(?:your |the |my )?bank\s+is\s+connected\b',
    }
    found = [name for name, pattern in patterns.items() if re.search(pattern, reply, re.I)]
    for match in re.finditer(r'\b(?:confirmed fraud|definitely fraudulent|(?:this |it )?proves fraud|fraud is confirmed)\b', reply, re.I):
        prefix = reply[max(0, match.start() - 35):match.start()]
        if not re.search(r'\b(?:not|no|cannot|can\x27t|does not|doesn\x27t)\s+(?:\w+\s+){0,3}$', prefix, re.I):
            found.append('UNSUPPORTED_FRAUD_VERDICT')
    return sorted(set(found))


def score_protocol_v2(raw, case, label, rule):
    v1 = score_raw(raw, case, label)
    if not v1['schema_valid']:
        return {'schema_valid': False, 'factual_checks': {}, 'factual_checks_passed': False,
                'strict_v1_raw_passed': False, 'coverage': 'UNRESOLVED_SCHEMA'}
    if case['task'] == 'extract':
        immutable = ('date', 'description', 'debit_minor', 'credit_minor', 'source_unit_ids')
        rows = v1['normalized_rows']
        expected = label['expected_rows']
        facts = len(rows) == len(expected) and all(
            all(actual[key] == wanted[key] for key in immutable) for actual, wanted in zip(rows, expected))
        kind = len(rows) == len(expected) and all(actual['kind'] == wanted['kind'] for actual, wanted in zip(rows, expected))
        category = len(rows) == len(expected) and all(actual['category'] in rule.get('category_alternatives', {}).get(str(index), [wanted['category']])
            for index, (actual, wanted) in enumerate(zip(rows, expected)))
        checks = {'immutable_rows_exact': facts, 'source_references_valid': not v1['invalid_references'], 'not_abstained': not v1['abstained']}
        return {'schema_valid': True, 'factual_checks': checks, 'factual_checks_passed': all(checks.values()),
            'classification_conformance': {'kind': kind, 'category': category},
            'category_ambiguity_note': rule.get('ambiguity_reason'), 'strict_v1_raw_passed': v1['passed'],
            'strict_v1_row_mismatches': v1['row_mismatches'], 'coverage': 'FINITE_IMMUTABLE_SOURCE_ROW_CHECKS'}
    value = ChatAnswer.model_validate(raw)
    reply = value.reply
    supported = _source_amounts(case)
    unsupported = sorted(set(quoted_amounts(reply)) - {item['value_minor'] for item in supported})
    contradictions = _known_contradictions(reply)
    checks = {'source_backed_amounts': not unsupported, 'citations_valid': not v1['invalid_references'],
              'required_citations_present': not v1['missing_required_citations'], 'no_known_contradictory_claim': not contradictions}
    details = {}
    for name in rule.get('claim_checks', []):
        if name == 'IDENTIFIED_INCOME_ATTRIBUTION':
            attributed = _attributed_amounts(reply, r'\bidentified\s+income\b')
            details['identified_income_attributed_minor'] = attributed
            checks[name] = bool(attributed) and set(attributed) == {rule['required_income_minor']}
        elif name == 'BORROWING_NOT_EARNINGS':
            checks[name] = bool(re.search(r'\b(?:loans?|loan (?:proceeds|credits|receipts)|borrowing)\b[^.!?;]{0,70}\b(?:are not|is not|do not count as|does not count as|not counted as|excluded from|separate from)\b[^.!?;]{0,45}\b(?:income|earnings|salary)\b', reply, re.I))
        elif name == 'MISSING_PERIOD_DECLARED':
            year, month = rule['missing_month'].split('-')
            subject = _MONTH_NAMES[month] + rf'(?:\s+{year})?'
            explicit_wrong_year = bool(re.search(rf'\b{_MONTH_NAMES[month]}\s+(?!{year}\b)20\d{{2}}\b', reply, re.I))
            checks[name] = not explicit_wrong_year and bool(re.search(
                rf'\b{subject}\s+(?:(?:is|was)\s+)?(?:missing|absent|unavailable|not (?:supplied|provided|available|included))\b|'
                rf'\b{subject}\s+(?:has|had)\s+no\s+(?:(?:supplied|transaction)\s+)?rows\b|'
                rf'\bno\s+(?:supplied\s+)?rows(?:\s+(?:are|were))?\s+(?:for|in)\s+{subject}\b', reply, re.I))
            if re.search(rf'\b{subject}[^.!?;]{{0,25}}\b(?:not missing|not absent|(?:spending )?(?:is|was) zero)\b', reply, re.I):
                contradictions.append('MISSING_PERIOD_CONTRADICTION')
                checks[name] = False
        elif name == 'MISSING_IS_NOT_ZERO':
            checks[name] = bool(re.search(r'\b(?:missing|absent|unavailable)[^.!?;]{0,45}\b(?:not|cannot|can\x27t|doesn\x27t)[^.!?;]{0,25}\bzero\b', reply, re.I))
        elif name == 'MONTH_AMOUNT_ATTRIBUTION':
            attribution = {}
            for period, expected in rule['month_amounts_minor'].items():
                year, month = period.split('-')
                observed = _attributed_amounts(reply, rf'\b{_MONTH_NAMES[month]}(?:\s+{year})?\b')
                attribution[period] = observed
            details['month_amount_attribution'] = attribution
            checks[name] = all(not values or set(values) == {rule['month_amounts_minor'][period]} for period, values in attribution.items())
        elif name == 'ENQUIRY_UNSENT':
            checks[name] = bool(re.search(r'\bunsent\b|\b(?:not|never) (?:been )?sent\b|\b(?:will not|won\x27t) send\b', reply, re.I))
        elif name == 'LIVE_BALANCE_UNAVAILABLE':
            checks[name] = bool(re.search(r'\b(?:cannot|can\x27t|am unable to|not able to|do not|don\x27t)\s+(?:directly\s+)?(?:determine|know|see|view|access|retrieve|check|provide)\b[^.!?;]{0,80}\b(?:balances?|bank accounts?)\b|\bbalances?[^.!?;]{0,35}\b(?:unknown|unavailable|not (?:provided|available|established))\b', reply, re.I))
            if re.search(r'\b(?:can|am able to)\s+(?:see|view|access|retrieve|check)\s+(?:your |the |live |bank )*balances?\b|\bcannot not (?:see|view|access|retrieve|check)\b', reply, re.I):
                contradictions.append('BALANCE_ACCESS_CONTRADICTION')
                checks[name] = False
        else:
            raise ValueError('Unknown protocol v2 claim check')
    checks['no_known_contradictory_claim'] = not contradictions
    return {'schema_valid': True, 'factual_checks': checks, 'factual_checks_passed': all(checks.values()),
        'source_backed_amounts': supported, 'unsupported_amounts_minor': unsupported,
        'known_contradictions': sorted(set(contradictions)), 'attribution_details': details,
        'strict_v1_raw_passed': v1['passed'], 'strict_typed_field_conformance': v1['intent_fields'],
        'strict_v1_literal_misses': v1['missing_literal_claim_checks'],
        'strict_v1_abstention_conformance': v1['abstention_correct'], 'coverage': 'FINITE_DECLARED_FACT_CHECKS_NOT_FULL_PROSE_TRUTH'}


def attach_protocol_v2(report, cases, labels, rules_path=DEFAULT_PROTOCOL_V2, original_report=None):
    rules, by_id, fingerprint = load_protocol_v2(rules_path, cases, report['manifest'])
    cases_by_id = {case['id']: case for case in cases}
    original_rows = {row['record_id']: row for row in original_report.get('results', [])} if original_report else {}
    for row in report['results']:
        raw = row['calls'][-1].get('response') if row['calls'] else None
        row['protocol_v2'] = score_protocol_v2(raw, cases_by_id[row['case_id']], labels[row['case_id']], by_id[row['case_id']])
        original = original_rows.get(row['record_id'])
        row['protocol_v2']['current_runtime_admitted'] = row['admitted']
        row['protocol_v2']['original_recorded_admitted'] = original['admitted'] if original else None
        row['protocol_v2']['original_recorded_v1_passed'] = original['passed'] if original else None
        row['protocol_v2']['original_recorded_v1_raw_score'] = original.get('raw_score') if original else None
    from carapace_core.friday_narration import VERSION as narration_version
    provenance_files = ('src/carapace_core/friday_checkup.py', 'src/carapace_core/friday_narration.py',
                        'src/carapace_core/friday_refund_shield.py', 'src/carapace_api/friday_cashflow.py')
    report['source_sha256'].update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in provenance_files})
    rows = report['results']
    def summarize(selected):
        return {'outputs': len(selected), 'raw_factual_checks_passed': sum(row['protocol_v2']['factual_checks_passed'] for row in selected),
                'current_runtime_admitted': sum(row['admitted'] for row in selected),
                'original_recorded_admission_known': sum(row['protocol_v2']['original_recorded_admitted'] is not None for row in selected),
                'original_recorded_admitted': sum(row['protocol_v2']['original_recorded_admitted'] is True for row in selected),
                'strict_v1_current_runtime_passed': sum(row['passed'] for row in selected),
                'original_recorded_v1_passed': sum(row['protocol_v2']['original_recorded_v1_passed'] is True for row in selected)}
    report['protocol_v2'] = {'version': 2, 'rules_sha256': fingerprint, 'rules': rules,
        'narration_version': narration_version, 'summary': summarize(rows),
        'by_task': {task: summarize([row for row in rows if row['task'] == task]) for task in ('extract', 'chat')},
        'original_recorded_source_sha256': original_report.get('source_sha256') if original_report else None,
        'original_recorded_summary': original_report.get('summary') if original_report else None,
        'original_recorded_report_sha256': report['manifest']['responses_sha256'] if original_report else None,
        'interpretation': 'A scoring-protocol revision on already-seen outputs, not a measured model improvement. Raw factual diagnostics, original/current admission and strict conformance are separate axes; there is no replacement overall pass score.'}
    return report


def evaluate(cases, labels, records, manifest, *, client=None, model='gemini-offline-scorer-control', max_model_calls=60, output_cap=4096):
    if type(max_model_calls) is not int or not 1 <= max_model_calls <= 60:
        raise ValueError('Require an explicit 1–60 total call cap')
    captured = CapturedClient(model, max_model_calls, client=client, output_cap=output_cap)
    planner = GeminiFinancialFridayPlanner(captured, model, 'VERTEX_AI' if client is not None else 'OFFLINE_RECORDED_CONTROL')
    by_id = {case['id']: case for case in cases}
    work = records if client is None else [{'id': case['id'] + '-live', 'case_id': case['id']} for case in cases]
    results = []
    for item in work:
        if len(captured.calls) >= max_model_calls:
            break
        case = by_id[item['case_id']]
        label = labels[case['id']]
        captured.recorded = item.get('response')
        start_call = len(captured.calls)
        row = {'record_id': item['id'], 'case_id': case['id'], 'task': case['task'],
               'input_sha256': digest(case), 'label_sha256': digest(label), 'admitted': False}
        if client is None and 'control_expected_pass' in item:
            row['control_expected_pass'] = item['control_expected_pass']
        try:
            if case['task'] == 'extract':
                statement, metadata = extract_statement(planner, data=synthetic_pdf(case['pages']), mime='application/pdf',
                    account_alias='Synthetic Benchmark', account_type=case['account_type'], use_ai=True)
                checks = metadata['reconciliation']['checks']
                row['source_checks'] = {key: checks[key]['status'] for key in label['expected_checks']}
                row['source_checks_correct'] = row['source_checks'] == label['expected_checks']
                row['admitted_rows'] = [{key: entry.model_dump(mode='json')[key] for key in label['expected_rows'][0]} for entry in statement.entries]
                row['admitted_rows_exact'] = row['admitted_rows'] == label['expected_rows']
            else:
                answer = answer_chat(planner, FridayChatRequest.model_validate(case['request']), {}, statements=statement_context(case))
                row['admitted_answer'] = {key: answer[key] for key in ChatAnswer.model_fields}
            row['admitted'] = True
        except Exception as error:
            row['error_type'] = type(error).__name__
            row['failure_category'] = chat_failure_category(error) if case['task'] == 'chat' else 'EXTRACTION_REJECTED'
        calls = captured.calls[start_call:]
        raw = calls[-1].get('response') if calls else None
        row['raw_score'] = score_raw(raw, case, label)
        row['passed'] = row['admitted'] and row['raw_score']['passed'] and row.get('source_checks_correct', True) and row.get('admitted_rows_exact', True)
        if 'control_expected_pass' in row:
            row['scorer_control_matched'] = row['passed'] == row['control_expected_pass']
        row['calls'] = calls
        results.append(row)
    times = [call['model_latency_seconds'] for call in captured.calls if call['model_latency_seconds'] is not None]
    tokens = [call['tokens']['total_token_count'] for call in captured.calls if call['tokens'] and 'total_token_count' in call['tokens']]
    source_files = ('tools/evaluate_friday_statement_ai.py', 'src/carapace_ai/friday_chat.py', 'src/carapace_ai/friday_statements.py',
                    'src/carapace_core/friday_statement_reconciliation.py', 'src/carapace_core/friday_portfolio.py')
    def aggregate(selected):
        return {'outputs': len(selected), 'passed': sum(row['passed'] for row in selected),
            'admitted': sum(row['admitted'] for row in selected), 'rejected': sum(not row['admitted'] for row in selected),
            'schema_errors': sum(not row['raw_score']['schema_valid'] for row in selected),
            'scored_schema_valid_outputs': sum(row['raw_score']['schema_valid'] for row in selected),
            'incorrect_amounts': sum(row['raw_score'].get('incorrect_amounts', 0) for row in selected),
            'invalid_references': sum(len(row['raw_score'].get('invalid_references', [])) for row in selected),
            'unsupported_known_claims': sum(len(row['raw_score'].get('unsupported_known_claims', [])) for row in selected),
            'missing_literal_claim_checks': sum(len(row['raw_score'].get('missing_literal_claim_checks', [])) for row in selected),
            'abstentions': sum(row['raw_score'].get('abstained', False) for row in selected),
            'wrong_intents': sum(row['raw_score'].get('intent_correct') is False for row in selected)}
    origin = 'RECORDED_SYNTHETIC_MODEL_OUTPUT' if client is not None else manifest['response_provenance']
    return {'schema_version': 1, 'synthetic': True,
        'status': 'LIVE_SYNTHETIC_SMOKE' if client is not None else 'OFFLINE_AUTHOR_WRITTEN_SCORER_CONTROLS' if origin == 'AUTHOR_WRITTEN_SCORER_CONTROLS_NOT_MODEL_OUTPUT' else 'OFFLINE_RECORDED_MODEL_RESPONSE_REPLAY',
        'response_provenance': origin,
        'independent_validation_completed': False, 'live_model_quality_measured': client is not None,
        'manifest': manifest, 'model': model, 'model_identity_sha256': digest(model),
        'frozen_case_ids': [case['id'] for case in cases], 'frozen_response_ids': [item['id'] for item in work],
        'production_paths': ['carapace_ai.friday_statements.extract_statement', 'carapace_ai.friday_chat.answer_chat'],
        'score_definitions': {
            'incorrect_amounts': 'Extraction: row positions with a wrong debit/credit pair, plus parse errors. Chat: distinct currency-marked values outside that case\'s pre-authored allowed amounts. Task counts have different units and are also shown separately.',
            'invalid_references': 'Unknown extraction source-unit IDs or chat evidence IDs outside the pre-authored case allowlist.',
            'unsupported_known_claims': 'Number of matching pre-authored forbidden factual/action phrase patterns; not all unsupported prose.',
            'missing_literal_claim_checks': 'Number of pre-authored required factual phrase patterns absent; paraphrases may be missed.',
            'passed': 'Production admission AND static raw expectations, plus exact normalized extraction rows/source checks where applicable.',
            'abstentions': 'Extraction complete=false or a pre-authored chat abstention phrase. Schema/provider failures are separate rejected/unresolved outputs.',
            'hash_encoding': 'SHA256 of UTF-8 compact sorted JSON for structured values; raw file bytes for fixture/source files; raw UTF-8 strings for contents/response text.'},
        'source_sha256': {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in source_files},
        'planned_outputs': len(work), 'attempted_outputs': len(results), 'skipped_output_ids': [item['id'] for item in work[len(results):]],
        'completion_status': 'COMPLETE' if len(results) == len(work) else 'INCOMPLETE_CALL_BUDGET',
        'total_sdk_invocations': len(captured.calls), 'live_model_calls': len(captured.calls) if client is not None else 0,
        'call_cap': max_model_calls, 'live_output_token_cap_per_call': output_cap if client is not None else None,
        'model_latency_seconds': {'coverage': len(times), 'median': statistics.median(times) if times else None, 'maximum': max(times) if times else None},
        'total_tokens_reported': sum(tokens) if tokens else None, 'token_coverage_calls': len(tokens),
        'summary': aggregate(results), 'by_task': {task: aggregate([row for row in results if row['task'] == task]) for task in ('extract', 'chat')},
        'scorer_controls': {'declared': sum('control_expected_pass' in row for row in results),
            'matched': sum(row.get('scorer_control_matched', False) for row in results),
            'mismatched_record_ids': [row['record_id'] for row in results if row.get('scorer_control_matched') is False]},
        'payment_effects': 0, 'external_messages': 0, 'user_records': 0, 'results': results,
        'limitations': [
            'Small unreviewed agent-authored synthetic smoke corpus, no independent, held-out or representative accuracy claim.',
            'Offline controls are hand-authored good/bad outputs; their pass rate measures the scorer and admission paths, never Gemini quality.',
            'Chat intent means production typed navigation/checkup fields; there is no separate semantic-intent classifier in this run.',
            'Currency-marker amounts, exact reference membership and narrow required/forbidden phrase patterns are scored. Bare numbers, attribution swaps and unrestricted prose semantics are not fully verified.',
            'Missing-citation checks measure expected references, not whether a valid reference semantically supports every sentence. No judge model supplies truth.',
            'Abstention is a predeclared literal-phrase diagnostic because production ChatAnswer has no abstention field; paraphrases can be missed.',
            'Extraction uses two tiny text PDFs; OCR, scanned images, complex layouts and real institution format coverage remain unmeasured.',
            'Production chat may repair once; every SDK invocation consumes the same hard cap. Provider retries are disabled for opt-in live runs.',
            'A configured model name hash identifies requested configuration, not immutable provider weights. Response model version is recorded when supplied.',
        ]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=DEFAULT_INPUTS)
    parser.add_argument('--labels', type=Path, default=DEFAULT_LABELS)
    parser.add_argument('--responses', type=Path, default=DEFAULT_RESPONSES)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--protocol', choices=('v1', 'v2'), default='v1')
    parser.add_argument('--protocol-rules', type=Path, default=DEFAULT_PROTOCOL_V2)
    parser.add_argument('--run-live', action='store_true')
    parser.add_argument('--max-model-calls', type=int)
    parser.add_argument('--max-output-tokens', type=int, default=4096)
    parser.add_argument('--project')
    parser.add_argument('--model')
    parser.add_argument('--token-stdin', action='store_true')
    args = parser.parse_args(argv)
    if args.protocol == 'v2' and args.output and args.output.resolve() in {
            args.inputs.resolve(), args.labels.resolve(), args.responses.resolve(),
            (DIRECTORY / 'statement_ai_live_0320.json').resolve()}:
        parser.error('Protocol v2 must write a separate report; preserve original inputs, labels and recorded responses')
    if not 256 <= args.max_output_tokens <= 16000:
        parser.error('Output-token cap must be 256–16000')
    if args.run_live and (not args.max_model_calls or not 1 <= args.max_model_calls <= 12 or not args.project or not args.model or not args.token_stdin):
        parser.error('Live execution requires --max-model-calls 1–12, --project, --model, and --token-stdin')
    cases, labels, records, manifest = load_corpus(args.inputs, args.labels, args.responses)
    if args.run_live:
        token = sys.stdin.read().strip()
        if not token or '\n' in token:
            raise ValueError('One authorized access token must arrive via stdin; it is never stored or printed')
        from google import genai
        from google.genai import types
        from google.oauth2.credentials import Credentials
        with genai.Client(vertexai=True, project=args.project, location='global', credentials=Credentials(token),
            http_options=types.HttpOptions(timeout=45000, retry_options=types.HttpRetryOptions(attempts=1))) as client:
            report = evaluate(cases, labels, records, manifest, client=client, model=args.model,
                max_model_calls=args.max_model_calls, output_cap=args.max_output_tokens)
    else:
        report = evaluate(cases, labels, records, manifest, model=manifest.get('recorded_model') or 'gemini-offline-scorer-control',
            max_model_calls=args.max_model_calls if args.max_model_calls is not None else 60)
    if args.protocol == 'v2':
        prior, _ = _load(args.responses)
        original = prior if not args.run_live and 'results' in prior and 'manifest' in prior else None
        attach_protocol_v2(report, cases, labels, args.protocol_rules, original)
    rendered = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(rendered)
    else:
        sys.stdout.write(rendered)
    if args.run_live:
        return 0 if not report['skipped_output_ids'] and report['summary']['passed'] == report['summary']['outputs'] else 1
    return 1 if report['scorer_controls']['mismatched_record_ids'] else 0


if __name__ == '__main__':
    raise SystemExit(main())

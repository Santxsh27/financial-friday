"""Friday extraction attestations. These are not bank authentication.

The browser may review classification labels, but cannot rewrite source facts or
immutable transaction fields while retaining a server-issued extraction receipt.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .canonical import canonical_json

PURPOSE = 'FRIDAY_STATEMENT_EXTRACTION_V1'


class StatementExtractionReceipt(BaseModel):
    model_config = ConfigDict(extra='forbid')
    purpose: Literal['FRIDAY_STATEMENT_EXTRACTION_V1'] = PURPOSE
    key_id: str = Field(pattern=r'^[a-f0-9]{16}$')
    binding_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    workspace_generation: str = Field(min_length=1, max_length=80)
    signature: str = Field(min_length=80, max_length=100, pattern=r'^[A-Za-z0-9_=-]+$')


def _binding(statement, tenant, generation):
    data = statement.model_dump(mode='json') if hasattr(statement, 'model_dump') else statement
    rows = [{k: row.get(k) for k in (
        'date', 'description', 'debit_minor', 'credit_minor', 'source_row',
        'running_balance_minor', 'source_unit_ids')}
        for row in data['entries']]
    return {
        'purpose': PURPOSE,
        'tenant_binding': sha256(('friday-extraction-tenant:' + tenant).encode()).hexdigest(),
        'workspace_generation': str(generation),
        'source_sha256': data['source_sha256'],
        'extraction': data['extraction'],
        'account_alias': data['account_alias'],
        'account_type': data['account_type'],
        'source_facts': data.get('source_facts'),
        'entries': rows,
    }


def _envelope(binding, key_id):
    return {'purpose': PURPOSE, 'key_id': key_id,
            'binding_sha256': sha256(canonical_json(binding).encode()).hexdigest(),
            'workspace_generation': binding['workspace_generation']}


def sign_statement_extraction(statement, tenant, generation, signer):
    envelope = _envelope(_binding(statement, tenant, generation), signer.key_id)
    return StatementExtractionReceipt(**envelope, signature=signer.sign(envelope))


def verify_statement_extraction(statement, tenant, generation, signer):
    receipt = getattr(statement, 'extraction_receipt', None)
    if receipt is None:
        return False
    expected = _envelope(_binding(statement, tenant, generation), receipt.key_id)
    return (receipt.model_dump(exclude={'signature'}) == expected and
            signer.verify_for_key(expected, receipt.signature, receipt.key_id))

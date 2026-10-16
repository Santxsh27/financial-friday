"""Finite, literal narration grammars; no fuzzy counterparty or ownership inference.

Only these complete layouts are interpreted (ASCII labels, optional space around
separators): RAIL/[DR|CR/]REFERENCE/PAYEE[/VPA], RAIL TO|FROM PAYEE REF|RRN|UTR:
REFERENCE, and RAIL/TO|FROM:PAYEE/REF|RRN|UTR:REFERENCE (also pipe separators).
RAIL is UPI, IMPS, NEFT or RTGS. A payee is an exact name, an exact VPA, or an
exact name plus VPA; words, digits, punctuation and non-ASCII codepoints remain
significant. ASCII case/space presentation may differ. No Unicode compatibility
normalization, transliteration, stemming or bank-format certification occurs.

Saved descriptions may already replace numeric references with [IDENTIFIER].
That explicit missing slot can support a weak literal-payee recurring candidate,
never an assertion that two reliable transaction references are the same.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

VERSION = 'NARRATION_1'
MAX_DESCRIPTION = 180
MAX_REFERENCE = 35
MAX_PAYEE = 96
_ASCII_LOWER = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')
_RAILS = {'UPI', 'IMPS', 'NEFT', 'RTGS'}
_VPA = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}@[A-Za-z][A-Za-z0-9.-]{1,63}\Z', re.ASCII)
_PLACEHOLDERS = {'[IDENTIFIER]', '[REFERENCE REDACTED]', '[REDACTED]'}
_GENERIC = {'unknown', 'merchant', 'payee', 'payment', 'transfer', 'refund', 'self', 'own account'}


def _literal_key(text):
    # ASCII spaces/case only. In particular, ß != ss, NBSP != space, and a
    # Cyrillic/width/combining-codepoint lookalike remains a different identity.
    return re.sub(r' +', ' ', text.translate(_ASCII_LOWER)).strip(' ')


@dataclass(frozen=True)
class NarrationMatch:
    status: str
    exact_key: str | None
    counterparty_key: tuple[str, ...] | None = None
    reference_key: str | None = None
    transport: str | None = None
    direction: str | None = None
    match_basis: str = 'EXACT_DESCRIPTION_ONLY'
    reference_status: str = 'NOT_ESTABLISHED'
    uncertainty: tuple[str, ...] = ('Literal description equality does not establish transaction or payee identity.',)

    def direction_agrees(self, debit_minor, credit_minor):
        return self.direction is None or (self.direction == 'DEBIT' and debit_minor > 0 and not credit_minor) or (self.direction == 'CREDIT' and credit_minor > 0 and not debit_minor)


def _fallback(text, *, ambiguous=False, reason=None):
    base = 'Literal description equality does not establish transaction or payee identity.'
    return NarrationMatch(status='AMBIGUOUS' if ambiguous else 'EXACT_ONLY', exact_key=_literal_key(text),
                          uncertainty=(base, reason) if reason else (base,))


def _payee_key(name, vpa=None):
    if not 3 <= len(name) <= MAX_PAYEE or name != name.strip(' '):
        return None
    if vpa is not None:
        if not _VPA.fullmatch(vpa):
            return None
        display = _payee_key(name)
        if display is None or display[0] != 'NAME':
            return None
        return ('NAME_AND_VPA', display[1], _literal_key(vpa))
    if _VPA.fullmatch(name):
        return ('VPA', _literal_key(name))
    # Structural punctuation and embedded field labels create competing parses.
    if any(char in name for char in '/|:@[]{}<>\\;=') or not any(char.isalpha() for char in name):
        return None
    if re.search(r'\b(?:REF|REFERENCE|RRN|UTR)\s*[:#=]', name, re.I | re.ASCII):
        return None
    key = _literal_key(name)
    if key in _GENERIC:
        return None
    return ('NAME', key)


def _reference(token, rail):
    if token.upper() in _PLACEHOLDERS:
        return None, 'MASKED'
    # A token is reliable for literal distinction only, not bank validation.
    # Numeric RRN grouping is the only accepted internal separator removal.
    if re.fullmatch(r'[0-9]{4}([- ])[0-9]{4}\1[0-9]{4}', token, re.ASCII):
        token = token.replace('-', '').replace(' ', '')
    if rail in {'UPI', 'IMPS'}:
        valid = bool(re.fullmatch(r'[0-9]{12}', token, re.ASCII))
    else:
        valid = bool(re.fullmatch(r'[A-Za-z0-9]{12,35}', token, re.ASCII)) and sum('0' <= char <= '9' for char in token) >= 6
    return (token.translate(_ASCII_LOWER), 'EXPLICIT_TOKEN_UNVERIFIED') if valid else (None, 'UNSUPPORTED')


def parse_narration(description: str) -> NarrationMatch:
    """Return bounded match keys; original descriptions are never rewritten.

    Unsupported or ambiguous syntax falls back to complete literal text. Keys
    must still be scoped by exact account alias/type, date/direction and amount
    as appropriate. Never persist these keys as authenticated bank references.
    """
    if not isinstance(description, str) or not 1 <= len(description) <= MAX_DESCRIPTION:
        return NarrationMatch(status='AMBIGUOUS', exact_key=None,
                              uncertainty=('Narration is outside the supported 1–180 character bound; matching withheld.',))
    text = description.strip(' ')
    if any(unicodedata.category(char).startswith('C') or (char.isspace() and char != ' ') for char in text):
        return _fallback(text, ambiguous=True, reason='Control or non-ASCII whitespace prevents structured narration matching.')
    prefix = re.match(r'([A-Za-z]+)(?=[ /|])', text, re.ASCII)
    if prefix is None or prefix[1].upper() not in _RAILS:
        return _fallback(text)
    rail = prefix[1].upper()
    direction = None
    reference = payee = vpa = None
    # Labels establish field roles. The complete remainder must be consumed.
    labelled = re.fullmatch(r'(UPI|IMPS|NEFT|RTGS) +(TO|FROM) +(.+?) +(REF|REFERENCE|RRN|UTR) *[:#=] *([^/|]+)', text, re.I | re.ASCII)
    if labelled:
        direction = 'DEBIT' if labelled[2].upper() == 'TO' else 'CREDIT'
        payee, reference = labelled[3].strip(' '), labelled[5].strip(' ')
    else:
        separator = '/' if '/' in text else '|' if '|' in text else None
        if separator is None:
            return _fallback(text, ambiguous=True, reason='Explicit transport narration has an unsupported or ambiguous layout.')
        parts = [part.strip(' ') for part in text.split(separator)]
        if any(not part for part in parts) or not 3 <= len(parts) <= 5 or parts[0].upper() != rail:
            return _fallback(text, ambiguous=True, reason='Narration has empty, extra or unsupported transport fields.')
        rest = parts[1:]
        labelled_payee = re.fullmatch(r'(TO|FROM) *[:=] *(.+)', rest[0], re.I | re.ASCII)
        labelled_ref = re.fullmatch(r'(REF|REFERENCE|RRN|UTR) *[:#=] *(.+)', rest[1], re.I | re.ASCII) if len(rest) == 2 else None
        if labelled_payee and labelled_ref:
            direction = 'DEBIT' if labelled_payee[1].upper() == 'TO' else 'CREDIT'
            payee, reference = labelled_payee[2].strip(' '), labelled_ref[2].strip(' ')
        else:
            if rest[0].upper() in {'DR', 'CR'}:
                direction = 'DEBIT' if rest[0].upper() == 'DR' else 'CREDIT'
                rest = rest[1:]
            if len(rest) not in {2, 3}:
                return _fallback(text, ambiguous=True, reason='Narration does not have one reference and one counterparty slot.')
            reference, payee = rest[:2]
            vpa = rest[2] if len(rest) == 3 else None
    if len(reference) > MAX_REFERENCE:
        return _fallback(text, ambiguous=True, reason='Reference exceeds the supported bound.')
    counterparty = _payee_key(payee, vpa)
    reference_key, reference_status = _reference(reference, rail)
    if counterparty is None or reference_status == 'UNSUPPORTED':
        return _fallback(text, ambiguous=True, reason='Counterparty or reference field is not unambiguous under the supported grammar.')
    uncertainty = ['Counterparty fields are literal source claims, not verified payee identity.']
    if reference_status == 'MASKED':
        uncertainty.append('Reference was masked before matching; distinct transactions cannot be distinguished by that reference.')
    else:
        uncertainty.append('Explicit reference tokens support literal comparison only; bank authenticity and uniqueness are unverified.')
    return NarrationMatch(status='PARSED', exact_key=_literal_key(text),
        counterparty_key=(rail, *counterparty), reference_key=reference_key, transport=rail,
        direction=direction, match_basis='EXPLICIT_COUNTERPARTY_AND_TRANSPORT',
        reference_status=reference_status, uncertainty=tuple(uncertainty))

"""Hardcoded authority rule for the MVP locked fixture pair (FIXTURES.md §4).

Doc A (60% baseline) is authoritative; Doc B (90% revision) is deviation. This
is the only authority surface the MVP exposes. Configurable per-pair authority
is platform-path (BACKLOG.md).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorityDecision:
    authoritative_doc_id: str
    deviating_doc_id: str
    confidence: float
    rule: str


_MVP_RULE = "MVP-hardcoded: Doc A (60% baseline) authoritative over Doc B (90% revision)"


def authority_for(
    doc_a_id: str, doc_b_id: str, parameter_name: str
) -> AuthorityDecision:
    return AuthorityDecision(
        authoritative_doc_id=doc_a_id,
        deviating_doc_id=doc_b_id,
        confidence=1.0,
        rule=_MVP_RULE,
    )

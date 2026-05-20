"""Emit directional flags from aligned pairs.

A Flag declares which doc is authoritative for the parameter family and which
is deviating, with citations on both sides and an assembled confidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from interlock.align.exact import AlignedPair
from interlock.detect.authority import authority_for
from interlock.detect.confidence import flag_confidence
from interlock.extract.parameters import ParameterRecord


@dataclass(frozen=True)
class Flag:
    parameter: str
    authoritative_doc_id: str
    deviating_doc_id: str
    a_record: ParameterRecord
    b_record: ParameterRecord
    confidence: float
    rationale: str
    authority_rule: str


def detect_flags(pairs: list[AlignedPair]) -> list[Flag]:
    out: list[Flag] = []
    for p in pairs:
        if p.value_equivalent:
            continue
        # If both magnitudes are present and numerically equal, suppress
        # (defensive: equivalent() should already have caught this).
        if (
            p.a.normalized_magnitude is not None
            and p.b.normalized_magnitude is not None
            and p.a.normalized_magnitude == p.b.normalized_magnitude
        ):
            continue
        decision = authority_for(p.a.doc_id, p.b.doc_id, p.a.name)
        conf = flag_confidence(
            extraction=1.0,
            match=p.name_match_confidence,
            authority=decision.confidence,
        )
        out.append(
            Flag(
                parameter=p.a.name,
                authoritative_doc_id=decision.authoritative_doc_id,
                deviating_doc_id=decision.deviating_doc_id,
                a_record=p.a,
                b_record=p.b,
                confidence=conf,
                rationale=(
                    f"{p.a.raw_value} (authoritative, p{p.a.page}) "
                    f"≠ {p.b.raw_value} (deviation, p{p.b.page})"
                ),
                authority_rule=decision.rule,
            )
        )
    return out

"""Exact-name alignment with positional 1-to-1 pairing.

When two documents share layout (e.g., a 90% revision derived from a 60%
baseline), records with the same name pair greedily by (page, y-center)
proximity. This avoids the cross-product explosion that would happen if every
A record with name X matched every B record with name X.

Pairing is intra-page: only same-page records may pair.
"""

from __future__ import annotations

from dataclasses import dataclass

from interlock.extract.parameters import ParameterRecord
from interlock.extract.units import equivalent


@dataclass(frozen=True)
class AlignedPair:
    a: ParameterRecord
    b: ParameterRecord
    name_match_confidence: float
    value_equivalent: bool


def _y_center(r: ParameterRecord) -> float:
    return (r.bbox[1] + r.bbox[3]) / 2


def align_exact(
    a: list[ParameterRecord], b: list[ParameterRecord], y_tol: float = 1000.0
) -> list[AlignedPair]:
    """Pair records by exact name + greedy positional proximity.

    For each (a record, candidate b records with same name on same page),
    pick the b record with minimum y-center distance not yet used. y_tol is
    intentionally loose because page heights vary; tightness is delegated to
    later confidence scoring rather than hard-rejecting at this stage.
    """
    by_name_b: dict[str, list[ParameterRecord]] = {}
    for r in b:
        by_name_b.setdefault(r.name.strip().lower(), []).append(r)

    out: list[AlignedPair] = []
    used_b: set[int] = set()
    for ra in a:
        candidates = by_name_b.get(ra.name.strip().lower(), [])
        if not candidates:
            continue
        same_page = [rb for rb in candidates if rb.page == ra.page and id(rb) not in used_b]
        if not same_page:
            continue
        best_rb = min(same_page, key=lambda rb: abs(_y_center(rb) - _y_center(ra)))
        if abs(_y_center(best_rb) - _y_center(ra)) > y_tol:
            continue
        used_b.add(id(best_rb))
        out.append(
            AlignedPair(
                a=ra,
                b=best_rb,
                name_match_confidence=1.0,
                value_equivalent=equivalent(ra.raw_value, best_rb.raw_value),
            )
        )
    return out

"""Combine exact and semantic alignment results.

Rule: a record from A keeps its exact-alignment pair if present; otherwise
the semantic pair is used. This avoids cross-product duplicates when both
paths produced a pair for the same A record.
"""

from __future__ import annotations

from interlock.align.exact import AlignedPair


def _key_for_a(p: AlignedPair) -> tuple[str, int, float, float, str]:
    return (
        p.a.doc_id,
        p.a.page,
        p.a.bbox[0],
        p.a.bbox[1],
        p.a.name,
    )


def combine_alignments(
    exact: list[AlignedPair], semantic: list[AlignedPair]
) -> list[AlignedPair]:
    out: list[AlignedPair] = list(exact)
    covered_a = {_key_for_a(p) for p in exact}
    for p in semantic:
        if _key_for_a(p) in covered_a:
            continue
        out.append(p)
        covered_a.add(_key_for_a(p))
    return out

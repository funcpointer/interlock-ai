"""Semantic alignment via embeddings.

Injectable ``embed_fn`` returns a dict mapping each text to its vector. Real
implementation in ``align/embed.py`` calls Voyage. Tests inject deterministic
stubs.

Cosine similarity above ``threshold`` emits an AlignedPair. Used as a fallback
for records that exact-name + positional matching could not pair.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from interlock.align.exact import AlignedPair
from interlock.extract.parameters import ParameterRecord
from interlock.extract.units import equivalent

EmbedFn = Callable[[list[str]], dict[str, list[float]]]


def _cos(u: list[float], v: list[float]) -> float:
    if not u or not v:
        return 0.0
    num = sum(x * y for x, y in zip(u, v, strict=False))
    du = math.sqrt(sum(x * x for x in u))
    dv = math.sqrt(sum(y * y for y in v))
    return num / (du * dv) if du and dv else 0.0


def align_semantic(
    a: list[ParameterRecord],
    b: list[ParameterRecord],
    embed_fn: EmbedFn,
    threshold: float = 0.85,
) -> list[AlignedPair]:
    if not a or not b:
        return []
    names = list({r.name for r in a} | {r.name for r in b})
    vecs = embed_fn(names)
    out: list[AlignedPair] = []
    for ra in a:
        va = vecs.get(ra.name)
        if not va:
            continue
        best_sim = 0.0
        best_rb: ParameterRecord | None = None
        for rb in b:
            # Only pair records of compatible value-type: both numeric or both string.
            if (ra.normalized_magnitude is None) != (rb.normalized_magnitude is None):
                continue
            vb = vecs.get(rb.name)
            if not vb:
                continue
            sim = _cos(va, vb)
            if sim > best_sim:
                best_sim, best_rb = sim, rb
        if best_rb is not None and best_sim >= threshold:
            out.append(
                AlignedPair(
                    a=ra,
                    b=best_rb,
                    name_match_confidence=best_sim,
                    value_equivalent=equivalent(ra.raw_value, best_rb.raw_value),
                )
            )
    return out

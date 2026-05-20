"""Confidence assembly per SCOPE.md §4 item 9: extraction × match × authority."""

from __future__ import annotations


def flag_confidence(*, extraction: float, match: float, authority: float) -> float:
    raw = extraction * match * authority
    return max(0.0, min(1.0, raw))

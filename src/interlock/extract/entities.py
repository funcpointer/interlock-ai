"""Entity + Claim layer (Phase 14, additive).

Wraps the existing ``ParameterRecord`` evidence layer with an ``Entity``
(equipment / line / circuit identifier) and a ``Claim`` (one
``(entity, attribute, value)`` statement backed by a source record).

This is purely additive — no existing tests construct claims by hand, and
``ParameterRecord`` is unchanged. The pipeline adopts claims as a parallel
view in Task 14.4.

DocETL vocabulary alignment
---------------------------
- Entity inference + canonical attribute = ``resolve`` operator.
- ``claims_from_records`` = ``map`` operator (per-record transform).
- Future cross-doc grouping by ``(entity, attribute)`` = ``reduce``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from interlock.align.semantic import canonical_name
from interlock.extract.parameters import ParameterRecord

EntityType = Literal[
    "transformer",
    "pump",
    "motor",
    "breaker",
    "bus",
    "line",
    "motor_operated_valve",
    "valve",
    "relay",
    "implicit",
]


# Each pattern captures only the *tail* (the unique identifier of the
# equipment) — never the prefix. The id_prefix column supplies the
# canonical-lowercase prefix used in the entity.id. The label column
# supplies a format string applied to the matched groups for the human-
# readable label.
#
# Ordering matters: longer/more specific patterns first so 'MOV-' wins
# over 'V-' on 'MOV-100'.
_TAG_PATTERNS: list[tuple[re.Pattern[str], EntityType, str, str]] = [
    # 2+ letter prefixes
    (re.compile(r"\bMOV-(\d+)\b", re.IGNORECASE), "motor_operated_valve", "mov", "MOV-{0}"),
    (re.compile(r"\bXFMR-(\d+)\b", re.IGNORECASE), "transformer", "xfmr", "XFMR-{0}"),
    (re.compile(r"\bCB-(\d+)\b", re.IGNORECASE), "breaker", "cb", "CB-{0}"),
    (re.compile(r"\bLine\s+(\d+[A-Za-z]?)\b", re.IGNORECASE), "line", "line", "Line {0}"),
    (re.compile(r"\bBus\s+([A-Z])-(\d+)\b"), "bus", "", "Bus {0}-{1}"),
    (re.compile(r"\bRelay\s+([A-Z])-(\d+)\b", re.IGNORECASE), "relay", "", "Relay {0}-{1}"),
    # Single-letter prefixes — least specific, come last
    (re.compile(r"\bT-(\d+)\b"), "transformer", "t", "T-{0}"),
    (re.compile(r"\bP-(\d+)\b"), "pump", "p", "P-{0}"),
    (re.compile(r"\bM-(\d+)\b"), "motor", "m", "M-{0}"),
    (re.compile(r"\bV-(\d+)\b"), "valve", "v", "V-{0}"),
    (re.compile(r"\bR-(\d+)\b"), "relay", "r", "R-{0}"),
]


@dataclass(frozen=True)
class Entity:
    """A piece of equipment, a line, a bus, etc. — anything claims can be
    *about*. ``id`` is the canonical key used for cross-doc grouping.
    """

    id: str
    type: EntityType
    label: str


@dataclass(frozen=True)
class Claim:
    """One statement: ``entity.attribute = value`` with citation back to
    the source ``ParameterRecord``.

    ``attribute`` is canonicalized (via ``align.semantic.canonical_name``) so
    that ``%Z``, ``Rated Impedance``, etc. all collapse to the same string.
    This lets downstream code group by ``(entity, attribute)`` without
    re-canonicalizing.
    """

    entity: Entity
    attribute: str
    raw_value: str
    source_record: ParameterRecord

    @property
    def doc_id(self) -> str:
        return self.source_record.doc_id

    @property
    def page(self) -> int:
        return self.source_record.page


def _id_from_match(match: re.Match[str], id_prefix: str) -> str:
    """Build a canonical entity id: lowercase prefix + underscore + tail groups.

    Empty ``id_prefix`` means no prefix (patterns like Bus B-3 → b_3 supply
    the prefix as a capture group themselves).
    """
    tail = "_".join(g for g in match.groups() if g).lower()
    if id_prefix:
        return f"{id_prefix}_{tail}"
    return tail


def infer_entity_from_text(text: str, *, doc_id: str) -> Entity | None:
    """Find the first equipment / line / bus tag in *text* and build an Entity.

    Returns None when no tag matches. The implicit-entity fallback lives in
    ``claims_from_records`` — this function is purely about tag detection so
    it stays composable.
    """
    best: tuple[int, Entity] | None = None
    for pattern, etype, id_prefix, label_fmt in _TAG_PATTERNS:
        m = pattern.search(text)
        if m is None:
            continue
        candidate = Entity(
            id=_id_from_match(m, id_prefix),
            type=etype,
            label=label_fmt.format(*m.groups()),
        )
        # Keep the left-most match across all patterns so output is
        # deterministic regardless of pattern declaration order.
        if best is None or m.start() < best[0]:
            best = (m.start(), candidate)
    return best[1] if best is not None else None


def _implicit_entity(doc_id: str) -> Entity:
    """Per-doc placeholder used when a record has no equipment tag in its span."""
    safe_doc = re.sub(r"[^A-Za-z0-9]+", "_", doc_id).strip("_").lower() or "doc"
    return Entity(
        id=f"implicit_{safe_doc}",
        type="implicit",
        label=f"(unnamed equipment in {doc_id})",
    )


def claims_from_records(records: list[ParameterRecord]) -> list[Claim]:
    """Lift each record into a Claim, inferring entity from the source span.

    Pure function — same input always yields the same output, so the result
    is safe to cache by hash of the record list.
    """
    out: list[Claim] = []
    for r in records:
        entity = infer_entity_from_text(r.span_text, doc_id=r.doc_id)
        if entity is None:
            entity = _implicit_entity(r.doc_id)
        out.append(
            Claim(
                entity=entity,
                attribute=canonical_name(r.name),
                raw_value=r.raw_value,
                source_record=r,
            )
        )
    return out

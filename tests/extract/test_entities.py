"""Entity + Claim layer invariants (Phase 14, additive).

The Entity + Claim model wraps the existing ParameterRecord *evidence* layer
without breaking it. Tests assert:

1. Entity tag inference from realistic text patterns (XFMR-001, P-101,
   Line 14A, Bus B-3, MOV-100).
2. Fallback to implicit-entity per doc when no tag is present.
3. Claim carries a back-pointer to the source ParameterRecord (lossless).
4. claims_from_records is a pure function: same input → same output.
5. Equipment-type inference from tag prefix.
"""

from __future__ import annotations

import pytest

from interlock.extract.entities import (
    Claim,
    Entity,
    claims_from_records,
    infer_entity_from_text,
)
from interlock.extract.parameters import ParameterRecord


def _record(name: str, raw: str, doc: str = "doc_a", span: str | None = None) -> ParameterRecord:
    return ParameterRecord(
        doc_id=doc,
        page=1,
        bbox=(0, 0, 100, 10),
        section=None,
        span_text=span if span is not None else f"{name}: {raw}",
        name=name,
        raw_value=raw,
        normalized_magnitude=None,
        normalized_unit=None,
    )


# ----- Entity inference -----


def test_infer_xfmr_tag() -> None:
    entity = infer_entity_from_text("XFMR-001 Rated Power: 1000 kVA", doc_id="doc_a")
    assert entity is not None
    assert entity.id == "xfmr_001"
    assert entity.type == "transformer"
    assert entity.label == "XFMR-001"


def test_infer_pump_tag() -> None:
    entity = infer_entity_from_text("Pump P-101 flow rate is 1200 gpm", doc_id="doc_a")
    assert entity is not None
    assert entity.id == "p_101"
    assert entity.type == "pump"


def test_infer_line_tag() -> None:
    entity = infer_entity_from_text("Line 14A material: SS316", doc_id="doc_a")
    assert entity is not None
    assert entity.id == "line_14a"
    assert entity.type == "line"


def test_infer_bus_tag() -> None:
    entity = infer_entity_from_text("Bus B-3 voltage 13.8 kV", doc_id="doc_a")
    assert entity is not None
    assert entity.id == "b_3"
    assert entity.type == "bus"


def test_infer_breaker_tag() -> None:
    entity = infer_entity_from_text("Breaker CB-52 trip setting 600 A", doc_id="doc_a")
    assert entity is not None
    assert entity.id == "cb_52"
    assert entity.type == "breaker"


def test_no_tag_returns_none() -> None:
    """Generic spec text without an explicit tag returns None."""
    entity = infer_entity_from_text("Rated Voltage: 132 kV", doc_id="doc_a")
    assert entity is None


def test_multiple_tags_returns_first() -> None:
    """When text mentions multiple tagged equipment, return the first
    (left-most) — deterministic + caller can re-scan if needed."""
    entity = infer_entity_from_text(
        "XFMR-001 feeds XFMR-002 via Line 14A", doc_id="doc_a"
    )
    assert entity is not None
    assert entity.id == "xfmr_001"


# ----- Claim wraps ParameterRecord -----


def test_claim_preserves_source_record() -> None:
    rec = _record("Rated Power", "1000 kVA", span="XFMR-001 Rated Power: 1000 kVA")
    claims = claims_from_records([rec])
    assert len(claims) == 1
    c = claims[0]
    assert isinstance(c, Claim)
    assert c.source_record is rec  # identity preserved
    assert c.raw_value == "1000 kVA"


def test_implicit_entity_when_no_tag() -> None:
    """Span without an equipment tag → implicit entity per doc."""
    rec = _record("Rated Voltage", "132 kV", doc="doc_a", span="Rated Voltage: 132 kV")
    claims = claims_from_records([rec])
    assert len(claims) == 1
    e = claims[0].entity
    assert e.id == "implicit_doc_a"
    assert e.type == "implicit"


def test_explicit_entity_inferred_from_span() -> None:
    rec = _record(
        "Rated Power", "1000 kVA", doc="doc_a", span="XFMR-001 Rated Power: 1000 kVA"
    )
    claims = claims_from_records([rec])
    e = claims[0].entity
    assert e.id == "xfmr_001"
    assert e.type == "transformer"


def test_claims_from_records_is_pure() -> None:
    """Same input → same output. Required for cache key stability."""
    rec = _record("Rated Power", "1000 kVA")
    a = claims_from_records([rec])
    b = claims_from_records([rec])
    assert len(a) == len(b) == 1
    assert a[0] == b[0]


def test_claim_attribute_uses_canonical_phrase() -> None:
    """Different name aliases on the same parameter family collapse to one
    canonical attribute string — enables (entity, attribute) grouping."""
    rec_a = _record("%Z", "5.75%", span="XFMR-001 %Z = 5.75%")
    rec_b = _record("Rated Impedance", "5.75%", span="XFMR-001 Rated Impedance: 5.75%")
    claims = claims_from_records([rec_a, rec_b])
    assert claims[0].attribute == claims[1].attribute


def test_multi_equipment_doc_yields_one_claim_per_entity() -> None:
    """When two equipment tags appear in a doc, each gets its own claim."""
    a = _record("Rated Power", "1000 kVA", span="XFMR-001 Rated Power: 1000 kVA")
    b = _record("Rated Power", "750 kVA", span="XFMR-002 Rated Power: 750 kVA")
    claims = claims_from_records([a, b])
    entities = {c.entity.id for c in claims}
    assert entities == {"xfmr_001", "xfmr_002"}


# ----- Entity is hashable and comparable -----


def test_entity_is_hashable() -> None:
    e1 = Entity(id="xfmr_001", type="transformer", label="XFMR-001")
    e2 = Entity(id="xfmr_001", type="transformer", label="XFMR-001")
    assert hash(e1) == hash(e2)
    assert {e1, e2} == {e1}


def test_claim_equality_uses_canonical_form() -> None:
    rec = _record("Rated Power", "1000 kVA", span="XFMR-001 Rated Power: 1000 kVA")
    c1 = claims_from_records([rec])[0]
    c2 = claims_from_records([rec])[0]
    assert c1 == c2


@pytest.mark.parametrize(
    "tag,expected_id,expected_type",
    [
        ("XFMR-001", "xfmr_001", "transformer"),
        ("T-200", "t_200", "transformer"),
        ("P-101", "p_101", "pump"),
        ("M-50", "m_50", "motor"),
        ("CB-52", "cb_52", "breaker"),
        ("Bus B-3", "b_3", "bus"),
        ("Line 14A", "line_14a", "line"),
        ("MOV-100", "mov_100", "motor_operated_valve"),
        ("V-200", "v_200", "valve"),
        ("Relay R-87", "r_87", "relay"),
    ],
)
def test_tag_pattern_matrix(tag: str, expected_id: str, expected_type: str) -> None:
    entity = infer_entity_from_text(f"Equipment {tag}: some attribute", doc_id="doc_a")
    assert entity is not None, f"failed to infer entity from {tag!r}"
    assert entity.id == expected_id
    assert entity.type == expected_type

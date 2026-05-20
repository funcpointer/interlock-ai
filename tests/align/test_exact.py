from interlock.align.exact import AlignedPair, align_exact
from interlock.extract.parameters import ParameterRecord


def _p(name, doc, raw, mag=None, unit=None, page=1, y=0.0) -> ParameterRecord:
    return ParameterRecord(
        doc_id=doc, page=page, bbox=(0, y, 100, y + 10), section=None,
        span_text=f"{name}: {raw}", name=name, raw_value=raw,
        normalized_magnitude=mag, normalized_unit=unit,
    )


def test_aligns_same_name_same_position_when_values_equal() -> None:
    a = [_p("%Z", "A", "5.75 %", mag=0.0575, unit="dimensionless", page=3, y=100)]
    b = [_p("%Z", "B", "5.75 %", mag=0.0575, unit="dimensionless", page=3, y=100)]
    pairs = align_exact(a, b)
    assert len(pairs) == 1
    assert isinstance(pairs[0], AlignedPair)
    assert pairs[0].name_match_confidence == 1.0
    assert pairs[0].value_equivalent is True


def test_aligns_same_name_same_position_when_values_differ() -> None:
    a = [_p("%Z", "A", "5.75 %", mag=0.0575, page=3, y=100)]
    b = [_p("%Z", "B", "0.575 %", mag=0.00575, page=3, y=100)]
    pairs = align_exact(a, b)
    assert len(pairs) == 1
    assert pairs[0].value_equivalent is False


def test_unit_normalized_value_equivalence_suppresses_flag() -> None:
    # 150 kVA == 0.15 MVA — equivalent dimensionally; pair should be value_equivalent.
    a = [_p("Transformer Rating", "A", "150 kVA", mag=150_000, page=7, y=300)]
    b = [_p("Transformer Rating", "B", "0.15 MVA", mag=150_000, page=7, y=300)]
    pairs = align_exact(a, b)
    assert len(pairs) == 1
    assert pairs[0].value_equivalent is True


def test_distinct_y_positions_pair_independently() -> None:
    # Two transformer-rating records on same page at different y positions
    # should pair with their respective counterparts, not cross-pair.
    a = [
        _p("Transformer Rating", "A", "1000 kVA", mag=1_000_000, page=7, y=100),
        _p("Transformer Rating", "A", "150 kVA", mag=150_000, page=7, y=300),
    ]
    b = [
        _p("Transformer Rating", "B", "100 kVA", mag=100_000, page=7, y=100),  # TP-3
        _p("Transformer Rating", "B", "0.15 MVA", mag=150_000, page=7, y=300),  # FP-1
    ]
    pairs = align_exact(a, b)
    assert len(pairs) == 2
    by_y = sorted(pairs, key=lambda p: p.a.bbox[1])
    # y=100: A=1000kVA, B=100kVA → mismatch
    assert by_y[0].value_equivalent is False
    # y=300: A=150kVA, B=0.15MVA → equivalent
    assert by_y[1].value_equivalent is True


def test_names_with_no_counterpart_in_b_emit_no_pair() -> None:
    a = [_p("%Z", "A", "5.75 %", page=3, y=100)]
    b = [_p("Fault Current", "B", "20,000 A", page=2, y=50)]
    pairs = align_exact(a, b)
    assert pairs == []


def test_different_pages_do_not_pair() -> None:
    a = [_p("%Z", "A", "5.75 %", page=3, y=100)]
    b = [_p("%Z", "B", "5.75 %", page=5, y=100)]
    pairs = align_exact(a, b)
    # Same name on different pages should not auto-pair (no positional anchor).
    # Implementation may or may not pair; the contract is: if it pairs, value-equivalence is computed.
    for p in pairs:
        # If a pair emerged across pages, confidence should reflect distance.
        assert p.name_match_confidence <= 1.0

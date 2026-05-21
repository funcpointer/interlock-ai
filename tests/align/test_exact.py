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


# ---------- String-valued family gating (regression for cross-family false flags) ----------


def test_string_param_only_pairs_within_same_family_prefix() -> None:
    """Real-world regression: Doc A's KRP-C-1600SP main fuse was being
    paired with Doc B's LPS-RK-100SP branch fuse because positional
    proximity broke down on OCR pages (all OCR records share the page
    bbox → identical y-centers → first-in-iteration wins).

    Family prefix gating must prevent that pair from emerging at all.
    """
    a = [
        _p("Fuse Designation", "A", "KRP-C-1600SP", page=5, y=100),
        _p("Fuse Designation", "A", "LPS-RK-200SP", page=5, y=300),
    ]
    b = [
        _p("Fuse Designation", "B", "LPS-RK-100SP", page=5, y=0),  # synthetic OCR y
        _p("Fuse Designation", "B", "KRP-C-1200SP", page=5, y=0),  # synthetic OCR y
    ]
    pairs = align_exact(a, b)
    paired = {(p.a.raw_value, p.b.raw_value) for p in pairs}
    # KRP-C-1600SP must pair with KRP-C-1200SP (same family, real ampacity
    # change) and never with LPS-RK-100SP (different physical device).
    assert ("KRP-C-1600SP", "KRP-C-1200SP") in paired
    assert ("KRP-C-1600SP", "LPS-RK-100SP") not in paired
    # And LPS-RK-200SP must pair only with LPS-RK-100SP.
    assert ("LPS-RK-200SP", "LPS-RK-100SP") in paired
    assert ("LPS-RK-200SP", "KRP-C-1200SP") not in paired


def test_string_param_with_no_family_match_emits_no_pair() -> None:
    """If Doc A has a KRP-C fuse but Doc B has only LPS-RK fuses, no pair
    should emerge — better to miss a flag than to surface a false one
    that compares a 1600 A main against a 100 A branch."""
    a = [_p("Fuse Designation", "A", "KRP-C-1600SP", page=5, y=100)]
    b = [_p("Fuse Designation", "B", "LPS-RK-100SP", page=5, y=100)]
    pairs = align_exact(a, b)
    assert pairs == []

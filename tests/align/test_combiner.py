from interlock.align.combiner import combine_alignments
from interlock.align.exact import AlignedPair
from interlock.extract.parameters import ParameterRecord


def _p(name: str, doc: str, page: int = 1, y: float = 0.0) -> ParameterRecord:
    return ParameterRecord(
        doc_id=doc, page=page, bbox=(0, y, 100, y + 10), section=None,
        span_text=name, name=name, raw_value="x",
        normalized_magnitude=None, normalized_unit=None,
    )


def test_exact_takes_precedence_over_semantic() -> None:
    a_rec = _p("Z", "A")
    b_exact = _p("Z", "B")
    b_semantic = _p("%Z", "B")
    exact = [AlignedPair(a_rec, b_exact, 1.0, True)]
    semantic = [AlignedPair(a_rec, b_semantic, 0.95, False)]
    out = combine_alignments(exact, semantic)
    assert len(out) == 1
    assert out[0].b.name == "Z"


def test_semantic_fills_when_no_exact_for_that_a_record() -> None:
    a_rec1 = _p("Z", "A")
    a_rec2 = _p("Impedance", "A")
    b_exact = _p("Z", "B")
    b_semantic = _p("%Z", "B")
    exact = [AlignedPair(a_rec1, b_exact, 1.0, True)]
    semantic = [AlignedPair(a_rec2, b_semantic, 0.95, False)]
    out = combine_alignments(exact, semantic)
    assert len(out) == 2


def test_empty_inputs() -> None:
    assert combine_alignments([], []) == []

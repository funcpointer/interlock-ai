from interlock.citation.render import Citation, render_citation
from interlock.extract.parameters import ParameterRecord


def _r(pdf: str = "fixtures/pdfs/doc_a_60pct.pdf") -> ParameterRecord:
    return ParameterRecord(
        doc_id=pdf, page=3, bbox=(72, 100, 200, 115),
        section="Time Current Curve #1 (TCC1)",
        span_text="5.75%Z, liquid",
        name="%Z", raw_value="5.75 %",
        normalized_magnitude=0.0575, normalized_unit="dimensionless",
    )


def test_render_returns_full_citation_tuple_and_png_bytes() -> None:
    c = render_citation(_r())
    assert isinstance(c, Citation)
    assert c.doc_id.endswith("doc_a_60pct.pdf")
    assert c.page == 3
    assert c.section == "Time Current Curve #1 (TCC1)"
    assert c.quoted_text == "5.75%Z, liquid"
    assert isinstance(c.snippet_png, (bytes, bytearray))
    # PNG magic bytes
    assert c.snippet_png[:4] == b"\x89PNG"


def test_render_handles_bbox_at_page_edge() -> None:
    r = ParameterRecord(
        doc_id="fixtures/pdfs/doc_a_60pct.pdf", page=1,
        bbox=(0, 0, 50, 20), section=None,
        span_text="edge", name="X", raw_value="x",
        normalized_magnitude=None, normalized_unit=None,
    )
    c = render_citation(r)
    assert c.snippet_png[:4] == b"\x89PNG"

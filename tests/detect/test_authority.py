from interlock.detect.authority import AuthorityDecision, authority_for


def test_hardcoded_doc_a_authoritative_over_doc_b() -> None:
    d = authority_for(
        doc_a_id="doc_a_60pct.pdf",
        doc_b_id="doc_b_90pct.pdf",
        parameter_name="%Z",
    )
    assert isinstance(d, AuthorityDecision)
    assert d.authoritative_doc_id == "doc_a_60pct.pdf"
    assert d.deviating_doc_id == "doc_b_90pct.pdf"
    assert 0 < d.confidence <= 1
    assert d.rule

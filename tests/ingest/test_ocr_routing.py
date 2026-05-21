"""OCR routing invariants — verifies the vision fallback wires correctly.

The locked scanned fixture ``fixtures/pdfs/doc_a_scanned.pdf`` is a
deterministic JPEG-encoded raster of every page of ``doc_a_60pct.pdf``.
PyMuPDF sees zero native text on every page; the coverage router must
classify every page as low-coverage, and when ``enable_vision_ocr=True``
the vision pass (mocked here) must produce page-level Spans that flow
into the rest of the pipeline.

Live-API vision quality is covered separately in
``tests/real_world/test_ocr_yield.py`` (slow-marked).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from interlock.ingest.pdf import MIN_CHARS_PER_PAGE, IngestResult, ingest
from interlock.ingest.vision_fallback import VisionResult

SCANNED = Path("fixtures/pdfs/doc_a_scanned.pdf")
NATIVE = Path("fixtures/pdfs/doc_a_60pct.pdf")


# ---------- Coverage router ----------


def test_scanned_pdf_yields_zero_native_spans() -> None:
    """The scanned fixture must look like a scan to PyMuPDF: no native text."""
    assert SCANNED.exists(), f"missing fixture {SCANNED}"
    result = ingest(str(SCANNED), doc_id="scanned")
    assert isinstance(result, IngestResult)
    # Every page is image-only -> spans list should be empty (no native text
    # extracted) and every page should appear in low_coverage_pages.
    assert result.spans == [], f"unexpected native spans on scanned PDF: {len(result.spans)}"
    assert len(result.low_coverage_pages) >= 9, (
        f"expected all 9+ pages flagged low-coverage; got {result.low_coverage_pages}"
    )


def test_native_pdf_has_zero_low_coverage_pages() -> None:
    """Sanity: the native PDF must NOT be flagged as low-coverage."""
    result = ingest(str(NATIVE), doc_id="native")
    assert result.low_coverage_pages == []


# ---------- Vision wiring ----------


def test_vision_ocr_off_by_default_produces_no_ocr_spans() -> None:
    result = ingest(str(SCANNED), doc_id="scanned")
    assert result.ocr_pages == []


def test_enable_vision_ocr_routes_every_low_coverage_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When enable_vision_ocr=True, every low-coverage page is routed
    through vision_extract_page, and the returned text becomes a page-level
    Span. We stub vision_extract_page so this stays a fast/offline test."""

    calls: list[int] = []

    def fake_vision(pdf_path: str, page: int) -> VisionResult:
        calls.append(page)
        return VisionResult(
            text=f"OCR-recovered text from page {page} — Rated Power: 1000 kVA",
            confidence=0.9,
        )

    monkeypatch.setattr(
        "interlock.ingest.pdf.vision_extract_page",  # imported lazily inside _ocr_pages
        fake_vision,
        raising=False,
    )
    # The lazy import in _ocr_pages means we also have to patch the source
    # module so the function reference is the stub.
    monkeypatch.setattr(
        "interlock.ingest.vision_fallback.vision_extract_page",
        fake_vision,
    )

    result = ingest(str(SCANNED), doc_id="scanned", enable_vision_ocr=True)

    # Every low-coverage page was routed through the vision callable
    assert len(calls) == len(result.low_coverage_pages)
    # Every successful OCR page is represented by ≥1 Span (one Span per
    # non-empty OCR line; the stub returns a single-line payload so the
    # page-set equals the span-page-set).
    assert {s.page for s in result.spans} == set(result.low_coverage_pages)
    assert len(result.ocr_pages) == len(result.low_coverage_pages)
    # Each Span is a per-line synthetic span carrying part of the OCR text
    # at the whole-page bbox (x0=0).
    for span in result.spans:
        assert "OCR-recovered text" in span.text
        assert span.bbox[0] == 0


def test_vision_ocr_skips_pages_returning_empty_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A vision call that returns whitespace-only text should NOT produce
    a Span and should NOT appear in ocr_pages."""

    def empty_vision(pdf_path: str, page: int) -> VisionResult:
        return VisionResult(text="   \n  \t", confidence=0.0)

    monkeypatch.setattr(
        "interlock.ingest.vision_fallback.vision_extract_page",
        empty_vision,
    )

    result = ingest(str(SCANNED), doc_id="scanned", enable_vision_ocr=True)
    assert result.ocr_pages == []
    assert all(s.text.strip() for s in result.spans), (
        "no empty-text spans should be retained"
    )


def test_vision_ocr_continues_on_per_page_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If vision_extract_page raises on some page, ingest must surface the
    other pages without aborting the whole pass."""

    def flaky_vision(pdf_path: str, page: int) -> VisionResult:
        if page % 2 == 0:
            raise RuntimeError("simulated vision failure on even pages")
        return VisionResult(text=f"page {page} content", confidence=0.8)

    monkeypatch.setattr(
        "interlock.ingest.vision_fallback.vision_extract_page",
        flaky_vision,
    )

    result = ingest(str(SCANNED), doc_id="scanned", enable_vision_ocr=True)
    # Only odd-numbered pages produce OCR spans
    expected_odd = [p for p in result.low_coverage_pages if p % 2 == 1]
    assert result.ocr_pages == expected_odd
    assert {s.page for s in result.spans} == set(expected_odd)


def test_native_pdf_with_vision_enabled_does_no_ocr_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When a PDF is fully native-text, enabling vision must not call the
    vision model at all (cost saver + idempotency)."""

    called = {"n": 0}

    def panic_vision(pdf_path: str, page: int) -> VisionResult:
        called["n"] += 1
        return VisionResult(text="should not run", confidence=1.0)

    monkeypatch.setattr(
        "interlock.ingest.vision_fallback.vision_extract_page",
        panic_vision,
    )

    result = ingest(str(NATIVE), doc_id="native", enable_vision_ocr=True)
    assert called["n"] == 0
    assert result.ocr_pages == []
    # All native-extracted spans are still present
    assert result.spans
    # And we did detect 0 low-coverage pages on a native doc
    assert result.low_coverage_pages == []


# ---------- Per-line OCR span emission ----------


def test_vision_ocr_emits_one_span_per_visual_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each non-empty newline-separated line from the vision model becomes
    its own Span. Critical for snippet quality — a whole-page blob would
    glue unrelated lines together in the per-flag excerpt."""

    multi_line_payload = (
        "1000KVA XFMR Inrush Point | 12 x FLA @ .1 Seconds\n"
        "1000KVA XFMR Damage Curves | 5.75%Z, liquid filled\n"
        "JCN 80E | E-Rated Fuse\n"
        "\n"  # blank line must be skipped
        "  \n"  # whitespace-only line must be skipped
        "#6 Conductor Damage Curve | Copper, XLP Insulation"
    )

    def fake_vision(pdf_path: str, page: int) -> VisionResult:
        return VisionResult(text=multi_line_payload, confidence=0.85)

    monkeypatch.setattr(
        "interlock.ingest.vision_fallback.vision_extract_page",
        fake_vision,
    )

    result = ingest(str(SCANNED), doc_id="scanned", enable_vision_ocr=True)
    # Every low-coverage page should yield exactly 4 non-blank lines.
    expected_lines_per_page = 4
    expected_total_spans = expected_lines_per_page * len(result.low_coverage_pages)
    assert len(result.spans) == expected_total_spans
    # Each Span text is a single line (no embedded newlines).
    for s in result.spans:
        assert "\n" not in s.text
        assert s.text.strip() == s.text
    # The 5.75%Z line must appear as its own Span — this is the snippet-
    # quality regression guard. If splitting regresses, this line would
    # be glued to surrounding rows and the assertion fails.
    impedance_spans = [s for s in result.spans if "5.75%Z, liquid filled" in s.text]
    assert len(impedance_spans) == len(result.low_coverage_pages)
    for s in impedance_spans:
        # Just the one line, not the whole payload.
        assert s.text == "1000KVA XFMR Damage Curves | 5.75%Z, liquid filled"


# ---------- Coverage threshold constant ----------


def test_min_chars_per_page_constant_is_documented() -> None:
    """If we ever change MIN_CHARS_PER_PAGE the change should be deliberate."""
    assert MIN_CHARS_PER_PAGE == 80

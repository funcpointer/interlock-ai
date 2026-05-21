"""Top-level ingestion orchestrator.

Runs PyMuPDF span extraction + Camelot table extraction. Flags pages with
near-zero text density and, when ``enable_vision_ocr=True``, falls back to
a vision OCR pass (Claude Sonnet 4.5) on each such page. Vision-derived
text is wrapped as page-level Spans so the rest of the pipeline sees a
uniform input stream.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import fitz

from .tables import Table, extract_tables
from .text import Span, aggregate_line_spans, extract_spans

MIN_CHARS_PER_PAGE = 80


@dataclass(frozen=True)
class IngestResult:
    doc_id: str
    spans: list[Span]
    tables: list[Table]
    low_coverage_pages: list[int] = field(default_factory=list)
    ocr_pages: list[int] = field(default_factory=list)  # pages that fell back to vision OCR


def _ocr_pages(
    pdf_path: str,
    doc_id: str,
    page_numbers: list[int],
    source_path: str,
) -> tuple[list[Span], list[int]]:
    """Vision-OCR a list of pages, return Spans + the pages that produced text.

    Import is deferred so callers who don't enable OCR don't need an
    Anthropic key available. Each OCR page becomes one synthetic Span
    occupying the full page bbox (the bbox is the page rect — the vision
    model doesn't return word-level coordinates).
    """
    from interlock.ingest.vision_fallback import vision_extract_page

    out_spans: list[Span] = []
    out_pages: list[int] = []
    doc = fitz.open(pdf_path)
    try:
        for page_num in page_numbers:
            try:
                result = vision_extract_page(pdf_path, page_num)
            except Exception:  # pragma: no cover — surface as no-op
                continue
            text = (result.text or "").strip()
            if not text:
                continue
            rect = doc[page_num - 1].rect
            out_spans.append(
                Span(
                    doc_id=doc_id,
                    page=page_num,
                    bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                    text=text,
                    source_path=source_path,
                )
            )
            out_pages.append(page_num)
    finally:
        doc.close()
    return out_spans, out_pages


def ingest(
    pdf_path: str,
    doc_id: str | None = None,
    *,
    table_max_pages: int | None = None,
    enable_vision_ocr: bool = False,
) -> IngestResult:
    """Run PyMuPDF span + Camelot table extraction with optional vision OCR.

    ``table_max_pages`` caps the Camelot page span; ``None`` defers to the
    default in ``extract_tables`` (currently 20). Pass an int to override
    or 0 to scan every page (long PDFs will be slow).

    ``enable_vision_ocr=True`` routes every low-coverage page (under 80
    native chars) through ``vision_extract_page`` (Claude Sonnet 4.5).
    Requires ``ANTHROPIC_API_KEY``. Each OCR page yields one synthetic
    page-level Span containing the model's transcribed text. Surfaced
    pages are reported in ``IngestResult.ocr_pages``.
    """
    did = doc_id or pdf_path
    raw_spans = extract_spans(pdf_path, did)
    merged_spans = aggregate_line_spans(raw_spans)
    if table_max_pages is None:
        tables = extract_tables(pdf_path, doc_id=did)
    else:
        tables = extract_tables(pdf_path, doc_id=did, max_pages=table_max_pages or None)

    low_cov: list[int] = []
    doc = fitz.open(pdf_path)
    try:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if len(text) < MIN_CHARS_PER_PAGE:
                low_cov.append(i)
    finally:
        doc.close()

    ocr_pages: list[int] = []
    if enable_vision_ocr and low_cov:
        ocr_spans, ocr_pages = _ocr_pages(pdf_path, did, low_cov, pdf_path)
        merged_spans = merged_spans + ocr_spans

    return IngestResult(
        doc_id=did,
        spans=merged_spans,
        tables=tables,
        low_coverage_pages=low_cov,
        ocr_pages=ocr_pages,
    )

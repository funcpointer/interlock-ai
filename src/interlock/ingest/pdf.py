"""Top-level ingestion orchestrator.

Runs PyMuPDF span extraction + Camelot table extraction. Flags pages with
near-zero text density and, when ``enable_vision_ocr=True``, falls back to
a vision OCR pass (Claude Sonnet 4.5) on each such page. Vision-derived
text is wrapped as page-level Spans so the rest of the pipeline sees a
uniform input stream.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import fitz

from .tables import Table, extract_tables
from .text import Span, aggregate_line_spans, extract_spans

OcrProgressCallback = Callable[[int, int, int], None]  # (completed, total, page_num)
OCR_MAX_WORKERS = 5  # cap concurrent vision API calls (Anthropic tier-aware)

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
    progress_cb: OcrProgressCallback | None = None,
) -> tuple[list[Span], list[int]]:
    """Vision-OCR a list of pages in parallel; return Spans + completed pages.

    Vision API calls are I/O-bound so a ThreadPoolExecutor reduces the
    wall-clock from N×latency to roughly ceil(N/workers)×latency. On a
    9-page scanned PDF that's ~15-25s instead of ~90-180s.

    ``progress_cb`` (if provided) is called once per completed page with
    ``(completed_count, total, last_page_number)`` so a UI can render a
    progress bar / status update. The callback runs on the main thread
    via ``as_completed``.
    """
    from interlock.ingest.vision_fallback import vision_extract_page

    out_spans: list[Span] = []
    out_pages: list[int] = []
    if not page_numbers:
        return out_spans, out_pages

    doc = fitz.open(pdf_path)
    try:
        page_rects = {p: doc[p - 1].rect for p in page_numbers}
    finally:
        doc.close()

    completed = 0
    total = len(page_numbers)
    with ThreadPoolExecutor(max_workers=OCR_MAX_WORKERS) as ex:
        future_to_page = {
            ex.submit(vision_extract_page, pdf_path, p): p for p in page_numbers
        }
        for future in as_completed(future_to_page):
            page_num = future_to_page[future]
            completed += 1
            try:
                result = future.result()
            except Exception:  # pragma: no cover — surface as no-op
                if progress_cb is not None:
                    progress_cb(completed, total, page_num)
                continue
            text = (result.text or "").strip()
            if not text:
                if progress_cb is not None:
                    progress_cb(completed, total, page_num)
                continue
            rect = page_rects[page_num]
            # Split OCR text into per-line Spans. The v2 vision prompt
            # preserves visual line breaks, so each non-empty newline-
            # separated line corresponds to one line on the page. Emitting
            # one Span per line means downstream ParameterRecord.span_text
            # carries just the line containing the matched value — the UI
            # snippet then reads cleanly instead of pulling unrelated
            # neighbours from a whole-page blob.
            #
            # Bbox stays whole-page because vision lacks per-line bbox;
            # the citation image therefore still shows the full page,
            # which the UI already captions as a whole-page OCR snippet.
            page_bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
            line_count = 0
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                out_spans.append(
                    Span(
                        doc_id=doc_id,
                        page=page_num,
                        bbox=page_bbox,
                        text=line,
                        source_path=source_path,
                    )
                )
                line_count += 1
            if line_count == 0:
                # All lines were whitespace-only after stripping — skip page.
                if progress_cb is not None:
                    progress_cb(completed, total, page_num)
                continue
            out_pages.append(page_num)
            if progress_cb is not None:
                progress_cb(completed, total, page_num)

    # Deterministic order — pages may have completed out of order in the pool.
    out_spans.sort(key=lambda s: s.page)
    out_pages.sort()
    return out_spans, out_pages


def ingest(
    pdf_path: str,
    doc_id: str | None = None,
    *,
    table_max_pages: int | None = None,
    enable_vision_ocr: bool = False,
    ocr_progress_cb: OcrProgressCallback | None = None,
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
        ocr_spans, ocr_pages = _ocr_pages(
            pdf_path, did, low_cov, pdf_path, progress_cb=ocr_progress_cb
        )
        merged_spans = merged_spans + ocr_spans

    return IngestResult(
        doc_id=did,
        spans=merged_spans,
        tables=tables,
        low_coverage_pages=low_cov,
        ocr_pages=ocr_pages,
    )

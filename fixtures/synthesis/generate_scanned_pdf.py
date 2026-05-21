"""Render an existing PDF as a scanned-style image-only PDF.

Used to test the vision-OCR fallback path: take Doc A (a native-text PDF),
render every page as a raster image at 150 DPI, and embed those images
into a new PDF. The resulting PDF has zero native text — exactly what a
scanned document looks like to PyMuPDF.

Run:
    uv run python fixtures/synthesis/generate_scanned_pdf.py

Writes ``fixtures/pdfs/doc_a_scanned.pdf`` and appends its sha256 to
``fixtures/pdfs/HASHES.txt``.
"""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import fitz

SRC = Path("fixtures/pdfs/doc_a_60pct.pdf")
OUT = Path("fixtures/pdfs/doc_a_scanned.pdf")
HASHES = Path("fixtures/pdfs/HASHES.txt")
DPI = 100  # Enough for OCR; keeps fixture under ~3 MB after JPEG compression


def main() -> None:
    src = fitz.open(str(SRC))
    out = fitz.open()
    for page in src:
        # Render as pixmap at DPI, then re-encode as JPEG (lossy but small).
        pix = page.get_pixmap(dpi=DPI)
        jpg_bytes = pix.tobytes("jpeg", jpg_quality=70)
        new_page = out.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, stream=BytesIO(jpg_bytes))
    src.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(str(OUT))
    out.close()

    sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
    line = f"{sha}  fixtures/pdfs/doc_a_scanned.pdf\n"
    # Append only if not already present.
    existing = HASHES.read_text() if HASHES.exists() else ""
    if "doc_a_scanned.pdf" not in existing:
        with HASHES.open("a") as f:
            f.write(line)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) sha256={sha[:16]}…")


if __name__ == "__main__":
    main()

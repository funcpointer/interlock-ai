"""Vision-model fallback via Claude Sonnet 4.5.

Invoked for low-coverage pages (PyMuPDF + Camelot extracted little text).
Results are disk-cached by (PDF content hash + page + model + prompt
version) so a repeat ingest of the same scanned PDF skips the API.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from dataclasses import dataclass

import fitz
from anthropic import Anthropic

from interlock.cache import disk as disk_cache

MODEL = "claude-sonnet-4-5"
PROMPT_VERSION = "v1"
PROMPT = (
    "You are extracting engineering parameters from a single PDF page image. "
    "Return STRICT JSON only with this shape: "
    '{"text": <full extracted text as a single string>, '
    '"confidence": <number between 0 and 1>}. '
    "Preserve Greek letters and electrical units (Ω, μF, kV, MVA) and table structure."
)
_DPI = 200


@dataclass(frozen=True)
class VisionResult:
    text: str
    confidence: float


def _call_claude(image_b64: str) -> object:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )


_FENCED_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_BARE_JSON = re.compile(r"(\{.*\})", re.DOTALL)


def _parse_payload(raw: str) -> dict[str, object]:
    m = _FENCED_JSON.search(raw)
    if m:
        return json.loads(m.group(1))  # type: ignore[no-any-return]
    m = _BARE_JSON.search(raw)
    if m:
        return json.loads(m.group(1))  # type: ignore[no-any-return]
    return json.loads(raw)  # type: ignore[no-any-return]


def _pdf_content_sha(pdf_path: str) -> str:
    with open(pdf_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def vision_extract_page(pdf_path: str, page: int) -> VisionResult:
    """OCR a single page via Claude vision. Disk-cached by content + page.

    Repeat calls with the same PDF content + page return instantly.
    Cache invalidates automatically on model bump or prompt change.
    """
    cache_key = {
        "pdf_sha": _pdf_content_sha(pdf_path),
        "page": page,
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "dpi": _DPI,
    }

    def _compute() -> dict[str, float | str]:
        doc = fitz.open(pdf_path)
        try:
            pix = doc[page - 1].get_pixmap(dpi=_DPI)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
        finally:
            doc.close()
        resp = _call_claude(img_b64)
        raw = resp.content[0].text  # type: ignore[attr-defined]
        payload = _parse_payload(raw)
        return {
            "text": str(payload["text"]),
            "confidence": float(payload["confidence"]),  # type: ignore[arg-type]
        }

    cached, _hit = disk_cache.get_or_compute("vision-ocr", cache_key, _compute)
    return VisionResult(text=str(cached["text"]), confidence=float(cached["confidence"]))

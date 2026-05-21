"""Vision-model fallback via Claude Sonnet 4.5.

Invoked for low-coverage pages (PyMuPDF + Camelot extracted little text).
Results are disk-cached by (PDF content hash + page + model + prompt
version + DPI) so a repeat ingest of the same scanned PDF skips the API.

Two-pass plausibility loop (Phase 20)
-------------------------------------
A single vision call can hallucinate decimal placement on tight numeric
strings ("5.75%Z" → "0.575%Z" was a real user-reported case). Bumping
DPI helps but doesn't catch every misread.

After the first OCR call we scan the returned text for engineering
tokens and validate each against a (deliberately wide) plausibility
range per attribute family. If any token is outside its range, we
issue a SECOND call at higher DPI with a verification-focused prompt
that explicitly tells the model to re-check decimal placement. Then we
compare implausible-counts: the pass with fewer wins; tie keeps pass 1.

This costs an extra ~$0.10 only on pages that actually have a
suspicious token. Most pages take the single-call path.
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
# v4: added plausibility re-OCR (text returned may now come from a 2nd
# call); bump invalidates v3 cached entries which never ran validation.
PROMPT_VERSION = "v4"
PROMPT = (
    "You are an OCR engine for a single PDF page image of an engineering "
    "document. Transcribe every visible character verbatim. Do not paraphrase, "
    "summarize, translate, correct, or interpret content.\n\n"
    "Output format: STRICT JSON only — no prose, no fences, no commentary. "
    "Schema:\n"
    '{"text": <string>, "confidence": <number between 0 and 1>}\n\n'
    "Transcription rules:\n"
    "- Preserve visual reading order: top to bottom. In multi-column layouts "
    "transcribe the left column fully before the right column. Never interleave "
    "columns or glue unrelated lines together.\n"
    "- Preserve line breaks. Each visual line on the page becomes one "
    "newline-separated line in `text`. Do not merge lines that belong to "
    "different paragraphs, list items, table rows, or columns.\n"
    "- Preserve **row identifiers / Device IDs** as the FIRST token of each "
    "row line. Examples: circled digits ①②③…⑳㉑…㉟ stay as the original glyph; "
    "tag-style codes like \"A1\", \"F2\", \"T-200\", \"XFMR-001\" stay "
    "uppercase; numbered prefixes like \"21\" or \"3.\" stay numeric. These "
    "row IDs are how the downstream alignment knows which row in Doc A "
    "corresponds to which row in Doc B — dropping them destroys cross-doc "
    "comparison.\n"
    "- Preserve list numbering (\"1.\", \"a)\", \"i.\"), bullet markers, and "
    "indentation with leading spaces.\n"
    "- Preserve tables. Emit one row per line with cells separated by \" | \" "
    "(space pipe space). Keep the header row first if present. Always "
    "include the Device ID column as the leftmost cell when present.\n"
    "- Preserve Greek letters, electrical units, and engineering notation "
    "exactly: Ω, μ, μF, kV, MVA, kVA, °C, %, %Z, kA, mA, Hz, °, Δ, θ, Φ, λ, Σ.\n"
    "- Preserve numeric formats including thousands separators (e.g. 20,000), "
    "decimals (e.g. 5.75), scientific notation, and signed values.\n"
    "- If a character is illegible, emit \"?\" in that position rather than "
    "guessing. Do NOT guess a Device ID — emit \"?\" if you cannot read it.\n"
    "- `confidence` reflects overall page legibility (1.0 = print-quality, "
    "0.5 = scanner artifacts present, 0.2 = heavily degraded). It is not a "
    "judgment about content correctness."
)
# Verification prompt for the second pass: same rules plus a dedicated
# numeric-accuracy directive. Used only when pass-1 produced an
# implausible-looking engineering value.
_PROMPT_VERIFY = (
    PROMPT
    + "\n\n"
    "VERIFICATION PASS — the previous OCR attempt produced a numeric "
    "value that falls outside the typical engineering range for its "
    "parameter family. Re-read the page with explicit attention to "
    "decimal placement, thousands separators, and the boundary between "
    "adjacent numeric tokens. Common misreads to watch for:\n"
    "  - decimal slip: \"5.75\" misread as \"0.575\" or \"57.5\"\n"
    "  - grouped-digit slip: \"20,000\" misread as \"200,000\" or \"2,000\"\n"
    "  - subscript / superscript drift between adjacent tokens\n"
    "If a character is illegible after careful inspection, emit \"?\". "
    "Do not bias toward making the previous answer plausible."
)
# 300 DPI roughly doubles input tokens vs 200 but improves character
# recognition on degraded scans — Greek glyphs (Ω, μ), decimal placement
# in tight numeric strings ("5.75%Z" vs "0.575%Z" misreads), and small
# subscripts all benefit. The cache key includes _DPI so a bump
# invalidates cleanly without a PROMPT_VERSION change.
_DPI = 300
# Verification pass renders at 400 DPI — higher fidelity for the
# tokens most likely to have been misread by pass 1.
_DPI_VERIFY = 400


@dataclass(frozen=True)
class VisionResult:
    text: str
    confidence: float
    # True when the result was produced by the verification pass (pass 1
    # tripped plausibility validation). Exposed for telemetry / UI
    # surfacing, never gates downstream behavior.
    reocr_triggered: bool = False


def _call_claude(image_b64: str, prompt: str = PROMPT) -> object:
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
                    {"type": "text", "text": prompt},
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


# ---------- Plausibility validation ----------

# Wide ranges per attribute family. These are sanity bands, not tolerance
# bands — purpose is to catch decimal-place misreads, not to flag
# unusual-but-real values. Values outside trigger the second OCR pass.
#
# Sources for the ranges (rough envelopes, not standards):
#   impedance_pct: IEC 60076-1 typical 4-10% for power xfmrs; 1.5 lower
#     bound allows for shunt reactors / aux transformers but excludes
#     decimal-slipped 0.575 misreads.
#   rated_power_kva: 1 kVA distribution dry-type up to 1 GVA GSU.
#   voltage_kv: 0.1 kV (100 V) up to 1500 kV (UHV transmission).
#   fault_current_a: 50 A minimum (tiny systems) up to 200 kA (massive
#     bus faults).
#   ifla_a: 0.1 A (instrument scale) up to 100 kA.
_PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "impedance_pct": (1.5, 25.0),
    "rated_power_kva": (1.0, 1_000_000.0),
    "voltage_kv": (0.1, 1500.0),
    "fault_current_a": (50.0, 200_000.0),
    "ifla_a": (0.1, 100_000.0),
}

# Scan patterns reused from the extractor — kept inline (not imported)
# so the OCR layer stays decoupled from the parameter extractor's
# pattern set. Tight scope: only families with known decimal-slip risk.
_SCAN_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"(\d[\d,]*\.?\d*)\s*%\s*Z\b"), "impedance_pct", 1.0),
    (re.compile(r"(\d[\d,]*\.?\d*)\s*MVA\b", re.IGNORECASE), "rated_power_kva", 1000.0),
    (re.compile(r"(\d[\d,]*\.?\d*)\s*K?VA\b", re.IGNORECASE), "rated_power_kva", 1.0),
    (re.compile(r"(\d[\d,]*\.?\d*)\s*(?:kV|KV)\b(?!A)"), "voltage_kv", 1.0),
    (re.compile(r"Fault\s+\S+\s+(\d[\d,]*\.?\d*)\s*A\s+RMS", re.IGNORECASE), "fault_current_a", 1.0),
    (re.compile(r"IFLA\s*=\s*(\d[\d,]*\.?\d*)\s*A\b"), "ifla_a", 1.0),
]


def _implausible_tokens(text: str) -> list[str]:
    """Return human-readable list of values in ``text`` that fall outside
    their family's plausibility range. Empty list ⇒ all values pass."""
    out: list[str] = []
    for regex, family, unit_scale in _SCAN_PATTERNS:
        lo, hi = _PLAUSIBLE_RANGES[family]
        for m in regex.finditer(text):
            try:
                raw_num = float(m.group(1).replace(",", ""))
            except ValueError:
                continue
            value_in_family_units = raw_num * unit_scale
            if not (lo <= value_in_family_units <= hi):
                out.append(f"{m.group(0)} (family {family} outside [{lo}, {hi}])")
    return out


# ---------- Public entry point ----------


def _render_page_b64(pdf_path: str, page: int, dpi: int) -> str:
    doc = fitz.open(pdf_path)
    try:
        pix = doc[page - 1].get_pixmap(dpi=dpi)
        return base64.b64encode(pix.tobytes("png")).decode()
    finally:
        doc.close()


def vision_extract_page(pdf_path: str, page: int) -> VisionResult:
    """OCR a single page via Claude vision. Disk-cached by content + page.

    Two-pass plausibility loop: a single call runs unconditionally; a
    second verification call runs only when the first produced a numeric
    value outside its family's plausibility range. The result that
    contains fewer implausible values wins; ties keep pass 1.

    Repeat calls with the same PDF content + page return instantly from
    cache (no re-OCR cost). The cache key includes prompt_version + dpi
    so any tuning bump invalidates cleanly.
    """
    cache_key = {
        "pdf_sha": _pdf_content_sha(pdf_path),
        "page": page,
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "dpi": _DPI,
    }

    def _compute() -> dict[str, float | str | bool]:
        # Pass 1 — standard prompt at the configured DPI.
        img_b64 = _render_page_b64(pdf_path, page, _DPI)
        resp = _call_claude(img_b64, prompt=PROMPT)
        raw = resp.content[0].text  # type: ignore[attr-defined]
        payload = _parse_payload(raw)
        text_1 = str(payload["text"])
        conf_1 = float(payload["confidence"])  # type: ignore[arg-type]

        bad_1 = _implausible_tokens(text_1)
        if not bad_1:
            return {"text": text_1, "confidence": conf_1, "reocr_triggered": False}

        # Pass 2 — verification prompt at higher DPI. Only fires when
        # pass 1 left at least one implausible token; ~$0.10 marginal
        # cost on those pages.
        img_b64_v = _render_page_b64(pdf_path, page, _DPI_VERIFY)
        resp_v = _call_claude(img_b64_v, prompt=_PROMPT_VERIFY)
        raw_v = resp_v.content[0].text  # type: ignore[attr-defined]
        payload_v = _parse_payload(raw_v)
        text_2 = str(payload_v["text"])
        conf_2 = float(payload_v["confidence"])  # type: ignore[arg-type]

        bad_2 = _implausible_tokens(text_2)
        # Strictly fewer implausible tokens ⇒ pass 2 wins. Tie keeps
        # pass 1 (avoids flapping when both passes hallucinate similarly).
        if len(bad_2) < len(bad_1):
            return {"text": text_2, "confidence": conf_2, "reocr_triggered": True}
        return {"text": text_1, "confidence": conf_1, "reocr_triggered": False}

    cached, _hit = disk_cache.get_or_compute("vision-ocr", cache_key, _compute)
    return VisionResult(
        text=str(cached["text"]),
        confidence=float(cached["confidence"]),
        reocr_triggered=bool(cached.get("reocr_triggered", False)),
    )

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from interlock.cache import disk as disk_cache
from interlock.ingest.vision_fallback import (
    PROMPT,
    PROMPT_VERSION,
    VisionResult,
    _implausible_tokens,
    vision_extract_page,
)

DOC_A = Path("fixtures/pdfs/doc_a_60pct.pdf")


@pytest.fixture(autouse=True)
def _clear_vision_cache() -> None:
    """Vision results are diskcache-keyed by PDF content + page; clear the
    namespace between tests so a mocked response in test A doesn't leak
    into test B (same fixture PDF, same page)."""
    disk_cache.clear_namespace("vision-ocr")
    yield
    disk_cache.clear_namespace("vision-ocr")


def test_vision_extract_page_returns_text_and_confidence(mocker) -> None:  # type: ignore[no-untyped-def]
    fake_content = MagicMock()
    fake_content.text = '{"text":"Z=5.75%","confidence":0.92}'
    fake_response = MagicMock(content=[fake_content])
    mocker.patch(
        "interlock.ingest.vision_fallback._call_claude",
        return_value=fake_response,
    )
    result = vision_extract_page(str(DOC_A), page=1)
    assert isinstance(result, VisionResult)
    assert "5.75" in result.text
    assert 0 < result.confidence <= 1


def test_prompt_includes_critical_transcription_directives() -> None:
    """Regression guard for OCR snippet + alignment quality.

    Without explicit line-break / column-order / verbatim directives the
    model glues unrelated lines together and downstream excerpts read as
    nonsense. Without explicit row-ID preservation it drops the Device
    IDs that downstream alignment uses as entity tags — collapsing the
    cross-doc identity signal. Lock both classes of rule in.
    """
    low = PROMPT.lower()
    assert "verbatim" in low, "must demand verbatim transcription"
    assert "line break" in low or "newline" in low, "must require line-break preservation"
    assert "column" in low, "must specify multi-column reading order"
    assert "table" in low, "must specify table-row handling"
    assert "%Z" in PROMPT, "must call out engineering notation"
    # Phase 19: Device IDs are the cross-doc alignment anchor — losing
    # them silently regresses alignment quality without breaking any test.
    assert "device id" in low, "must instruct preservation of Device IDs"
    assert "①" in PROMPT, "must call out circled-digit row markers explicitly"
    assert PROMPT_VERSION, "PROMPT_VERSION must be non-empty (cache invalidation key)"


def test_vision_extract_page_robust_to_extra_prose(mocker) -> None:  # type: ignore[no-untyped-def]
    # Real Claude responses sometimes wrap JSON in fenced code blocks or add prose.
    fake_content = MagicMock()
    fake_content.text = 'Here is the JSON:\n```json\n{"text":"abc","confidence":0.5}\n```'
    fake_response = MagicMock(content=[fake_content])
    mocker.patch(
        "interlock.ingest.vision_fallback._call_claude",
        return_value=fake_response,
    )
    result = vision_extract_page(str(DOC_A), page=1)
    assert result.text == "abc"
    assert result.confidence == 0.5


# ---------- Plausibility validator ----------


def test_implausible_tokens_flags_decimal_slip_on_impedance() -> None:
    """0.575%Z is the exact user-reported hallucination — must be flagged."""
    bad = _implausible_tokens("XFMR1 0.575%Z, liquid-filled")
    assert bad
    assert any("0.575%Z" in s for s in bad)


def test_implausible_tokens_passes_typical_impedance() -> None:
    """5.75%Z is squarely typical for a distribution transformer — no flag."""
    bad = _implausible_tokens("XFMR1 5.75%Z, liquid-filled")
    assert bad == []


def test_implausible_tokens_flags_grouped_digit_slip_on_fault_current() -> None:
    """2,000,000A fault is well above the 200 kA ceiling."""
    bad = _implausible_tokens("Fault X1 2,000,000A RMS Sym")
    assert bad
    assert any("2,000,000A" in s for s in bad)


def test_implausible_tokens_handles_multiple_tokens_per_text() -> None:
    text = "XFMR1 5.75%Z, 1000KVA, 13.8kV, Fault X1 20,000A RMS Sym, IFLA=42A"
    assert _implausible_tokens(text) == []  # all typical


def test_implausible_tokens_does_not_misfire_on_decimal_zero() -> None:
    """0.15 MVA == 150 kVA — a legitimate small transformer, must pass."""
    bad = _implausible_tokens("0.15 MVA XFMR")
    assert bad == []


# ---------- Re-OCR flow ----------


def _fake_response(text: str, conf: float = 0.85) -> MagicMock:
    """Build a Claude-shaped mock response carrying a JSON OCR payload."""
    content = MagicMock()
    content.text = f'{{"text":"{text}","confidence":{conf}}}'
    return MagicMock(content=[content])


def test_reocr_triggers_when_pass_one_implausible_and_pass_two_better(
    mocker,  # type: ignore[no-untyped-def]
) -> None:
    """Pass 1 returns implausible 0.575%Z; pass 2 returns plausible 5.75%Z.
    Final result must be pass-2 text with reocr_triggered=True."""
    call_count = {"n": 0}

    def fake_claude(image_b64, prompt=None):  # type: ignore[no-untyped-def]
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response("XFMR1 0.575%Z, liquid-filled", conf=0.6)
        return _fake_response("XFMR1 5.75%Z, liquid-filled", conf=0.92)

    mocker.patch(
        "interlock.ingest.vision_fallback._call_claude",
        side_effect=fake_claude,
    )
    result = vision_extract_page(str(DOC_A), page=1)
    assert call_count["n"] == 2, "expected a second OCR call when pass 1 was implausible"
    assert "5.75%Z" in result.text
    assert result.reocr_triggered is True
    assert result.confidence == 0.92


def test_no_reocr_when_pass_one_is_plausible(mocker) -> None:  # type: ignore[no-untyped-def]
    """Cheap path: no implausible token on pass 1 ⇒ no second call."""
    spy = mocker.patch(
        "interlock.ingest.vision_fallback._call_claude",
        return_value=_fake_response("XFMR1 5.75%Z, liquid-filled", conf=0.9),
    )
    result = vision_extract_page(str(DOC_A), page=1)
    assert spy.call_count == 1
    assert result.reocr_triggered is False


def test_reocr_keeps_pass_one_when_pass_two_no_better(mocker) -> None:  # type: ignore[no-untyped-def]
    """Both passes hallucinate — keep pass 1 (no flapping). reocr_triggered
    stays False because pass 2 wasn't preferred."""
    call_count = {"n": 0}

    def fake_claude(image_b64, prompt=None):  # type: ignore[no-untyped-def]
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response("XFMR1 0.575%Z", conf=0.5)
        return _fake_response("XFMR1 0.0575%Z", conf=0.5)

    mocker.patch(
        "interlock.ingest.vision_fallback._call_claude",
        side_effect=fake_claude,
    )
    result = vision_extract_page(str(DOC_A), page=1)
    assert call_count["n"] == 2
    assert "0.575%Z" in result.text
    assert result.reocr_triggered is False

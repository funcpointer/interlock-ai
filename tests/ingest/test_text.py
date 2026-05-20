from pathlib import Path

import fitz

PROBE = Path("fixtures/probes/symbol_probe.pdf")
REQUIRED = ["Ω", "μ", "μF", "kV", "MVA", "θ", "Δ", "cos φ", "°C", "±", "≤", "≥"]


def test_symbol_probe_roundtrip() -> None:
    assert PROBE.exists(), "symbol probe PDF must exist"
    doc = fitz.open(str(PROBE))
    text = "".join(p.get_text("text") for p in doc)
    doc.close()
    missing = [s for s in REQUIRED if s not in text]
    assert not missing, f"symbols missing from extracted text: {missing}"

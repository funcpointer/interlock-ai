"""Generate symbol-fidelity probe PDF.

PyMuPDF's built-in 'helv' font lacks Greek / unicode symbols. We embed Arial Unicode
(macOS supplemental font) so Ω, μF, θ, Δ, cos φ, °C, ±, ≤, ≥ all round-trip.
"""

from __future__ import annotations

from pathlib import Path

import fitz

OUT = Path("fixtures/probes/symbol_probe.pdf")
UNICODE_TTF = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

TEXT = (
    "Symbol probe — engineering notation\n"
    "Resistance: 50 Ω.  Capacitance: 4.7 μF.\n"
    "Voltage: 132 kV.  Apparent power: 25 MVA.\n"
    "Phase angle θ = 30°.  Delta winding: Δ.\n"
    "Power factor: cos φ = 0.95.\n"
    "Temperature rise: 65 °C.  Tolerance: ± 2.5 %.\n"
    "Limits: ≤ 50, ≥ 10.\n"
)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_font(fontname="uni", fontfile=UNICODE_TTF)
    page.insert_text((72, 100), TEXT, fontname="uni", fontsize=11)
    doc.save(str(OUT))
    doc.close()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

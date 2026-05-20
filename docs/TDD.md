# InterLock AI — TDD

*Version: v1.5-mvp-ready · Companion docs: `PRD.md`, `ARCHITECTURE.md`, `AUTHORSHIP.md`*

This is the technical complement to `docs/PRD.md`. Architecture diagrams (component, control flow, data flow, cache hierarchy, LLM call patterns) live in `docs/ARCHITECTURE.md` so this file stays at the two-page bar set by the deliverable spec.

## 1. Ingestion and extraction architecture

Two stages, with a vision fallback for low-coverage pages.

**Stage A — span + table extraction.** `PyMuPDF` (`fitz`) iterates page → block → line → span and yields a `Span(doc_id, page, bbox, text, source_path)` per visual run. `aggregate_line_spans` merges same-y spans within a 2-point tolerance so multi-line labels like `Rated\nVoltage: 132 kV` match downstream regex. `Camelot` extracts tables (lattice first, stream fallback); table extraction is capped at the first 20 pages by default so a 56-page PDF does not stall the cloud UI for two minutes (`extract_tables(max_pages=20)`). Native-text PDFs round-trip Unicode losslessly; the symbol-fidelity probe (`fixtures/probes/symbol_probe.pdf`) verifies that `Ω`, `μF`, `kV`, `MVA`, `θ`, `Δ`, `cos φ`, `°C`, `±`, `≤`, `≥` all survive.

**Stage B — parameter extraction.** `extract_parameters` runs a domain-specific regex set against spans yielding `ParameterRecord(doc_id, page, bbox, section, span_text, name, raw_value, normalized_magnitude, normalized_unit, source_path)`. The patterns cover the actual shape of the locked fixtures: `1000KVA XFMR`, `5.75%Z`, `Fault X1 20,000A RMS Sym`, generic `Label: value unit`. Pint with a `percent = 0.01 = %` alias normalizes units to SI base for value comparison. Section headings are attributed to spans via per-page nearest-preceding-heading.

**Stage C — vision fallback (opt-in).** Pages with under 80 characters of native text are flagged in `IngestResult.low_coverage_pages`. The fallback (`src/interlock/ingest/vision_fallback.py`) renders the page at 200 DPI, base64-encodes it, and prompts Claude Sonnet 4.5 for `{text, confidence}` JSON. Not exercised by the locked fixtures (Eaton has zero low-coverage pages).

## 2. OCR and layout parsing

Layout parsing is handled by Stage A above; OCR is the vision-fallback path. No tesseract integration. Three findings worth recording:

- **Camelot detects chart axes as tables** on the Eaton coordination-curve pages (lattice mode happily returns 50-row × 38-column "tables" representing log-log gridlines). The real parameter signal lives in span text. Table extraction is retained as a no-cost fallback for future fixtures with native PDF tables; current parameter extraction is span-driven.
- **PyMuPDF's `helv` font lacks Greek glyphs**, so the symbol-fidelity probe is generated with Arial Unicode TTF embedded via `page.insert_font(fontfile=…)`.
- **Anthropic vision is the deployed-runtime OCR option**, not tesseract — keeps the runtime dependency surface small and avoids language-pack management.

## 3. Comparison logic

Three signals composed per pair, with explicit guards against false matches.

- **Layout-anchored exact** (`align/exact.py`): records with the same parameter name on the same page pair by minimum y-center distance, greedy 1-to-1. Dominant path for revision-diff fixtures.
- **Pint unit normalization** (`extract/units.py`): each paired value is checked for dimensional equivalence via Pint's `UnitRegistry`. `150 kVA == 0.15 MVA == 150 000 V·A` reduces to one base-unit comparison. A case-insensitive string-equality short-circuit handles part numbers (`KRP-C-1600SP`) so Pint never raises on non-numeric tokens.
- **Voyage semantic** (`align/semantic.py`): for A records left unmatched by the exact pass, cosine on Voyage `voyage-3` name embeddings yields a fallback pair if similarity ≥ 0.85. Three guards: (a) string-valued records excluded from semantic matching (part-number embeddings cluster spuriously); (b) `same_page_only=True` for revision-diff, lifted in cross-doc mode; (c) `same_dimension` filter rejects voltage ↔ current candidates even when an embedder reports cosine 1.0.
- **Canonical glossary** (`align/semantic.py::_CANONICAL`): explicit engineering shorthand mapping. Voyage alone scores `%Z` ↔ `Impedance` at cosine ≈ 0.44 — below the 0.85 threshold. Mapping each to a canonical phrase (`transformer impedance percent`) before embedding lifts cosine to ≈ 1.0. This is the explicit engineering knowledge that distinguishes InterLock from Adobe-Acrobat-class textual diff.
- **Optional Entity + Claim layer** (`extract/entities.py`, `align/claims.py`): when `use_claim_layer=True`, tag-pattern regex (XFMR-001, T-200, P-101, M-50, CB-52, Bus B-3, Line 14A, MOV-100, V-200, R-87, Relay R-87) lifts each record into a `Claim(entity, attribute, raw_value, source_record)`. The aligner then applies a same-entity filter; implicit entities (per-doc placeholder) are treated as wildcards so the v1.3 revision-diff path keeps working. Persistence to SQLite is a separate opt-in (`persist_claims=True`).
- **Directional emission with hardcoded authority** (`detect/mismatch.py`, `detect/authority.py`): the MVP fixture pair uses a hardcoded rule (Doc A = 60 % baseline, authoritative; Doc B = 90 % revision, deviation candidate). Every `Flag` carries the rule string verbatim. Configurable per-pair authority is in `docs/BACKLOG.md`.

## 4. Citation and confidence

Every `Flag` carries a citation tuple `(doc_id, page, section, bbox, quoted_text, snippet_png)`. The snippet renderer (`citation/render.py`) opens the source PDF, draws a 1.5-pt red bbox over the parameter span, clips to a generous window, and rasterizes at 200 DPI. The Streamlit UI shows the snippet side-by-side for both records of a flag so the reviewer never alt-tabs to the source PDF.

Confidence is the product of three orthogonal factors, each clamped to `[0, 1]`:

```
flag_confidence = extraction_confidence × match_confidence × authority_confidence
```

- `extraction_confidence`: 1.0 for native PyMuPDF spans; drops on vision-fallback pages proportional to model self-report.
- `match_confidence`: 1.0 for exact-name layout-anchored pairs; equals Voyage cosine for semantic pairs.
- `authority_confidence`: 1.0 for the hardcoded MVP rule; drops when authority is inferred / unknown (platform path).

**Severity (Phase 13 addition)** is a separate axis from confidence: per-attribute tolerance bands (`detect/tolerances.py::TOLERANCE_TABLE`) map relative deviation percent to one of `critical` / `major` / `minor` / `info`. Sources cited inline: IEEE C57.12.00-2015 §9.1 Table 17 for impedance; IEC 60076-1:2011 §5.3 for voltage ratio; IEEE C57.12.00-2015 §5.10 and NEMA TR 1-2013 for kVA rating; IEEE Std 242 (Buff Book) for fault current. **The shipped bands are starting defaults, not absolute truth** — see `set_tolerance_overrides()` for the project-config hook and `BACKLOG.md` Phase 15 for the UI ontology path.

The optional LLM significance judge (`detect/significance.py`, opt-in via `use_llm_judge=True`) runs each candidate flag through Claude Opus 4.7 with `messages.parse(output_format=SignificanceJudgment)` and two-tier prompt caching (1 hour TTL on the engineering ontology, 5 minutes on per-flag context). Returns `severity`, `deviation_pct`, `within_typical_tolerance`, `engineering_explanation`, and `downstream_effects`. Disk-cached so repeat runs cost effectively zero.

## 5. Evaluation design

The locked gold set (`fixtures/eval/gold.yaml`) is derived directly from `fixtures/mutations/MUTATIONS.md`. Six labeled cases on the Option 1 pair:

| ID | Category | Expected | What it tests |
|---|---|---|---|
| TP-1 | parameter_mismatch | surfaced ≥ 0.6, severity critical | Decimal-shifted transformer impedance (5.75 % → 0.575 %) — AES anecdote class |
| TP-2 | parameter_mismatch | surfaced ≥ 0.6, severity critical | Decimal-shifted fault current (20 000 A → 200 000 A) |
| TP-3 | parameter_mismatch | surfaced ≥ 0.6, severity critical | Decimal-shifted transformer rating (1000 kVA → 100 kVA), two sites |
| FP-1 | unit_normalization | suppressed | 150 kVA vs 0.15 MVA — must register as equivalent via Pint |
| FP-2 | heading_only | suppressed | "Time Current Curve #1" → "Time Current Curve 1" — heading rephrase only |
| FN-1 | checklist_gap | best-effort | Fuse `LPN-RK-500SP` removed from B — current pipeline doesn't surface explicit-removal flags; documented system limitation |

The harness (`scripts/run_eval.py`) runs the full pipeline with real Voyage embeddings and writes per-id results plus aggregate metrics to `eval/results/baseline.json`. A pytest gate enforces the acceptance thresholds: TP recall = 1.0, FP rate = 0.0. The Option 2 cross-doc fixture has its own gold set at `fixtures/eval/gold_cross_doc.yaml` and its own pytest test (`tests/eval/test_harness_cross_doc.py`). The A/B comparison (`scripts/run_ab.py`) emits `eval/results/ab_comparison.json` showing that Option 2 surfaces flags via the semantic path that Option 1 cannot (Option 1 has zero exact-name matches between spec and study).

**Current baseline (`eval/results/baseline.json`):**

- 4 flags surfaced, all real
- Recall on planted TPs: 1.0 (3 of 3)
- FP rate on traps: 0.0 (0 of 2 surfaced above threshold)
- FN-1: not detected (documented limitation; explicit-removal detection is platform-path)

**Test surface:** 294 passing tests, 7 slow-marked deselected by default, across ingest / extract / entities / align / detect / citation / store / llm / eval harness / real-world e2e / edge cases / property / canonical glossary / perf budgets. `mypy --strict` clean on 36 source files. `ruff check` clean.

**Cost during build:** about $0.20 total Anthropic spend recorded in the `cost_event` ledger across all Phase 13–14 development. Voyage spend separately tracked, sub-dollar. Per-call breakdown queryable via `cost_ledger.summary()`.

## 6. Architectural direction beyond v1.5

The MVP intentionally stops at parameter-name-level pairing with an additive entity layer. The natural next architecture is the SQLite-backed claim graph already shipped in `data/interlock.schema.sql`, with relationships (`derived_from`, `governed_by`, `supersedes`) added in Phase 16 + 17 (see `docs/BACKLOG.md`). The deterministic pipeline is intentional: every flag is reproducible from the regex set, Pint registry, tolerance bands, and Voyage cache. LLM significance enrichment is a second-opinion layer that does not change the underlying value pair — the reviewer's audit trail stays short and verifiable. Findings, not chat.

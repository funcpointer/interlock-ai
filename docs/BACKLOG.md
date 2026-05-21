# InterLock AI — Backlog

Anything that surfaces during MVP execution and would expand scope goes here. Roadmap items are lettered (R-A, R-B, …) to avoid collision with shipped phase tags (`phase-0` through `phase-20-ocr-quality`).

## Closed (shipped in this build)

- ~~Cross-document semantic alignment fixture (Option 2)~~ — done 2026-05-20 (v1.1-cross-doc, `phase-11-cross-doc`). Verified strictly stronger than Option 1 by `scripts/run_ab.py` / `eval/results/ab_comparison.json`.
- ~~Tolerance-band severity tiers + opt-in LLM significance judge + cost ledger + diskcache~~ — done 2026-05-21 (v1.3-tolerance). Sourced from IEEE C57.12.00, IEC 60076-1, IEEE Std 242, NEMA TR 1. Runtime override hook (`set_tolerance_overrides`) ships for project-specific bands.
- ~~Entity + Claim layer as additive layer over ParameterRecord; SQLite store for entity/claim/decision~~ — done 2026-05-21 (v1.4-entity-claim). Tag-pattern entity inference (XFMR / T / P / M / CB / Bus / Line / MOV / V / R). Aligner gains `same_entity_only` filter with implicit-entity wildcard. All opt-in via `use_claim_layer=True` / `persist_claims=True`.
- ~~Vision-fallback exercise on a scanned-PDF~~ — done 2026-05-22 (`phase-18-ux-ocr`). `doc_a_scanned.pdf` JPEG-encoded raster fixture; Claude Sonnet 4.5 vision; parallel × 5 ThreadPool; per-page progress bar in UI; `tests/real_world/test_ocr_yield.py` asserts ≥ 50 % parameter recovery vs native baseline (actual: 104 % recovery on locked fixture).
- ~~Identity-first alignment + honest gap surface~~ — done 2026-05-22 (`phase-19-identity-alignment`). `entity_tag` first-class field; pair-by-tag before any positional rule; ambiguity gates (family, count, y-degeneracy); `pairing_confidence` per rule; `ReviewResult.unpaired_*` surfaced in UI.
- ~~OCR quality refresh~~ — done 2026-05-22 (`phase-20-ocr-quality`). DPI bump 200 → 300; two-pass plausibility re-OCR at 400 DPI with verification prompt only when first-pass values fall outside per-family sanity bands.
- ~~Camelot on long PDFs is slow (capped at 20 pages by default)~~ — done in Phase 12. `table_max_pages` parameter with UI slider for override.
- ~~`render_citation` `doc_id`-as-path bug~~ — fixed in Phase 12. Added `source_path` to `Span` and `ParameterRecord`; renderer prefers `source_path` with `doc_id` fallback.

## Still open (post-MVP, ranked by leverage)

### R-A — Pluggable entity-tag detector (Phase 19 generalisation)

**Status:** `_LEADING_DEVICE_ID` regex captures circled digits / numeric prefixes / `T-200`-style tags. Misses `XFMR-001` (prefix too long), `P-101A`, `T200` (no hyphen), bullets / brackets, IDs not in column 1.

- Register multiple regex banks per doc class, keyed off ingest-time classification (HVAC schedule, P&ID, BOM, coordination study, …).
- Reviewer can declare a doc class at upload to bias detector choice.
- Unlocks broader doc-class coverage without per-fixture regex churn.

### R-B — Camelot-row binding (Phase 19 generalisation)

**Status:** when Camelot finds a table but no leading row marker is captured by `_LEADING_DEVICE_ID`, records lose their natural row identity.

- Every parameter extracted from row R of a Camelot-detected table inherits `entity_tag = "row-R"` (or a hashed row signature) even without a leading marker.
- High leverage on spec sheets / BOMs with right-aligned ID columns.

### R-C — Diverse fixture suite (Phase 19 generalisation)

**Status:** every regression test uses fuses + transformer kVA. Unknown behaviour on HVAC schedules, P&IDs, BOMs, untagged docs.

- Add ≥ 3 fixture pairs covering distinct doc classes with gold flags on each.
- Calibrate `pairing_confidence` magnitudes against labelled ground truth.

### R-D — Multi-engine OCR consensus (Phase 20 generalisation)

**Status:** single-model OCR with two-pass plausibility loop catches decimal-slip class. Doesn't catch model-specific systematic errors.

- Optional second engine (Tesseract, PaddleOCR, Surya) on the same image.
- Agreement → high confidence; disagreement → flag for reviewer or trigger third call.
- Cost overhead: 2× per OCR'd page; only triggered when confidence is borderline.
- Also unlocks line-level bboxes on the OCR side (currently whole-page only).

### R-E — Labelled OCR accuracy corpus (Phase 20 generalisation)

**Status:** "Claude vs Tesseract vs Surya" comparison is currently vibes-based. No ground-truth character-level accuracy metric beyond parameter-recovery yield.

- Hand-label OCR ground truth for the 9-page scanned fixture (char-level transcription).
- Run each candidate engine and measure CER / WER / parameter-recovery / pairing-survival.
- Engine choice becomes data-driven instead of integration-effort-driven.

### R-F — Entity fingerprinting (Phase 14 follow-on)

**Status:** known limitation. When one side has explicit equipment tags (XFMR-001, XFMR-002) and the other has only implicit entities, the same-entity filter treats the implicit side as a wildcard and admits every cross-pairing.

- Bind an implicit entity to the explicit entity on the other side whose attribute fingerprint best matches (voltage class, power rating).
- Unlocks the multi-equipment cross-doc demo.

### R-G — Per-project tolerance ontology UI

**Status:** runtime override hook shipped (`detect.tolerances.set_tolerance_overrides`); UI editor + project-config loading is next.

The Phase 13 tolerance bands are industry-typical defaults from public standards. Not the right values for every project (standard edition variance, owner internal standards, equipment class / vintage, discipline / phase, risk posture).

- Per-project config loading (`tolerances.yaml` or SQLite table seeded at session start).
- UI panel for the reviewer to amend the active band before / during a review.
- Decision-log entry for every band override.
- Per-attribute-family confidence (lower confidence when the band itself is recent / contested).

### R-H — Revision lineage

- Per-document revision metadata (Rev A / B / C, dates, supersession chain).
- Supersession-aware authority: "Rev C supersedes Rev B" overrides hardcoded rules.
- Parameter-evolution timeline per claim.

### R-I — Coupled-effect propagation

- Graph traversal over the SQLite claim graph: claim X changes → identify derived claims that become suspect.
- "Transformer impedance changed → recheck coordination study and relay settings" without re-reading either document.

### R-J — Standards-as-authority pass

- IEEE / IEC / NERC code-edition tracking.
- Project-vs-code compliance pass.
- Eliminates the slowest senior-reviewer task: standards cross-reference.

### R-K — Multi-doc review sessions + DMS integration

- Whole-project corpora.
- SharePoint / Bentley ProjectWise / Autodesk Docs ingest.
- Triage queue with ownership, comment threads, status lifecycle.
- UI wires the existing `decision` table for persistent reviewer audit trail (today the UI exports JSON only).

### R-L — CAD geometry comparison

- 2D / 3D drawing comparison (bananaz.ai-class) integrated with the same claim graph.
- One consistency engine across drawings + specs, not two siloed tools.

### R-M — Prose-embedded parameter extraction

**Status:** Phase 12 confirmed SEL transformer-protection paper is prose-heavy ("the percentage 2 harmonic setting PCT2 is also calculated…"); current regex extractors yield zero parameters. Pinned at zero by `tests/real_world/test_real_pdf_extraction.py::test_sel_paper_known_prose_extraction_limit`.

- NLP / LLM-based extraction needed for technical papers.
- Risk: drops determinism — needs to live behind an opt-in flag with cached results.

### R-N — Option 4 fixture (real spec ↔ real study)

**Status:** Option 2's spec is synthetic (disclosed in AUTHORSHIP). Option 4 would prove the pipeline on uncurated reality.

- Candidate: SEL 6079 transformer protection paper paired with a public manufacturer data sheet.
- Gate: real-spec curation must satisfy the same gold-set authoring rigor as Options 1 + 2.

### R-O — DocETL adoption

- Refactor the deterministic pipeline onto DocETL operator vocabulary in code as well as documentation; leverage the DocETL agentic optimizer once we have enough labeled fixture pairs for it to train against.

### R-P — Continuous engineering assurance

- Always-on monitor across project lifecycle (design → procurement → construction → as-built).
- Asset operators pay for traceable assurance across years of project deliverables.

## Findings discovered during execution

- 2026-05-20 (P2): Camelot detects chart axes (50-row × 38-col grids) on Eaton coordination-curve pages, not the device-ID tables. The device-ID "tables" are visually-laid-out paragraphs, not bordered tables. For this fixture, parameter extraction is span-driven; the table-cell extractor in the plan (Tasks 3.3b/3.3c) was skipped. Platform-path: real engineering specs with native PDF tables will exercise this.
- 2026-05-20 (P11): Voyage `voyage-3` embeddings alone do not match engineering shorthand reliably ("%Z" ↔ "Impedance" cosine ≈ 0.44; "Rated Power" ↔ "Transformer Rating" ≈ 0.66, both below the 0.85 alignment threshold). A small canonical glossary in `align/semantic.py` (`_CANONICAL`) maps shorthand to canonical phrases before embedding; cosine on canonical forms is then ≈ 1.0. Extend per fixture family. Voyage rerank-2 considered as an alternative but glossary is more interpretable and faster.
- 2026-05-20 (P12): `render_citation` bug — `fitz.open(record.doc_id)` requires `doc_id` to be a real file path, but the pipeline default sets `doc_id="doc_a"` (a label). In the deployed Streamlit app this caused silent citation-snippet failures. **Fixed** by adding `source_path` to `Span` and `ParameterRecord`. Renderer prefers `source_path` with `doc_id` fallback.
- 2026-05-20 (P12): Voyage embedding API has minor non-determinism across calls (cosine drift ~1e-3). Idempotency tests must check flag-parameter *sets*, not exact confidence values.
- 2026-05-22 (P18): Vision OCR produces flat text without per-line bboxes. Mitigated by splitting OCR text on newlines into one Span per visual line (whole-page bbox preserved for citation image). Caveat: red-box highlight on snippet is whole-page for OCR records; multi-engine consensus (R-D) would resolve this.
- 2026-05-22 (P19): User-reported false flags on multi-instance same-name pages (KRP-C-1600SP vs LPS-RK-100SP, 150 kVA vs 100 kVA) traced to alignment having no record identity. Captured leading Device IDs as `entity_tag`. Heuristics-overfit-to-fuse-tables disclosed in `docs/TDD.md` § "Known limits"; broader doc-class coverage tracked as R-A through R-C.
- 2026-05-22 (P20): User-reported decimal-place OCR hallucination (`5.75%Z` → `0.575%Z`) resolved by DPI bump 200 → 300; two-pass plausibility loop ships as defense-in-depth. Re-OCR did not fire on locked scanned fixture in live verification (first pass was clean).

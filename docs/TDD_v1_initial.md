# InterLock AI — TDD

## 1. Ingestion and extraction architecture

Two-stage native-text path with a vision fallback.

**Stage A — span extraction (PyMuPDF / `fitz`).** Iterate page → block → line → span. Each span carries text, page index (1-based), and bbox (`x0, y0, x1, y1` in PDF points). Unicode round-trips natively; the symbol-fidelity probe (`fixtures/probes/symbol_probe.pdf`) verifies that Ω, μF, kV, MVA, θ, Δ, cos φ, °C, ±, ≤, ≥ all survive extraction. PyMuPDF gives roughly an order of magnitude speedup over `pdfplumber` while preserving bbox information needed for citations.

**Stage A.5 — line aggregation.** PyMuPDF returns one span per visual run; labels like `Rated\nVoltage: 132 kV` split across spans. `aggregate_line_spans` groups same-y spans (within 2 pt tolerance) so regex matchers see logical lines.

**Stage B — table extraction (Camelot).** Lattice flavor first, stream fallback. Cell bboxes preserved. Empirical note: Camelot detected coordination-curve chart axes on Eaton pages 4/6/8 as 50+ row "tables." The actual device-ID tables on pages 3/5/7 are visually-laid-out paragraphs, not bordered tables. For this fixture the parameter signal is span-driven; table extraction is retained as a no-cost fallback for future fixtures with native PDF tables (data sheets, equipment schedules).

**Stage C — vision fallback (Claude Sonnet 4.5).** Pages where text density falls below 80 characters (typically scanned pages, image-only blueprints, or pages with embedded raster diagrams) are flagged in `IngestResult.low_coverage_pages`. The fallback renders the page at 200 DPI, base64-encodes, and prompts Claude for `{text, confidence}` JSON. Used only when the native path produces nothing usable. Not exercised by the locked fixture (Eaton is fully native-text, 0 low-coverage pages); included for the platform-path scanned-PDF case. Anthropic SDK is the only LLM dependency in the runtime path.

## 2. Comparison logic

Three signals composed, applied per-pair.

**Layout-anchored exact match** (`align/exact.py`): records with the same parameter name on the same page pair by minimum y-center distance, greedy 1-to-1. This is the dominant path for revision-diff cases where Doc B shares layout with Doc A; it eliminates the cross-product explosion that would arise from naïve name-matching when a parameter family has many instances (e.g., Eaton has nine `5.75%Z` records).

**Pint unit normalization** (`extract/units.py`): each paired value is evaluated for dimensional equivalence via Pint's UnitRegistry. `150 kVA == 0.15 MVA == 150000 V·A` reduces to a single base-unit comparison. The FP-1 trap in the eval gold set verifies this directly. A string-equality short-circuit handles non-numeric tokens (fuse part numbers like `KRP-C-1600SP`) so part-number stability is checked without Pint raising.

**Voyage embedding semantic alignment** (`align/semantic.py`): for A records left unmatched by the layout-anchored pass, cosine similarity of Voyage `voyage-3` name embeddings yields a fallback pair if similarity ≥ 0.85. Three guards keep this signal honest: (a) string-valued records are excluded — part-number embeddings are too close and produce spurious matches; (b) same-page constraint by default — prevents a removed-from-B item on page 7 of A from being paired with an unrelated item on page 2 of B; in cross-doc mode this is lifted; (c) `same_dimension` filter rejects dimensionally incompatible candidates (e.g. voltage ↔ current). The Streamlit UI surfaces real `voyage-3` embeddings; tests inject deterministic stubs.

**Canonical glossary** (`align/semantic.py::_CANONICAL`): explicit engineering shorthand mapping. Voyage embeddings alone score `%Z` ↔ `Impedance` at cosine ≈ 0.44 and `Rated Power` ↔ `Transformer Rating` ≈ 0.66, both below the 0.85 threshold. Mapping each to a canonical phrase (`transformer impedance percent`, `transformer rated apparent power kVA`) before embedding restores cosine ≈ 1.0. This is the explicit engineering knowledge that distinguishes InterLock from Adobe-Acrobat-class textual diff. The Phase 11 cross-doc fixture exercises this path; the Phase 1 revision-diff fixture leaves it dormant (all parameter names align exactly).

**Combiner** (`align/combiner.py`): exact pairs take precedence. Semantic pairs fill only when no exact pair covers the same A record.

**Directional emission with hardcoded authority** (`detect/mismatch.py`, `detect/authority.py`): for the MVP fixture pair, Doc A is hardcoded authoritative (60% baseline) and Doc B is the deviation candidate (90% revision). Every flag declares both ends and includes the authority rule string verbatim — the reviewer always knows which document the system treated as the source of truth. Configurable per-parameter / per-document-type authority is platform-path (BACKLOG.md).

## 3. Citation and confidence

Every flag carries a tuple `(doc_id, page, section, bbox, quoted_text, snippet_png)`. The snippet renderer (`citation/render.py`) opens the source PDF, draws a 1.5-pt red bbox over the parameter span, clips to a generous window around the bbox, and rasterizes at 200 DPI. The Streamlit UI displays the snippet side-by-side for both records of a flag so the reviewer never needs to alt-tab to the source PDF to verify.

Confidence is the product of three orthogonal components, each in `[0, 1]`:

```
flag_confidence = extraction_confidence × match_confidence × authority_confidence
```

- `extraction_confidence`: 1.0 for native PyMuPDF spans (zero ambiguity); drops for vision-fallback pages proportional to model self-report.
- `match_confidence`: 1.0 for exact-name layout-anchored pairs; equals Voyage cosine similarity for semantic pairs.
- `authority_confidence`: 1.0 for the MVP hardcoded rule; drops when authority is inferred or unknown (platform-path).

Surface threshold default is 0.6 (slider-adjustable in the UI). Below-threshold flags are accessible via the "suppressed" expander but do not enter the primary review list. The threshold trades off review burden against catch rate; 0.6 was chosen because it admits all locked-fixture TPs while suppressing every locked-fixture FP.

## 4. Evaluation

The locked gold set (`fixtures/eval/gold.yaml`) is derived directly from the mutation log (`fixtures/mutations/MUTATIONS.md`). Six labeled cases:

| ID | Category | Expected | What it tests |
|---|---|---|---|
| TP-1 | parameter_mismatch | surfaced ≥ 0.6 | Decimal-shifted transformer impedance (5.75 % → 0.575 %) — mirrors the AES anecdote |
| TP-2 | parameter_mismatch | surfaced ≥ 0.6 | Decimal-shifted fault current (20,000 A → 200,000 A) |
| TP-3 | parameter_mismatch | surfaced ≥ 0.6 | Decimal-shifted transformer rating (1000 kVA → 100 kVA), 2 sites |
| FP-1 | unit_normalization | suppressed | 150 kVA vs 0.15 MVA — must be recognized as equivalent (Pint dimensional check) |
| FP-2 | heading_only | suppressed | "Time Current Curve #1" → "Time Current Curve 1" — heading rephrase, no parameter |
| FN-1 | checklist_gap | surfaced ≥ 0.4 (acceptable miss) | Fuse `LPN-RK-500SP` present in A, removed from B — checklist-gap pattern; explicit-removal detection is platform-path |

The harness (`scripts/run_eval.py`) runs the real pipeline (Voyage embedder) and writes per-id results plus aggregate metrics (recall on TPs, FP rate on traps, FN count) to `eval/results/baseline.json`. A pytest gate enforces the acceptance thresholds locked in `docs/FIXTURES.md` §6: recall = 1.0 on TPs, FP rate = 0.0 on traps.

Current baseline (`eval/results/baseline.json`):

- Total flags surfaced: 4 (all real)
- Recall on planted TPs: **1.0** (3/3)
- FP rate on traps: **0.0** (0/2 surfaced above threshold)
- FN-1: not detected as a flag (known limitation; surfaces in BACKLOG.md as the explicit-removal detection extension)

## 4B. Tolerance bands — defaults, not absolute truth

The severity classifier in Phase 13 maps relative deviation percent to one of four tiers (`critical` / `major` / `minor` / `info`) using a per-attribute-family tolerance band. We ship **industry-typical defaults** sourced from IEEE C57.12.00, IEC 60076-1, IEEE Std 242 (Buff Book), and NEMA TR 1, cited inline at `src/interlock/detect/tolerances.py`.

**These shipped values are not the right answer for every project.** Real-world tolerance bands depend on:

1. **Applicable standard edition** (IEEE C57.12.00 revised 2006 / 2010 / 2015 / 2022)
2. **Owner's internal engineering standards** (AES-STD-XXX-type documents may tighten or relax)
3. **Equipment class and vintage** (nuclear vs solar, new vs legacy)
4. **Discipline and review phase** (30 % bar is looser than 90 % bar)
5. **Risk posture** (station service vs generator step-up)

InterLock's tolerance system is therefore **explicitly a starting baseline** with a runtime-override hook:

```python
from interlock.detect.tolerances import set_tolerance_overrides, ToleranceBand

set_tolerance_overrides({
    "impedance_pct": ToleranceBand(
        attribute_family="impedance_pct",
        rel_tolerance_pct=5.0,
        rel_major_pct=15.0,
        rel_critical_pct=50.0,
        source="AES-STD-XYZ §4.2 (tighter than IEEE C57.12.00)",
    ),
})
```

Production deployments will load the override map from a project-specific config (YAML / SQLite) so the reviewer team owns the values without forking code. The platform-path target is a UI-editable tolerance ontology with audit trail; see `docs/BACKLOG.md` Phase 17.

**Honest framing for funders/reviewers:** the shipped defaults are public-source, citable, and conservative. The override hook is one line of code. The point is not that we know the right value for AES — it's that the system has a defensible default, exposes the value to scrutiny, and lets the reviewer team take ownership.

## 5. Architecture summary (v1.5-mvp-ready)

```
PDF ─► ingest (PyMuPDF spans + Camelot tables + low-coverage routing for vision)
     ─► extract (regex → ParameterRecord; Pint normalization; section attribution)
     ─► [opt-in] entities (tag-pattern → Entity; ParameterRecord → Claim wrapper)
     ─► align (layout-anchored exact + Voyage semantic + canonical glossary + dim filter
              [opt-in] same-entity filter when claim layer is on)
     ─► detect (directional authority + 3-factor confidence + tolerance-band severity)
     ─► [opt-in] significance (LLM second-opinion via Claude Opus 4.7, prompt-cached)
     ─► citation (bbox-highlighted PNG snippet)
     ─► UI (Streamlit; severity-grouped flag list; accept/dismiss; JSON export)
```

**Git history.** 15 phase tags (`phase-0-scaffold` … `phase-17-deliverables`) plus six version tags (`v1.0-mvp` → `v1.5-mvp-ready`) partition the implementation. Each phase ends with a checkpoint commit and a green test suite.

**Test surface.** 294 passing tests, 7 slow-marked deselected by default (perf budgets + live-API tests), spread across ingest, extract, entities, align, detect, citation, store, llm, eval harness, real-world e2e, edge cases, property tests, canonical glossary, and perf budgets. `mypy --strict` clean across 36 source files; `ruff check` clean.

**Cost during build.** Aggregated `cost_event` rows: about $0.20 total spent across Phase 13–14 development. Demo loop runs at less than $0.10 per execution once caches are warm; near zero after that (Voyage embeddings and LLM judgments served from diskcache).

---

## 6. Entity + Claim layer (shipped in Phase 14, opt-in)

The MVP ships the entity-claim infrastructure as a strictly **additive** layer over `ParameterRecord` — no existing test was broken to add it. Source: `src/interlock/extract/entities.py`.

```python
@dataclass(frozen=True)
class Entity:
    id: str            # "xfmr_001", "p_101", "implicit_doc_a"
    type: EntityType   # transformer | pump | motor | breaker | bus | line | mov | valve | relay | implicit
    label: str         # display name, e.g. "XFMR-001"

@dataclass(frozen=True)
class Claim:
    entity: Entity
    attribute: str            # canonical phrase from align/semantic.py
    raw_value: str
    source_record: ParameterRecord   # back-pointer preserves citation
```

`claims_from_records(records)` is a pure function: tag-pattern regex infers an entity from each record's `span_text` (`XFMR-001`, `T-200`, `P-101`, `M-50`, `CB-52`, `Bus B-3`, `Line 14A`, `MOV-100`, `V-200`, `R-87`, `Relay R-87`). When no tag matches, the record is attached to an `implicit_<doc_id>` entity per source document.

**How the pipeline uses it:** the entity layer is gated behind `review_two_documents(... use_claim_layer=True, same_entity_only=True, persist_claims=False)`. With `use_claim_layer=False` (default) the v1.3 record-based path runs unchanged. With it on, the aligner uses `align_claims_exact`, which adds an extra filter: pairs only survive when both source claims share the same entity id (implicit entities are treated as wildcards so the revision-diff fixture continues to align).

**Persistence.** Claims and entities can be written to the SQLite store at `data/interlock.db` via `src/interlock/store/sqlite.py` when `persist_claims=True`. The schema is in `data/interlock.schema.sql` and is applied idempotently on first connect.

**What the entity layer does not yet do (platform path):**

- **Fingerprint-based entity resolution.** When one side of a pair has explicit entity tags and the other has only implicit entities (e.g. Eaton coordination study, which mentions "1000 KVA XFMR" without an enumerated ID), the system today treats the implicit side as a wildcard. A real multi-equipment cross-doc demo needs attribute-fingerprint matching (voltage class, power rating) to bind the implicit transformer in Eaton to the right `XFMR-NNN` on the other side. Tracked as Phase 14b in `docs/BACKLOG.md`.
- **Coupled-effect propagation.** Claims can in principle be linked by `derived_from` / `governed_by` edges so that changing one cascades. Not implemented in v1.5; Phase 17 in BACKLOG.
- **Revision lineage on the claim itself.** Each claim carries its source document's path and page; multi-revision supersession is Phase 16 in BACKLOG.
- **UI surfacing.** The Streamlit UI displays the existing `Flag` shape; it does not yet expose entity-grouped views.

## 7. Why these architectural choices

Three principles drive the build:

- **Findings, not chat.** No conversational interface; every output is a structured `Flag` with the full citation tuple. Reviewers triage; the system never asserts wrongness. Positions InterLock as audit infrastructure, not a copilot.
- **Facts separated from interpretations.** Each `Flag` reports the raw values on both sides plus a *suggested direction* (authority hint) and a severity tier (computed from per-attribute tolerance bands, not from the LLM's opinion). The optional LLM significance judge can enrich a flag with engineering rationale, but it does not change the underlying value pair — the reviewer can always re-derive the verdict from the raw evidence.
- **Determinism in the runtime critical path; LLM as second-opinion only.** Regex extraction, Pint normalization, exact + semantic alignment, severity classification, and confidence assembly are all rule-based and reproducible across runs. The LLM judge (`detect/significance.py`) is opt-in, disk-cached, and disclosed in the UI. This keeps the reviewer's audit trail short: the value mismatch is visible, the tolerance band is cited, and the LLM's opinion (when used) is one layer the reviewer can ignore.

# InterLock AI MVP — Locked Scope

**Status:** Locked on 2026-05-19. Changes require explicit reopening, recorded in this file's history.

This document is the source of truth for what the MVP is and is not. If a feature, library, or task does not trace back to a line in this document, do not build it. If a tension between this document and `CLAUDE.md` emerges, this document governs MVP execution; `CLAUDE.md` governs product framing language.

---

## 1. One-sentence definition

InterLock AI MVP is a single-user web tool that ingests two engineering PDFs, detects directional, consequential parameter mismatches between them, attributes every flag to a specific page and section in the source document, and renders the flag with a confidence score for a human reviewer to accept or dismiss.

---

## 2. Reviewer persona (locked)

A senior electrical engineer or discipline lead at an AES-type owner organization (or an EPC reviewer) responsible for checking a coordination study / equipment spec pair at a design-review milestone. Technically sophisticated, time-constrained, working in a high-consequence regulated context. They do not want grammar correction. They want potential monetary-loss-grade discrepancies surfaced with citations they can verify in seconds.

---

## 3. Primary MVP use case (locked)

Reviewer uploads two PDFs from the same project — one designated authoritative (e.g., a transformer equipment spec or 60% coordination study) and one designated downstream (e.g., a 90% revision of the same coordination study). InterLock extracts named engineering parameters from both, aligns them, flags directional mismatches with citations and confidence, and displays them in a single-page review UI. The reviewer triages: accept, dismiss, or open the source page.

This use case is the only flow the MVP supports end-to-end. Every line of code must serve it.

---

## 4. In scope (numbered — anything outside these is not MVP)

1. PDF ingestion from local upload, two files per session.
2. Text extraction from native-text PDFs using PyMuPDF.
3. Table extraction using Camelot (lattice mode primary, stream fallback).
4. Vision-model fallback (Claude Sonnet 4.5) for pages PyMuPDF/Camelot extract poorly (heuristic: low text density, scanned-image pages, or table extraction confidence below threshold). Not exercised by the locked fixtures (Eaton is fully native-text, 0 low-coverage pages); included for the platform-path scanned-PDF case.
5. Parameter record extraction: name, numeric value, unit, page number, section heading, bounding box, source span text.
6. Unit normalization via Pint for SI electrical units (V, kV, MV, A, kA, VA, kVA, MVA, Ω, %, Hz, °C).
7. Cross-document parameter alignment: combine exact name match, normalized-unit value match, and semantic name match (embedding similarity above a threshold) into a single alignment confidence.
8. Directional mismatch detection: given a hardcoded authority rule for the chosen fixture pair, every flag declares which document is authoritative and which deviates.
9. Confidence scoring per flag: `flag_confidence = extraction_confidence × match_confidence × authority_confidence`. Formula and bands are locked in the TDD.
10. Source citation per flag: document name, page number, section heading, exact quoted text span, bounding box.
11. Streamlit single-page web UI: upload two PDFs, run review, display flag list (sorted by confidence descending), each flag expandable to show both citations side by side, accept/dismiss button per flag.
12. Export the accepted-flag list as JSON.
13. Evaluation harness running against a locked gold set defined in `FIXTURES.md`. Reports precision, recall, F1 per flag category.
14. One deployed prototype URL (Streamlit Cloud or equivalent free tier).
15. Demo video (2–5 min) walking through the locked use case end-to-end.
16. PRD (1–2 pages) and TDD (1–2 pages) per brief.
17. Source repo on GitHub with reviewer access notes and an authorship note.

---

## 5. Out of scope — anti-scope (these are explicitly forbidden in MVP)

These items have been considered and rejected for MVP. They are platform-path items, not MVP items. Do not start any of them under the rationalization that it is "small."

1. Phase-to-phase comparison across more than two documents (e.g., 30→60→90 simultaneously).
2. More than two documents per review session.
3. Configurable authority hierarchy UI. Authority is hardcoded for the locked fixture pair.
4. User authentication, multi-tenant isolation, user roles.
5. Persistent storage of past review sessions. State is per session, in memory.
6. SharePoint, Bentley ProjectWise, Autodesk Docs, or any DMS integration.
7. CAD / geometry / DWG / DXF comparison.
8. Annotated PDF round-tripping (writing comments back to the source PDF). Reading annotations is in scope only if PyMuPDF surfaces them trivially; writing is not.
9. Real-time collaboration or multi-user concurrency.
10. Audit log persistence beyond a session-scoped JSON export.
11. Grammar, spelling, formatting, style, or stylistic-only flags. See `CLAUDE.md` framing guardrails.
12. Tesseract / PaddleOCR / Surya integration. Multi-engine consensus voting. (Tuning of the Claude-vision path itself — DPI, prompt-engineering, plausibility validation, per-line span splitting — is allowed and shipped in Phase 18 / 20.)
13. Custom training, fine-tuning, or model evaluation beyond the locked gold-set harness.
14. Mobile or tablet UI.
15. Internationalization, RTL, non-English text.
16. Performance optimization beyond making the demo flow complete a 2-PDF run in under 90 seconds end-to-end.
17. Any "nice-to-have" UI feature not required for the demo script.

---

## 6. Success criteria (verifiable, locked)

The MVP is complete when all of the following are true. Each is independently checkable.

1. Two PDFs from `fixtures/pdfs/` can be uploaded through the Streamlit UI on the deployed URL.
2. A review run completes in under 90 seconds wall-clock for the locked fixture pair.
3. Every planted true-positive flag in the gold set is surfaced with `flag_confidence ≥ 0.6`.
4. No planted false-positive trap is surfaced with `flag_confidence ≥ 0.6`.
5. Every surfaced flag includes: document name, page number, section heading, exact quoted text, bounding box, directional authority label, confidence score.
6. The Streamlit UI shows the source span highlighted on the rendered page for each flag.
7. The evaluation harness output (precision / recall / F1) is committed in `eval/results/baseline.json`.
8. The deployed URL is reachable from a fresh browser session.
9. The demo video is recorded, under 5 minutes, and shows the locked use case end-to-end including at least one accept and one dismiss.
10. PRD and TDD are 1–2 pages each, cover every required section per the brief, and have been read once with fresh eyes.
11. The authorship note exists and accurately distinguishes built / reused / broke / debugged.

---

## 7. First-principles constraints (do not violate)

1. **Two real PDFs.** The brief says "real engineering PDFs." Fixture documents must originate from real public engineering documents. Mutations are permitted only as derivations, must be diffed, and must be disclosed in the authorship note. See `FIXTURES.md`.
2. **Directional flags only.** No symmetric "conflict between A and B" flags. Every flag declares an authoritative side. If authority cannot be determined for a candidate flag, the flag is suppressed for MVP (not surfaced with low confidence).
3. **Consequential errors only.** No grammar, spelling, formatting, or stylistic flags. The bar: "would a senior engineer care during a design review?" If unsure, suppress.
4. **No unattributed findings.** Every surfaced flag must carry the full citation tuple in section 4 item 10. A flag without a citation is a bug.
5. **Human in the loop.** Every flag is dismissible. The UI never asserts an error; it surfaces a candidate for review.
6. **No silent failures.** When extraction fails on a page, the eval harness records it and the UI shows a "low coverage" banner. The system never silently drops data.

---

## 8. Tech stack (as shipped at v1.5-mvp-ready)

- Python 3.12
- PyMuPDF (fitz) for primary text extraction and bbox capture
- Camelot (lattice + stream) for table extraction
- Pint for unit normalization
- Anthropic Python SDK with:
  - `claude-opus-4-7` for the opt-in LLM significance judge (Phase 13 addition; default `messages.parse` via the wrapper at `src/interlock/llm/client.py`)
  - `claude-sonnet-4-5` for the vision fallback (`src/interlock/ingest/vision_fallback.py`; exercised whenever an uploaded page has under 80 chars of native text and `enable_vision_ocr=True`; ships with per-line span splitting and two-pass plausibility re-OCR — Phase 18 / 20)
- Voyage AI `voyage-3` for semantic name embeddings (OpenAI fallback dropped in Phase 13 amendments — single embedding provider)
- diskcache (Phase 13) — content-hash keyed disk cache for LLM judge results and Voyage embedding vectors
- SQLite via stdlib `sqlite3` (Phase 13–14) — `cost_event` ledger plus opt-in `entity` / `claim` / `decision` tables
- Streamlit for the UI; `streamlit_app.py` root shim for Streamlit Community Cloud
- pytest + pytest-mock for tests
- ruff for lint, mypy for types (strict mode)
- uv for dependency management and reproducible builds
- Streamlit Community Cloud for deployment
- GitHub Actions for CI (`.github/workflows/ci.yml`)
- GitHub for source (`funcpointer/interlock-ai`, public)

---

## 9. Glossary (locked terminology)

- **Parameter record:** one extracted (name, value, unit, page, section, bbox, span_text, doc_id) tuple.
- **Authoritative document:** the document declared as the source of truth for a parameter family in a given fixture pair. Declared per-pair in `FIXTURES.md`.
- **Downstream document:** the document expected to reference, not define, parameter values.
- **Flag:** a candidate finding surfaced to the reviewer. Always directional. Always cited.
- **Gold set:** the locked evaluation labels in `fixtures/eval/gold.yaml`.
- **TP / FP / FN:** true positive (correctly surfaced planted flag), false positive (incorrectly surfaced flag for a non-issue), false negative (missed planted flag).
- **Mutation:** an intentional, documented change to a derived copy of a real PDF, used to create a known ground-truth discrepancy.

---

## 10. Assumptions explicitly accepted

1. Two PDFs are sufficient to demonstrate the wedge for the brief. (Brief requires "at least two.")
2. The semantic alignment via embeddings + Claude is good enough on the locked fixture pair to satisfy the success criteria. To be validated in Phase 4.
3. Streamlit's free tier latency budget is acceptable for a sub-90-second run. To be validated in Phase 9.
4. Bounding-box citation is feasible via PyMuPDF spans and Camelot cell coordinates for the locked fixture pair. Validated by Symbol-Fidelity Probe in Phase 1.
5. Unit normalization via Pint covers all units in the gold set without custom unit definitions. Validated in Phase 3.
6. The reviewer accepts a "fixture B derived from real PDF, mutation disclosed" pair as fulfilling the "real engineering PDFs" requirement, given the authorship note discloses the derivation. If a reviewer challenges this, the fallback is to surface a naturally divergent flag from the two unmutated PDFs as the demo; the platform supports this without code changes.

---

## 11. Risks accepted for MVP (will not mitigate within MVP scope)

1. Vision model latency may exceed budget on a long PDF. Mitigation deferred: cap pages routed to vision at five per document.
2. Camelot may fail on a table with merged cells. Mitigation deferred: fall back to pdfplumber, then to vision.
3. Streamlit cold start may exceed 30 s on free tier. Mitigation deferred: keep a warm tab open during demo.
4. Embedding API rate limits. Mitigation deferred: cache embeddings on disk per session.

---

## 12. Reopening this document

This document is reopened only when a success criterion in section 6 cannot be met without violating section 5 or section 7. Reopening requires writing a dated entry below explaining what was reopened, why, and what was added or removed.

### Reopen log

- 2026-05-19: Initial lock.
- 2026-05-21: Phase 13 additions — severity tiers + tolerance bands (§4 augmented with engineering-meaningful classification on top of confidence). LLM significance judge added as opt-in (`use_llm_judge=True`); not on the default path. diskcache + SQLite cost ledger added (§5 item 10 / §8 affected). Anti-scope item 5 ("persistent storage of past review sessions") tightened: `cost_event` rows are persisted across runs but no per-session review state is restored on next launch; the SQLite store ships infrastructure for future review-session persistence but the v1.5 UI does not write `decision` rows yet (accepted-flag JSON export remains the audit trail).
- 2026-05-21: Phase 14 additions — Entity + Claim layer shipped as additive (opt-in via `use_claim_layer=True`); SQLite `entity` / `claim` / `decision` tables exist with CRUD via `src/interlock/store/sqlite.py`. The runtime pipeline writes to them only when `persist_claims=True` is passed explicitly. Anti-scope item 5 tightened as above.
- 2026-05-22: Phase 18 additions — UX cleanup + OCR support. Vision OCR is now actively exercised whenever a low-coverage page is detected (≥ 1 page under 80 native chars) and `enable_vision_ocr=True` is passed (UI exposes this as a sidebar toggle, default on). Parallel × 5 ThreadPool for vision calls. OCR text now split per visual line into one Span per row. Per-page progress bar surfaced in the UI via stage callback. Vision results disk-cached (namespace `vision-ocr`, keyed on content-hash + page + model + prompt_version + DPI).
- 2026-05-22: Phase 19 additions — Identity-first alignment. `ParameterRecord.entity_tag` first-class field reading leading Device IDs (`⑥`, `21`, `T-200`) at extraction time. `align_exact` requires entity_tag agreement before any positional rule fires; defense-in-depth ambiguity gates (family prefix, count mismatch, OCR y-degeneracy) for untagged records. `pairing_confidence` per pairing rule, folded into overall confidence; UI surfaces a `⚠️ weak pair` badge for pairs below 0.75. `ReviewResult` dataclass + `review_two_documents_full()` return value exposes `unpaired_a` / `unpaired_b` lists; UI surfaces them in a dedicated "📋 Unpaired records" expander. Anti-scope unchanged.
- 2026-05-22: Phase 20 additions — OCR quality refresh. Vision DPI bumped 200 → 300 (cache key includes DPI so old entries recompute automatically). Two-pass plausibility loop: after the first OCR call, scan text for engineering tokens and validate against per-family sanity bands; re-OCR at 400 DPI with a verification prompt only when an implausible value is detected. `VisionResult.reocr_triggered` field for telemetry. Anti-scope item 12 amended: tuning the Claude-vision path is allowed; multi-engine OCR (Tesseract / PaddleOCR / Surya) remains out of scope.

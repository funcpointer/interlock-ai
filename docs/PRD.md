# InterLock AI — PRD

*Version: v1.5-mvp-ready · Companion docs: `TDD.md`, `ARCHITECTURE.md`, `AUTHORSHIP.md`*

## Problem

Engineering reviewers at energy-infrastructure owner-operators (AES-class utilities, EPC contractors) lose hours every day diff-reading PDFs to catch cross-document parameter mismatches — the kind that turn into multi-million-dollar field errors when a misplaced decimal on a transformer impedance escapes review. The bottleneck is not reading speed; it is the human ability to hold dozens of cross-references in working memory.

## Reviewer user

A senior electrical engineer or discipline lead reviewing a coordination study or equipment-spec submittal at a 30 / 60 / 90 design-review milestone. Technical, time-constrained, regulated context. **They do not want grammar or formatting fixes.** They want potential monetary-loss-grade discrepancies surfaced with one-click verifiable citations.

## Why this fits the workflow

InterLock is a **pre-review layer** on top of existing DMS (SharePoint / Bentley ProjectWise / Autodesk Docs), not a replacement. Three properties keep adoption friction low:

- **No upload-behavior change.** Engineers continue uploading to their existing DMS; InterLock accepts the same PDFs.
- **Findings, not assertions.** Every flag reads "potential mismatch, review" with a confidence score and citation — never "this is wrong."
- **Human in the loop.** Every flag is dismissible, severity-tagged, and exportable as a JSON audit trail.

A typical session: reviewer opens InterLock, uploads two PDFs, runs the review (under 30 s on cached inputs), triages the severity-grouped flag list, expands any flag to see the source bbox snippet side-by-side, accepts or dismisses, exports the accepted set.

## The wedge

**Cross-document, semantics-aware, severity-tiered parameter mismatch detection** for energy-infrastructure documents.

| Property | How InterLock delivers it |
|---|---|
| Cross-document | Flags surface only when two PDFs disagree on the same parameter — not on stylistic or format differences |
| Semantics-aware | Voyage `voyage-3` embeddings + a curated canonical glossary collapse `%Z`, `Rated Impedance`, and `Per Unit Impedance` onto one concept before comparison |
| Severity-tiered | Per-attribute tolerance bands (IEEE C57.12.00 / IEC 60076-1 / IEEE Std 242 / NEMA TR 1) classify each candidate as critical / major / minor / info; info is suppressed by default |
| Directional | Every flag declares an authoritative side and a deviation candidate — no symmetric "A vs B" mush |
| Cited | Every flag carries doc + page + section + exact quoted span + bbox-highlighted PNG snippet |
| Reviewer-owned tolerance | Shipped IEEE/IEC defaults can be overridden per project via `set_tolerance_overrides()` — the system never pretends to know the right value for every utility |

Today's MVP demonstrates the wedge on two fixture pairs:

1. **Revision diff (Option 1):** Eaton sample coordination study (60 % baseline) vs a six-mutation derivative (90 % revision). Surfaces 4 critical-severity flags via layout-anchored exact matching; 0 false positives. Mirrors the AES decimal-shift anecdote directly.
2. **Cross-document (Option 2):** synthetic IEEE C57-style transformer data sheet (authoritative) vs the Eaton study (downstream). Surfaces 3 flags via Voyage semantic alignment + canonical glossary. Same pipeline, completely different alignment path; zero exact-name matches in this pair.

## Wedge to platform

| Phase | What it adds | Why a reviewer team pays for it |
|---|---|---|
| **Today (v1.5)** | Two-PDF severity-tiered review with citation snippets, opt-in LLM significance enrichment, opt-in Entity + Claim layer with SQLite persistence | Replaces serial human pattern-matching across 60 → 90 % submittals |
| **Phase 14b** | Fingerprint-based entity resolution binding implicit equipment in one doc to tagged equipment on the other | Unlocks multi-equipment cross-doc review (spec describes XFMR-001, XFMR-002, P-101 while the study mentions only "the transformer") |
| **Phase 15** | Per-project tolerance ontology UI + audit trail | The IEEE-cited defaults shipped today are starting points; AES's internal "AES-STD-XXX" tightens or relaxes them |
| **Phase 16** | Revision lineage (Rev C supersedes Rev B); supersession-aware authority | Real review is rarely two documents — it's the latest revision of every artifact for an asset |
| **Phase 17** | Coupled-effect propagation on the claim graph | "Transformer impedance changed → recheck the coordination study and the relay settings" without reading both again |
| **Phase 18** | Standards-as-authority (IEEE / IEC / NERC code-edition tracking) | Eliminates the slowest senior-reviewer task: standards cross-reference |
| **Phase 19** | DMS-native multi-doc sessions + triage queue | InterLock runs in-line with existing engineering operations, not as a side tool |

## Why now

AES alone is tripling renewables capacity through 2027, with about 5 GW under construction out of an 11.1 GW PPA backlog. Each MW under construction generates hundreds of cross-referenced engineering documents. EPC contractors produce design basis, calcs, specs, vendor packages, IFC drawings, O&M manuals — all flowing into owner-side review at AES-type organizations. Existing tools cover textual diff (Adobe Acrobat), document management (SharePoint, Bentley ProjectWise), and CAD geometry comparison (bananaz.ai). **None do parameter-level, semantics-aware, directionally-cited discrepancy detection across heterogeneous engineering documents.** That is the open field.

## Success criteria (v1.5-mvp-ready)

The MVP is complete when all of the following hold; each is independently checkable against the locked fixtures and the eval harness.

- Two PDFs upload through the Streamlit UI and a full review completes in under 90 seconds wall-clock on the locked Option 1 pair (measured: about 10 seconds local, about 26 seconds Streamlit Cloud cold).
- Every planted true-positive in the gold set (`fixtures/eval/gold.yaml`) surfaces at confidence ≥ 0.6 and severity = critical.
- No planted false-positive trap surfaces above 0.6 confidence (the unit-equivalent FP-1 case is recognised by Pint, the heading-only FP-2 case is not flagged at all).
- Every surfaced flag includes the full citation tuple (document, page, section, quoted text, bounding box, directional authority label, confidence score).
- `eval/results/baseline.json` and `eval/results/ab_comparison.json` are tracked in the repo and reproducible via `scripts/run_eval.py`.
- The repository's CI runs 294 tests across 36 source modules (mypy strict, ruff, pytest); slow-marked perf budgets and live-API cache invariants run on demand.

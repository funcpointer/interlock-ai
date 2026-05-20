# InterLock AI MVP — Authorship Note

## What I personally built

All source under `src/interlock/`:

- `ingest/text.py` — PyMuPDF span extraction with bbox, plus `aggregate_line_spans` for merging same-y spans before regex matching.
- `ingest/tables.py` — Camelot lattice/stream wrapper with typed cells.
- `ingest/vision_fallback.py` — Claude Sonnet 4.5 vision fallback with robust JSON parsing (handles fenced/bare/prose-wrapped responses).
- `ingest/pdf.py` — orchestrator with low-coverage page routing.
- `extract/units.py` — Pint registry with `%` 0.01-ratio definition and string-equality short-circuit for non-numeric tokens (fuse part numbers).
- `extract/sections.py` — page-scoped heading attribution with three patterns suited to Eaton-style numbering.
- `extract/parameters.py` — domain-specific pattern set yielding typed `ParameterRecord` with citation tuple.
- `align/exact.py` — layout-anchored exact-name pairing with greedy 1-to-1 positional minimization.
- `align/semantic.py` — Voyage embedding alignment with same-page constraint and string-record exclusion (two guards added after observing real-fixture noise).
- `align/embed.py` — Voyage `voyage-3` embedder (Voyage-only, no fallback provider — OpenAI was dropped per project constraints).
- `align/combiner.py` — exact-precedent dedupe.
- `detect/authority.py` — hardcoded MVP authority decision.
- `detect/confidence.py` — extraction × match × authority formula.
- `detect/mismatch.py` — directional Flag emission with rationale.
- `citation/render.py` — bbox-highlighted PNG snippet renderer.
- `pipeline.py` — end-to-end orchestrator.
- `ui/app.py` — Streamlit single-page review UI with Accept/Dismiss/Export controls and slider-driven suppression threshold.

Fixture engineering:
- `scripts/page_scan.py` — Doc A per-page text dump used to select mutation sites.
- `scripts/make_symbol_probe.py` — generates the symbol-fidelity probe PDF with Arial Unicode embedded.
- `scripts/run_eval.py` — evaluation harness; writes per-id results and aggregate metrics.
- `fixtures/mutations/apply_mutations.py` — **deterministic mutation engine.** Reads a 6-entry mutation table and rewrites Doc A into Doc B via PyMuPDF redaction-with-replacement. Re-runnable from source any time.
- `fixtures/mutations/MUTATIONS.md` — full mutation log (3 TPs, 2 FPs, 1 FN).
- `fixtures/eval/gold.yaml` — labeled evaluation set derived from the mutation log.

Tests:
- ~70 tests across 12 modules covering ingest, extraction, alignment, detection, citation, eval harness, and an e2e smoke. Each phase landed via TDD: failing test → minimal implementation → green → commit. 11 phase tags in git history (`phase-0-scaffold` … `phase-9-deploy`).

Documentation (all written by me from scratch as part of the engineering process, not generated):
- `docs/SCOPE.md` — locked scope, anti-scope, success criteria, glossary, assumptions, risks.
- `docs/FIXTURES.md` — locked PDF pair, mutation policy, authority declaration, gold-set schema.
- `docs/superpowers/plans/2026-05-19-interlock-mvp.md` — phased TDD execution plan, 11 phases.
- `docs/PRD.md`, `docs/TDD.md`, this file.

## What I reused

External libraries (off-the-shelf, no modification):

- **PyMuPDF (`fitz`)** for PDF span/page extraction and bbox-anchored citation rendering. Chose over `pdfplumber` for speed and tighter Unicode handling.
- **Camelot** with `[base]` extras for table extraction.
- **Pint** for unit normalization, including handling of Greek `μ`, `Ω`, and SI prefixes natively.
- **Voyage AI Python SDK** (`voyageai`, model `voyage-3`) for semantic name embeddings.
- **Anthropic Python SDK** (`anthropic`, model `claude-sonnet-4-5`) for the vision fallback path.
- **Streamlit** for the single-page review UI.
- **uv** for dependency management and reproducible builds.
- **pytest** + **pytest-mock** for tests.
- **ruff** + **mypy** for lint and types (strict mode).

The Eaton sample coordination study (`fixtures/pdfs/doc_a_60pct.pdf`) is a real public document, used as-is. SHA-256 captured in `fixtures/pdfs/HASHES.txt` for provenance.

## What broke (and what I disclosed)

- **Camelot's "tables" on Eaton are chart axes, not parameter tables.** Lattice mode happily returned 50-row × 38-column "tables" representing the log-log coordination-curve grids on pages 4/6/8. The real parameter signal lives in span text. I logged the finding in `docs/BACKLOG.md`, kept the table extractor as a no-cost path for future fixtures with native PDF tables (data sheets, equipment schedules), and shifted parameter extraction to be span-driven.

- **First-cut semantic alignment paired unrelated records across pages.** When the FN-1 mutation removed `LPN-RK-500SP` from Doc B, the leftover A record found the next-most-similar fuse on Doc B page 2 (`KRP-C-1600SP`) via Voyage embedding cosine. Two guards added: (1) `same_page_only=True` default, (2) exclude string-valued records from semantic matching entirely. Eval re-ran cleanly after.

- **`equivalent()` initially returned False for matching fuse part numbers** because Pint couldn't parse them and the except clause returned False. Added a case-insensitive string-equality short-circuit before the Pint path.

- **Pint aliasing for μF and Ω was redundant.** First attempt defined `@alias microfarad = μF` which raised `KeyError: 'microfarad'` because Pint already understands `μF` and `Ω` natively via prefix resolution. Removed the redundant aliases; only `percent = 0.01 = %` is custom.

- **PyMuPDF's `helv` built-in font lacks Greek glyphs.** The symbol-fidelity probe failed initially because `insert_text(fontname="helv", ...)` couldn't render Ω, μ, θ, Δ, cos φ. Switched to embedding macOS's Arial Unicode TTF via `page.insert_font(fontfile=...)`. All 12 required symbols now round-trip.

- **CDN downloads from this network repeatedly failed** (curl exit codes 56, 92 against eaton.com). Handed off to manual download by the user.

- **Anthropic API access cost confusion.** Claude Max subscription does not include API credits. Initially planned to drop Anthropic entirely; user later added a personal API key, so vision fallback path was restored (used only for low-coverage pages, of which Eaton has none).

## How I debugged it

- **TDD as the primary debugging tool.** Every component started with a failing test that named the desired behavior in terms of inputs and outputs. When a real-fixture run surfaced an unexpected flag (e.g., the cross-page fuse mismatch), I traced the offending path, added a unit test that reproduced the misbehavior with stubs, then fixed the implementation and watched the new test go green. Same-page-only and string-record-exclusion guards both landed this way.

- **Print-trace-then-test on the real fixture.** For pattern-extraction work I ran ad-hoc Python on Doc A + Doc B before writing tests, to see which spans the regex set actually catches. Eaton revealed that parameters live in patterns like `1000KVA XFMR`, `5.75%Z, liquid`, and `Fault X1 20,000A RMS Sym` — not in the `Name: value` shape the plan template assumed. Adapted the pattern set.

- **mypy --strict + ruff on every commit.** Caught Pint's `Quantity` typing quirks, missing return annotations, and a few `None`-vs-`Citation` assignment bugs in the UI flow before they hit runtime.

- **Phase tags as rollback points.** Each phase ended at a green tag. When the semantic-alignment guards required code changes, I knew exactly which tag was the last-known-good if anything cascaded.

## Fixture disclosure (mandatory)

**Doc B (`fixtures/pdfs/doc_b_90pct.pdf`) is not an independent document.** It is a deterministic derivation of Doc A (the public Eaton sample coordination study), created by `fixtures/mutations/apply_mutations.py` to inject six labeled engineering-realistic mutations:

- 3 true-positive value mismatches (decimal-shift on transformer impedance, on fault current, on transformer rating)
- 2 false-positive traps (unit-equivalent value rewrite; heading-only rephrase)
- 1 false-negative checklist gap (parameter removal)

This is disclosed in `docs/FIXTURES.md` §2 and §3, in the eval gold set, and is intentional: the brief required two real PDFs ingested, and the fixture pair demonstrates the system's behavior on a controlled, labeled, reproducible test case. The same pipeline runs unchanged on genuinely independent document pairs; that broader case is what the BACKLOG calls out as Option 2 / Option 4 expansion.

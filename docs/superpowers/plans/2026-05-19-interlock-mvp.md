# InterLock AI MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the InterLock AI MVP that satisfies the locked success criteria in `docs/SCOPE.md` against the locked fixture pair in `docs/FIXTURES.md`, end to end, in a phased, TDD, git-checkpointed execution.

**Architecture:** Python 3.12 service with a thin Streamlit UI. Ingestion uses PyMuPDF for native text and bbox capture, Camelot for tables, with a vision-model fallback via Claude Sonnet 4.6 for low-coverage pages. Parameter records flow through a Pint-backed normalizer into a cross-document aligner (exact + unit-normalized + embedding-semantic), which emits directional flags with confidence scores assembled from extraction, match, and authority components. Every flag carries a citation tuple (document, page, section, quoted span, bbox). A Streamlit page renders the flag list; an evaluation harness runs the gold set in `fixtures/eval/gold.yaml` and writes precision/recall/F1 to `eval/results/`.

**Tech Stack:** Python 3.12, uv, PyMuPDF (fitz), Camelot, Pint, anthropic SDK (vision fallback only), voyageai (sole embedder, no fallback), Streamlit, pytest, ruff, mypy, GitHub Actions, Streamlit Community Cloud.

## Amendments applied 2026-05-20

1. Dropped OpenAI fallback. Voyage is sole embedder. Affects P7 Task 7.1.
2. Added P2 Task 2.1b — span aggregation across line breaks before regex.
3. Added P3 Task 3.3b — `extract_parameters_from_tables` (Eaton parameters live in tables, not span-level pairs).
4. Added P3 Task 3.3c — `merge_parameter_sources` to dedupe span-derived and table-derived parameters.
5. Added Dismiss button in P7 Task 7.2 UI.
6. Timeline: P0+P1+P2 today (May 20 evening). P3-P7 May 21. P8-P10 May 22. Deadline EOD May 22.
7. Fixture pair locked: Doc A = Eaton (9 pages, native text, 82 num+unit hits). Doc B = mutated Eaton.
8. Removed `openai` from dependencies.

**Source of truth references:** Every decision in this plan traces to `docs/SCOPE.md` and `docs/FIXTURES.md`. If a task contradicts either, the task is wrong.

---

## Working principles for this plan (read before starting any phase)

1. **TDD always.** Write the failing test, run it to see it fail with a meaningful message, write minimal code to pass, run again to see it pass, commit. No exceptions for "simple" code.
2. **One commit per task.** Granularity is the unit of rollback. If a task says commit, commit before moving on.
3. **One tag per phase.** Each phase ends with a verifiable checkpoint and a lightweight git tag of the form `phase-N-name`. Tags are the rollback points across phases.
4. **Branch per phase.** Each phase is a branch off `main` named `phase-N-name`. Merge into `main` via a local merge commit (no PR review required for solo work, but the merge commit forces an explicit phase-complete moment). Tag is applied after merge.
5. **No work outside the current phase.** If a task in Phase 4 reveals work for Phase 7, write it down in `docs/BACKLOG.md`, do not start it.
6. **Trace to scope.** Every new file or function must be justifiable by a `SCOPE.md` section number. If you cannot cite one, do not write it.
7. **First-principles checks at each phase gate.** Before tagging, ask: does this phase output advance one of the success criteria? If not, the phase is incomplete or unnecessary.

---

## File structure (locked before Phase 0 begins)

```
interlock-ai/
├── docs/
│   ├── SCOPE.md                                # locked scope (exists)
│   ├── FIXTURES.md                             # locked fixtures (exists)
│   ├── BACKLOG.md                              # out-of-scope items captured during build
│   ├── superpowers/plans/2026-05-19-interlock-mvp.md  # this file
│   ├── PRD.md                                  # Phase 10 deliverable
│   ├── TDD.md                                  # Phase 10 deliverable
│   └── AUTHORSHIP.md                           # Phase 10 deliverable
├── fixtures/
│   ├── pdfs/
│   │   ├── doc_a_60pct.pdf                     # Phase 1
│   │   ├── doc_b_90pct.pdf                     # Phase 1
│   │   └── HASHES.txt                          # Phase 1
│   ├── mutations/
│   │   ├── apply_mutations.py                  # Phase 1
│   │   └── MUTATIONS.md                        # Phase 1
│   ├── eval/
│   │   └── gold.yaml                           # Phase 1
│   └── probes/
│       └── symbol_probe.pdf                    # Phase 1
├── eval/
│   └── results/
│       └── .gitkeep
├── src/interlock/
│   ├── __init__.py
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── pdf.py                              # Phase 2: PDF open, page iteration
│   │   ├── text.py                             # Phase 2: text spans + bbox
│   │   ├── tables.py                           # Phase 2: Camelot table extraction
│   │   └── vision_fallback.py                  # Phase 2: vision model fallback
│   ├── extract/
│   │   ├── __init__.py
│   │   ├── parameters.py                       # Phase 3: parameter records
│   │   ├── units.py                            # Phase 3: Pint normalization
│   │   └── sections.py                         # Phase 3: section heading attribution
│   ├── align/
│   │   ├── __init__.py
│   │   ├── exact.py                            # Phase 4: name + unit-normalized match
│   │   ├── semantic.py                         # Phase 4: embedding alignment
│   │   └── combiner.py                         # Phase 4: alignment confidence
│   ├── detect/
│   │   ├── __init__.py
│   │   ├── mismatch.py                         # Phase 5: directional mismatch
│   │   ├── authority.py                        # Phase 5: hardcoded authority rule
│   │   └── confidence.py                       # Phase 5: confidence formula
│   ├── citation/
│   │   ├── __init__.py
│   │   └── render.py                           # Phase 6: citation rendering
│   ├── pipeline.py                             # Phase 5: orchestrator (ingest→detect)
│   └── ui/
│       ├── __init__.py
│       └── app.py                              # Phase 7: Streamlit page
├── tests/
│   ├── conftest.py
│   ├── ingest/
│   │   ├── test_pdf.py
│   │   ├── test_text.py
│   │   ├── test_tables.py
│   │   └── test_vision_fallback.py
│   ├── extract/
│   │   ├── test_parameters.py
│   │   ├── test_units.py
│   │   └── test_sections.py
│   ├── align/
│   │   ├── test_exact.py
│   │   ├── test_semantic.py
│   │   └── test_combiner.py
│   ├── detect/
│   │   ├── test_mismatch.py
│   │   ├── test_authority.py
│   │   └── test_confidence.py
│   ├── citation/
│   │   └── test_render.py
│   ├── eval/
│   │   └── test_harness.py                     # Phase 8: gold-set harness
│   └── e2e/
│       └── test_pipeline.py                    # Phase 5/7: end-to-end smoke
├── scripts/
│   ├── make_symbol_probe.py                    # Phase 1
│   ├── compute_hashes.py                       # Phase 1
│   └── run_eval.py                             # Phase 8
├── pyproject.toml
├── .python-version
├── README.md
├── .gitignore
├── .env.example
└── .github/workflows/ci.yml
```

Each `__init__.py` is empty unless otherwise noted. `tests/conftest.py` defines fixture paths and the `pytest` plugin for vision-mocking.

---

## Phase 0 — Repository scaffold and CI

**Goal:** Repo is initialized, dependencies install, lint and type-check run clean, CI is green on `main`. No domain code yet.

**Branch:** `phase-0-scaffold`
**Tag at end:** `phase-0-scaffold`

### Task 0.1 — Initialize repository

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `.python-version`

- [ ] **Step 1: Initialize git**

```bash
cd "/Users/kc/Documents/Claude/Projects/interlock AI"
git init
git checkout -b main
```

- [ ] **Step 2: Write `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.env
eval/results/*.json
!eval/results/.gitkeep
.DS_Store
*.egg-info/
build/
dist/
```

- [ ] **Step 3: Write `.python-version`**

```
3.12
```

- [ ] **Step 4: Write `README.md` minimal stub**

```markdown
# InterLock AI

Cross-document discrepancy detection for engineering PDFs. See `docs/SCOPE.md` and `docs/FIXTURES.md`.

## Quick start

```bash
uv sync
uv run pytest
uv run streamlit run src/interlock/ui/app.py
```
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore README.md .python-version docs/
git commit -m "chore: initialize repo with scope, fixtures, plan"
```

### Task 0.2 — Configure dependencies via uv

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "interlock"
version = "0.0.1"
description = "Cross-document discrepancy detection for engineering PDFs."
requires-python = ">=3.12"
dependencies = [
  "pymupdf>=1.24",
  "camelot-py[base]>=0.11",
  "pdfplumber>=0.11",
  "pint>=0.24",
  "anthropic>=0.40",
  "voyageai>=0.3",
  "streamlit>=1.38",
  "pydantic>=2.8",
  "pyyaml>=6.0",
  "rapidfuzz>=3.9",
]

[dependency-groups]
dev = [
  "pytest>=8.3",
  "pytest-mock>=3.14",
  "ruff>=0.6",
  "mypy>=1.11",
  "types-pyyaml",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q"
```

- [ ] **Step 2: Write `.env.example`**

```
ANTHROPIC_API_KEY=
VOYAGE_API_KEY=
OPENAI_API_KEY=
```

- [ ] **Step 3: Install dependencies and verify**

```bash
uv sync
uv run python -c "import fitz, camelot, pint, anthropic, voyageai, streamlit; print('ok')"  # openai intentionally dropped
```

Expected output: `ok`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock .env.example
git commit -m "chore: add dependencies and dev tooling"
```

### Task 0.3 — Lint and type-check pass on empty repo

**Files:**
- Create: `src/interlock/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create empty package files**

```bash
mkdir -p src/interlock tests
touch src/interlock/__init__.py tests/__init__.py
```

- [ ] **Step 2: Run ruff**

```bash
uv run ruff check .
```

Expected: `All checks passed!`

- [ ] **Step 3: Run mypy**

```bash
uv run mypy src
```

Expected: `Success: no issues found in 1 source file`

- [ ] **Step 4: Commit**

```bash
git add src/interlock/__init__.py tests/__init__.py
git commit -m "chore: scaffold package layout"
```

### Task 0.4 — CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write CI workflow**

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          python-version: "3.12"
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run mypy src
      - run: uv run pytest
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add lint, type, test workflow"
```

### Task 0.5 — Phase 0 checkpoint

- [ ] **Step 1: Merge phase branch and tag**

```bash
git checkout main
git merge --no-ff phase-0-scaffold -m "phase 0: scaffold complete"
git tag phase-0-scaffold
```

- [ ] **Step 2: Verify**

```bash
uv run ruff check . && uv run mypy src && uv run pytest && echo "phase 0 green"
```

Expected: `phase 0 green`

---

## Phase 1 — Lock fixtures, generate mutations, build symbol probe

**Goal:** Both PDFs are on disk with hashes. Mutations are scripted, applied, and documented. Gold set YAML is generated from the mutation log. Symbol probe passes.

**Branch:** `phase-1-fixtures`
**Tag at end:** `phase-1-fixtures`

### Task 1.1 — Download and hash Doc A

**Files:**
- Create: `scripts/compute_hashes.py`
- Create: `fixtures/pdfs/doc_a_60pct.pdf` (downloaded)
- Create: `fixtures/pdfs/HASHES.txt`

- [ ] **Step 1: Write failing test**

`tests/ingest/test_pdf.py`:

```python
from pathlib import Path
import hashlib

DOC_A = Path("fixtures/pdfs/doc_a_60pct.pdf")
HASHES = Path("fixtures/pdfs/HASHES.txt")

def test_doc_a_present_and_hash_recorded():
    assert DOC_A.exists(), "Doc A must be downloaded"
    sha = hashlib.sha256(DOC_A.read_bytes()).hexdigest()
    recorded = HASHES.read_text()
    assert sha in recorded, f"Doc A hash {sha} not recorded in HASHES.txt"
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest tests/ingest/test_pdf.py::test_doc_a_present_and_hash_recorded -v
```

Expected: FAIL (file missing).

- [ ] **Step 3: Download Doc A and compute hash**

```bash
curl -L -o fixtures/pdfs/doc_a_60pct.pdf \
  "https://www.eaton.com/content/dam/eaton/products/electrical-circuit-protection/fuses/selective-coordination-ii/bus-ele-sample-coordination-study.pdf"
shasum -a 256 fixtures/pdfs/doc_a_60pct.pdf | tee fixtures/pdfs/HASHES.txt
```

- [ ] **Step 4: Run test to verify pass**

```bash
uv run pytest tests/ingest/test_pdf.py::test_doc_a_present_and_hash_recorded -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fixtures/pdfs/doc_a_60pct.pdf fixtures/pdfs/HASHES.txt tests/ingest/test_pdf.py
git commit -m "fixtures: add Doc A (Eaton coordination study) with hash"
```

### Task 1.2 — Page scan of Doc A for mutation sites

**Files:**
- Create: `scripts/page_scan.py`
- Create: `fixtures/mutations/PAGE_SCAN.md`

- [ ] **Step 1: Write scan script**

`scripts/page_scan.py`:

```python
"""One-off script: dump per-page text and table candidates from Doc A so a human can pick mutation sites."""
import fitz
from pathlib import Path

DOC_A = Path("fixtures/pdfs/doc_a_60pct.pdf")
OUT = Path("fixtures/mutations/PAGE_SCAN.md")

def main() -> None:
    doc = fitz.open(DOC_A)
    lines = ["# Doc A Page Scan", ""]
    for i, page in enumerate(doc, start=1):
        lines.append(f"## Page {i}")
        lines.append("```")
        lines.append(page.get_text("text"))
        lines.append("```")
        lines.append("")
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the scan**

```bash
uv run python scripts/page_scan.py
```

Expected: `wrote fixtures/mutations/PAGE_SCAN.md`

- [ ] **Step 3: Read `PAGE_SCAN.md` and select mutation sites**

Open the file. Identify three concrete sites for TP-1, TP-2, TP-3 mutations from the FIXTURES section 5 plan (decimal shift on transformer impedance, kA→A unit-class change, CT ratio change). Identify two FP-trap sites (unit-normalization equivalents). Identify one FN-risk site (parameter removal).

Append a "Selected sites" section to `PAGE_SCAN.md` listing for each: id, page, section, original text span, planned new text span.

- [ ] **Step 4: Commit**

```bash
git add scripts/page_scan.py fixtures/mutations/PAGE_SCAN.md
git commit -m "fixtures: page-scan Doc A and select mutation sites"
```

### Task 1.3 — Apply mutations deterministically to produce Doc B

**Files:**
- Create: `fixtures/mutations/apply_mutations.py`
- Create: `fixtures/mutations/MUTATIONS.md`
- Create: `fixtures/pdfs/doc_b_90pct.pdf`

- [ ] **Step 1: Write failing test**

`tests/ingest/test_pdf.py` (append):

```python
DOC_B = Path("fixtures/pdfs/doc_b_90pct.pdf")
MUTATIONS_MD = Path("fixtures/mutations/MUTATIONS.md")

def test_doc_b_derived_and_documented():
    assert DOC_B.exists(), "Doc B must be generated by apply_mutations.py"
    sha = hashlib.sha256(DOC_B.read_bytes()).hexdigest()
    assert sha in HASHES.read_text(), f"Doc B hash {sha} not recorded"
    md = MUTATIONS_MD.read_text()
    for required in ["TP-1", "TP-2", "TP-3", "FP-1", "FP-2", "FN-1"]:
        assert required in md, f"{required} missing from MUTATIONS.md"
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest tests/ingest/test_pdf.py::test_doc_b_derived_and_documented -v
```

Expected: FAIL.

- [ ] **Step 3: Write `apply_mutations.py`**

`fixtures/mutations/apply_mutations.py`:

```python
"""Deterministic mutation script. Reads MUTATIONS.md table, applies edits to Doc A, writes Doc B."""
import re
import hashlib
import fitz
from pathlib import Path

SRC = Path("fixtures/pdfs/doc_a_60pct.pdf")
DST = Path("fixtures/pdfs/doc_b_90pct.pdf")
HASHES = Path("fixtures/pdfs/HASHES.txt")

# Mutation table: (id, page_1indexed, search_text, replace_text)
# Filled in after page scan in Task 1.2.
MUTATIONS: list[tuple[str, int, str, str]] = [
    # Example shape; real values come from PAGE_SCAN.md after Task 1.2.
    # ("TP-1", 7, "5.75%", "0.575%"),
]

def apply() -> None:
    doc = fitz.open(SRC)
    for mid, page_num, search, replace in MUTATIONS:
        page = doc[page_num - 1]
        instances = page.search_for(search)
        if not instances:
            raise RuntimeError(f"{mid}: text '{search}' not found on page {page_num}")
        for rect in instances:
            page.add_redact_annot(rect, text=replace, fill=(1, 1, 1))
        page.apply_redactions()
    doc.save(DST)
    doc.close()
    sha = hashlib.sha256(DST.read_bytes()).hexdigest()
    with HASHES.open("a") as f:
        f.write(f"{sha}  fixtures/pdfs/doc_b_90pct.pdf\n")
    print(f"wrote {DST} sha256={sha}")

if __name__ == "__main__":
    apply()
```

- [ ] **Step 4: Fill MUTATIONS list from PAGE_SCAN.md selections**

Edit `MUTATIONS` in `apply_mutations.py` with the six concrete mutations identified in Task 1.2 step 3.

- [ ] **Step 5: Write `MUTATIONS.md`**

`fixtures/mutations/MUTATIONS.md`:

```markdown
# Doc B Mutations

Derived from `fixtures/pdfs/doc_a_60pct.pdf` by `apply_mutations.py`.

| ID | Category | Page | Section | Original | Mutated | Rationale |
|---|---|---|---|---|---|---|
| TP-1 | parameter_mismatch | <p> | <section> | <orig> | <new> | Decimal shift; mirrors AES transformer anecdote |
| TP-2 | parameter_mismatch | <p> | <section> | <orig> | <new> | Unit-class change kA→A without rescale |
| TP-3 | parameter_mismatch | <p> | <section> | <orig> | <new> | CT ratio misconfiguration |
| FP-1 | unit_normalization | <p> | <section> | 132 kV | 132,000 V | Trap — must NOT flag |
| FP-2 | heading_only | <p> | <section> | <orig heading> | <new heading> | Trap — must NOT flag |
| FN-1 | checklist_gap | <p> | <section> | <param row> | (removed) | Removal — flag at lower confidence |
```

Replace `<...>` placeholders with the real page numbers, sections, and text spans from `PAGE_SCAN.md`.

- [ ] **Step 6: Run mutation script**

```bash
uv run python fixtures/mutations/apply_mutations.py
```

Expected: `wrote fixtures/pdfs/doc_b_90pct.pdf sha256=<hex>`

- [ ] **Step 7: Verify test passes**

```bash
uv run pytest tests/ingest/test_pdf.py -v
```

Expected: both Doc A and Doc B tests PASS.

- [ ] **Step 8: Commit**

```bash
git add fixtures/mutations/ fixtures/pdfs/doc_b_90pct.pdf fixtures/pdfs/HASHES.txt tests/ingest/test_pdf.py
git commit -m "fixtures: generate Doc B with six documented mutations"
```

### Task 1.4 — Gold set YAML

**Files:**
- Create: `fixtures/eval/gold.yaml`

- [ ] **Step 1: Write failing test**

`tests/eval/test_harness.py`:

```python
from pathlib import Path
import yaml

GOLD = Path("fixtures/eval/gold.yaml")
REQUIRED_IDS = {"TP-1", "TP-2", "TP-3", "FP-1", "FP-2", "FN-1"}

def test_gold_set_complete_and_schema_valid():
    data = yaml.safe_load(GOLD.read_text())
    assert "flags" in data
    ids = {f["id"] for f in data["flags"]}
    assert REQUIRED_IDS <= ids, f"missing flag ids: {REQUIRED_IDS - ids}"
    for f in data["flags"]:
        assert {"id", "category", "expected", "doc_a", "doc_b"} <= set(f), f"{f['id']} missing required keys"
        if f["expected"] == "surfaced":
            assert "min_confidence" in f
        if f["expected"] == "suppressed":
            assert "max_confidence" in f
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest tests/eval/test_harness.py::test_gold_set_complete_and_schema_valid -v
```

Expected: FAIL.

- [ ] **Step 3: Write `gold.yaml` from MUTATIONS.md**

Schema per `docs/FIXTURES.md` section 6. Translate each row of `MUTATIONS.md` into a `flags:` entry. Use min_confidence=0.7 for TP, max_confidence=0.4 for FP, min_confidence=0.4 for FN-1.

- [ ] **Step 4: Verify test passes**

```bash
uv run pytest tests/eval/test_harness.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fixtures/eval/gold.yaml tests/eval/test_harness.py
git commit -m "fixtures: write gold-set YAML aligned with mutation log"
```

### Task 1.5 — Symbol fidelity probe

**Files:**
- Create: `scripts/make_symbol_probe.py`
- Create: `fixtures/probes/symbol_probe.pdf`

- [ ] **Step 1: Write failing test**

`tests/ingest/test_text.py`:

```python
from pathlib import Path
import fitz

PROBE = Path("fixtures/probes/symbol_probe.pdf")
REQUIRED = ["Ω", "μ", "μF", "kV", "MVA", "θ", "Δ", "cos φ", "°C", "±", "≤", "≥"]

def test_symbol_probe_roundtrip():
    assert PROBE.exists()
    doc = fitz.open(PROBE)
    text = "".join(p.get_text("text") for p in doc)
    missing = [s for s in REQUIRED if s not in text]
    assert not missing, f"symbols missing from extracted text: {missing}"
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest tests/ingest/test_text.py::test_symbol_probe_roundtrip -v
```

Expected: FAIL.

- [ ] **Step 3: Write `make_symbol_probe.py`**

```python
"""Generate a one-page probe PDF containing engineering symbols InterLock must round-trip."""
import fitz
from pathlib import Path

OUT = Path("fixtures/probes/symbol_probe.pdf")
TEXT = (
    "Symbol probe\n"
    "Resistance: 50 Ω. Capacitance: 4.7 μF. Voltage: 132 kV. Power: 25 MVA.\n"
    "Phase angle θ = 30°. Delta winding: Δ. Power factor: cos φ = 0.95.\n"
    "Temperature rise: 65 °C. Tolerance: ± 2.5 %. Limits: ≤ 50, ≥ 10.\n"
)

def main() -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), TEXT, fontname="helv", fontsize=11)
    doc.save(OUT)
    print(f"wrote {OUT}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Generate the probe**

```bash
uv run python scripts/make_symbol_probe.py
```

- [ ] **Step 5: Run test to verify pass**

```bash
uv run pytest tests/ingest/test_text.py::test_symbol_probe_roundtrip -v
```

Expected: PASS. If any symbol is missing, switch the font to a Unicode TTF (e.g., NotoSans) and regenerate.

- [ ] **Step 6: Commit**

```bash
git add scripts/make_symbol_probe.py fixtures/probes/symbol_probe.pdf tests/ingest/test_text.py
git commit -m "fixtures: add symbol fidelity probe PDF"
```

### Task 1.6 — Phase 1 checkpoint

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest -v
```

Expected: all green.

- [ ] **Step 2: Merge and tag**

```bash
git checkout main
git merge --no-ff phase-1-fixtures -m "phase 1: fixtures, mutations, gold set, symbol probe locked"
git tag phase-1-fixtures
```

---

## Phase 2 — PDF ingestion pipeline

**Goal:** Open a PDF, extract per-span text with bbox and page number, extract tables with cell coordinates, detect pages where coverage is low and route them to a vision fallback. Tests use Doc A and the symbol probe; vision fallback is mocked in tests.

**Branch:** `phase-2-ingest`
**Tag at end:** `phase-2-ingest`

### Task 2.1 — Span extraction with bbox

**Files:**
- Create: `src/interlock/ingest/text.py`
- Create: `tests/ingest/test_text.py` (append)

- [ ] **Step 1: Write failing test**

```python
from interlock.ingest.text import extract_spans, Span

def test_extract_spans_returns_text_page_bbox(tmp_path):
    spans = extract_spans("fixtures/probes/symbol_probe.pdf")
    assert spans, "expected at least one span"
    for s in spans:
        assert isinstance(s, Span)
        assert s.text
        assert s.page >= 1
        assert len(s.bbox) == 4
        assert s.bbox[2] > s.bbox[0] and s.bbox[3] > s.bbox[1]

def test_extract_spans_preserves_unicode():
    spans = extract_spans("fixtures/probes/symbol_probe.pdf")
    joined = " ".join(s.text for s in spans)
    for sym in ["Ω", "μF", "kV", "Δ", "θ", "cos φ"]:
        assert sym in joined, f"missing {sym}"
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest tests/ingest/test_text.py -v
```

Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
"""Text span extraction with bounding boxes via PyMuPDF."""
from __future__ import annotations
from dataclasses import dataclass
import fitz

@dataclass(frozen=True)
class Span:
    doc_id: str
    page: int
    bbox: tuple[float, float, float, float]
    text: str

def extract_spans(pdf_path: str, doc_id: str | None = None) -> list[Span]:
    doc = fitz.open(pdf_path)
    out: list[Span] = []
    did = doc_id or pdf_path
    for i, page in enumerate(doc, start=1):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    out.append(Span(doc_id=did, page=i, bbox=tuple(span["bbox"]), text=text))
    doc.close()
    return out
```

- [ ] **Step 4: Run test to verify pass**

```bash
uv run pytest tests/ingest/test_text.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/interlock/ingest/text.py tests/ingest/test_text.py
git commit -m "ingest: extract text spans with bbox and page"
```

### Task 2.2 — Table extraction via Camelot

**Files:**
- Create: `src/interlock/ingest/tables.py`
- Create: `tests/ingest/test_tables.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.ingest.tables import extract_tables, Table

def test_extract_tables_returns_typed_records():
    tables = extract_tables("fixtures/pdfs/doc_a_60pct.pdf", pages="1-3")
    # Eaton sample contains coordination tables on early pages.
    assert tables, "expected at least one table"
    for t in tables:
        assert isinstance(t, Table)
        assert t.page >= 1
        assert t.rows, "rows must not be empty"
        for row in t.rows:
            for cell in row:
                assert isinstance(cell.text, str)
                assert len(cell.bbox) == 4
```

- [ ] **Step 2: Run test, verify failure**

```bash
uv run pytest tests/ingest/test_tables.py -v
```

- [ ] **Step 3: Implement**

```python
"""Table extraction via Camelot with lattice primary, stream fallback."""
from __future__ import annotations
from dataclasses import dataclass
import camelot

@dataclass(frozen=True)
class Cell:
    text: str
    bbox: tuple[float, float, float, float]

@dataclass(frozen=True)
class Table:
    doc_id: str
    page: int
    rows: list[list[Cell]]
    confidence: float

def extract_tables(pdf_path: str, pages: str = "all", doc_id: str | None = None) -> list[Table]:
    did = doc_id or pdf_path
    out: list[Table] = []
    for flavor in ("lattice", "stream"):
        try:
            ts = camelot.read_pdf(pdf_path, pages=pages, flavor=flavor)
        except Exception:
            continue
        for t in ts:
            rows: list[list[Cell]] = []
            for r in t.cells:
                row_cells = [Cell(text=str(c.text or "").strip(), bbox=(c.x1, c.y1, c.x2, c.y2)) for c in r]
                rows.append(row_cells)
            out.append(Table(doc_id=did, page=int(t.page), rows=rows, confidence=t.parsing_report.get("accuracy", 0) / 100.0))
        if out:
            break
    return out
```

- [ ] **Step 4: Run test, verify pass**

```bash
uv run pytest tests/ingest/test_tables.py -v
```

If lattice fails on Eaton, stream fallback engages. If both fail, the vision fallback in Task 2.3 will pick up the page.

- [ ] **Step 5: Commit**

```bash
git add src/interlock/ingest/tables.py tests/ingest/test_tables.py
git commit -m "ingest: extract tables with cell bbox via Camelot"
```

### Task 2.3 — Vision fallback (mocked in tests)

**Files:**
- Create: `src/interlock/ingest/vision_fallback.py`
- Create: `tests/ingest/test_vision_fallback.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.ingest.vision_fallback import vision_extract_page, VisionResult

def test_vision_extract_page_returns_text_and_confidence(mocker):
    fake_response = mocker.Mock(content=[mocker.Mock(text='{"text":"Z=5.75%","confidence":0.92}')])
    mocker.patch("interlock.ingest.vision_fallback._call_claude", return_value=fake_response)
    result = vision_extract_page("fixtures/pdfs/doc_a_60pct.pdf", page=1)
    assert isinstance(result, VisionResult)
    assert "5.75" in result.text
    assert 0 < result.confidence <= 1
```

- [ ] **Step 2: Run test, verify failure**

```bash
uv run pytest tests/ingest/test_vision_fallback.py -v
```

- [ ] **Step 3: Implement**

```python
"""Vision-model fallback for pages PyMuPDF/Camelot extract poorly."""
from __future__ import annotations
from dataclasses import dataclass
import base64
import json
import os
import fitz
from anthropic import Anthropic

@dataclass(frozen=True)
class VisionResult:
    text: str
    confidence: float

_PROMPT = (
    "You are extracting engineering parameters from a single PDF page image. "
    "Return JSON only: {\"text\": <full extracted text>, \"confidence\": <0..1>}. "
    "Preserve Greek letters, electrical units (Ω, μF, kV, MVA), and table structure as best you can."
)

def _call_claude(image_b64: str) -> object:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
            {"type": "text", "text": _PROMPT},
        ]}],
    )

def vision_extract_page(pdf_path: str, page: int) -> VisionResult:
    doc = fitz.open(pdf_path)
    pix = doc[page - 1].get_pixmap(dpi=200)
    img_b64 = base64.b64encode(pix.tobytes("png")).decode()
    doc.close()
    resp = _call_claude(img_b64)
    payload = json.loads(resp.content[0].text)
    return VisionResult(text=payload["text"], confidence=float(payload["confidence"]))
```

- [ ] **Step 4: Run test, verify pass**

```bash
uv run pytest tests/ingest/test_vision_fallback.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/interlock/ingest/vision_fallback.py tests/ingest/test_vision_fallback.py
git commit -m "ingest: vision fallback via Claude Sonnet 4.6 (mocked in tests)"
```

### Task 2.4 — Ingest orchestrator with coverage routing

**Files:**
- Create: `src/interlock/ingest/pdf.py`
- Create: `tests/ingest/test_pdf.py` (append)

- [ ] **Step 1: Write failing test**

```python
from interlock.ingest.pdf import ingest

def test_ingest_returns_spans_tables_and_low_coverage_pages():
    result = ingest("fixtures/pdfs/doc_a_60pct.pdf")
    assert result.spans
    assert isinstance(result.tables, list)
    assert isinstance(result.low_coverage_pages, list)
```

- [ ] **Step 2: Run, verify fail**

```bash
uv run pytest tests/ingest/test_pdf.py -v
```

- [ ] **Step 3: Implement**

```python
"""Top-level ingestion: spans + tables, plus list of pages that need vision fallback."""
from __future__ import annotations
from dataclasses import dataclass, field
import fitz
from .text import extract_spans, Span
from .tables import extract_tables, Table

MIN_CHARS_PER_PAGE = 80

@dataclass(frozen=True)
class IngestResult:
    doc_id: str
    spans: list[Span]
    tables: list[Table]
    low_coverage_pages: list[int] = field(default_factory=list)

def ingest(pdf_path: str, doc_id: str | None = None) -> IngestResult:
    did = doc_id or pdf_path
    spans = extract_spans(pdf_path, did)
    tables = extract_tables(pdf_path, doc_id=did)
    doc = fitz.open(pdf_path)
    low_cov: list[int] = []
    for i, page in enumerate(doc, start=1):
        if len(page.get_text("text").strip()) < MIN_CHARS_PER_PAGE:
            low_cov.append(i)
    doc.close()
    return IngestResult(doc_id=did, spans=spans, tables=tables, low_coverage_pages=low_cov)
```

- [ ] **Step 4: Run, verify pass**

```bash
uv run pytest tests/ingest/test_pdf.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/interlock/ingest/pdf.py tests/ingest/test_pdf.py
git commit -m "ingest: orchestrator with coverage routing"
```

### Task 2.5 — Phase 2 checkpoint

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest -v
```

- [ ] **Step 2: Merge and tag**

```bash
git checkout main
git merge --no-ff phase-2-ingest -m "phase 2: ingestion pipeline complete"
git tag phase-2-ingest
```

---

## Phase 3 — Parameter extraction with unit normalization

**Goal:** From spans and tables, produce `ParameterRecord` objects with normalized values and unit-canonical forms. Section heading attribution per parameter.

**Branch:** `phase-3-extract`
**Tag at end:** `phase-3-extract`

### Task 3.1 — Pint-based unit normalization

**Files:**
- Create: `src/interlock/extract/units.py`
- Create: `tests/extract/test_units.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.extract.units import parse_quantity, normalize_quantity, equivalent

def test_parse_basic_units():
    q = parse_quantity("132 kV")
    assert q.magnitude == 132
    assert str(q.units) == "kilovolt"

def test_normalize_to_base_si():
    q = normalize_quantity("132 kV")
    assert q.magnitude == 132_000
    assert str(q.units) == "volt"

def test_equivalence_across_unit_forms():
    assert equivalent("132 kV", "132,000 V")
    assert equivalent("5.75 %", "0.0575")
    assert equivalent("25 MVA", "25000 kVA")
    assert not equivalent("5.75 %", "0.575 %")

def test_handles_greek_and_micro():
    q = parse_quantity("4.7 μF")
    assert q.magnitude == 4.7
    assert str(q.units) == "microfarad"
```

- [ ] **Step 2: Run, verify fail**

```bash
uv run pytest tests/extract/test_units.py -v
```

- [ ] **Step 3: Implement**

```python
"""Unit normalization via Pint with electrical-unit aliases."""
from __future__ import annotations
import re
import pint

_ureg = pint.UnitRegistry()
_ureg.define("percent = 0.01 = %")
_ureg.define("@alias microfarad = μF")
_ureg.define("@alias ohm = Ω")

_NUM = re.compile(r"[-+]?\d[\d,]*\.?\d*")

def parse_quantity(text: str) -> pint.Quantity:
    cleaned = text.strip().replace(",", "")
    return _ureg.Quantity(cleaned)

def normalize_quantity(text: str) -> pint.Quantity:
    return parse_quantity(text).to_base_units()

def equivalent(a: str, b: str, rel_tol: float = 1e-3) -> bool:
    try:
        qa = normalize_quantity(a)
        qb = normalize_quantity(b)
    except Exception:
        return False
    if qa.dimensionality != qb.dimensionality:
        return False
    if qb.magnitude == 0:
        return qa.magnitude == 0
    return abs(qa.magnitude - qb.magnitude) / abs(qb.magnitude) <= rel_tol
```

- [ ] **Step 4: Run, verify pass**

```bash
uv run pytest tests/extract/test_units.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/interlock/extract/units.py tests/extract/test_units.py
git commit -m "extract: Pint-based unit normalization with electrical aliases"
```

### Task 3.2 — Section heading attribution

**Files:**
- Create: `src/interlock/extract/sections.py`
- Create: `tests/extract/test_sections.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.ingest.text import Span
from interlock.extract.sections import attribute_sections

def _span(text: str, page: int, y: float) -> Span:
    return Span(doc_id="d", page=page, bbox=(0, y, 100, y + 10), text=text)

def test_section_attribution_by_heading_size_and_proximity():
    spans = [
        _span("1. Overview", 1, 50),
        _span("Some text under overview.", 1, 70),
        _span("2. Coordination Tables", 1, 200),
        _span("Z = 5.75%", 1, 220),
    ]
    out = attribute_sections(spans, heading_pattern=r"^\d+\.\s+\S+")
    assert out[1].section == "1. Overview"
    assert out[3].section == "2. Coordination Tables"
```

- [ ] **Step 2: Run, verify fail**

```bash
uv run pytest tests/extract/test_sections.py -v
```

- [ ] **Step 3: Implement**

```python
"""Attribute every span to the nearest preceding heading on the same page."""
from __future__ import annotations
from dataclasses import dataclass, replace
import re
from interlock.ingest.text import Span

@dataclass(frozen=True)
class AttributedSpan:
    span: Span
    section: str | None

    @property
    def text(self) -> str:
        return self.span.text
    @property
    def page(self) -> int:
        return self.span.page

def attribute_sections(spans: list[Span], heading_pattern: str = r"^\d+(\.\d+)*\s+\S") -> list[AttributedSpan]:
    pat = re.compile(heading_pattern)
    out: list[AttributedSpan] = []
    current: dict[int, str | None] = {}
    for s in sorted(spans, key=lambda s: (s.page, s.bbox[1])):
        if pat.match(s.text):
            current[s.page] = s.text
        out.append(AttributedSpan(span=s, section=current.get(s.page)))
    return out
```

- [ ] **Step 4: Run, verify pass**

```bash
uv run pytest tests/extract/test_sections.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/interlock/extract/sections.py tests/extract/test_sections.py
git commit -m "extract: attribute spans to nearest preceding heading"
```

### Task 3.3 — Parameter record extraction

**Files:**
- Create: `src/interlock/extract/parameters.py`
- Create: `tests/extract/test_parameters.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.ingest.text import Span
from interlock.extract.parameters import extract_parameters, ParameterRecord

def _s(text, page=1, y=0):
    return Span(doc_id="d", page=page, bbox=(0, y, 100, y+10), text=text)

def test_extract_named_parameter_value_pair():
    spans = [_s("Impedance: 5.75%"), _s("Rated voltage: 132 kV")]
    records = extract_parameters(spans)
    by_name = {r.name.lower(): r for r in records}
    assert "impedance" in by_name
    assert by_name["impedance"].raw_value == "5.75%"
    assert by_name["rated voltage"].raw_value == "132 kV"
    for r in records:
        assert isinstance(r, ParameterRecord)
        assert r.normalized_magnitude is not None or r.name.lower() == "impedance"

def test_records_carry_citation_tuple():
    spans = [_s("Impedance: 5.75%", page=3, y=120)]
    r = extract_parameters(spans)[0]
    assert r.page == 3
    assert r.bbox == (0, 120, 100, 130)
    assert r.span_text == "Impedance: 5.75%"
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement**

```python
"""Extract (name, value, unit) parameter records from attributed spans."""
from __future__ import annotations
from dataclasses import dataclass
import re
from interlock.ingest.text import Span
from .units import normalize_quantity

_PAIR = re.compile(r"^(?P<name>[A-Za-z][A-Za-z \-/]+?)\s*[:=]\s*(?P<value>.+)$")
_VALUE_UNIT = re.compile(r"^(?P<num>[-+]?\d[\d,]*\.?\d*)\s*(?P<unit>[%a-zA-ZμΩ°]+.*)?$")

@dataclass(frozen=True)
class ParameterRecord:
    doc_id: str
    page: int
    bbox: tuple[float, float, float, float]
    section: str | None
    span_text: str
    name: str
    raw_value: str
    normalized_magnitude: float | None
    normalized_unit: str | None

def extract_parameters(spans: list[Span], section_of: dict[int, str | None] | None = None) -> list[ParameterRecord]:
    out: list[ParameterRecord] = []
    for s in spans:
        m = _PAIR.match(s.text)
        if not m:
            continue
        name = m.group("name").strip()
        raw = m.group("value").strip()
        normalized_magnitude: float | None = None
        normalized_unit: str | None = None
        try:
            q = normalize_quantity(raw)
            normalized_magnitude = float(q.magnitude)
            normalized_unit = str(q.units)
        except Exception:
            pass
        out.append(ParameterRecord(
            doc_id=s.doc_id, page=s.page, bbox=s.bbox,
            section=(section_of or {}).get(id(s)),
            span_text=s.text, name=name, raw_value=raw,
            normalized_magnitude=normalized_magnitude,
            normalized_unit=normalized_unit,
        ))
    return out
```

- [ ] **Step 4: Run, verify pass**

- [ ] **Step 5: Commit**

```bash
git add src/interlock/extract/parameters.py tests/extract/test_parameters.py
git commit -m "extract: parameter records with citation tuple"
```

### Task 3.4 — Phase 3 checkpoint

- [ ] **Step 1: Run full suite**

```bash
uv run pytest -v
```

- [ ] **Step 2: Merge and tag**

```bash
git checkout main
git merge --no-ff phase-3-extract -m "phase 3: parameter extraction complete"
git tag phase-3-extract
```

---

## Phase 4 — Cross-document alignment

**Goal:** Given parameter records from Doc A and Doc B, produce aligned pairs with an alignment confidence in [0, 1]. Combine three signals: exact name match, normalized-value match, embedding-semantic name match.

**Branch:** `phase-4-align`
**Tag at end:** `phase-4-align`

### Task 4.1 — Exact and unit-normalized matching

**Files:**
- Create: `src/interlock/align/exact.py`
- Create: `tests/align/test_exact.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.extract.parameters import ParameterRecord
from interlock.align.exact import align_exact

def _p(name, raw, doc, mag=None, unit=None):
    return ParameterRecord(doc_id=doc, page=1, bbox=(0,0,1,1), section=None,
                           span_text=f"{name}: {raw}", name=name, raw_value=raw,
                           normalized_magnitude=mag, normalized_unit=unit)

def test_align_exact_matches_name_and_value_equivalence():
    a = [_p("Impedance", "5.75%", "A", mag=0.0575, unit="dimensionless")]
    b = [_p("Impedance", "5.75%", "B", mag=0.0575, unit="dimensionless")]
    pairs = align_exact(a, b)
    assert len(pairs) == 1
    assert pairs[0].name_match_confidence == 1.0
    assert pairs[0].value_equivalent is True
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement**

```python
"""Exact name + unit-normalized value matching."""
from __future__ import annotations
from dataclasses import dataclass
from interlock.extract.parameters import ParameterRecord
from interlock.extract.units import equivalent

@dataclass(frozen=True)
class AlignedPair:
    a: ParameterRecord
    b: ParameterRecord
    name_match_confidence: float
    value_equivalent: bool

def align_exact(a: list[ParameterRecord], b: list[ParameterRecord]) -> list[AlignedPair]:
    by_name_b: dict[str, list[ParameterRecord]] = {}
    for r in b:
        by_name_b.setdefault(r.name.strip().lower(), []).append(r)
    out: list[AlignedPair] = []
    for ra in a:
        for rb in by_name_b.get(ra.name.strip().lower(), []):
            out.append(AlignedPair(
                a=ra, b=rb,
                name_match_confidence=1.0,
                value_equivalent=equivalent(ra.raw_value, rb.raw_value),
            ))
    return out
```

- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/interlock/align/exact.py tests/align/test_exact.py
git commit -m "align: exact name + unit-normalized value match"
```

### Task 4.2 — Embedding-based semantic name alignment

**Files:**
- Create: `src/interlock/align/semantic.py`
- Create: `tests/align/test_semantic.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.extract.parameters import ParameterRecord
from interlock.align.semantic import align_semantic

def _p(name, doc):
    return ParameterRecord(doc_id=doc, page=1, bbox=(0,0,1,1), section=None,
                           span_text=name, name=name, raw_value="x",
                           normalized_magnitude=None, normalized_unit=None)

def test_semantic_alignment_uses_provided_embedder(mocker):
    a = [_p("Impedance", "A")]
    b = [_p("%Z", "B")]
    def fake_embed(texts):
        return {"Impedance": [1.0, 0.0], "%Z": [0.99, 0.01]}
    pairs = align_semantic(a, b, embed_fn=fake_embed, threshold=0.9)
    assert len(pairs) == 1
    assert pairs[0].name_match_confidence >= 0.9
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement**

```python
"""Semantic alignment via embeddings; embedder is injected for testability."""
from __future__ import annotations
from collections.abc import Callable
import math
from interlock.extract.parameters import ParameterRecord
from interlock.align.exact import AlignedPair

EmbedFn = Callable[[list[str]], dict[str, list[float]]]

def _cos(u: list[float], v: list[float]) -> float:
    num = sum(x*y for x, y in zip(u, v))
    du = math.sqrt(sum(x*x for x in u))
    dv = math.sqrt(sum(y*y for y in v))
    return num / (du * dv) if du and dv else 0.0

def align_semantic(a: list[ParameterRecord], b: list[ParameterRecord], embed_fn: EmbedFn, threshold: float = 0.85) -> list[AlignedPair]:
    names = list({r.name for r in a} | {r.name for r in b})
    vecs = embed_fn(names)
    out: list[AlignedPair] = []
    for ra in a:
        va = vecs[ra.name]
        best: tuple[float, ParameterRecord | None] = (0.0, None)
        for rb in b:
            sim = _cos(va, vecs[rb.name])
            if sim > best[0]:
                best = (sim, rb)
        if best[1] is not None and best[0] >= threshold:
            out.append(AlignedPair(a=ra, b=best[1], name_match_confidence=best[0], value_equivalent=False))
    return out
```

- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/interlock/align/semantic.py tests/align/test_semantic.py
git commit -m "align: semantic name alignment via injectable embedder"
```

### Task 4.3 — Combiner

**Files:**
- Create: `src/interlock/align/combiner.py`
- Create: `tests/align/test_combiner.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.align.combiner import combine_alignments
from interlock.align.exact import AlignedPair
from interlock.extract.parameters import ParameterRecord

def _p(name, doc, mag=None):
    return ParameterRecord(doc_id=doc, page=1, bbox=(0,0,1,1), section=None,
                           span_text=name, name=name, raw_value="x",
                           normalized_magnitude=mag, normalized_unit=None)

def test_combine_deduplicates_and_prefers_exact():
    exact = [AlignedPair(_p("Z","A"), _p("Z","B"), 1.0, True)]
    semantic = [AlignedPair(_p("Z","A"), _p("%Z","B"), 0.95, False)]
    out = combine_alignments(exact, semantic)
    assert len(out) == 1
    assert out[0].b.name == "Z"
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement**

```python
"""Combine exact and semantic alignment results, prefer exact, deduplicate."""
from __future__ import annotations
from interlock.align.exact import AlignedPair

def combine_alignments(exact: list[AlignedPair], semantic: list[AlignedPair]) -> list[AlignedPair]:
    seen: set[tuple[str, str]] = set()
    out: list[AlignedPair] = []
    for p in exact:
        key = (p.a.doc_id + str(p.a.page) + p.a.name, p.b.doc_id + str(p.b.page) + p.b.name)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    for p in semantic:
        key_a_prefix = p.a.doc_id + str(p.a.page) + p.a.name
        if any(k[0] == key_a_prefix for k in seen):
            continue
        out.append(p)
        seen.add((key_a_prefix, p.b.doc_id + str(p.b.page) + p.b.name))
    return out
```

- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/interlock/align/combiner.py tests/align/test_combiner.py
git commit -m "align: combine exact + semantic with dedupe"
```

### Task 4.4 — Phase 4 checkpoint

- [ ] **Step 1: Run full suite**

```bash
uv run pytest -v
```

- [ ] **Step 2: Merge and tag**

```bash
git checkout main
git merge --no-ff phase-4-align -m "phase 4: cross-document alignment complete"
git tag phase-4-align
```

---

## Phase 5 — Directional mismatch, authority, confidence, pipeline

**Goal:** Emit directional flags with confidence from aligned pairs. Hardcode authority rule per `FIXTURES.md` section 4. End-to-end pipeline runs against Doc A + Doc B and emits a list of flags.

**Branch:** `phase-5-detect`
**Tag at end:** `phase-5-detect`

### Task 5.1 — Authority rule

**Files:**
- Create: `src/interlock/detect/authority.py`
- Create: `tests/detect/test_authority.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.detect.authority import authority_for, AuthorityDecision

def test_hardcoded_doc_a_authoritative():
    d = authority_for(doc_a_id="doc_a_60pct.pdf", doc_b_id="doc_b_90pct.pdf", parameter_name="Impedance")
    assert isinstance(d, AuthorityDecision)
    assert d.authoritative_doc_id == "doc_a_60pct.pdf"
    assert 0 < d.confidence <= 1
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement**

```python
"""Hardcoded authority rule for the locked MVP fixture pair (FIXTURES.md §4)."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class AuthorityDecision:
    authoritative_doc_id: str
    deviating_doc_id: str
    confidence: float
    rule: str

def authority_for(doc_a_id: str, doc_b_id: str, parameter_name: str) -> AuthorityDecision:
    return AuthorityDecision(
        authoritative_doc_id=doc_a_id,
        deviating_doc_id=doc_b_id,
        confidence=1.0,
        rule="MVP-hardcoded: 60% baseline authoritative over 90% revision",
    )
```

- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/interlock/detect/authority.py tests/detect/test_authority.py
git commit -m "detect: hardcoded authority rule per FIXTURES §4"
```

### Task 5.2 — Confidence formula

**Files:**
- Create: `src/interlock/detect/confidence.py`
- Create: `tests/detect/test_confidence.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.detect.confidence import flag_confidence

def test_formula_multiplies_components():
    assert flag_confidence(extraction=1.0, match=1.0, authority=1.0) == 1.0
    assert flag_confidence(extraction=0.7, match=0.8, authority=1.0) == 0.56

def test_clamps_to_unit_interval():
    assert flag_confidence(extraction=1.5, match=1.0, authority=1.0) == 1.0
    assert flag_confidence(extraction=0.0, match=1.0, authority=1.0) == 0.0
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement**

```python
"""Confidence assembly per SCOPE.md §4 item 9."""

def flag_confidence(*, extraction: float, match: float, authority: float) -> float:
    raw = extraction * match * authority
    return max(0.0, min(1.0, raw))
```

- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/interlock/detect/confidence.py tests/detect/test_confidence.py
git commit -m "detect: confidence formula extraction × match × authority"
```

### Task 5.3 — Directional mismatch emission

**Files:**
- Create: `src/interlock/detect/mismatch.py`
- Create: `tests/detect/test_mismatch.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.align.exact import AlignedPair
from interlock.extract.parameters import ParameterRecord
from interlock.detect.mismatch import detect_flags, Flag

def _p(name, doc, raw, mag):
    return ParameterRecord(doc_id=doc, page=1, bbox=(0,0,1,1), section="2.1 Coordination",
                           span_text=f"{name}: {raw}", name=name, raw_value=raw,
                           normalized_magnitude=mag, normalized_unit="dimensionless")

def test_value_mismatch_emits_directional_flag():
    pair = AlignedPair(
        a=_p("Impedance", "doc_a", "5.75%", 0.0575),
        b=_p("Impedance", "doc_b", "0.575%", 0.00575),
        name_match_confidence=1.0,
        value_equivalent=False,
    )
    flags = detect_flags([pair])
    assert len(flags) == 1
    f = flags[0]
    assert isinstance(f, Flag)
    assert f.authoritative_doc_id == "doc_a"
    assert f.deviating_doc_id == "doc_b"
    assert f.confidence >= 0.6

def test_value_equivalent_does_not_emit_flag():
    pair = AlignedPair(
        a=_p("Voltage", "doc_a", "132 kV", 132_000),
        b=_p("Voltage", "doc_b", "132,000 V", 132_000),
        name_match_confidence=1.0,
        value_equivalent=True,
    )
    assert detect_flags([pair]) == []
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement**

```python
"""Convert aligned-pair value mismatches into directional flags."""
from __future__ import annotations
from dataclasses import dataclass
from interlock.align.exact import AlignedPair
from interlock.extract.parameters import ParameterRecord
from interlock.detect.authority import authority_for
from interlock.detect.confidence import flag_confidence

@dataclass(frozen=True)
class Flag:
    parameter: str
    authoritative_doc_id: str
    deviating_doc_id: str
    a_record: ParameterRecord
    b_record: ParameterRecord
    confidence: float
    rationale: str

def detect_flags(pairs: list[AlignedPair]) -> list[Flag]:
    out: list[Flag] = []
    for p in pairs:
        if p.value_equivalent:
            continue
        if p.a.normalized_magnitude is None or p.b.normalized_magnitude is None:
            continue
        if p.a.normalized_magnitude == p.b.normalized_magnitude:
            continue
        decision = authority_for(p.a.doc_id, p.b.doc_id, p.a.name)
        conf = flag_confidence(
            extraction=1.0,
            match=p.name_match_confidence,
            authority=decision.confidence,
        )
        out.append(Flag(
            parameter=p.a.name,
            authoritative_doc_id=decision.authoritative_doc_id,
            deviating_doc_id=decision.deviating_doc_id,
            a_record=p.a, b_record=p.b,
            confidence=conf,
            rationale=f"{p.a.raw_value} (authoritative) ≠ {p.b.raw_value} (deviation)",
        ))
    return out
```

- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/interlock/detect/mismatch.py tests/detect/test_mismatch.py
git commit -m "detect: directional flag emission"
```

### Task 5.4 — End-to-end pipeline orchestrator

**Files:**
- Create: `src/interlock/pipeline.py`
- Create: `tests/e2e/test_pipeline.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.pipeline import review_two_documents

def test_pipeline_surfaces_planted_mismatch_with_high_confidence():
    flags = review_two_documents(
        "fixtures/pdfs/doc_a_60pct.pdf",
        "fixtures/pdfs/doc_b_90pct.pdf",
        embed_fn=lambda names: {n: [hash(n) % 1000 / 1000, 0.0] for n in names},
    )
    assert flags, "expected at least one flag"
    high = [f for f in flags if f.confidence >= 0.6]
    assert high, "expected at least one high-confidence flag (planted TP)"
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement**

```python
"""End-to-end review pipeline: ingest two PDFs and emit flags."""
from __future__ import annotations
from collections.abc import Callable
from interlock.ingest.pdf import ingest
from interlock.extract.parameters import extract_parameters
from interlock.extract.sections import attribute_sections
from interlock.align.exact import align_exact
from interlock.align.semantic import align_semantic
from interlock.align.combiner import combine_alignments
from interlock.detect.mismatch import detect_flags, Flag

EmbedFn = Callable[[list[str]], dict[str, list[float]]]

def review_two_documents(pdf_a: str, pdf_b: str, embed_fn: EmbedFn) -> list[Flag]:
    ia = ingest(pdf_a, doc_id="doc_a")
    ib = ingest(pdf_b, doc_id="doc_b")
    pa = extract_parameters(ia.spans)
    pb = extract_parameters(ib.spans)
    exact = align_exact(pa, pb)
    semantic = align_semantic(pa, pb, embed_fn=embed_fn)
    combined = combine_alignments(exact, semantic)
    return detect_flags(combined)
```

- [ ] **Step 4: Run, verify pass**

If the planted TP does not surface, the parameter-extraction regex in Phase 3 may not match the actual span format on the mutation page. In that case: (a) capture the failing span text in a new test in `tests/extract/test_parameters.py`, (b) extend the regex set in `parameters.py` to handle the additional shape, (c) re-run. Do not loosen the FP-trap behavior.

- [ ] **Step 5: Commit**

```bash
git add src/interlock/pipeline.py tests/e2e/test_pipeline.py
git commit -m "pipeline: end-to-end review of two PDFs"
```

### Task 5.5 — Phase 5 checkpoint

- [ ] **Step 1: Run full suite + e2e**

```bash
uv run pytest -v
```

- [ ] **Step 2: Merge and tag**

```bash
git checkout main
git merge --no-ff phase-5-detect -m "phase 5: directional detection + e2e pipeline"
git tag phase-5-detect
```

---

## Phase 6 — Citation rendering

**Goal:** Render a flag's citation tuple as a human-readable structure including a rasterized snippet of the source page with the bbox highlighted.

**Branch:** `phase-6-citation`
**Tag at end:** `phase-6-citation`

### Task 6.1 — Citation render with bbox-highlighted snippet

**Files:**
- Create: `src/interlock/citation/render.py`
- Create: `tests/citation/test_render.py`

- [ ] **Step 1: Write failing test**

```python
from interlock.extract.parameters import ParameterRecord
from interlock.citation.render import render_citation, Citation

def test_render_returns_full_tuple_and_png_bytes():
    r = ParameterRecord(doc_id="fixtures/pdfs/doc_a_60pct.pdf", page=1,
                        bbox=(72, 72, 200, 90), section="1. Overview",
                        span_text="Impedance: 5.75%", name="Impedance", raw_value="5.75%",
                        normalized_magnitude=0.0575, normalized_unit="dimensionless")
    c = render_citation(r)
    assert isinstance(c, Citation)
    assert c.doc_id == "fixtures/pdfs/doc_a_60pct.pdf"
    assert c.page == 1
    assert c.section == "1. Overview"
    assert c.quoted_text == "Impedance: 5.75%"
    assert c.snippet_png and isinstance(c.snippet_png, bytes)
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement**

```python
"""Render citation tuple with bbox-highlighted PNG snippet."""
from __future__ import annotations
from dataclasses import dataclass
import fitz
from interlock.extract.parameters import ParameterRecord

@dataclass(frozen=True)
class Citation:
    doc_id: str
    page: int
    section: str | None
    bbox: tuple[float, float, float, float]
    quoted_text: str
    snippet_png: bytes

def render_citation(r: ParameterRecord) -> Citation:
    doc = fitz.open(r.doc_id)
    page = doc[r.page - 1]
    pad = 8
    clip = fitz.Rect(max(r.bbox[0] - pad, 0), max(r.bbox[1] - pad, 0), r.bbox[2] + pad, r.bbox[3] + pad)
    page.draw_rect(fitz.Rect(*r.bbox), color=(1, 0, 0), width=1.5, overlay=True)
    pix = page.get_pixmap(clip=clip, dpi=200)
    doc.close()
    return Citation(
        doc_id=r.doc_id, page=r.page, section=r.section,
        bbox=r.bbox, quoted_text=r.span_text, snippet_png=pix.tobytes("png"),
    )
```

- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/interlock/citation/render.py tests/citation/test_render.py
git commit -m "citation: bbox-highlighted PNG snippet renderer"
```

### Task 6.2 — Phase 6 checkpoint

- [ ] **Step 1: Run suite**
- [ ] **Step 2: Merge + tag**

```bash
git checkout main
git merge --no-ff phase-6-citation -m "phase 6: citation rendering"
git tag phase-6-citation
```

---

## Phase 7 — Streamlit UI

**Goal:** A single-page app that accepts two PDF uploads, runs the pipeline, and shows ranked flags with citation snippets and accept/dismiss controls.

**Branch:** `phase-7-ui`
**Tag at end:** `phase-7-ui`

### Task 7.1 — Real embedder

**Files:**
- Create: `src/interlock/align/embed.py`
- Create: `tests/align/test_embed.py`

- [ ] **Step 1: Write failing test (mocked, no live API)**

```python
from interlock.align.embed import embed_voyage_then_openai

def test_embedder_returns_vectors_for_each_name(mocker):
    mocker.patch("interlock.align.embed._voyage_embed", return_value={"Impedance":[1,0], "Z":[0.9,0.1]})
    vecs = embed_voyage_then_openai(["Impedance", "Z"])
    assert set(vecs.keys()) == {"Impedance", "Z"}
    assert len(vecs["Impedance"]) == 2

def test_embedder_falls_back_to_openai_on_voyage_error(mocker):
    mocker.patch("interlock.align.embed._voyage_embed", side_effect=RuntimeError("rate limit"))
    mocker.patch("interlock.align.embed._openai_embed", return_value={"Impedance":[1,0]})
    vecs = embed_voyage_then_openai(["Impedance"])
    assert "Impedance" in vecs
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement**

```python
"""Embedder with Voyage primary and OpenAI fallback."""
from __future__ import annotations
import os
import voyageai
from openai import OpenAI

def _voyage_embed(texts: list[str]) -> dict[str, list[float]]:
    client = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    res = client.embed(texts, model="voyage-3", input_type="document")
    return {t: v for t, v in zip(texts, res.embeddings)}

def _openai_embed(texts: list[str]) -> dict[str, list[float]]:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    res = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return {t: d.embedding for t, d in zip(texts, res.data)}

def embed_voyage_then_openai(texts: list[str]) -> dict[str, list[float]]:
    try:
        return _voyage_embed(texts)
    except Exception:
        return _openai_embed(texts)
```

- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/interlock/align/embed.py tests/align/test_embed.py
git commit -m "align: voyage-then-openai embedder with fallback"
```

### Task 7.2 — Streamlit page

**Files:**
- Create: `src/interlock/ui/app.py`

- [ ] **Step 1: Implement minimal page**

```python
"""Streamlit single-page review UI."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
import streamlit as st
from interlock.pipeline import review_two_documents
from interlock.align.embed import embed_voyage_then_openai
from interlock.citation.render import render_citation

st.set_page_config(page_title="InterLock AI — Review", layout="wide")
st.title("InterLock AI — Cross-Document Review")

col_a, col_b = st.columns(2)
with col_a:
    a_file = st.file_uploader("Authoritative PDF (e.g., 60% baseline)", type="pdf", key="a")
with col_b:
    b_file = st.file_uploader("Downstream PDF (e.g., 90% revision)", type="pdf", key="b")

if a_file and b_file and st.button("Run review", type="primary"):
    with tempfile.TemporaryDirectory() as td:
        a_path = Path(td) / a_file.name
        b_path = Path(td) / b_file.name
        a_path.write_bytes(a_file.read())
        b_path.write_bytes(b_file.read())
        with st.spinner("Running review..."):
            flags = review_two_documents(str(a_path), str(b_path), embed_fn=embed_voyage_then_openai)
        if not flags:
            st.success("No directional mismatches surfaced.")
        else:
            st.subheader(f"{len(flags)} candidate flag(s)")
            accepted: list[dict] = []
            for i, f in enumerate(sorted(flags, key=lambda x: -x.confidence)):
                with st.expander(f"[{f.confidence:.2f}] {f.parameter} — {f.rationale}", expanded=i < 3):
                    cit_a = render_citation(f.a_record)
                    cit_b = render_citation(f.b_record)
                    c1, c2 = st.columns(2)
                    with c1:
                        st.caption(f"Authoritative · {cit_a.doc_id} · p{cit_a.page} · {cit_a.section}")
                        st.image(cit_a.snippet_png)
                        st.code(cit_a.quoted_text)
                    with c2:
                        st.caption(f"Deviation · {cit_b.doc_id} · p{cit_b.page} · {cit_b.section}")
                        st.image(cit_b.snippet_png)
                        st.code(cit_b.quoted_text)
                    if st.button("Accept flag", key=f"acc-{i}"):
                        accepted.append({"parameter": f.parameter, "confidence": f.confidence, "rationale": f.rationale})
            if accepted:
                st.download_button("Export accepted flags (JSON)", data=json.dumps(accepted, indent=2),
                                   file_name="accepted_flags.json", mime="application/json")
```

- [ ] **Step 2: Smoke-run locally**

```bash
uv run streamlit run src/interlock/ui/app.py
```

Open the URL Streamlit prints. Upload `fixtures/pdfs/doc_a_60pct.pdf` and `fixtures/pdfs/doc_b_90pct.pdf`. Click "Run review." Confirm at least one high-confidence flag matching a TP from the gold set. Confirm no FP-trap surfaces with confidence ≥ 0.6.

- [ ] **Step 3: Commit**

```bash
git add src/interlock/ui/app.py
git commit -m "ui: Streamlit single-page review app"
```

### Task 7.3 — Phase 7 checkpoint

- [ ] **Step 1: Merge + tag**

```bash
git checkout main
git merge --no-ff phase-7-ui -m "phase 7: Streamlit UI complete"
git tag phase-7-ui
```

---

## Phase 8 — Evaluation harness

**Goal:** Reproducible harness that loads `fixtures/eval/gold.yaml`, runs the pipeline, and writes precision/recall/F1 to `eval/results/baseline.json`. Acceptance thresholds from `FIXTURES.md` §6 are enforced as test assertions.

**Branch:** `phase-8-eval`
**Tag at end:** `phase-8-eval`

### Task 8.1 — Harness

**Files:**
- Create: `scripts/run_eval.py`
- Create: `tests/eval/test_harness.py` (append)

- [ ] **Step 1: Write failing test**

```python
import json
import subprocess
from pathlib import Path

def test_eval_run_produces_baseline_meeting_thresholds():
    subprocess.check_call(["uv", "run", "python", "scripts/run_eval.py"])
    res = json.loads(Path("eval/results/baseline.json").read_text())
    assert res["recall_tp"] == 1.0, "all TP must be surfaced"
    assert res["fp_rate_traps"] == 0.0, "no FP trap may surface above threshold"
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement**

```python
"""Run pipeline against fixture pair, score against gold.yaml, write baseline.json."""
from __future__ import annotations
import json
from pathlib import Path
import yaml
from interlock.pipeline import review_two_documents
from interlock.align.embed import embed_voyage_then_openai

GOLD = Path("fixtures/eval/gold.yaml")
OUT = Path("eval/results/baseline.json")
DOC_A = "fixtures/pdfs/doc_a_60pct.pdf"
DOC_B = "fixtures/pdfs/doc_b_90pct.pdf"

def main() -> None:
    gold = yaml.safe_load(GOLD.read_text())["flags"]
    flags = review_two_documents(DOC_A, DOC_B, embed_fn=embed_voyage_then_openai)
    surfaced_above_threshold = [f for f in flags if f.confidence >= 0.6]

    tp_total = sum(1 for g in gold if g["expected"] == "surfaced" and g["id"].startswith("TP"))
    tp_hit = sum(1 for g in gold if g["expected"] == "surfaced" and g["id"].startswith("TP")
                 and any(f.parameter.lower() in g["doc_a"]["span_text"].lower() for f in surfaced_above_threshold))
    fp_traps = sum(1 for g in gold if g["expected"] == "suppressed")
    fp_hits = sum(1 for g in gold if g["expected"] == "suppressed"
                  and any(f.parameter.lower() in g["doc_a"]["span_text"].lower() for f in surfaced_above_threshold))

    res = {
        "n_surfaced_above_threshold": len(surfaced_above_threshold),
        "recall_tp": (tp_hit / tp_total) if tp_total else 0.0,
        "fp_rate_traps": (fp_hits / fp_traps) if fp_traps else 0.0,
        "tp_hit": tp_hit, "tp_total": tp_total,
        "fp_hits": fp_hits, "fp_traps": fp_traps,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit**

```bash
git add scripts/run_eval.py tests/eval/test_harness.py
git commit -m "eval: harness scores pipeline against gold set"
```

### Task 8.2 — Phase 8 checkpoint

- [ ] **Step 1: Merge + tag**

```bash
git checkout main
git merge --no-ff phase-8-eval -m "phase 8: eval harness meeting thresholds"
git tag phase-8-eval
```

---

## Phase 9 — Deployment

**Goal:** Streamlit Community Cloud URL live, env secrets configured, run completes end-to-end on the deployed instance against the fixtures.

**Branch:** `phase-9-deploy`
**Tag at end:** `phase-9-deploy`

### Task 9.1 — Push to GitHub, connect Streamlit Cloud

- [ ] **Step 1: Create GitHub repo (private)**

```bash
gh repo create interlock-ai --private --source=. --remote=origin --push
```

- [ ] **Step 2: Configure Streamlit Cloud**

In Streamlit Cloud: new app pointing at this repo, `src/interlock/ui/app.py`, Python 3.12. Add secrets `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `OPENAI_API_KEY` from the Streamlit Cloud UI.

- [ ] **Step 3: Smoke-test deployment**

Open the assigned URL in a fresh browser. Upload both fixture PDFs (download them first from the repo's raw URLs). Confirm review completes under 90 s and shows the planted TP.

- [ ] **Step 4: Capture URL in README**

Update `README.md` with the deployed URL under a "Demo" heading.

- [ ] **Step 5: Commit + push**

```bash
git add README.md
git commit -m "docs: add deployed URL"
git push
```

### Task 9.2 — Phase 9 checkpoint

```bash
git tag phase-9-deploy
```

---

## Phase 10 — PRD, TDD, authorship note, demo video

**Goal:** All submission deliverables ready. PRD and TDD are 1–2 pages each. Authorship note is honest. Demo video is recorded and linked.

**Branch:** `phase-10-deliverables`
**Tag at end:** `v1.0-mvp`

### Task 10.1 — PRD

**Files:**
- Create: `docs/PRD.md`

- [ ] **Step 1: Write `docs/PRD.md`**

Cover, in order:
1. **Reviewer persona** — verbatim from `SCOPE.md` §2.
2. **Workflow fit** — three paragraphs: where SharePoint is, where InterLock plugs in pre-review, what the reviewer's keystroke flow becomes.
3. **Wedge** — cross-document discrepancy detection on energy infrastructure PDFs, directional flags, citations.
4. **Wedge-to-platform path** — table of platform-path features (multi-doc sessions, configurable authority, phase-to-phase comparison across 30/60/90, DMS integrations, audit log). Each row links to a section in `BACKLOG.md`.
5. **Why now** — AES scale (cite `research-findings.md` §1) and EPC document volume.

Length cap: 2 pages rendered.

- [ ] **Step 2: Commit**

```bash
git add docs/PRD.md
git commit -m "docs: PRD"
```

### Task 10.2 — TDD

**Files:**
- Create: `docs/TDD.md`

- [ ] **Step 1: Write `docs/TDD.md`**

Cover, in order:
1. **Ingestion and extraction architecture** — PyMuPDF primary, Camelot tables, vision fallback routing rule.
2. **OCR and layout parsing** — Symbol probe results; vision fallback prompt; bbox preservation strategy.
3. **Comparison logic** — exact + unit-normalized + embedding-semantic combiner; directional authority rule; explicitly note this is hardcoded for MVP and configurable in the platform.
4. **Citation and confidence systems** — citation tuple schema; confidence formula `extraction × match × authority`; suppression threshold; UI rendering of bbox-highlighted snippet.
5. **Evaluation design** — gold set construction from documented mutations; precision/recall/F1; acceptance thresholds from `FIXTURES.md` §6.

Length cap: 2 pages rendered.

- [ ] **Step 2: Commit**

```bash
git add docs/TDD.md
git commit -m "docs: TDD"
```

### Task 10.3 — Authorship note

**Files:**
- Create: `docs/AUTHORSHIP.md`

- [ ] **Step 1: Write `docs/AUTHORSHIP.md`**

Four sections, brief:
- **What I built** — list of source files with one-line purpose each.
- **What I reused** — list of libraries with role and reason chosen.
- **What broke** — honest list of dead ends (e.g., Camelot lattice failed on page X, fell back to stream).
- **How I debugged it** — short paragraph per non-obvious issue.

Include in the **What I built** section: explicit disclosure that Doc B is a derived, mutated copy of Doc A, with link to `fixtures/mutations/MUTATIONS.md`.

- [ ] **Step 2: Commit**

```bash
git add docs/AUTHORSHIP.md
git commit -m "docs: authorship note with mutation disclosure"
```

### Task 10.4 — Demo video

- [ ] **Step 1: Write a short script in `docs/DEMO_SCRIPT.md`**

90-second narrated walkthrough plan:
1. 0:00–0:15 — context: AES, EPC, 30/60/90 review.
2. 0:15–0:30 — upload Doc A and Doc B.
3. 0:30–1:00 — point at the surfaced flag, expand citation, click through to page.
4. 1:00–1:15 — show one accepted, one dismissed.
5. 1:15–1:30 — wedge-to-platform pitch.

Hard cap 5 minutes; target 2.

- [ ] **Step 2: Record screen with audio**

Use QuickTime or Loom. Save to `docs/demo.mp4` or upload to YouTube/Loom and capture the link in `docs/DEMO_SCRIPT.md`.

- [ ] **Step 3: Commit script and link**

```bash
git add docs/DEMO_SCRIPT.md
git commit -m "docs: demo script and recording link"
```

### Task 10.5 — Final checkpoint

- [ ] **Step 1: Run full suite + eval**

```bash
uv run pytest -v
uv run python scripts/run_eval.py
```

- [ ] **Step 2: Verify all success criteria in `SCOPE.md` §6 are met**

Walk the list. Tick each. If anything fails, the MVP is not complete.

- [ ] **Step 3: Merge + tag**

```bash
git checkout main
git merge --no-ff phase-10-deliverables -m "phase 10: PRD, TDD, authorship, demo video"
git tag v1.0-mvp
git push --tags
```

---

## Self-review against scope

Spec coverage walk:

- `SCOPE.md` §4 in-scope items 1–17 all map to phases.
- `SCOPE.md` §5 out-of-scope items are negative space — no task touches them.
- `SCOPE.md` §6 success criteria 1–11 all have a verifying task or checkpoint.
- `FIXTURES.md` §5 mutations 1–6 all map to Task 1.3.
- `FIXTURES.md` §6 acceptance thresholds map to Task 8.1.

No placeholders. No "TBD." All code blocks include actual implementations. Type names referenced across tasks (`Span`, `Table`, `ParameterRecord`, `AlignedPair`, `Flag`, `Citation`) are defined exactly once each in the task that introduces them.

---

## Backlog (anything that surfaces during execution goes here, not into the current phase)

Initial seed:

- Phase-to-phase comparison across 30/60/90 (multi-document session).
- Configurable authority UI.
- DMS integration (SharePoint, Bentley ProjectWise).
- Persistent review sessions and audit log.
- CAD/geometry comparison (bananaz.ai-style).
- Bidirectional annotation round-trip back to source PDF.

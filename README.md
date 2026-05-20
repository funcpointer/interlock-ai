# InterLock AI

Cross-document discrepancy detection for engineering PDFs. Reviewer uploads two PDFs from the same project; the system surfaces directional, cited, **severity-tiered** parameter mismatches with optional LLM significance judgment.

- PRD: [`docs/PRD.md`](docs/PRD.md) — reviewer persona, wedge, 5-layer platform path
- TDD: [`docs/TDD.md`](docs/TDD.md) — architecture, tolerance bands, evaluation
- Architecture diagrams: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — control flow, data flow, cache hierarchy
- Authorship: [`docs/AUTHORSHIP.md`](docs/AUTHORSHIP.md) — what's built / reused / disclosed
- Locked scope + fixtures: [`docs/SCOPE.md`](docs/SCOPE.md), [`docs/FIXTURES.md`](docs/FIXTURES.md)
- Risk register: [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
- Backlog (out-of-scope): [`docs/BACKLOG.md`](docs/BACKLOG.md)

## Quick start (local)

```bash
uv sync
uv run pytest
uv run streamlit run src/interlock/ui/app.py
```

## Requirements

- Python 3.12 (pinned in `.python-version`)
- [uv](https://github.com/astral-sh/uv)
- Ghostscript (Camelot dependency): `brew install ghostscript`
- `.env` populated from `.env.example`:
  - `VOYAGE_API_KEY` — required (semantic alignment)
  - `ANTHROPIC_API_KEY` — required (vision fallback path; not exercised by default fixtures)

## Demo

Two fixture pairs ship with the repo.

### Option 1 — revision-diff (60% baseline ↔ 90% revision)

- `doc_a_60pct.pdf` — Doc A (authoritative, real Eaton sample coordination study)
- `doc_b_90pct.pdf` — Doc B (downstream, derived from Doc A with 6 documented mutations — see `fixtures/mutations/MUTATIONS.md`)

Cross-document mode **off**. Expected: 4 flags grouped under **critical** severity (TP-1 impedance, TP-2 fault current, TP-3 transformer rating × 2 sites — all decimal-shift class). Zero false positives. FP-1 unit-equivalent trap (`150 kVA` vs `0.15 MVA`) suppressed by Pint normalization. **Info-tier within-tolerance changes** are suppressed by default (toggle the threshold slider to surface them).

### Option 2 — cross-document (equipment spec ↔ coordination study)

- `spec_xfmr_001.pdf` — Doc A (authoritative, synthetic transformer Equipment Data Sheet; see `docs/AUTHORSHIP.md` for disclosure)
- `doc_a_60pct.pdf` — Doc B (downstream, the same Eaton study reused)

Cross-document mode **on**. Expected: 3 flags surfaced via semantic alignment + canonical glossary — Rated Power ↔ Transformer Rating (minor), Rated Impedance ↔ %Z (major, 22 % deviation), Primary Voltage ↔ System Voltage (major). Zero exact-name matches in this pair; the semantic path + IEEE C57.12.00-cited tolerance bands carry the entire signal. Toggle **Use LLM significance judge** in the UI sidebar to enrich each flag with engineering rationale + downstream-effect propagation (Anthropic Opus 4.7, prompt-cached).

A/B comparison verifies Option 2 demonstrates a capability Option 1 cannot:

```bash
uv run python scripts/run_ab.py
cat eval/results/ab_comparison.json
```

## Evaluation

```bash
uv run python scripts/run_eval.py
cat eval/results/baseline.json
```

Gold set: `fixtures/eval/gold.yaml`. Acceptance thresholds locked in `docs/FIXTURES.md` §6 (recall=1.0 on TPs, FP-rate=0.0 on traps).

## Deploy (Streamlit Cloud)

1. Sign in at https://share.streamlit.io with the same GitHub account that owns this repo.
2. New app → repo `funcpointer/interlock-ai`, branch `main`, main file `streamlit_app.py` (root entrypoint shim; real UI in `src/interlock/ui/app.py`).
3. Advanced settings → Python 3.12.
4. Secrets → paste `VOYAGE_API_KEY` and `ANTHROPIC_API_KEY` as TOML.
5. Deploy.

`packages.txt` declares `ghostscript` so Camelot's lattice parser works on the cloud runner.

## Phase tags

The repo's history is partitioned into TDD phases; each phase ends in a verifiable checkpoint tag.

```
phase-0-scaffold    phase-3-extract     phase-6-citation    phase-9-deploy
phase-1-fixtures    phase-4-align       phase-7-ui          phase-11-cross-doc
phase-2-ingest      phase-5-detect      phase-8-eval        phase-12-real-world

phase-13-tolerance       v1.3-tolerance
phase-14-entity-claim    v1.4-entity-claim

v1.0-mvp · v1.1-cross-doc · v1.2-real-world · v1.3-tolerance · v1.4-entity-claim
```

**Test surface (v1.4):** 294 passing, 7 slow-marked deselected, mypy strict clean, ruff clean. Cost-per-demo-run < $0.10 with diskcache + Anthropic 1-hour prompt caching on ontology blocks.

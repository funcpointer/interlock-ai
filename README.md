# InterLock AI

Cross-document discrepancy detection for engineering PDFs. Reviewer uploads two PDFs from the same project; the system surfaces directional, cited, confidence-scored parameter mismatches.

Locked scope: see [`docs/SCOPE.md`](docs/SCOPE.md).
Locked fixtures: see [`docs/FIXTURES.md`](docs/FIXTURES.md).
Implementation plan: see [`docs/superpowers/plans/2026-05-19-interlock-mvp.md`](docs/superpowers/plans/2026-05-19-interlock-mvp.md).

## Quick start

```bash
uv sync
uv run pytest
uv run streamlit run src/interlock/ui/app.py
```

## Requirements

- Python 3.12 (`.python-version` pins it)
- [uv](https://github.com/astral-sh/uv)
- Ghostscript (Camelot dependency): `brew install ghostscript`
- `.env` with `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` (see `.env.example`)

"""Streamlit Cloud entrypoint shim.

Streamlit Cloud's default 'Main file' is ``streamlit_app.py`` at repo root.
The real UI lives in ``src/interlock/ui/app.py``; we run it as a script here
so Streamlit's runtime context is preserved.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

# Ensure the src-layout package is importable when running from the repo root.
SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

runpy.run_path(str(Path(__file__).parent / "src" / "interlock" / "ui" / "app.py"), run_name="__main__")

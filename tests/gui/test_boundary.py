"""The GUI must stay behind the core boundary: no PIL imports."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIL_IMPORT = re.compile(r"^\s*(from|import)\s+PIL\b", re.MULTILINE)


def test_gui_sources_do_not_import_pil():
    sources = list((ROOT / "src" / "gui").glob("*.py")) + [ROOT / "src" / "app.py"]
    assert len(sources) > 1
    offenders = [str(p) for p in sources if PIL_IMPORT.search(p.read_text(encoding="utf-8"))]
    assert offenders == []

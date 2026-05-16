"""Import-path setup for direct execution of evaluation scripts."""

from __future__ import annotations

import sys
from pathlib import Path


def bootstrap_repo_imports() -> None:
    """Allow eval scripts to run from a source checkout without PYTHONPATH."""

    repo_root = Path(__file__).resolve().parents[2]
    for path in (repo_root / "src", repo_root):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)

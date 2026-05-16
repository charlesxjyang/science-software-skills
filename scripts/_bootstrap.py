"""Import-path setup for direct execution of repository scripts."""

from __future__ import annotations

import sys
from pathlib import Path


def bootstrap_repo_imports() -> None:
    """Allow scripts to run from a source checkout without PYTHONPATH."""

    repo_root = Path(__file__).resolve().parents[1]
    source_root = repo_root / "src"
    for path in (source_root, repo_root):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)

"""Shared helpers for evaluation score-report state."""

from __future__ import annotations

import re
from pathlib import Path


UNSCORED_MARKERS = (
    "Outcome: `not-scored`",
    "- [ ] ",
)


def without_fenced_blocks(text: str) -> str:
    lines: list[str] = []
    in_fence = False
    fence = ""
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^(`{3,})", stripped)
        if match and not in_fence:
            in_fence = True
            fence = match.group(1)
            lines.append("")
            continue
        if in_fence:
            if stripped.startswith(fence):
                in_fence = False
                fence = ""
            lines.append("")
            continue
        lines.append(line)
    return "\n".join(lines)


def report_looks_manually_scored(path: Path) -> bool:
    if not path.is_file():
        return False
    text = without_fenced_blocks(path.read_text(encoding="utf-8"))
    return all(marker not in text for marker in UNSCORED_MARKERS)

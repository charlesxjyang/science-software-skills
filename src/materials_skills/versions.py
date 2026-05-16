"""Version helpers for skill compatibility metadata."""

from __future__ import annotations

import re


def compatibility_status(matched_versions: dict[str, str], compatible_versions: str) -> str:
    """Return an advisory compatibility status for a selected skill."""

    if not matched_versions or not compatible_versions:
        return "unknown"
    bounds = compatible_version_bounds(compatible_versions)
    if bounds is None:
        return "unknown"
    lower, upper = bounds
    saw_unknown = False
    for version in matched_versions.values():
        parsed = version_tuple(version)
        if parsed is None:
            saw_unknown = True
            continue
        if parsed < lower or parsed >= upper:
            return "out-of-range"
    return "unknown" if saw_unknown else "compatible"


def compatible_version_bounds(spec: str) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    match = re.fullmatch(r">=([^,]+),<(.+)", spec.strip())
    if not match:
        return None
    lower = version_tuple(match.group(1))
    upper = version_tuple(match.group(2))
    if lower is None or upper is None:
        return None
    return lower, upper


def version_tuple(version: str) -> tuple[int, ...] | None:
    stripped = version.strip()
    match = re.match(r"\d+(?:\.\d+)*", stripped)
    if not match:
        return None
    suffix = stripped[match.end() :]
    if suffix and not suffix.startswith(("+", ".post")):
        return None
    return tuple(int(part) for part in match.group(0).split("."))

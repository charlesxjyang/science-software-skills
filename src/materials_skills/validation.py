"""Validation for package-scoped SKILL.md files."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from .registry import REGISTRY
from .versions import compatible_version_bounds


REQUIRED_SKILL_SECTIONS = (
    "## What this library is for",
    "## When to use this vs. alternatives",
    "## Canonical workflow",
    "## Key conventions and gotchas",
    "## Anti-patterns",
    "## Diagnostic checks",
    "## Pointers to deeper material",
)
SKILL_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
COMPATIBLE_VERSIONS_PATTERN = re.compile(r"^>=\d+(?:\.\d+)*,<\d+(?:\.\d+)*$")


def parse_skill_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    try:
        _, frontmatter, _ = text.split("---\n", 2)
    except ValueError as exc:
        raise ValueError("unterminated YAML frontmatter") from exc

    values: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def frontmatter_block_value(text: str, key: str) -> str:
    try:
        _, frontmatter, _ = text.split("---\n", 2)
    except ValueError:
        return ""

    lines = frontmatter.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            _, value = line.split(":", 1)
            stripped = value.strip()
            if stripped != "|":
                return stripped.strip('"')
            block_lines: list[str] = []
            for block_line in lines[index + 1 :]:
                if block_line and not block_line.startswith((" ", "\t")):
                    break
                if block_line.strip():
                    block_lines.append(block_line.strip())
            return "\n".join(block_lines).strip()
    return ""


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def canonical_url_identity(value: str) -> tuple[str, str, str, str, str]:
    parsed = urlparse(value)
    path = parsed.path.rstrip("/") or "/"
    return (parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.params, parsed.query)


def parse_frontmatter_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        raise ValueError("expected inline list")
    inner = value[1:-1].strip()
    if not inner:
        return []
    items = [item.strip().strip("'\"") for item in inner.split(",")]
    if any(not item for item in items):
        raise ValueError("contains an empty list item")
    return items


def validate_skills(skills_root: Path, source_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    seen_names: set[str] = set()
    registry_names = {record.skill_name for record in REGISTRY}

    for record in REGISTRY:
        skill_file = skills_root / record.skill_dir / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{record.skill_name}: missing {skill_file}")
            continue

        text = skill_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        try:
            frontmatter = parse_skill_frontmatter(text)
        except ValueError as exc:
            errors.append(f"{record.skill_name}: {exc}")
            continue

        name = frontmatter.get("name")
        if name != record.skill_name:
            errors.append(f"{record.skill_name}: frontmatter name {name!r} does not match registry")
        if name in seen_names:
            errors.append(f"{record.skill_name}: duplicate skill name {name!r}")
        if name:
            seen_names.add(name)

        for key in (
            "description",
            "version",
            "compatible_versions",
            "related_skills",
            "canonical_docs",
            "canonical_tutorials",
        ):
            if key not in frontmatter:
                errors.append(f"{record.skill_name}: missing frontmatter key {key}")

        for key in ("description", "version", "compatible_versions", "canonical_docs", "canonical_tutorials"):
            if key in frontmatter and not frontmatter[key].strip():
                errors.append(f"{record.skill_name}: frontmatter key {key} must not be empty")
        if "description" in frontmatter and not frontmatter_block_value(text, "description"):
            errors.append(f"{record.skill_name}: frontmatter key description must not be empty")

        version = frontmatter.get("version")
        if version and not SKILL_VERSION_PATTERN.fullmatch(version):
            errors.append(f"{record.skill_name}: version must be semantic X.Y.Z")

        compatible_versions = frontmatter.get("compatible_versions")
        if compatible_versions and not COMPATIBLE_VERSIONS_PATTERN.fullmatch(compatible_versions):
            errors.append(f"{record.skill_name}: compatible_versions must look like >=X.Y,<A.B")
        elif compatible_versions:
            bounds = compatible_version_bounds(compatible_versions)
            if bounds is not None and bounds[0] >= bounds[1]:
                errors.append(f"{record.skill_name}: compatible_versions lower bound must be below upper bound")

        if "related_skills" in frontmatter:
            try:
                related = parse_frontmatter_list(frontmatter["related_skills"])
            except ValueError as exc:
                errors.append(f"{record.skill_name}: related_skills {exc}")
            else:
                seen_related: set[str] = set()
                for related_name in related:
                    if related_name in seen_related:
                        errors.append(f"{record.skill_name}: duplicate related skill {related_name!r}")
                    seen_related.add(related_name)
                    if related_name not in registry_names:
                        errors.append(f"{record.skill_name}: related skill {related_name!r} is not registered")
                    if related_name == record.skill_name:
                        errors.append(f"{record.skill_name}: related skill must not reference itself")

        for key in ("canonical_docs", "canonical_tutorials"):
            url = frontmatter.get(key, "")
            if url and not is_http_url(url):
                errors.append(f"{record.skill_name}: {key} must be an http(s) URL")
        canonical_docs = frontmatter.get("canonical_docs", "")
        canonical_tutorials = frontmatter.get("canonical_tutorials", "")
        if (
            canonical_docs
            and canonical_tutorials
            and is_http_url(canonical_docs)
            and is_http_url(canonical_tutorials)
            and canonical_url_identity(canonical_docs) == canonical_url_identity(canonical_tutorials)
        ):
            errors.append(f"{record.skill_name}: canonical_docs and canonical_tutorials must differ")

        if len(lines) > 300:
            errors.append(f"{record.skill_name}: SKILL.md has {len(lines)} lines, expected <= 300")

        for section in REQUIRED_SKILL_SECTIONS:
            if section not in text:
                errors.append(f"{record.skill_name}: missing section {section}")

        if source_root is not None:
            source_file = source_root / record.skill_dir / "SKILL.md"
            if not source_file.is_file():
                errors.append(f"{record.skill_name}: missing source skill {source_file}")
            elif source_file.read_text(encoding="utf-8") != text:
                errors.append(f"{record.skill_name}: packaged skill differs from source skill")

    return errors

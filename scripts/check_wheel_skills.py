#!/usr/bin/env python3
"""Check that a built wheel carries the expected materials-skills payload."""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

try:
    from scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from materials_skills.registry import REGISTRY


SOURCE_ONLY_PREFIXES = ("docs/", "eval/", "research/", "scripts/", "skills/", "tests/")


def check_wheel_skills(
    wheel: Path,
    source_root: Path | None = None,
    package_root: Path | None = None,
    console_script: str = "",
    pyproject: Path | None = None,
    readme: Path | None = None,
) -> list[str]:
    """Return human-readable wheel payload problems."""

    if not wheel.is_file():
        return [f"missing wheel: {wheel}"]

    expected = {
        f"materials_skills/skills/{record.skill_dir}/SKILL.md"
        for record in REGISTRY
    }
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        wheel_skill_text = {
            path: archive.read(path).decode("utf-8")
            for path in expected
            if path in names
        }
        wheel_text = {
            name: archive.read(name).decode("utf-8")
            for name in names
            if name.startswith("materials_skills/") and name.endswith(".py")
        }
        entry_points = {
            name: archive.read(name).decode("utf-8")
            for name in names
            if name.endswith(".dist-info/entry_points.txt")
        }
        metadata_text = {
            name: archive.read(name).decode("utf-8")
            for name in names
            if name.endswith(".dist-info/METADATA")
        }

    skill_files = [name for name in names if name.startswith("materials_skills/skills/") and name.endswith("/SKILL.md")]
    skill_counts = {name: skill_files.count(name) for name in set(skill_files)}
    actual = set(skill_files)
    errors: list[str] = []
    source_only_files = [
        name
        for name in names
        if name.startswith(SOURCE_ONLY_PREFIXES) and not name.endswith("/")
    ]
    for name in sorted(source_only_files):
        errors.append(f"source-only file included in wheel: {name}")

    for path in sorted(expected - actual):
        errors.append(f"missing wheel skill: {path}")
    for path in sorted(actual - expected):
        errors.append(f"extra wheel skill: {path}")
    for path, count in sorted(skill_counts.items()):
        if count != 1:
            errors.append(f"duplicate wheel skill: {path} appears {count} times")

    if source_root is not None:
        for record in REGISTRY:
            wheel_path = f"materials_skills/skills/{record.skill_dir}/SKILL.md"
            source_path = source_root / record.skill_dir / "SKILL.md"
            if not source_path.is_file():
                errors.append(f"missing source skill: {source_path}")
                continue
            if wheel_path in wheel_skill_text and wheel_skill_text[wheel_path] != source_path.read_text(encoding="utf-8"):
                errors.append(f"stale wheel skill: {wheel_path} differs from {source_path}")

    if package_root is not None:
        expected_modules = {
            "materials_skills/" + str(path.relative_to(package_root)).replace("\\", "/")
            for path in package_root.rglob("*.py")
        }
        actual_modules = set(wheel_text)
        for path in sorted(expected_modules - actual_modules):
            errors.append(f"missing wheel module: {path}")
        for path in sorted(actual_modules - expected_modules):
            errors.append(f"extra wheel module: {path}")
        for wheel_path in sorted(expected_modules & actual_modules):
            source_path = package_root / Path(wheel_path).relative_to("materials_skills")
            if wheel_text[wheel_path] != source_path.read_text(encoding="utf-8"):
                errors.append(f"stale wheel module: {wheel_path} differs from {source_path}")

    if console_script:
        expected_line = f"{console_script} = materials_skills.cli:main"
        if not entry_points:
            errors.append("missing wheel entry_points.txt")
        elif not any(expected_line in text for text in entry_points.values()):
            errors.append(f"missing wheel console script: {expected_line}")

    if pyproject is not None:
        project_version = _project_version(pyproject)
        init_version = _init_version(package_root) if package_root is not None else ""
        wheel_version = _wheel_metadata_version(metadata_text)
        if not project_version:
            errors.append(f"missing project version: {pyproject}")
        if not init_version:
            errors.append("missing package __version__")
        if not wheel_version:
            errors.append("missing wheel metadata version")
        if project_version and init_version and project_version != init_version:
            errors.append(f"version mismatch: pyproject {project_version} != __version__ {init_version}")
        if project_version and wheel_version and project_version != wheel_version:
            errors.append(f"version mismatch: pyproject {project_version} != wheel {wheel_version}")

    if readme is not None:
        if not readme.is_file():
            errors.append(f"missing README: {readme}")
        elif not metadata_text:
            errors.append("missing wheel metadata for README check")
        else:
            readme_text = readme.read_text(encoding="utf-8")
            if not any(readme_text in text for text in metadata_text.values()):
                errors.append(f"stale wheel README metadata: METADATA does not include {readme}")

    return errors


def _project_version(pyproject: Path) -> str:
    if not pyproject.is_file():
        return ""
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


def _init_version(package_root: Path | None) -> str:
    if package_root is None:
        return ""
    init_file = package_root / "__init__.py"
    if not init_file.is_file():
        return ""
    match = re.search(r'(?m)^__version__\s*=\s*"([^"]+)"', init_file.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


def _wheel_metadata_version(metadata_text: dict[str, str]) -> str:
    for text in metadata_text.values():
        match = re.search(r"(?m)^Version:\s*(.+)$", text)
        if match:
            return match.group(1).strip()
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path, help="built materials-skills wheel to inspect")
    parser.add_argument(
        "--source-root",
        type=Path,
        help="optional source skills root; when provided, wheel SKILL.md files must match it exactly",
    )
    parser.add_argument(
        "--package-root",
        type=Path,
        help="optional source package root; when provided, wheel Python modules must match it exactly",
    )
    parser.add_argument(
        "--console-script",
        default="",
        help="optional console script name that must point to materials_skills.cli:main",
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        help="optional pyproject.toml; when provided, project version must match __version__ and wheel metadata",
    )
    parser.add_argument(
        "--readme",
        type=Path,
        help="optional README path; when provided, wheel METADATA must include its current text",
    )
    args = parser.parse_args(argv)

    errors = check_wheel_skills(
        args.wheel,
        source_root=args.source_root,
        package_root=args.package_root,
        console_script=args.console_script,
        pyproject=args.pyproject,
        readme=args.readme,
    )
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1

    print("Wheel payload is complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

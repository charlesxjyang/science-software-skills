#!/usr/bin/env python3
"""Check that a built source distribution carries the current source payload."""

from __future__ import annotations

import argparse
from collections import Counter
import tarfile
from pathlib import Path

try:
    from scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from materials_skills.registry import REGISTRY


def check_sdist_payload(
    sdist: Path,
    source_root: Path | None = None,
    package_root: Path | None = None,
    scripts_root: Path | None = None,
    docs_root: Path | None = None,
    eval_root: Path | None = None,
    research_root: Path | None = None,
    tests_root: Path | None = None,
    registry_json: Path | None = None,
    readme: Path | None = None,
    pyproject: Path | None = None,
) -> list[str]:
    """Return human-readable source distribution payload problems."""

    if not sdist.is_file():
        return [f"missing sdist: {sdist}"]

    errors: list[str] = []
    try:
        with tarfile.open(sdist, "r:gz") as archive:
            members = [member for member in archive.getmembers() if member.isfile()]
            normalized_paths = [_strip_root(member.name) for member in members]
            for path, count in sorted(Counter(normalized_paths).items()):
                if count > 1:
                    errors.append(f"duplicate sdist file: {path} appears {count} times")
            text_by_path: dict[str, str] = {}
            for member in members:
                normalized = _strip_root(member.name)
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                try:
                    text_by_path[normalized] = extracted.read().decode("utf-8")
                except UnicodeDecodeError:
                    continue
    except (OSError, tarfile.TarError) as exc:
        return [f"invalid sdist: {sdist}: {exc}"]

    expected_source_skills = {f"skills/{record.skill_dir}/SKILL.md" for record in REGISTRY}
    actual_source_skills = {
        path for path in text_by_path if path.startswith("skills/") and path.endswith("/SKILL.md")
    }
    _compare_path_sets(errors, "sdist source skill", expected_source_skills, actual_source_skills)

    expected_packaged_skills = {
        f"src/materials_skills/skills/{record.skill_dir}/SKILL.md" for record in REGISTRY
    }
    actual_packaged_skills = {
        path
        for path in text_by_path
        if path.startswith("src/materials_skills/skills/") and path.endswith("/SKILL.md")
    }
    _compare_path_sets(errors, "sdist packaged skill", expected_packaged_skills, actual_packaged_skills)

    if source_root is not None:
        for record in REGISTRY:
            sdist_path = f"skills/{record.skill_dir}/SKILL.md"
            source_path = source_root / record.skill_dir / "SKILL.md"
            _compare_text(errors, "stale sdist source skill", text_by_path, sdist_path, source_path)

    if package_root is not None:
        expected_modules = {
            "src/materials_skills/" + str(path.relative_to(package_root)).replace("\\", "/")
            for path in package_root.rglob("*.py")
        }
        actual_modules = {path for path in text_by_path if path.startswith("src/materials_skills/") and path.endswith(".py")}
        _compare_path_sets(errors, "sdist module", expected_modules, actual_modules)

        for record in REGISTRY:
            sdist_path = f"src/materials_skills/skills/{record.skill_dir}/SKILL.md"
            source_path = package_root / "skills" / record.skill_dir / "SKILL.md"
            _compare_text(errors, "stale sdist packaged skill", text_by_path, sdist_path, source_path)

        for sdist_path in sorted(expected_modules & actual_modules):
            source_path = package_root / Path(sdist_path).relative_to("src/materials_skills")
            _compare_text(errors, "stale sdist module", text_by_path, sdist_path, source_path)

    if scripts_root is not None:
        if not scripts_root.is_dir():
            errors.append(f"missing scripts root: {scripts_root}")
        else:
            expected_scripts = {
                "scripts/" + str(path.relative_to(scripts_root)).replace("\\", "/")
                for path in scripts_root.rglob("*.py")
            }
            actual_scripts = {path for path in text_by_path if path.startswith("scripts/") and path.endswith(".py")}
            _compare_path_sets(errors, "sdist script", expected_scripts, actual_scripts)
            for sdist_path in sorted(expected_scripts & actual_scripts):
                source_path = scripts_root / Path(sdist_path).relative_to("scripts")
                _compare_text(errors, "stale sdist script", text_by_path, sdist_path, source_path)

    if readme is not None:
        _compare_text(errors, "stale sdist README", text_by_path, "README.md", readme)

    if docs_root is not None:
        if not docs_root.is_dir():
            errors.append(f"missing docs root: {docs_root}")
        else:
            expected_docs = {
                "docs/" + str(path.relative_to(docs_root)).replace("\\", "/")
                for path in docs_root.rglob("*.md")
            }
            actual_docs = {path for path in text_by_path if path.startswith("docs/") and path.endswith(".md")}
            _compare_path_sets(errors, "sdist doc", expected_docs, actual_docs)
            for sdist_path in sorted(expected_docs & actual_docs):
                source_path = docs_root / Path(sdist_path).relative_to("docs")
                _compare_text(errors, "stale sdist doc", text_by_path, sdist_path, source_path)

    if eval_root is not None:
        _compare_text_tree(
            errors,
            "sdist eval file",
            "stale sdist eval file",
            text_by_path,
            eval_root,
            "eval",
            suffixes={".json", ".jsonl", ".md", ".py"},
        )

    if research_root is not None:
        _compare_text_tree(
            errors,
            "sdist research note",
            "stale sdist research note",
            text_by_path,
            research_root,
            "research",
            suffixes={".md"},
        )

    if tests_root is not None:
        _compare_text_tree(
            errors,
            "sdist test file",
            "stale sdist test file",
            text_by_path,
            tests_root,
            "tests",
            suffixes={".json", ".py", ".txt", ".yaml", ".yml"},
        )

    if registry_json is not None:
        _compare_text(errors, "stale sdist registry", text_by_path, "registry.json", registry_json)

    if pyproject is not None:
        _compare_text(errors, "stale sdist pyproject", text_by_path, "pyproject.toml", pyproject)

    return errors


def _strip_root(path: str) -> str:
    parts = Path(path).parts
    if len(parts) <= 1:
        return path
    return str(Path(*parts[1:])).replace("\\", "/")


def _compare_path_sets(errors: list[str], label: str, expected: set[str], actual: set[str]) -> None:
    for path in sorted(expected - actual):
        errors.append(f"missing {label}: {path}")
    for path in sorted(actual - expected):
        errors.append(f"extra {label}: {path}")


def _compare_text(
    errors: list[str],
    label: str,
    text_by_path: dict[str, str],
    archive_path: str,
    source_path: Path,
) -> None:
    if not source_path.is_file():
        errors.append(f"missing source file: {source_path}")
        return
    if archive_path not in text_by_path:
        errors.append(f"missing sdist file: {archive_path}")
        return
    if text_by_path[archive_path] != source_path.read_text(encoding="utf-8"):
        errors.append(f"{label}: {archive_path} differs from {source_path}")


def _compare_text_tree(
    errors: list[str],
    set_label: str,
    stale_label: str,
    text_by_path: dict[str, str],
    source_root: Path,
    archive_prefix: str,
    suffixes: set[str],
) -> None:
    if not source_root.is_dir():
        errors.append(f"missing {archive_prefix} root: {source_root}")
        return
    expected_paths = {
        f"{archive_prefix}/" + str(path.relative_to(source_root)).replace("\\", "/")
        for path in source_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix in suffixes
    }
    actual_paths = {
        path
        for path in text_by_path
        if path.startswith(f"{archive_prefix}/") and Path(path).suffix in suffixes
    }
    _compare_path_sets(errors, set_label, expected_paths, actual_paths)
    for archive_path in sorted(expected_paths & actual_paths):
        source_path = source_root / Path(archive_path).relative_to(archive_prefix)
        _compare_text(errors, stale_label, text_by_path, archive_path, source_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sdist", type=Path, help="built materials-skills sdist to inspect")
    parser.add_argument("--source-root", type=Path, help="source skills root")
    parser.add_argument("--package-root", type=Path, help="source package root")
    parser.add_argument("--scripts-root", type=Path, help="scripts root with Python files that must match the sdist")
    parser.add_argument("--docs-root", type=Path, help="docs root with markdown files that must match the sdist")
    parser.add_argument("--eval-root", type=Path, help="evaluation harness root that must match the sdist")
    parser.add_argument("--research-root", type=Path, help="research notes root that must match the sdist")
    parser.add_argument("--tests-root", type=Path, help="tests root and fixtures that must match the sdist")
    parser.add_argument("--registry-json", type=Path, help="registry JSON path that must match the sdist")
    parser.add_argument("--readme", type=Path, help="README path that must match the sdist")
    parser.add_argument("--pyproject", type=Path, help="pyproject.toml path that must match the sdist")
    args = parser.parse_args(argv)

    errors = check_sdist_payload(
        args.sdist,
        source_root=args.source_root,
        package_root=args.package_root,
        scripts_root=args.scripts_root,
        docs_root=args.docs_root,
        eval_root=args.eval_root,
        research_root=args.research_root,
        tests_root=args.tests_root,
        registry_json=args.registry_json,
        readme=args.readme,
        pyproject=args.pyproject,
    )
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1

    print("Source distribution payload is complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

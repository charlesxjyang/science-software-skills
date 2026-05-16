"""Skill matching and installation helpers."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .environment import ParsedEnvironment
from .registry import SkillRecord, normalize_distribution_name
from .validation import parse_skill_frontmatter
from .versions import compatibility_status


AGENT_TARGETS = {
    "claude": Path(".claude") / "skills",
    "cursor": Path(".cursor") / "skills",
    "codex": Path(".codex") / "skills",
}
AGENT_CHOICES = tuple(AGENT_TARGETS) + ("all",)


@dataclass(frozen=True)
class InstallAction:
    skill_name: str
    destination: Path
    status: str


@dataclass(frozen=True)
class SkillMatch:
    skill_name: str
    matched_distributions: tuple[str, ...]
    matched_versions: tuple[tuple[str, str], ...]
    compatible_versions: str
    compatibility: str
    registered_distributions: tuple[str, ...]


def describe_skill_matches(
    records: Iterable[SkillRecord],
    package_names: set[str],
    package_versions: dict[str, str] | None = None,
    compatible_versions_by_skill: dict[str, str] | None = None,
) -> list[SkillMatch]:
    """Describe which installed package names triggered each skill match."""

    package_versions = package_versions or {}
    compatible_versions_by_skill = compatible_versions_by_skill or {}
    normalized_packages: dict[str, list[str]] = {}
    for package_name in package_names:
        normalized_packages.setdefault(normalize_distribution_name(package_name), []).append(package_name)

    matches: list[SkillMatch] = []
    for record in records:
        matched: list[str] = []
        for distribution in record.distributions:
            normalized = normalize_distribution_name(distribution)
            matched.extend(normalized_packages.get(normalized, []))
        matched_names = tuple(sorted(set(matched), key=normalize_distribution_name))
        matched_versions = tuple(
            (name, package_versions[name])
            for name in matched_names
            if package_versions.get(name)
        )
        compatible_versions = compatible_versions_by_skill.get(record.skill_name, "")
        matches.append(
            SkillMatch(
                skill_name=record.skill_name,
                matched_distributions=matched_names,
                matched_versions=matched_versions,
                compatible_versions=compatible_versions,
                compatibility=compatibility_status(dict(matched_versions), compatible_versions),
                registered_distributions=record.distributions,
            )
        )
    return matches


def skill_compatible_versions(records: Iterable[SkillRecord], skills_root: Path) -> dict[str, str]:
    """Read compatible_versions metadata from source or packaged skill files."""

    versions: dict[str, str] = {}
    for record in records:
        skill_file = skills_root / record.skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        try:
            frontmatter = parse_skill_frontmatter(skill_file.read_text(encoding="utf-8"))
        except ValueError:
            continue
        versions[record.skill_name] = frontmatter.get("compatible_versions", "")
    return versions


def install_skills(
    records: Iterable[SkillRecord],
    skills_root: Path,
    target_dir: Path,
    dry_run: bool = False,
    force: bool = False,
) -> list[InstallAction]:
    records = tuple(records)
    planned = plan_install_actions(records, skills_root, target_dir, force=force)
    if dry_run:
        return planned

    for action in planned:
        if action.status == "would-error":
            raise FileExistsError(f"{action.destination} already exists and differs; rerun with --force to overwrite")

    actions: list[InstallAction] = []
    source_by_skill = {record.skill_name: skills_root / record.skill_dir for record in records}
    for action in planned:
        source = source_by_skill[action.skill_name]
        if action.status == "unchanged":
            actions.append(InstallAction(action.skill_name, action.destination, "unchanged"))
        elif action.status == "would-install":
            shutil.copytree(source, action.destination)
            actions.append(InstallAction(action.skill_name, action.destination, "installed"))
        elif action.status == "would-overwrite":
            shutil.rmtree(action.destination)
            shutil.copytree(source, action.destination)
            actions.append(InstallAction(action.skill_name, action.destination, "overwritten"))
    return actions


def plan_install_actions(
    records: Iterable[SkillRecord],
    skills_root: Path,
    target_dir: Path,
    force: bool = False,
) -> list[InstallAction]:
    actions: list[InstallAction] = []
    target_dir = target_dir.resolve()
    for record in records:
        source = skills_root / record.skill_dir
        if not source.is_dir():
            raise FileNotFoundError(f"missing skill directory for {record.skill_name}: {source}")
        destination = target_dir / record.skill_name
        if destination.exists():
            if _directory_contents_equal(source, destination):
                actions.append(InstallAction(record.skill_name, destination, "unchanged"))
                continue
            actions.append(
                InstallAction(record.skill_name, destination, "would-overwrite" if force else "would-error")
            )
            continue
        actions.append(InstallAction(record.skill_name, destination, "would-install"))
    return actions


def preflight_install_actions(
    records: Iterable[SkillRecord],
    skills_root: Path,
    targets: Iterable[Path],
    force: bool = False,
) -> None:
    records = tuple(records)
    for target in targets:
        for action in plan_install_actions(records, skills_root, target, force=force):
            if action.status == "would-error":
                raise FileExistsError(
                    f"{action.destination} already exists and differs; rerun with --force to overwrite"
                )


def _directory_contents_equal(left: Path, right: Path) -> bool:
    if not left.is_dir() or not right.is_dir():
        return False
    left_files = {path.relative_to(left) for path in left.rglob("*") if path.is_file()}
    right_files = {path.relative_to(right) for path in right.rglob("*") if path.is_file()}
    if left_files != right_files:
        return False
    return all((left / relative).read_bytes() == (right / relative).read_bytes() for relative in left_files)


def select_install_targets(agent: str, explicit_target: Path | None) -> list[Path]:
    if explicit_target is not None:
        return [explicit_target]
    if agent == "all":
        return list(AGENT_TARGETS.values())
    return [AGENT_TARGETS[agent]]


def prepare_install_targets(targets: Iterable[Path]) -> None:
    for target in targets:
        target.resolve().mkdir(parents=True, exist_ok=True)


def install_payload_json(
    args: argparse.Namespace,
    environment: ParsedEnvironment,
    packages: set[str],
    records: Iterable[SkillRecord],
    skill_matches: list[SkillMatch],
    skill_matches_by_name: dict[str, SkillMatch],
    targets: list[Path],
    actions: list[InstallAction],
) -> str:
    return json.dumps(
        {
            "package_count": len(packages),
            "environment": {
                "source": environment.source,
                "requested_format": environment.requested_format,
                "format": environment.detected_format,
                "package_count": len(packages),
                "package_versions": {
                    name: environment.package_versions[name]
                    for name in sorted(environment.package_versions, key=normalize_distribution_name)
                },
            },
            "skills": [record.skill_name for record in records],
            "matches": [
                {
                    "skill": match.skill_name,
                    "matched_distributions": list(match.matched_distributions),
                    "matched_versions": dict(match.matched_versions),
                    "compatible_versions": match.compatible_versions,
                    "compatibility": match.compatibility,
                    "registered_distributions": list(match.registered_distributions),
                }
                for match in skill_matches
            ],
            "agent": args.agent,
            "target": str(targets[0]) if len(targets) == 1 else None,
            "targets": [str(target) for target in targets],
            "installed": [str(action.destination) for action in actions],
            "actions": [
                {
                    "skill": action.skill_name,
                    "path": str(action.destination),
                    "status": action.status,
                    "matched_distributions": list(skill_matches_by_name[action.skill_name].matched_distributions),
                    "matched_versions": dict(skill_matches_by_name[action.skill_name].matched_versions),
                    "compatible_versions": skill_matches_by_name[action.skill_name].compatible_versions,
                    "compatibility": skill_matches_by_name[action.skill_name].compatibility,
                }
                for action in actions
            ],
            "dry_run": args.dry_run,
            "force": args.force,
        },
        indent=2,
    )

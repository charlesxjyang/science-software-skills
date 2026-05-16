"""Command-line interface for environment-aware skill installation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from importlib import metadata
from pathlib import Path

from . import __version__
from .environment import (
    ParsedEnvironment,
    detect_current_environment,
    detect_current_environment_details,
    load_environment,
    parse_conda_export,
    parse_conda_json,
    parse_conda_list,
    parse_environment_file,
    parse_pip_json,
    parse_pip_list,
)
from .install import (
    AGENT_CHOICES,
    InstallAction,
    SkillMatch,
    describe_skill_matches,
    install_payload_json,
    install_skills,
    preflight_install_actions,
    prepare_install_targets,
    select_install_targets,
    skill_compatible_versions,
)
from .registry import REGISTRY, default_skills_root, match_skills, registry_payload
from .validation import (
    canonical_url_identity,
    frontmatter_block_value,
    is_http_url,
    parse_frontmatter_list,
    parse_skill_frontmatter,
    validate_skills,
)
from .versions import (
    compatibility_status,
    compatible_version_bounds as _compatible_version_bounds,
    version_tuple as _version_tuple,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="materials-skills")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install", help="install skills for a Python environment")
    install.add_argument("--env", type=Path, help="pip list, pip JSON, conda env export, conda list file, or '-'")
    install.add_argument(
        "--format",
        choices=("auto", "pip", "pip-json", "conda", "conda-json", "conda-list"),
        default="auto",
        help="environment file format",
    )
    install.add_argument(
        "--agent",
        choices=AGENT_CHOICES,
        default="claude",
        help="agent skill directory convention to use; 'all' installs to every built-in convention",
    )
    install.add_argument("--target", type=Path, help="explicit skill installation directory")
    install.add_argument("--skills-root", type=Path, default=default_skills_root())
    install.add_argument("--dry-run", action="store_true", help="print matches without writing files")
    install.add_argument("--force", action="store_true", help="overwrite existing skill directories that differ")
    install.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    validate = subparsers.add_parser("validate", help="validate registry skill files")
    validate.add_argument("--skills-root", type=Path, default=default_skills_root())
    validate.add_argument("--source-root", type=Path, default=None)
    validate.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    registry = subparsers.add_parser("registry", help="print the package-to-skill registry")
    registry.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    return parser


def install_command(args: argparse.Namespace) -> int:
    actions: list[InstallAction] = []
    try:
        environment = load_environment(args.env, args.format) if args.env else detect_current_environment_details()
        packages = environment.package_names
        records = match_skills(packages)
        compatible_versions_by_skill = skill_compatible_versions(records, args.skills_root)
        skill_matches = describe_skill_matches(
            records,
            packages,
            environment.package_versions,
            compatible_versions_by_skill,
        )
        skill_matches_by_name = {match.skill_name: match for match in skill_matches}
        targets = select_install_targets(args.agent, args.target)
        if not args.dry_run:
            preflight_install_actions(records, args.skills_root, targets, force=args.force)
            prepare_install_targets(targets)
        for target in targets:
            actions.extend(
                install_skills(
                    records,
                    args.skills_root,
                    target,
                    dry_run=args.dry_run,
                    force=args.force,
                )
            )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        else:
            print(f"ERROR {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(install_payload_json(args, environment, packages, records, skill_matches, skill_matches_by_name, targets, actions))
        return 0

    if not records:
        print("No matching materials/chemistry skills found for this environment.")
        return 0
    labels = {
        "installed": "Installed",
        "unchanged": "Unchanged",
        "overwritten": "Overwrote",
        "would-install": "Would install",
        "would-overwrite": "Would overwrite",
        "would-error": "Would fail",
    }
    for action in actions:
        print(f"{labels[action.status]} {action.skill_name} -> {action.destination}")
    return 0


def validate_command(args: argparse.Namespace) -> int:
    errors = validate_skills(args.skills_root, source_root=args.source_root)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    elif errors:
        for error in errors:
            print(f"ERROR {error}")
    else:
        print(f"Validated {len(REGISTRY)} skills in {args.skills_root}")
    return 1 if errors else 0


def registry_command(args: argparse.Namespace) -> int:
    payload = registry_payload()
    if args.json:
        print(json.dumps({"skills": payload}, indent=2))
    else:
        for record in payload:
            distributions = ", ".join(str(item) for item in record["distributions"])
            print(f"{record['skill_name']}: {distributions} -> {record['skill_dir']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "install":
        return install_command(args)
    if args.command == "validate":
        return validate_command(args)
    if args.command == "registry":
        return registry_command(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

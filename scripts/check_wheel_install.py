#!/usr/bin/env python3
"""Smoke-test the built wheel through its installed console script."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def wheel_filename_version(wheel: Path) -> str:
    parts = wheel.name.split("-")
    if len(parts) >= 2 and parts[0] == "materials_skills":
        return parts[1]
    return ""


def venv_bin(venv: Path, command: str) -> Path:
    if sys.platform == "win32":
        suffix = ".exe" if command in {"python", "pip", "materials-skills"} else ""
        return venv / "Scripts" / f"{command}{suffix}"
    return venv / "bin" / command


def run(command: list[str | Path], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def fail(message: str, result: subprocess.CompletedProcess[str] | None = None) -> int:
    print(f"ERROR {message}", file=sys.stderr)
    if result is not None:
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    return 1


def smoke_wheel_install(wheel: Path, env_file: Path, expected_skill_count: int) -> list[str]:
    errors: list[str] = []
    if not wheel.is_file():
        return [f"missing wheel: {wheel}"]
    if not env_file.is_file():
        return [f"missing environment fixture: {env_file}"]

    with tempfile.TemporaryDirectory(prefix="materials-skills-wheel-smoke-") as tmp:
        root = Path(tmp)
        venv = root / "venv"
        create = run([sys.executable, "-m", "venv", venv])
        if create.returncode != 0:
            return [f"venv creation failed: {create.stderr or create.stdout}".strip()]

        install = run([venv_bin(venv, "pip"), "install", "--no-index", str(wheel)])
        if install.returncode != 0:
            return [f"wheel install failed: {install.stderr or install.stdout}".strip()]

        console = venv_bin(venv, "materials-skills")
        version = run([console, "--version"])
        if version.returncode != 0:
            return [f"installed version failed: {version.stderr or version.stdout}".strip()]
        installed_version = version.stdout.strip()
        expected_version = wheel_filename_version(wheel)
        if expected_version and installed_version != f"materials-skills {expected_version}":
            errors.append(
                f"installed version returned {installed_version!r}, expected 'materials-skills {expected_version}'"
            )
        elif not installed_version.startswith("materials-skills "):
            errors.append(f"installed version returned {version.stdout.strip()!r}")

        validate = run([console, "validate", "--json"])
        if validate.returncode != 0:
            return [f"installed validate failed: {validate.stderr or validate.stdout}".strip()]
        try:
            validate_payload = json.loads(validate.stdout)
        except json.JSONDecodeError as exc:
            return [f"installed validate did not emit JSON: {exc}"]
        if validate_payload != {"ok": True, "errors": []}:
            errors.append(f"installed validate returned {validate_payload!r}")

        registry = run([console, "registry", "--json"])
        if registry.returncode != 0:
            return [f"installed registry failed: {registry.stderr or registry.stdout}".strip()]
        try:
            registry_payload = json.loads(registry.stdout)
        except json.JSONDecodeError as exc:
            return [f"installed registry did not emit JSON: {exc}"]
        if not isinstance(registry_payload, dict) or not isinstance(registry_payload.get("skills"), list):
            return ["installed registry JSON must be an object with a skills list"]
        registry_count = len(registry_payload["skills"])
        if registry_count != expected_skill_count:
            errors.append(f"installed registry returned {registry_count} skills, expected {expected_skill_count}")
        registry_skills = [
            skill.get("skill_name")
            for skill in registry_payload["skills"]
            if isinstance(skill, dict)
            and isinstance(skill.get("skill_name"), str)
            and skill.get("skill_name")
        ]
        registry_skill_set = set(registry_skills)
        if len(registry_skill_set) != registry_count:
            errors.append("installed registry contains duplicate or malformed skill names")

        target = root / ".claude" / "skills"
        install_skills = run(
            [
                console,
                "install",
                "--env",
                env_file,
                "--target",
                target,
                "--json",
            ]
        )
        if install_skills.returncode != 0:
            return [f"installed install command failed: {install_skills.stderr or install_skills.stdout}".strip()]
        try:
            install_payload = json.loads(install_skills.stdout)
        except json.JSONDecodeError as exc:
            return [f"installed install command did not emit JSON: {exc}"]
        if not isinstance(install_payload, dict) or not isinstance(install_payload.get("skills"), list):
            return ["installed install command JSON must be an object with a skills list"]
        if install_payload.get("agent") != "claude":
            errors.append(f"installed install command returned agent {install_payload.get('agent')!r}, expected 'claude'")
        raw_installed_skills = install_payload["skills"]
        installed_skills = [
            skill
            for skill in raw_installed_skills
            if isinstance(skill, str) and skill
        ]
        if len(installed_skills) != len(raw_installed_skills):
            errors.append("installed install command returned malformed skill names")
        if len(installed_skills) != expected_skill_count:
            errors.append(f"installed command selected {len(installed_skills)} skills, expected {expected_skill_count}")
        installed_skill_set = set(installed_skills)
        if installed_skill_set != registry_skill_set:
            errors.append(
                f"installed command selected {sorted(installed_skill_set)!r}, expected {sorted(registry_skill_set)!r}"
            )
        for skill in registry_skill_set:
            if not (target / skill / "SKILL.md").is_file():
                errors.append(f"installed skill missing from target: {skill}")
        target_skill_dirs = {path.name for path in target.iterdir() if path.is_dir()} if target.is_dir() else set()
        if target_skill_dirs != registry_skill_set:
            errors.append(
                f"installed target contains {sorted(target_skill_dirs)!r}, expected {sorted(registry_skill_set)!r}"
            )

        agent_all = run(
            [
                console,
                "install",
                "--env",
                env_file,
                "--agent",
                "all",
                "--dry-run",
                "--json",
            ]
        )
        if agent_all.returncode != 0:
            return [f"installed --agent all dry-run failed: {agent_all.stderr or agent_all.stdout}".strip()]
        try:
            agent_all_payload = json.loads(agent_all.stdout)
        except json.JSONDecodeError as exc:
            return [f"installed --agent all dry-run did not emit JSON: {exc}"]
        if not isinstance(agent_all_payload, dict) or not isinstance(agent_all_payload.get("skills"), list):
            return ["installed --agent all dry-run JSON must be an object with a skills list"]
        raw_agent_all_skills = agent_all_payload["skills"]
        agent_all_skills = [
            skill
            for skill in raw_agent_all_skills
            if isinstance(skill, str) and skill
        ]
        if len(agent_all_skills) != len(raw_agent_all_skills):
            errors.append("installed --agent all dry-run returned malformed skill names")
        agent_all_skill_set = set(agent_all_skills)
        if agent_all_skill_set != registry_skill_set:
            errors.append(
                f"installed --agent all dry-run selected {sorted(agent_all_skill_set)!r}, expected {sorted(registry_skill_set)!r}"
            )
        if agent_all_payload.get("agent") != "all":
            errors.append(
                f"installed --agent all dry-run returned agent {agent_all_payload.get('agent')!r}, expected 'all'"
            )
        if agent_all_payload.get("target") is not None:
            errors.append(
                f"installed --agent all dry-run returned target {agent_all_payload.get('target')!r}, expected None"
            )
        expected_targets = [".claude/skills", ".cursor/skills", ".codex/skills"]
        if agent_all_payload.get("targets") != expected_targets:
            errors.append(
                f"installed --agent all dry-run returned targets {agent_all_payload.get('targets')!r}, expected {expected_targets!r}"
            )
        if agent_all_payload.get("dry_run") is not True:
            errors.append(
                f"installed --agent all dry-run returned dry_run {agent_all_payload.get('dry_run')!r}, expected True"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path, help="built materials-skills wheel to install")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "pip-list.txt",
        help="environment fixture expected to select all bundled skills",
    )
    parser.add_argument("--expected-skill-count", type=int, default=12)
    args = parser.parse_args(argv)

    errors = smoke_wheel_install(args.wheel, args.env_file, args.expected_skill_count)
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print("Wheel install smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run local non-empirical v0 checks."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WHEEL = ROOT / "dist" / "materials_skills-0.1.0-py3-none-any.whl"
SDIST = ROOT / "dist" / "materials_skills-0.1.0.tar.gz"


@dataclass(frozen=True)
class Check:
    label: str
    command: tuple[str, ...]


CHECKS: tuple[Check, ...] = (
    Check("unit tests", (sys.executable, "-m", "unittest", "discover", "-s", "tests")),
    Check("skill validation", (sys.executable, "-m", "materials_skills.cli", "validate", "--source-root", "skills", "--json")),
    Check("package-data sync", (sys.executable, "scripts/sync_packaged_skills.py", "--check")),
    Check("registry JSON", (sys.executable, "scripts/check_registry_json.py", "--registry-json", "registry.json")),
    Check(
        "wheel payload",
        (
            sys.executable,
            "scripts/check_wheel_skills.py",
            str(WHEEL),
            "--source-root",
            "skills",
            "--package-root",
            "src/materials_skills",
            "--console-script",
            "materials-skills",
            "--pyproject",
            "pyproject.toml",
            "--readme",
            "README.md",
        ),
    ),
    Check(
        "wheel install smoke",
        (
            sys.executable,
            "scripts/check_wheel_install.py",
            str(WHEEL),
        ),
    ),
    Check(
        "sdist payload",
        (
            sys.executable,
            "scripts/check_sdist_payload.py",
            str(SDIST),
            "--source-root",
            "skills",
            "--package-root",
            "src/materials_skills",
            "--scripts-root",
            "scripts",
            "--docs-root",
            "docs",
            "--eval-root",
            "eval",
            "--research-root",
            "research",
            "--tests-root",
            "tests",
            "--registry-json",
            "registry.json",
            "--readme",
            "README.md",
            "--pyproject",
            "pyproject.toml",
        ),
    ),
)


def check_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath_parts = [str(ROOT / "src"), str(ROOT)]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    return env


def main() -> int:
    env = check_env()
    for check in CHECKS:
        print(f"==> {check.label}", flush=True)
        result = subprocess.run(check.command, cwd=ROOT, env=env, check=False)
        if result.returncode != 0:
            print(f"FAILED {check.label}: exit {result.returncode}", file=sys.stderr)
            return result.returncode
    print("Local v0 checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

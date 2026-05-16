#!/usr/bin/env python3
"""Report local and empirical v0 completion status without calling Claude."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    from scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from eval.scripts.check_eval_artifacts import check_artifacts
from eval.scripts.run_claude_eval import DEFAULT_TASKS, REPO_ROOT, load_tasks
from eval.scripts.score_results import DEFAULT_REPORT, DEFAULT_RESULTS
from scripts.check_wheel_install import smoke_wheel_install
from scripts.check_wheel_skills import check_wheel_skills
from scripts.check_sdist_payload import check_sdist_payload
from scripts.check_registry_json import check_registry_json
from scripts.sync_packaged_skills import check_sync
from materials_skills.cli import validate_skills


DEFAULT_WHEEL = REPO_ROOT / "dist" / "materials_skills-0.1.0-py3-none-any.whl"
DEFAULT_SDIST = REPO_ROOT / "dist" / "materials_skills-0.1.0.tar.gz"
DEFAULT_IMPEDANCE_TASKS = REPO_ROOT / "eval" / "impedance" / "tasks.json"
DEFAULT_IMPEDANCE_RESULTS = REPO_ROOT / "eval" / "impedance" / "results.jsonl"
DEFAULT_IMPEDANCE_REPORT = REPO_ROOT / "eval" / "impedance" / "score-report.md"
LOCAL_NEXT_STEPS = (
    "Fix local readiness errors.",
    "python scripts/check_local_v0.py",
)
EMPIRICAL_NEXT_STEPS = (
    "claude auth login",
    "claude auth status --json",
    "python eval/scripts/run_claude_eval.py --preflight-only --max-budget-usd 0.05",
    "python eval/scripts/run_impedance_pipeline.py --resume",
    "Manually score eval/impedance/score-report.md",
    "python eval/scripts/run_impedance_pipeline.py --skip-model-run --check-scored",
    "python eval/scripts/run_v0_pipeline.py --resume",
    "Manually score eval/score-report.md",
    "python eval/scripts/run_v0_pipeline.py --skip-model-run --check-scored",
)
EMPIRICAL_AUTOMATION_STEPS = (
    "python eval/scripts/run_impedance_pipeline.py --skip-model-run --check-scored --json",
    "python eval/scripts/run_v0_pipeline.py --skip-model-run --check-scored --json",
)


def check_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath_parts = [str(REPO_ROOT / "src"), str(REPO_ROOT)]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    return env


def run_unit_tests() -> list[str]:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    result = subprocess.run(command, cwd=REPO_ROOT, env=check_env(), text=True, capture_output=True, check=False)
    if result.returncode == 0:
        return []
    detail = (result.stderr or result.stdout).strip()
    if detail:
        return [f"unit tests failed with exit {result.returncode}: {detail}"]
    return [f"unit tests failed with exit {result.returncode}"]


def local_status(args: argparse.Namespace) -> dict[str, object]:
    unit_test_errors = run_unit_tests()
    validation_errors = validate_skills(args.skills_root, source_root=args.skills_root)
    sync_errors = check_sync(args.skills_root, args.package_skills_root)
    registry_errors = check_registry_json(args.registry_json)
    wheel_errors = check_wheel_skills(
        args.wheel,
        source_root=args.skills_root,
        package_root=args.package_root,
        console_script="materials-skills",
        pyproject=args.pyproject,
        readme=args.readme,
    )
    smoke_errors = smoke_wheel_install(args.wheel, args.env_file, args.expected_skill_count)
    sdist_errors = check_sdist_payload(
        args.sdist,
        source_root=args.skills_root,
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
    return {
        "ok": (
            not unit_test_errors
            and not validation_errors
            and not sync_errors
            and not registry_errors
            and not wheel_errors
            and not smoke_errors
            and not sdist_errors
        ),
        "unit_tests": unit_test_errors,
        "skill_validation": validation_errors,
        "package_data_sync": sync_errors,
        "registry_json": registry_errors,
        "wheel_payload": wheel_errors,
        "wheel_install_smoke": smoke_errors,
        "sdist_payload": sdist_errors,
    }


def empirical_status(args: argparse.Namespace) -> dict[str, object]:
    impedance = check_artifacts(args.impedance_tasks, args.impedance_results, args.impedance_report)
    full = check_artifacts(args.tasks, args.results, args.report)
    return {
        "ok": bool(impedance["ok"]) and bool(full["ok"]),
        "impedance": impedance,
        "full_matrix": full,
    }


def summarize_problems(problems: list[str], limit: int = 3) -> str:
    if not problems:
        return "none"
    visible = problems[:limit]
    suffix = "" if len(problems) <= limit else f"; ... {len(problems) - limit} more"
    return "; ".join(visible) + suffix


def next_steps(local_ok: bool, empirical_ok: bool) -> list[str]:
    if not local_ok:
        return list(LOCAL_NEXT_STEPS)
    if not empirical_ok:
        return list(EMPIRICAL_NEXT_STEPS)
    return []


def automation_steps(local_ok: bool, empirical_ok: bool) -> list[str]:
    if local_ok and not empirical_ok:
        return list(EMPIRICAL_AUTOMATION_STEPS)
    return []


def blockers(local_ok: bool, empirical_ok: bool) -> list[str]:
    result: list[str] = []
    if not local_ok:
        result.append("local-readiness")
    if not empirical_ok:
        result.append("empirical-artifacts")
    return result


def print_next_steps(steps: list[str]) -> None:
    if not steps:
        return
    if steps == list(LOCAL_NEXT_STEPS):
        print("Next: fix local readiness errors, then rerun `python scripts/check_local_v0.py`.")
        return
    print("Next empirical steps:")
    for step in steps:
        print(f"  {step}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skills-root", type=Path, default=REPO_ROOT / "skills")
    parser.add_argument("--package-root", type=Path, default=REPO_ROOT / "src" / "materials_skills")
    parser.add_argument("--package-skills-root", type=Path, default=REPO_ROOT / "src" / "materials_skills" / "skills")
    parser.add_argument("--scripts-root", type=Path, default=REPO_ROOT / "scripts")
    parser.add_argument("--docs-root", type=Path, default=REPO_ROOT / "docs")
    parser.add_argument("--eval-root", type=Path, default=REPO_ROOT / "eval")
    parser.add_argument("--research-root", type=Path, default=REPO_ROOT / "research")
    parser.add_argument("--tests-root", type=Path, default=REPO_ROOT / "tests")
    parser.add_argument("--registry-json", type=Path, default=REPO_ROOT / "registry.json")
    parser.add_argument("--wheel", type=Path, default=DEFAULT_WHEEL)
    parser.add_argument("--sdist", type=Path, default=DEFAULT_SDIST)
    parser.add_argument("--pyproject", type=Path, default=REPO_ROOT / "pyproject.toml")
    parser.add_argument("--readme", type=Path, default=REPO_ROOT / "README.md")
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / "tests" / "fixtures" / "pip-list.txt")
    parser.add_argument("--expected-skill-count", type=int, default=12)
    parser.add_argument("--impedance-tasks", type=Path, default=DEFAULT_IMPEDANCE_TASKS)
    parser.add_argument("--impedance-results", type=Path, default=DEFAULT_IMPEDANCE_RESULTS)
    parser.add_argument("--impedance-report", type=Path, default=DEFAULT_IMPEDANCE_REPORT)
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    try:
        load_tasks(args.impedance_tasks)
        load_tasks(args.tasks)
    except OSError as exc:
        parser.error(f"cannot load task manifest: {exc}")
    except ValueError as exc:
        parser.error(str(exc))

    local = local_status(args)
    empirical = empirical_status(args)
    steps = next_steps(bool(local["ok"]), bool(empirical["ok"]))
    automation = automation_steps(bool(local["ok"]), bool(empirical["ok"]))
    blocker_list = blockers(bool(local["ok"]), bool(empirical["ok"]))
    payload = {
        "ok": bool(local["ok"]) and bool(empirical["ok"]),
        "local": local,
        "empirical": empirical,
        "blockers": blocker_list,
        "next_steps": steps,
        "automation_steps": automation,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    elif payload["ok"]:
        print("v0 complete: local checks and empirical artifacts are complete.")
    else:
        print("v0 incomplete.")
        print(f"local ok: {local['ok']}")
        print(f"empirical ok: {empirical['ok']}")
        print(f"blockers: {', '.join(blocker_list)}")
        for name, errors in local.items():
            if name != "ok" and errors:
                print(f"ERROR local {name}: {summarize_problems(errors)}")
        for name in ("impedance", "full_matrix"):
            artifact = empirical[name]
            if not artifact["ok"]:
                if artifact.get("blockers"):
                    print(f"ERROR empirical {name} blockers: {', '.join(artifact['blockers'])}")
                print(
                    f"ERROR empirical {name}: evaluation="
                    f"{summarize_problems(artifact['evaluation']['problems'])}"
                )
                print(
                    f"ERROR empirical {name}: scoring="
                    f"{summarize_problems(artifact['scoring']['problems'])}"
                )
        print_next_steps(steps)
        print("Use --json for full status details.")

    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

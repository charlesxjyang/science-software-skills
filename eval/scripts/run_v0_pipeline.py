#!/usr/bin/env python3
"""Orchestrate the v0 empirical evaluation workflow."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

try:
    from eval.scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from eval.scripts.check_eval_artifacts import check_artifacts
from eval.scripts.check_eval_completeness import check_results_file
from eval.scripts.run_claude_eval import DEFAULT_TASKS, REPO_ROOT, load_tasks, main as run_eval_main
from eval.scripts.score_results import DEFAULT_REPORT, DEFAULT_RESULTS, load_jsonl, render_report
from eval.scripts.report_utils import report_looks_manually_scored


DEFAULT_KDENSE_ROOT = REPO_ROOT / "eval" / "kdense-public"
DEFAULT_SMOKE_RESULTS = Path(tempfile.gettempdir()) / "materials-skills-smoke-results.jsonl"
SMOKE_TASK = "impedance-fit-randles-cpe-warburg"
SMOKE_VARIANT = "package-skill"


def print_problems(prefix: str, problems: list[str]) -> None:
    for problem in problems:
        print(f"ERROR {prefix}: {problem}")


def run_model_steps(args: argparse.Namespace) -> int:
    print("Step 1/4: Claude preflight")
    preflight_code = run_eval_main(
        [
            "--tasks",
            str(args.tasks),
            "--skills-root",
            str(args.skills_root),
            "--preflight-only",
            "--max-budget-usd",
            args.max_budget_usd,
        ]
    )
    if preflight_code != 0:
        print("Claude preflight failed. Run `claude auth login`, then rerun this pipeline command.")
        return preflight_code

    if not args.skip_smoke:
        print("Step 2/4: package-skill smoke test")
        smoke_code = run_eval_main(
            [
                "--tasks",
                str(args.tasks),
                "--skills-root",
                str(args.skills_root),
                "--task",
                SMOKE_TASK,
                "--variant",
                SMOKE_VARIANT,
                "--results",
                str(args.smoke_results),
                "--max-budget-usd",
                args.max_budget_usd,
                "--skip-preflight",
            ]
        )
        if smoke_code != 0:
            return smoke_code
    else:
        print("Step 2/4: package-skill smoke test skipped")

    print("Step 3/4: full baseline/package-skill/K-Dense matrix")
    full_args = [
        "--tasks",
        str(args.tasks),
        "--skills-root",
        str(args.skills_root),
        "--kdense-root",
        str(args.kdense_root),
        "--results",
        str(args.results),
        "--max-budget-usd",
        args.max_budget_usd,
        "--skip-preflight",
    ]
    if args.resume:
        full_args.append("--resume")
    full_code = run_eval_main(full_args)
    if full_code != 0:
        return full_code

    print("Step 4/4: completeness gate and score-report scaffold")
    tasks = load_tasks(args.tasks)
    completeness = check_results_file(tasks, args.results)
    if not completeness["ok"]:
        print(
            "Evaluation incomplete: "
            f"{completeness['complete_count']}/{completeness['expected_count']} expected records are ok."
        )
        print_problems("evaluation", completeness["problems"])
        return 1

    if report_looks_manually_scored(args.report) and not args.overwrite_report:
        print(
            f"Refusing to overwrite manually scored report {args.report}. "
            "Use --skip-model-run --check-scored to validate it, or pass --overwrite-report to replace it."
        )
        return 1

    report = render_report(tasks, load_jsonl(args.results))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"Wrote score report scaffold to {args.report}")
    return 0


def check_scored_artifacts(args: argparse.Namespace) -> int:
    payload = check_artifacts(args.tasks, args.results, args.report)
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if payload["ok"] else 1
    if payload["ok"]:
        print("Evaluation artifacts complete.")
        return 0

    print("Evaluation artifacts incomplete.")
    print(f"blockers: {', '.join(payload['blockers'])}")
    print_problems("evaluation", payload["evaluation"]["problems"])
    print_problems("scoring", payload["scoring"]["problems"])
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--skills-root", type=Path, default=REPO_ROOT / "skills")
    parser.add_argument("--kdense-root", type=Path, default=DEFAULT_KDENSE_ROOT)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--smoke-results", type=Path, default=DEFAULT_SMOKE_RESULTS)
    parser.add_argument("--max-budget-usd", default="0.50")
    parser.add_argument("--resume", action="store_true", help="resume the full matrix, preserving complete ok records")
    parser.add_argument("--skip-smoke", action="store_true", help="skip the one-task package-skill smoke test")
    parser.add_argument(
        "--overwrite-report",
        action="store_true",
        help="allow model-run mode to replace an already manually scored report",
    )
    parser.add_argument(
        "--skip-model-run",
        action="store_true",
        help="do not call Claude; use with --check-scored after manually filling the score report",
    )
    parser.add_argument(
        "--check-scored",
        action="store_true",
        help="run the final combined artifact gate against existing manually scored artifacts",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON for --skip-model-run --check-scored artifact validation",
    )
    args = parser.parse_args(argv)

    if args.check_scored and not args.skip_model_run:
        parser.error("--check-scored requires --skip-model-run so the manually scored report is not overwritten")
    if args.skip_model_run and not args.check_scored:
        parser.error("--skip-model-run requires --check-scored so skipped model runs are still validated")
    if args.json and not (args.skip_model_run and args.check_scored):
        parser.error("--json is only supported with --skip-model-run --check-scored")

    try:
        load_tasks(args.tasks)
    except OSError as exc:
        parser.error(f"cannot load task manifest {args.tasks}: {exc}")
    except ValueError as exc:
        parser.error(str(exc))

    if not args.skip_model_run:
        model_code = run_model_steps(args)
        if model_code != 0:
            return model_code
    else:
        if not args.json:
            print("Model run skipped; using existing results and report.")

    if args.check_scored:
        return check_scored_artifacts(args)

    print("Model outputs are complete. Fill the score report manually, then rerun with --skip-model-run --check-scored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

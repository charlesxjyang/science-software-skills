#!/usr/bin/env python3
"""Check both v0 evaluation outputs and the manually scored report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from eval.scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from eval.scripts.check_eval_completeness import check_results_file
from eval.scripts.check_score_report import check_report
from eval.scripts.run_claude_eval import DEFAULT_TASKS, load_tasks
from eval.scripts.score_results import DEFAULT_REPORT, DEFAULT_RESULTS


def check_artifacts(tasks_path: Path, results_path: Path, report_path: Path) -> dict[str, object]:
    tasks = load_tasks(tasks_path)
    evaluation = check_results_file(tasks, results_path)
    scoring = check_report(report_path, tasks)
    blockers: list[str] = []
    if not evaluation["ok"]:
        blockers.append("evaluation")
    if not scoring["ok"]:
        blockers.append("scoring")
    return {
        "ok": bool(evaluation["ok"]) and bool(scoring["ok"]),
        "blockers": blockers,
        "evaluation": evaluation,
        "scoring": scoring,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    try:
        load_tasks(args.tasks)
    except OSError as exc:
        parser.error(f"cannot load task manifest {args.tasks}: {exc}")
    except ValueError as exc:
        parser.error(str(exc))

    payload = check_artifacts(args.tasks, args.results, args.report)
    if args.json:
        print(json.dumps(payload, indent=2))
    elif payload["ok"]:
        print("Evaluation artifacts complete.")
    else:
        print("Evaluation artifacts incomplete.")
        print(f"blockers: {', '.join(payload['blockers'])}")
        for problem in payload["evaluation"]["problems"]:
            print(f"ERROR evaluation: {problem}")
        for problem in payload["scoring"]["problems"]:
            print(f"ERROR scoring: {problem}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

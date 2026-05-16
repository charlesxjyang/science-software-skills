#!/usr/bin/env python3
"""Check whether the v0 empirical evaluation has complete model outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from eval.scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from eval.scripts.run_claude_eval import DEFAULT_TASKS, load_tasks, task_context_skills
from eval.scripts.score_results import DEFAULT_RESULTS, load_jsonl


EXPECTED_BASE_VARIANTS = ("baseline", "package-skill")
CONTEXT_REQUIRED_VARIANTS = {"package-skill", "kdense"}
BASELINE_CONTEXT_STATUS = "not-applicable"


def expected_keys(tasks: list[dict]) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    for task in tasks:
        keys.extend((task["id"], variant) for variant in EXPECTED_BASE_VARIANTS)
        if task.get("kdense_applicable", False):
            keys.append((task["id"], "kdense"))
    return keys


def latest_records(records: list[dict]) -> dict[tuple[str, str], dict]:
    latest: dict[tuple[str, str], dict] = {}
    for record in records:
        latest[(record.get("task_id", ""), record.get("variant", ""))] = record
    return latest


def check_results(tasks: list[dict], records: list[dict]) -> dict[str, object]:
    expected = expected_keys(tasks)
    expected_set = set(expected)
    tasks_by_id = {task["id"]: task for task in tasks}
    latest = latest_records(records)
    problems: list[str] = []
    complete_count = 0

    for key in expected:
        record = latest.get(key)
        label = f"{key[0]}:{key[1]}"
        if record is None:
            problems.append(f"{label}: missing result")
            continue
        if record.get("status") != "ok":
            problems.append(f"{label}: status is {record.get('status', 'missing')!r}, expected 'ok'")
            continue
        if not str(record.get("stdout", "")).strip():
            problems.append(f"{label}: missing stdout")
            continue
        if not isinstance(record.get("prompt"), str) or not record.get("prompt", "").strip():
            problems.append(f"{label}: missing prompt")
            continue
        expected_skill = tasks_by_id[key[0]]["skill"]
        if record.get("skill") != expected_skill:
            problems.append(f"{label}: skill is {record.get('skill', 'missing')!r}, expected {expected_skill!r}")
            continue
        if key[1] == "baseline":
            if record.get("context_status") != BASELINE_CONTEXT_STATUS:
                problems.append(
                    f"{label}: context_status is {record.get('context_status', 'missing')!r}, "
                    f"expected {BASELINE_CONTEXT_STATUS!r}"
                )
                continue
            if record.get("context_skills", "missing") != []:
                problems.append(
                    f"{label}: context_skills is {record.get('context_skills', 'missing')!r}, expected []"
                )
                continue
        if key[1] in CONTEXT_REQUIRED_VARIANTS and record.get("context_status") != "provided":
            problems.append(
                f"{label}: context_status is {record.get('context_status', 'missing')!r}, expected 'provided'"
            )
            continue
        if key[1] == "package-skill":
            expected_context_skills = list(task_context_skills(tasks_by_id[key[0]]))
            if record.get("context_skills") != expected_context_skills:
                problems.append(
                    f"{label}: context_skills is {record.get('context_skills', 'missing')!r}, "
                    f"expected {expected_context_skills!r}"
                )
                continue
        if key[1] == "kdense":
            expected_context_skills = [tasks_by_id[key[0]]["skill"]]
            if record.get("context_skills") != expected_context_skills:
                problems.append(
                    f"{label}: context_skills is {record.get('context_skills', 'missing')!r}, "
                    f"expected {expected_context_skills!r}"
                )
                continue
        complete_count += 1

    for key, record in latest.items():
        if key not in expected_set:
            problems.append(f"{key[0]}:{key[1]}: unexpected record with status {record.get('status', 'missing')!r}")

    return {
        "ok": not problems,
        "expected_count": len(expected),
        "complete_count": complete_count,
        "record_count": len(records),
        "problems": problems,
    }


def missing_results_payload(tasks: list[dict], results_path: Path) -> dict[str, object]:
    return {
        "ok": False,
        "expected_count": len(expected_keys(tasks)),
        "complete_count": 0,
        "record_count": 0,
        "problems": [f"missing results file: {results_path}"],
    }


def check_results_file(tasks: list[dict], results_path: Path) -> dict[str, object]:
    if not results_path.is_file():
        return missing_results_payload(tasks, results_path)
    try:
        records = load_jsonl(results_path)
    except (OSError, ValueError) as exc:
        return {
            "ok": False,
            "expected_count": len(expected_keys(tasks)),
            "complete_count": 0,
            "record_count": 0,
            "problems": [f"invalid results file: {exc}"],
        }
    return check_results(tasks, records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    try:
        tasks = load_tasks(args.tasks)
    except OSError as exc:
        parser.error(f"cannot load task manifest {args.tasks}: {exc}")
    except ValueError as exc:
        parser.error(str(exc))

    payload = check_results_file(tasks, args.results)
    if args.json:
        print(json.dumps(payload, indent=2))
    elif payload["ok"]:
        print(f"Evaluation complete: {payload['complete_count']}/{payload['expected_count']} expected records are ok.")
    else:
        print(f"Evaluation incomplete: {payload['complete_count']}/{payload['expected_count']} expected records are ok.")
        for problem in payload["problems"]:
            print(f"ERROR {problem}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

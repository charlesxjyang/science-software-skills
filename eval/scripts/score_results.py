#!/usr/bin/env python3
"""Render Claude evaluation JSONL into a manual scoring report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from eval.scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from eval.scripts.run_claude_eval import DEFAULT_TASKS, load_tasks, validate_result_record
from eval.scripts.report_utils import report_looks_manually_scored


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = REPO_ROOT / "eval" / "results.jsonl"
DEFAULT_REPORT = REPO_ROOT / "eval" / "score-report.md"
FINAL_OUTCOME_CHOICES = "`win`, `tie`, `loss`, or `blocked`"


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
                if not isinstance(record, dict):
                    raise ValueError(f"{path}:{line_number}: JSONL record must be an object")
                validate_result_record(record, path, line_number)
                records.append(record)
    return records


def first_text(record: dict) -> str:
    if record.get("status") == "dry-run":
        return "_Dry run only; no model output._"
    if record.get("status") == "error":
        message = record.get("stderr", "").strip() or record.get("stdout", "").strip() or "no output"
        return f"_Error: {message}_"
    text = record.get("stdout", "").strip()
    return text if text else "_No stdout captured._"


def fenced_text(text: str, language: str = "text") -> list[str]:
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return [f"{fence}{language}", text, fence]


def render_report(tasks: list[dict], records: list[dict]) -> str:
    known_task_ids = {task["id"] for task in tasks}
    grouped: dict[str, dict[str, dict]] = {task_id: {} for task_id in known_task_ids}
    extra_records: list[dict] = []
    for record in records:
        task_id = record["task_id"]
        if task_id in known_task_ids:
            grouped[task_id][record["variant"]] = record
        else:
            extra_records.append(record)

    lines = ["# Evaluation Score Report", ""]
    lines.append(
        "Manual scoring key: mark every criterion reviewed, then replace each "
        f"`not-scored` placeholder with {FINAL_OUTCOME_CHOICES}."
    )
    lines.append("")
    lines.extend(
        [
            "## Comparison Summary",
            "",
            "| Task | Baseline | Package Skill | K-Dense | Winner | Notes |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for task in tasks:
        kdense_cell = "not applicable" if not task.get("kdense_applicable", False) else "not-scored"
        lines.append(f"| `{task['id']}` | not-scored | not-scored | {kdense_cell} | not-scored |  |")
    lines.append("")

    if extra_records:
        lines.extend(["## Preflight And Unmatched Records", ""])
        for record in extra_records:
            lines.extend(
                [
                    f"### Variant: {record.get('variant', 'unknown')}",
                    "",
                    f"Task ID: `{record['task_id']}`",
                    "",
                    f"Status: `{record.get('status', 'unknown')}`",
                    "",
                    "Output:",
                    "",
                    *fenced_text(first_text(record)[:6000]),
                    "",
                ]
            )

    for task in tasks:
        lines.extend(
            [
                f"## {task['id']}: {task['title']}",
                "",
                f"Skill: `{task['skill']}`",
                "",
                "Criteria:",
            ]
        )
        lines.extend(f"- [ ] {criterion}" for criterion in task["success_criteria"])
        lines.append("")

        task_records = grouped.get(task["id"], {})
        for record in sorted(task_records.values(), key=lambda item: item["variant"]):
            lines.extend(
                [
                    f"### Variant: {record['variant']}",
                    "",
                    f"Status: `{record.get('status', 'unknown')}`",
                    "",
                    f"Context status: `{record.get('context_status', 'unknown')}`",
                    "",
                    f"Context skills: `{', '.join(record.get('context_skills', [])) or 'none'}`",
                    "",
                    "Prompt:",
                    "",
                    *fenced_text(record.get("prompt", "").strip() or "_No prompt captured._"),
                    "",
                    "Output:",
                    "",
                    *fenced_text(first_text(record)[:6000]),
                    "",
                    "Outcome: `not-scored`",
                    "",
                    f"Allowed outcomes: {FINAL_OUTCOME_CHOICES}",
                    "",
                    "Notes:",
                    "",
                    "- ",
                    "",
                ]
            )

        missing = {"baseline", "package-skill"}
        if task.get("kdense_applicable", False):
            missing.add("kdense")
        seen = set(task_records)
        for variant in sorted(missing - seen):
            lines.extend(
                [
                    f"### Variant: {variant}",
                    "",
                    "Status: `missing`",
                    "",
                    "Context status: `missing`",
                    "",
                    "Context skills: `unknown`",
                    "",
                    "Outcome: `blocked`",
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--overwrite-report",
        action="store_true",
        help="allow replacing an existing manually scored report",
    )
    args = parser.parse_args(argv)

    if not args.results.is_file():
        print(f"ERROR missing results file: {args.results}", file=sys.stderr)
        return 1

    try:
        tasks = load_tasks(args.tasks)
    except OSError as exc:
        parser.error(f"cannot load task manifest {args.tasks}: {exc}")
    except ValueError as exc:
        parser.error(str(exc))

    try:
        records = load_jsonl(args.results)
    except (OSError, ValueError) as exc:
        print(f"ERROR invalid results file: {exc}", file=sys.stderr)
        return 1
    if report_looks_manually_scored(args.report) and not args.overwrite_report:
        print(
            f"ERROR refusing to overwrite manually scored report: {args.report}. "
            "Use --overwrite-report to regenerate the scaffold.",
            file=sys.stderr,
        )
        return 1
    report = render_report(tasks, records)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"Wrote score report to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

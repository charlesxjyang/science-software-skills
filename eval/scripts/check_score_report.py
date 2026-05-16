#!/usr/bin/env python3
"""Check whether the manual evaluation score report has been filled in."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from eval.scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from eval.scripts.run_claude_eval import DEFAULT_TASKS, load_tasks, task_context_skills
from eval.scripts.score_results import DEFAULT_REPORT
from eval.scripts.report_utils import UNSCORED_MARKERS, without_fenced_blocks
SCORED_OUTCOMES = {"win", "tie", "loss", "blocked"}
WINNER_VALUES = {"baseline", "package-skill", "package skill", "kdense", "tie", "blocked"}
REQUIRED_VARIANT_FIELDS = ("Status:", "Context status:", "Context skills:", "Prompt:", "Output:")


def raw_section_by_heading(text: str, header: str, next_prefix: str) -> str:
    start: int | None = None
    in_fence = False
    fence = ""
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        match = re.match(r"^(`{3,})", stripped)
        if match and not in_fence:
            in_fence = True
            fence = match.group(1)
        elif in_fence and stripped.startswith(fence):
            in_fence = False
            fence = ""

        if not in_fence:
            if start is None and line.startswith(header):
                start = offset
            elif start is not None and line.startswith(next_prefix):
                return text[start:offset]
        offset += len(line)
    return "" if start is None else text[start:]


def expected_variants(task: dict) -> list[str]:
    variants = ["baseline", "package-skill"]
    if task.get("kdense_applicable", False):
        variants.append("kdense")
    return variants


def task_section(text: str, task: dict) -> str:
    text = without_fenced_blocks(text)
    header = f"## {task['id']}: {task['title']}"
    start = text.find(header)
    if start == -1:
        return ""
    next_start = text.find("\n## ", start + len(header))
    if next_start == -1:
        return text[start:]
    return text[start:next_start]


def task_section_count(text: str, task: dict) -> int:
    text = without_fenced_blocks(text)
    return text.count(f"## {task['id']}: {task['title']}")


def variant_section(section: str, variant: str) -> str:
    section = without_fenced_blocks(section)
    header = f"### Variant: {variant}"
    start = section.find(header)
    if start == -1:
        return ""
    next_start = section.find("\n### Variant: ", start + len(header))
    if next_start == -1:
        return section[start:]
    return section[start:next_start]


def raw_variant_section(section: str, variant: str) -> str:
    return raw_section_by_heading(section, f"### Variant: {variant}", "### Variant: ")


def variant_section_count(section: str, variant: str) -> int:
    section = without_fenced_blocks(section)
    return section.count(f"### Variant: {variant}")


def variant_headers(section: str) -> list[str]:
    section = without_fenced_blocks(section)
    variants: list[str] = []
    for line in section.splitlines():
        if line.startswith("### Variant: "):
            variants.append(line.removeprefix("### Variant: ").strip())
    return variants


def summary_row(text: str, task_id: str) -> list[str]:
    text = comparison_summary_section(text)
    prefix = f"| `{task_id}` |"
    for line in text.splitlines():
        if line.startswith(prefix):
            return [cell.strip() for cell in line.strip().strip("|").split("|")]
    return []


def summary_row_count(text: str, task_id: str) -> int:
    text = comparison_summary_section(text)
    prefix = f"| `{task_id}` |"
    return sum(1 for line in text.splitlines() if line.startswith(prefix))


def comparison_summary_section(text: str) -> str:
    text = without_fenced_blocks(text)
    header = "## Comparison Summary"
    start = text.find(header)
    if start == -1:
        return ""
    next_start = text.find("\n## ", start + len(header))
    if next_start == -1:
        return text[start:]
    return text[start:next_start]


def comparison_summary_count(text: str) -> int:
    text = without_fenced_blocks(text)
    return sum(1 for line in text.splitlines() if line == "## Comparison Summary")


def summary_task_ids(text: str) -> list[str]:
    section = comparison_summary_section(text)
    task_ids: list[str] = []
    for line in section.splitlines():
        match = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
        if match:
            task_ids.append(match.group(1).strip())
    return task_ids


def task_headers(text: str) -> list[str]:
    text = without_fenced_blocks(text)
    headers: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") and line != "## Comparison Summary":
            headers.append(line.strip())
    return headers


def variant_outcome(problems: list[str], label: str, section: str) -> str:
    match = re.search(r"Outcome: `([^`]+)`", section)
    if not match:
        problems.append(f"{label}: missing scored outcome")
        return ""
    outcome = match.group(1).strip()
    if outcome not in SCORED_OUTCOMES:
        problems.append(f"{label}: invalid outcome {outcome!r}")
        return ""
    return outcome


def audit_field_value(section: str, field: str) -> str:
    match = re.search(rf"^{re.escape(field)}:\s*`([^`]*)`", section, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def validate_output_block(problems: list[str], label: str, raw_section: str) -> None:
    match = re.search(r"^Output:\s*\n\s*(`{3,})[^\n]*\n(.*?)\n\s*\1", raw_section, flags=re.MULTILINE | re.DOTALL)
    if not match:
        problems.append(f"{label}: missing fenced output block")
        return
    if not match.group(2).strip():
        problems.append(f"{label}: empty output block")


def validate_prompt_block(problems: list[str], task: dict, variant: str, raw_section: str) -> None:
    label = f"{task['id']}:{variant}"
    match = re.search(r"^Prompt:\s*\n\s*(`{3,})[^\n]*\n(.*?)\n\s*\1", raw_section, flags=re.MULTILINE | re.DOTALL)
    if not match:
        problems.append(f"{label}: missing fenced prompt block")
        return
    prompt_text = match.group(2).strip()
    if not prompt_text:
        problems.append(f"{label}: empty prompt block")
        return
    if task["prompt"] not in prompt_text:
        problems.append(f"{label}: prompt block does not include the task manifest prompt")


def validate_variant_audit_fields(
    problems: list[str], task: dict, variant: str, section: str, raw_section: str
) -> None:
    label = f"{task['id']}:{variant}"
    section_lines = {line.strip() for line in section.splitlines()}
    for field in REQUIRED_VARIANT_FIELDS:
        if not any(line.startswith(field) for line in section_lines):
            problems.append(f"{label}: missing {field.rstrip(':').lower()} field")
    if "Status: `ok`" not in section_lines:
        problems.append(f"{label}: status field must be `ok`")
    validate_prompt_block(problems, task, variant, raw_section)
    validate_output_block(problems, label, raw_section)
    expected_context_status = "not-applicable" if variant == "baseline" else "provided"
    actual_context_status = audit_field_value(section, "Context status")
    if actual_context_status != expected_context_status:
        problems.append(
            f"{label}: context status is {actual_context_status!r}, expected {expected_context_status!r}"
        )

    if variant == "baseline":
        expected_context_skills = "none"
    elif variant == "package-skill":
        expected_context_skills = ", ".join(task_context_skills(task))
    else:
        expected_context_skills = task["skill"]
    actual_context_skills = audit_field_value(section, "Context skills")
    if actual_context_skills != expected_context_skills:
        problems.append(
            f"{label}: context skills are {actual_context_skills!r}, expected {expected_context_skills!r}"
        )


def validate_summary_row(problems: list[str], task: dict, row: list[str]) -> None:
    if len(row) != 6:
        problems.append(f"{task['id']}: malformed comparison summary row")
        return

    _, baseline, package_skill, kdense, winner, _ = row
    for column, value in (("baseline", baseline), ("package-skill", package_skill)):
        if value not in SCORED_OUTCOMES:
            problems.append(f"{task['id']}:{column}: invalid summary outcome {value!r}")

    if task.get("kdense_applicable", False):
        if kdense not in SCORED_OUTCOMES:
            problems.append(f"{task['id']}:kdense: invalid summary outcome {kdense!r}")
    elif kdense != "not applicable":
        problems.append(f"{task['id']}:kdense: expected 'not applicable', got {kdense!r}")

    if winner not in WINNER_VALUES:
        problems.append(f"{task['id']}: invalid winner {winner!r}")
        return

    applicable_outcomes = {
        "baseline": baseline,
        "package-skill": package_skill,
    }
    if task.get("kdense_applicable", False):
        applicable_outcomes["kdense"] = kdense

    if winner == "kdense" and not task.get("kdense_applicable", False):
        problems.append(f"{task['id']}: winner 'kdense' is not applicable for this task")
    elif winner in {"baseline", "package-skill", "package skill", "kdense"}:
        winner_column = "package-skill" if winner == "package skill" else winner
        winner_outcome = applicable_outcomes.get(winner_column, "")
        if winner_outcome in SCORED_OUTCOMES and winner_outcome != "win":
            problems.append(f"{task['id']}: winner {winner!r} has summary outcome {winner_outcome!r}, expected 'win'")
    elif winner == "tie" and all(value in SCORED_OUTCOMES for value in applicable_outcomes.values()):
        unique_outcomes = set(applicable_outcomes.values())
        if len(unique_outcomes) != 1 or unique_outcomes == {"blocked"}:
            problems.append(
                f"{task['id']}: winner 'tie' requires all applicable summary outcomes to match and not be blocked"
            )
    elif winner == "blocked" and all(value in SCORED_OUTCOMES for value in applicable_outcomes.values()):
        if set(applicable_outcomes.values()) != {"blocked"}:
            problems.append(f"{task['id']}: winner 'blocked' requires all applicable summary outcomes to be blocked")


def validate_task_criteria(problems: list[str], task: dict, section: str) -> None:
    section_lines = {line.strip() for line in section.splitlines()}
    for criterion in task["success_criteria"]:
        if f"- [x] {criterion}" not in section_lines and f"- [X] {criterion}" not in section_lines:
            problems.append(f"{task['id']}: missing checked criterion {criterion!r}")


def compare_summary_to_variants(
    problems: list[str],
    task: dict,
    row: list[str],
    outcomes: dict[str, str],
) -> None:
    if len(row) != 6:
        return
    summary_values = {
        "baseline": row[1],
        "package-skill": row[2],
    }
    if task.get("kdense_applicable", False):
        summary_values["kdense"] = row[3]

    for variant, summary_value in summary_values.items():
        outcome = outcomes.get(variant)
        if outcome and summary_value in SCORED_OUTCOMES and summary_value != outcome:
            problems.append(
                f"{task['id']}:{variant}: summary outcome {summary_value!r} does not match variant outcome {outcome!r}"
            )


def check_report_text(text: str, tasks: list[dict] | None = None) -> dict[str, object]:
    problems: list[str] = []
    structural_text = without_fenced_blocks(text)
    for marker in UNSCORED_MARKERS:
        count = structural_text.count(marker)
        if count:
            problems.append(f"found {count} unfilled marker(s): {marker!r}")

    summary_count = comparison_summary_count(text)
    if summary_count == 0:
        problems.append("missing comparison summary section")
    elif summary_count > 1:
        problems.append(f"duplicate comparison summary sections ({summary_count})")

    if "| Task | Baseline | Package Skill | K-Dense | Winner | Notes |" not in comparison_summary_section(text):
        problems.append("missing comparison summary table")

    if tasks is not None:
        expected_task_ids = {task["id"] for task in tasks}
        for task_id in summary_task_ids(text):
            if task_id not in expected_task_ids:
                problems.append(f"{task_id}: unexpected comparison summary row")

        expected_task_headers = {f"## {task['id']}: {task['title']}" for task in tasks}
        for header in task_headers(text):
            if header not in expected_task_headers:
                problems.append(f"{header.removeprefix('## ')}: unexpected task section")

        for task in tasks:
            row: list[str] = []
            row_count = summary_row_count(text, task["id"])
            if row_count == 0:
                problems.append(f"{task['id']}: missing comparison summary row")
            else:
                if row_count > 1:
                    problems.append(f"{task['id']}: duplicate comparison summary rows ({row_count})")
                row = summary_row(text, task["id"])
                validate_summary_row(problems, task, row)

            section = task_section(text, task)
            if not section:
                problems.append(f"{task['id']}: missing task section")
                continue
            section_count = task_section_count(text, task)
            if section_count > 1:
                problems.append(f"{task['id']}: duplicate task sections ({section_count})")
            validate_task_criteria(problems, task, section)
            outcomes: dict[str, str] = {}
            raw_section = raw_section_by_heading(text, f"## {task['id']}: {task['title']}", "## ")
            expected_variant_set = set(expected_variants(task))
            for variant in variant_headers(section):
                if variant not in expected_variant_set:
                    problems.append(f"{task['id']}:{variant}: unexpected variant section")
            for variant in expected_variants(task):
                count = variant_section_count(section, variant)
                if count > 1:
                    problems.append(f"{task['id']}:{variant}: duplicate variant sections ({count})")
                subsection = variant_section(section, variant)
                if not subsection:
                    problems.append(f"{task['id']}:{variant}: missing variant section")
                    continue
                raw_subsection = raw_variant_section(raw_section, variant)
                validate_variant_audit_fields(problems, task, variant, subsection, raw_subsection)
                outcome = variant_outcome(problems, f"{task['id']}:{variant}", subsection)
                if outcome:
                    outcomes[variant] = outcome
            compare_summary_to_variants(problems, task, row, outcomes)

    return {
        "ok": not problems,
        "problems": problems,
    }


def check_report(path: Path, tasks: list[dict] | None = None) -> dict[str, object]:
    if not path.is_file():
        return {"ok": False, "problems": [f"missing score report: {path}"]}
    return check_report_text(path.read_text(encoding="utf-8"), tasks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    try:
        tasks = load_tasks(args.tasks)
    except OSError as exc:
        parser.error(f"cannot load task manifest {args.tasks}: {exc}")
    except ValueError as exc:
        parser.error(str(exc))

    payload = check_report(args.report, tasks)
    if args.json:
        print(json.dumps(payload, indent=2))
    elif payload["ok"]:
        print(f"Score report complete: {args.report}")
    else:
        print(f"Score report incomplete: {args.report}")
        for problem in payload["problems"]:
            print(f"ERROR {problem}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

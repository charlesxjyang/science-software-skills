#!/usr/bin/env python3
"""Run or dry-run the v0 Claude evaluation matrix."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    from eval.scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from materials_skills.registry import REGISTRY


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASKS = REPO_ROOT / "eval" / "tasks" / "v0_tasks.json"
DEFAULT_RESULTS = REPO_ROOT / "eval" / "results.jsonl"
REQUIRED_TASK_FIELDS = ("id", "skill", "title", "prompt", "success_criteria")
REQUIRED_RESULT_FIELDS = ("task_id", "variant", "status")
RESULT_STATUSES = {"ok", "error", "dry-run"}
RESULT_VARIANTS = {"baseline", "package-skill", "kdense", "preflight"}
CONTEXT_STATUSES = {"provided", "missing", "not-applicable"}
REGISTERED_SKILL_NAMES = {record.skill_name for record in REGISTRY}
AUTH_STATUS_PREFLIGHT_PROMPT = "claude auth status --json"
MODEL_PREFLIGHT_PROMPT = "Reply with OK only."


@dataclass(frozen=True)
class Variant:
    name: str
    context: str
    context_status: str
    context_skills: tuple[str, ...] = ()


def load_tasks(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("task manifest must be a JSON list")
    task_ids: set[str] = set()
    for index, task in enumerate(data):
        label = f"task[{index}]"
        if not isinstance(task, dict):
            raise ValueError(f"{label} must be a JSON object")
        missing = [field for field in REQUIRED_TASK_FIELDS if field not in task]
        if missing:
            raise ValueError(f"{label} missing required field(s): {', '.join(missing)}")
        for field in ("id", "skill", "title", "prompt"):
            if not isinstance(task[field], str) or not task[field].strip():
                raise ValueError(f"{label}.{field} must be a non-empty string")
        for field in ("id", "skill", "title", "prompt"):
            if task[field] != task[field].strip():
                raise ValueError(f"{label}.{field} must not have leading or trailing whitespace")
        if task["skill"] not in REGISTERED_SKILL_NAMES:
            raise ValueError(f"{label}.skill {task['skill']!r} is not registered")
        if task["id"] in task_ids:
            raise ValueError(f"duplicate task id: {task['id']}")
        task_ids.add(task["id"])
        criteria = task["success_criteria"]
        if not isinstance(criteria, list) or not criteria:
            raise ValueError(f"{label}.success_criteria must be a non-empty list")
        if not all(isinstance(item, str) and item.strip() for item in criteria):
            raise ValueError(f"{label}.success_criteria must contain only non-empty strings")
        if any(item != item.strip() for item in criteria):
            raise ValueError(f"{label}.success_criteria must not have leading or trailing whitespace")
        if len(criteria) != len(set(criteria)):
            raise ValueError(f"{label}.success_criteria must not contain duplicates")
        if "context_skills" in task:
            context_skills = task["context_skills"]
            if not isinstance(context_skills, list) or not context_skills:
                raise ValueError(f"{label}.context_skills must be a non-empty list when present")
            if not all(isinstance(item, str) and item.strip() for item in context_skills):
                raise ValueError(f"{label}.context_skills must contain only non-empty strings")
            if any(item != item.strip() for item in context_skills):
                raise ValueError(f"{label}.context_skills must not have leading or trailing whitespace")
            if len(context_skills) != len(set(context_skills)):
                raise ValueError(f"{label}.context_skills must not contain duplicates")
            unknown_context_skills = [item for item in context_skills if item not in REGISTERED_SKILL_NAMES]
            if unknown_context_skills:
                raise ValueError(
                    f"{label}.context_skills references unregistered skill(s): "
                    f"{', '.join(unknown_context_skills)}"
                )
            if task["skill"] not in context_skills:
                raise ValueError(f"{label}.context_skills must include the primary skill {task['skill']!r}")
        if "kdense_applicable" in task and not isinstance(task["kdense_applicable"], bool):
            raise ValueError(f"{label}.kdense_applicable must be a boolean when present")
        if "hide_success_criteria" in task and not isinstance(task["hide_success_criteria"], bool):
            raise ValueError(f"{label}.hide_success_criteria must be a boolean when present")
        if "doc_sources" in task:
            doc_sources = task["doc_sources"]
            if not isinstance(doc_sources, list) or not doc_sources:
                raise ValueError(f"{label}.doc_sources must be a non-empty list when present")
            if not all(isinstance(item, str) and item.strip() for item in doc_sources):
                raise ValueError(f"{label}.doc_sources must contain only non-empty strings")
            if any(item != item.strip() for item in doc_sources):
                raise ValueError(f"{label}.doc_sources must not have leading or trailing whitespace")
        if "rubric_terms" in task:
            rubric_terms = task["rubric_terms"]
            if not isinstance(rubric_terms, list) or not rubric_terms:
                raise ValueError(f"{label}.rubric_terms must be a non-empty list when present")
            for group_index, group in enumerate(rubric_terms):
                if not isinstance(group, list) or not group:
                    raise ValueError(f"{label}.rubric_terms[{group_index}] must be a non-empty list")
                if not all(isinstance(item, str) and item.strip() for item in group):
                    raise ValueError(f"{label}.rubric_terms[{group_index}] must contain only non-empty strings")
                if any(item != item.strip() for item in group):
                    raise ValueError(f"{label}.rubric_terms[{group_index}] terms must not have whitespace padding")
    return data


def filter_tasks(tasks: list[dict], task_ids: list[str] | None) -> list[dict]:
    if not task_ids:
        return tasks

    requested = set(task_ids)
    known = {task["id"] for task in tasks}
    unknown = sorted(requested - known)
    if unknown:
        raise ValueError(f"unknown task id(s): {', '.join(unknown)}")
    return [task for task in tasks if task["id"] in requested]


def validate_result_record(record: dict, path: Path, line_number: int) -> None:
    missing = [field for field in REQUIRED_RESULT_FIELDS if field not in record]
    if missing:
        raise ValueError(f"{path}:{line_number}: result record missing required field(s): {', '.join(missing)}")
    for field in REQUIRED_RESULT_FIELDS:
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"{path}:{line_number}: result record field {field!r} must be a non-empty string")
        if record[field] != record[field].strip():
            raise ValueError(
                f"{path}:{line_number}: result record field {field!r} "
                "must not have leading or trailing whitespace"
            )
    if record["status"] not in RESULT_STATUSES:
        choices = ", ".join(sorted(RESULT_STATUSES))
        raise ValueError(f"{path}:{line_number}: result record field 'status' must be one of: {choices}")
    if record["variant"] not in RESULT_VARIANTS:
        choices = ", ".join(sorted(RESULT_VARIANTS))
        raise ValueError(f"{path}:{line_number}: result record field 'variant' must be one of: {choices}")
    if record["variant"] == "preflight" and record["task_id"] != "__preflight__":
        raise ValueError(f"{path}:{line_number}: preflight result records must use task_id '__preflight__'")
    if record["task_id"] == "__preflight__" and record["variant"] != "preflight":
        raise ValueError(f"{path}:{line_number}: task_id '__preflight__' is only valid with variant 'preflight'")
    if record["variant"] == "preflight" and record["status"] != "error":
        raise ValueError(f"{path}:{line_number}: preflight result records must have status 'error'")
    if record["variant"] == "preflight" and ("context_status" in record or "context_skills" in record):
        raise ValueError(f"{path}:{line_number}: preflight result records must not include context metadata")

    if "context_status" in record:
        context_status = record["context_status"]
        if not isinstance(context_status, str) or not context_status.strip():
            raise ValueError(f"{path}:{line_number}: result record field 'context_status' must be a non-empty string")
        if context_status != context_status.strip():
            raise ValueError(
                f"{path}:{line_number}: result record field 'context_status' "
                "must not have leading or trailing whitespace"
            )
        if context_status not in CONTEXT_STATUSES:
            choices = ", ".join(sorted(CONTEXT_STATUSES))
            raise ValueError(f"{path}:{line_number}: result record field 'context_status' must be one of: {choices}")

    if "context_skills" in record:
        context_skills = record["context_skills"]
        if not isinstance(context_skills, list):
            raise ValueError(f"{path}:{line_number}: result record field 'context_skills' must be a list")
        if not all(isinstance(item, str) and item.strip() for item in context_skills):
            raise ValueError(
                f"{path}:{line_number}: result record field 'context_skills' "
                "must contain only non-empty strings"
            )
        if any(item != item.strip() for item in context_skills):
            raise ValueError(
                f"{path}:{line_number}: result record field 'context_skills' "
                "must not have leading or trailing whitespace"
            )
        if len(context_skills) != len(set(context_skills)):
            raise ValueError(f"{path}:{line_number}: result record field 'context_skills' must not contain duplicates")
        unknown_context_skills = [item for item in context_skills if item not in REGISTERED_SKILL_NAMES]
        if unknown_context_skills:
            raise ValueError(
                f"{path}:{line_number}: result record field 'context_skills' references unregistered skill(s): "
                f"{', '.join(unknown_context_skills)}"
            )

    for field in ("skill", "prompt", "stdout", "stderr"):
        if field in record and not isinstance(record[field], str):
            raise ValueError(f"{path}:{line_number}: result record field {field!r} must be a string when present")

    if "skill" in record:
        skill = record["skill"]
        if record["variant"] == "preflight":
            if skill:
                raise ValueError(f"{path}:{line_number}: preflight result records must use an empty skill field")
        elif skill:
            if skill != skill.strip():
                raise ValueError(
                    f"{path}:{line_number}: result record field 'skill' must not have leading or trailing whitespace"
                )
            if skill not in REGISTERED_SKILL_NAMES:
                raise ValueError(f"{path}:{line_number}: result record field 'skill' is not registered")

    if "returncode" in record:
        returncode = record["returncode"]
        if not isinstance(returncode, int):
            raise ValueError(f"{path}:{line_number}: result record field 'returncode' must be an integer when present")
        if record["status"] == "ok" and returncode != 0:
            raise ValueError(f"{path}:{line_number}: result record status 'ok' requires returncode 0")
        if record["status"] == "error" and returncode == 0:
            raise ValueError(f"{path}:{line_number}: result record status 'error' requires nonzero returncode")


def skill_context(skill_name: str, skills_root: Path) -> str:
    skill_path = skills_root / skill_name / "SKILL.md"
    if not skill_path.is_file():
        raise FileNotFoundError(f"missing skill for {skill_name}: {skill_path}")
    return skill_path.read_text(encoding="utf-8")


def task_context_skills(task: dict) -> tuple[str, ...]:
    skill_names = task.get("context_skills") or [task["skill"]]
    unique: list[str] = []
    for skill_name in skill_names:
        if skill_name not in unique:
            unique.append(skill_name)
    return tuple(unique)


def package_skill_context(skill_names: tuple[str, ...], skills_root: Path) -> str:
    sections = []
    for skill_name in skill_names:
        sections.append(f"## Package Skill: {skill_name}\n\n{skill_context(skill_name, skills_root)}")
    return "\n\n".join(sections)


def kdense_candidates(skill_name: str, kdense_root: Path) -> list[Path]:
    return [
        kdense_root / skill_name / "SKILL.md",
        kdense_root / skill_name / "skill.md",
        kdense_root / f"{skill_name}.md",
    ]


def kdense_context_status(skill_name: str, kdense_root: Path | None) -> str:
    if kdense_root is None:
        return "missing"
    if any(candidate.is_file() for candidate in kdense_candidates(skill_name, kdense_root)):
        return "provided"
    return "missing"


def kdense_context(skill_name: str, kdense_root: Path | None) -> str:
    if kdense_root is None:
        return "K-Dense skill root not provided. Answer without additional package-skill context."

    for candidate in kdense_candidates(skill_name, kdense_root):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return f"No K-Dense skill found for {skill_name} under {kdense_root}."


def build_prompt(task: dict, variant: Variant) -> str:
    prompt = (
        "You are answering a scientific Python coding prompt. Use only the context "
        "provided here plus your general knowledge.\n\n"
        f"## Variant\n{variant.name}\n\n"
        f"## Context\n{variant.context}\n\n"
        f"## User Prompt\n{task['prompt']}\n\n"
    )
    if not task.get("hide_success_criteria", False):
        criteria = "\n".join(f"- {item}" for item in task["success_criteria"])
        prompt += "## Evaluation Criteria\n" f"{criteria}\n\n"
    return prompt + "Return a concise but complete answer with code where appropriate."


def iter_variants(task: dict, skills_root: Path, kdense_root: Path | None) -> list[Variant]:
    package_skills = task_context_skills(task)
    variants = [
        Variant("baseline", "No package-specific skill context provided.", "not-applicable"),
        Variant("package-skill", package_skill_context(package_skills, skills_root), "provided", package_skills),
    ]
    if task.get("kdense_applicable", False):
        variants.append(
            Variant(
                "kdense",
                kdense_context(task["skill"], kdense_root),
                kdense_context_status(task["skill"], kdense_root),
                (task["skill"],),
            )
        )
    return variants


def filter_variants(variants: list[Variant], variant_names: list[str] | None) -> list[Variant]:
    if not variant_names:
        return variants
    requested = set(variant_names)
    return [variant for variant in variants if variant.name in requested]


def selected_variant_names(task: dict, variant_names: list[str] | None) -> tuple[str, ...]:
    names = ["baseline", "package-skill"]
    if task.get("kdense_applicable", False):
        names.append("kdense")
    if variant_names:
        requested = set(variant_names)
        names = [name for name in names if name in requested]
    return tuple(names)


def iter_selected_variants(
    task: dict,
    skills_root: Path,
    kdense_root: Path | None,
    variant_names: list[str] | None,
) -> list[Variant]:
    variants: list[Variant] = []
    for name in selected_variant_names(task, variant_names):
        if name == "baseline":
            variants.append(Variant("baseline", "No package-specific skill context provided.", "not-applicable"))
        elif name == "package-skill":
            package_skills = task_context_skills(task)
            variants.append(
                Variant(
                    "package-skill",
                    package_skill_context(package_skills, skills_root),
                    "provided",
                    package_skills,
                )
            )
        elif name == "kdense":
            variants.append(
                Variant(
                    "kdense",
                    kdense_context(task["skill"], kdense_root),
                    kdense_context_status(task["skill"], kdense_root),
                    (task["skill"],),
                )
            )
    return variants


def missing_package_context_items(
    tasks: list[dict],
    skills_root: Path,
    variant_names: list[str] | None,
) -> list[str]:
    if variant_names is not None and "package-skill" not in variant_names:
        return []

    missing: list[str] = []
    seen: set[tuple[str, str]] = set()
    for task in tasks:
        for skill_name in task_context_skills(task):
            key = (task["id"], skill_name)
            skill_path = skills_root / skill_name / "SKILL.md"
            if key not in seen and not skill_path.is_file():
                missing.append(f"{task['id']}:{skill_name} ({skill_path})")
                seen.add(key)
    return missing


def missing_kdense_context_tasks(
    tasks: list[dict], kdense_root: Path | None, variant_names: list[str] | None
) -> list[str]:
    if variant_names is not None and "kdense" not in variant_names:
        return []
    return [
        task["id"]
        for task in tasks
        if task.get("kdense_applicable", False) and kdense_context_status(task["skill"], kdense_root) != "provided"
    ]


def run_claude(prompt: str, max_budget_usd: str) -> subprocess.CompletedProcess[str]:
    command = [
        "claude",
        "-p",
        "--max-budget-usd",
        max_budget_usd,
        "--tools",
        "",
        "--permission-mode",
        "dontAsk",
        prompt,
    ]
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        message = str(exc)
        return subprocess.CompletedProcess(command, returncode=127, stdout="", stderr=message)


def run_claude_auth_status() -> subprocess.CompletedProcess[str]:
    command = ["claude", "auth", "status", "--json"]
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        message = str(exc)
        return subprocess.CompletedProcess(command, returncode=127, stdout="", stderr=message)


def claude_auth_failure(status: subprocess.CompletedProcess[str]) -> subprocess.CompletedProcess[str] | None:
    if status.returncode != 0:
        try:
            payload = json.loads(status.stdout)
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict) and payload.get("loggedIn") is False:
            stdout = (
                "Claude auth status reports loggedIn=false. "
                "Run `claude auth login`, then retry.\n"
                f"{json.dumps(payload, sort_keys=True)}\n"
            )
            return subprocess.CompletedProcess(status.args, returncode=status.returncode, stdout=stdout, stderr=status.stderr)
        return status

    try:
        payload = json.loads(status.stdout)
    except json.JSONDecodeError:
        stdout = "Claude auth status did not return valid JSON.\n"
        return subprocess.CompletedProcess(status.args, returncode=1, stdout=stdout, stderr=status.stderr)

    if not isinstance(payload, dict) or payload.get("loggedIn") is not True:
        stdout = (
            "Claude auth status does not report loggedIn=true. "
            "Run `claude auth login`, then retry.\n"
            f"{status.stdout.strip()}\n"
        )
        return subprocess.CompletedProcess(status.args, returncode=1, stdout=stdout, stderr=status.stderr)

    return None


def check_claude_ready(max_budget_usd: str) -> subprocess.CompletedProcess[str]:
    auth_status = run_claude_auth_status()
    auth_failure = claude_auth_failure(auth_status)
    if auth_failure is not None:
        return auth_failure
    return run_claude(MODEL_PREFLIGHT_PROMPT, max_budget_usd)


def preflight_record_prompt(preflight: subprocess.CompletedProcess[str]) -> str:
    args = list(preflight.args) if isinstance(preflight.args, (list, tuple)) else [preflight.args]
    if args[:4] == ["claude", "auth", "status", "--json"]:
        return AUTH_STATUS_PREFLIGHT_PROMPT
    return MODEL_PREFLIGHT_PROMPT


def write_records(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def load_records(path: Path) -> list[dict]:
    if not path.is_file():
        return []

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


def record_key(record: dict) -> tuple[str, str]:
    return (record["task_id"], record["variant"])


def record_is_resumable(record: dict, expected_record: dict) -> bool:
    if record.get("status") != "ok":
        return False
    for field in ("task_id", "skill", "variant", "context_status", "context_skills", "prompt"):
        if record.get(field) != expected_record.get(field):
            return False
    if not str(record.get("stdout", "")).strip():
        return False
    return True


def record_count_text(count: int) -> str:
    noun = "record" if count == 1 else "records"
    return f"{count} {noun}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--skills-root", type=Path, default=REPO_ROOT / "skills")
    parser.add_argument("--kdense-root", type=Path)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--max-budget-usd", default="0.20")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--task", action="append", help="task id to run; may be passed multiple times")
    parser.add_argument(
        "--variant",
        action="append",
        choices=("baseline", "package-skill", "kdense"),
        help="variant to run; may be passed multiple times",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="skip the one-call Claude auth check before running the full matrix",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="check Claude auth/readiness and exit without writing evaluation records",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="preserve existing result records and skip task/variant pairs with complete current ok records",
    )
    args = parser.parse_args(argv)

    try:
        tasks = filter_tasks(load_tasks(args.tasks), args.task)
    except OSError as exc:
        parser.error(f"cannot load task manifest {args.tasks}: {exc}")
    except ValueError as exc:
        parser.error(str(exc))
    args.results.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing_records = load_records(args.results) if args.resume else []
    except (OSError, ValueError) as exc:
        parser.error(f"cannot load existing results {args.results}: {exc}")
    latest_existing = {record_key(record): record for record in existing_records}

    if args.preflight_only:
        preflight = check_claude_ready(args.max_budget_usd)
        if preflight.returncode == 0:
            print("Claude preflight succeeded.")
            return 0
        print("Claude preflight failed.")
        if preflight.stdout.strip():
            print(preflight.stdout.strip())
        if preflight.stderr.strip():
            print(preflight.stderr.strip())
        return 1

    if not args.dry_run:
        missing_kdense = missing_kdense_context_tasks(tasks, args.kdense_root, args.variant)
        if missing_kdense:
            print(
                "Missing K-Dense skill context for selected task(s): "
                f"{', '.join(missing_kdense)}. Pass --kdense-root with a matching SKILL.md before running real evaluation."
            )
            return 1
    missing_package = missing_package_context_items(tasks, args.skills_root, args.variant)
    if missing_package:
        print(
            "Missing package skill context for selected task/skill(s): "
            f"{', '.join(missing_package)}. Pass --skills-root with matching SKILL.md files."
        )
        return 1

    if not args.dry_run and not args.skip_preflight:
        preflight = check_claude_ready(args.max_budget_usd)
        if preflight.returncode != 0:
            records = [
                {
                    "task_id": "__preflight__",
                    "skill": "",
                    "variant": "preflight",
                    "prompt": preflight_record_prompt(preflight),
                    "status": "error",
                    "returncode": preflight.returncode,
                    "stdout": preflight.stdout,
                    "stderr": preflight.stderr,
                }
            ]
            write_records(args.results, existing_records + records)
            print(f"Claude preflight failed; wrote {record_count_text(len(existing_records) + 1)} to {args.results}")
            return 1

    records: list[dict] = []
    selected_count = 0
    for task in tasks:
        variants = iter_selected_variants(task, args.skills_root, args.kdense_root, args.variant)
        if not variants:
            print(f"No selected variants apply to task {task['id']}")
            continue
        for variant in variants:
            selected_count += 1
            prompt = build_prompt(task, variant)
            record = {
                "task_id": task["id"],
                "skill": task["skill"],
                "variant": variant.name,
                "context_status": variant.context_status,
                "context_skills": list(variant.context_skills),
                "prompt": prompt,
            }
            if args.resume and record_is_resumable(latest_existing.get(record_key(record), {}), record):
                continue
            if args.dry_run:
                record["status"] = "dry-run"
            else:
                result = run_claude(prompt, args.max_budget_usd)
                record.update(
                    {
                        "status": "ok" if result.returncode == 0 else "error",
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }
            )
            records.append(record)
            write_records(args.results, existing_records + records)

    if selected_count == 0:
        write_records(args.results, existing_records)
        print(f"No evaluation records selected; wrote {record_count_text(0)} to {args.results}")
        return 1

    if args.resume and not records:
        write_records(args.results, existing_records)
        print(f"No new records to run; preserved {record_count_text(len(existing_records))} in {args.results}")
        return 0

    output_records = existing_records + records
    write_records(args.results, output_records)
    print(f"Wrote {record_count_text(len(output_records))} to {args.results}")
    if not args.dry_run and any(record.get("status") == "error" for record in records):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

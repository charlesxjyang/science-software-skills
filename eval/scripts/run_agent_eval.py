#!/usr/bin/env python3
"""Run the package-skill evaluation matrix with non-Claude model providers."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

try:
    from eval.scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from eval.scripts.run_claude_eval import (  # noqa: E402
    DEFAULT_TASKS,
    REPO_ROOT,
    build_prompt,
    filter_tasks,
    iter_selected_variants,
    load_records,
    load_tasks,
    missing_kdense_context_tasks,
    missing_package_context_items,
    record_is_resumable,
    write_records,
)


MODEL_PREFLIGHT_PROMPT = "Reply with OK only."
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


def completed(
    args: list[str] | str,
    returncode: int,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


def agent_record_key(record: dict) -> tuple[str, str, str, str]:
    return (
        str(record["task_id"]),
        str(record["variant"]),
        str(record.get("provider", "")),
        str(record.get("model", "")),
    )


def agent_record_is_resumable(record: dict, expected_record: dict) -> bool:
    if not record_is_resumable(record, expected_record):
        return False
    return (
        record.get("provider", "") == expected_record.get("provider", "")
        and record.get("model", "") == expected_record.get("model", "")
    )


def run_codex(prompt: str, model: str | None) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile(prefix="materials-skills-codex-", suffix=".txt", delete=False) as handle:
        output_path = Path(handle.name)
    command = [
        "codex",
        "exec",
        "--cd",
        "/private/tmp",
        "--skip-git-repo-check",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--output-last-message",
        str(output_path),
    ]
    if model:
        command.extend(["--model", model])
    command.append(prompt)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if output_path.is_file():
            final_message = output_path.read_text(encoding="utf-8")
            if final_message.strip():
                return completed(command, result.returncode, final_message, result.stderr)
        return result
    except OSError as exc:
        return completed(command, 127, "", str(exc))
    finally:
        try:
            output_path.unlink()
        except OSError:
            pass


def run_gemini(prompt: str, model: str | None) -> subprocess.CompletedProcess[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    model_name = model or DEFAULT_GEMINI_MODEL
    if not api_key:
        return completed(
            f"gemini-api:{model_name}",
            127,
            "",
            "GEMINI_API_KEY is not set; cannot run Gemini evaluation.",
        )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return completed(f"gemini-api:{model_name}", exc.code, "", body)
    except OSError as exc:
        return completed(f"gemini-api:{model_name}", 127, "", str(exc))

    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError) as exc:
        return completed(f"gemini-api:{model_name}", 1, json.dumps(data), f"Unexpected Gemini response shape: {exc}")
    return completed(f"gemini-api:{model_name}", 0, text, "")


def run_provider(provider: str, prompt: str, model: str | None) -> subprocess.CompletedProcess[str]:
    if provider == "codex":
        return run_codex(prompt, model)
    if provider == "gemini":
        return run_gemini(prompt, model)
    raise ValueError(f"unsupported provider: {provider}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("codex", "gemini"), required=True)
    parser.add_argument("--model", help="optional provider model name")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--skills-root", type=Path, default=REPO_ROOT / "skills")
    parser.add_argument("--kdense-root", type=Path)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--task", action="append", help="task id to run; may be passed multiple times")
    parser.add_argument(
        "--variant",
        action="append",
        choices=("baseline", "package-skill", "kdense"),
        help="variant to run; may be passed multiple times",
    )
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)

    try:
        tasks = filter_tasks(load_tasks(args.tasks), args.task)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    args.results.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing_records = load_records(args.results) if args.resume else []
    except (OSError, ValueError) as exc:
        parser.error(f"cannot load existing results {args.results}: {exc}")
    latest_existing = {agent_record_key(record): record for record in existing_records}

    if args.preflight_only:
        result = run_provider(args.provider, MODEL_PREFLIGHT_PROMPT, args.model)
        if result.returncode == 0:
            print(f"{args.provider} preflight succeeded.")
            return 0
        print(f"{args.provider} preflight failed.")
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
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
        preflight = run_provider(args.provider, MODEL_PREFLIGHT_PROMPT, args.model)
        if preflight.returncode != 0:
            records = [
                {
                    "task_id": "__preflight__",
                    "skill": "",
                    "variant": "preflight",
                    "prompt": MODEL_PREFLIGHT_PROMPT,
                    "status": "error",
                    "returncode": preflight.returncode,
                    "stdout": preflight.stdout,
                    "stderr": preflight.stderr,
                    "provider": args.provider,
                    "model": args.model or "",
                }
            ]
            write_records(args.results, existing_records + records)
            print(f"{args.provider} preflight failed; wrote 1 record to {args.results}")
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
                "provider": args.provider,
                "model": args.model or "",
            }
            if args.resume and agent_record_is_resumable(latest_existing.get(agent_record_key(record), {}), record):
                continue
            if args.dry_run:
                record["status"] = "dry-run"
            else:
                result = run_provider(args.provider, prompt, args.model)
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
        print(f"No evaluation records selected; wrote 0 records to {args.results}")
        return 1
    if args.resume and not records:
        write_records(args.results, existing_records)
        print(f"No new records to run; preserved {len(existing_records)} records in {args.results}")
        return 0

    output_records = existing_records + records
    write_records(args.results, output_records)
    print(f"Wrote {len(output_records)} records to {args.results}")
    if not args.dry_run and any(record.get("status") == "error" for record in records):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

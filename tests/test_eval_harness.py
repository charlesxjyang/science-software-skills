from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eval.scripts.check_eval_artifacts import check_artifacts, main as artifact_main
from eval.scripts.check_eval_completeness import check_results, check_results_file, expected_keys, main as completeness_main
from eval.scripts.report_utils import report_looks_manually_scored
from eval.scripts.run_impedance_pipeline import main as impedance_pipeline_main
from eval.scripts.run_v0_pipeline import main as pipeline_main
from eval.scripts.run_claude_eval import (
    build_prompt,
    filter_tasks,
    filter_variants,
    iter_selected_variants,
    iter_variants,
    kdense_context,
    kdense_context_status,
    load_records,
    load_tasks,
    main,
    missing_kdense_context_tasks,
    record_is_resumable,
    record_key,
    record_count_text,
    task_context_skills,
)
from eval.scripts.check_score_report import check_report, check_report_text, main as score_check_main, task_section
from eval.scripts.score_results import first_text, load_jsonl, main as score_main, render_report
from eval.scripts.optimize_skills import score_results as score_optimization_results, write_report
from materials_skills.registry import REGISTRY


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "eval" / "tasks" / "v0_tasks.json"
EXTENSION_TASKS = ROOT / "eval" / "tasks" / "extension_tasks.json"
IMPEDANCE_TASKS = ROOT / "eval" / "impedance" / "tasks.json"
IMPEDANCE_DRY_RUN_RESULTS = ROOT / "eval" / "impedance" / "dry-run-results.jsonl"
IMPEDANCE_RESULTS = ROOT / "eval" / "impedance" / "results.jsonl"
IMPEDANCE_SCORE_REPORT = ROOT / "eval" / "impedance" / "score-report.md"
FULL_DRY_RUN_RESULTS = ROOT / "eval" / "dry-run-results.jsonl"
FULL_RESULTS = ROOT / "eval" / "results.jsonl"
FULL_SCORE_REPORT = ROOT / "eval" / "score-report.md"
KDENSE_DRY_RUN_RESULTS = ROOT / "eval" / "kdense-dry-run-results.jsonl"
KDENSE_DRY_RUN_SCORE_REPORT = ROOT / "eval" / "kdense-dry-run-score-report.md"
AUTH_PREFLIGHT_RESULTS = ROOT / "eval" / "auth-preflight-results.jsonl"
AUTH_PREFLIGHT_SCORE_REPORT = ROOT / "eval" / "auth-preflight-score-report.md"
AUTH_BLOCKED_RESULTS = ROOT / "eval" / "auth-blocked-results.jsonl"
AUTH_BLOCKED_SCORE_REPORT = ROOT / "eval" / "auth-blocked-score-report.md"
SKILLS_ROOT = ROOT / "skills"


def filled_score_report(tasks: list[dict]) -> str:
    lines = [
        "# Evaluation Score Report",
        "",
        "Manual scoring key: mark each criterion pass/fail after reading outputs.",
        "",
        "## Comparison Summary",
        "",
        "| Task | Baseline | Package Skill | K-Dense | Winner | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for task in tasks:
        kdense = "tie" if task.get("kdense_applicable", False) else "not applicable"
        lines.append(f"| `{task['id']}` | loss | win | {kdense} | package-skill | Filled. |")

    for task in tasks:
        lines.extend(["", f"## {task['id']}: {task['title']}", "", "Criteria:"])
        lines.extend(f"- [x] {criterion}" for criterion in task["success_criteria"])
        lines.append("")
        for variant in ("baseline", "package-skill", "kdense"):
            if variant == "kdense" and not task.get("kdense_applicable", False):
                continue
            outcome = "win" if variant == "package-skill" else "loss"
            if variant == "kdense":
                outcome = "tie"
            context_status = "not-applicable" if variant == "baseline" else "provided"
            if variant == "baseline":
                context_skills = "none"
            elif variant == "package-skill":
                context_skills = ", ".join(task_context_skills(task))
            else:
                context_skills = task["skill"]
            lines.extend(
                [
                    f"### Variant: {variant}",
                    "",
                    "Status: `ok`",
                    "",
                    f"Context status: `{context_status}`",
                    "",
                    f"Context skills: `{context_skills}`",
                    "",
                    "Prompt:",
                    "",
                    "```text",
                    task["prompt"],
                    "```",
                    "",
                    "Output:",
                    "",
                    "```text",
                    "answer",
                    "```",
                    "",
                    f"Outcome: `{outcome}`",
                    "",
                ]
            )
    return "\n".join(lines)


def complete_records(tasks: list[dict]) -> list[dict]:
    task_by_id = {task["id"]: task for task in tasks}
    return [
        {
            "task_id": task_id,
            "skill": task_by_id[task_id]["skill"],
            "variant": variant,
            "context_status": "provided" if variant in {"package-skill", "kdense"} else "not-applicable",
            "context_skills": (
                list(task_context_skills(task_by_id[task_id]))
                if variant == "package-skill"
                else [task_by_id[task_id]["skill"]] if variant == "kdense" else []
            ),
            "status": "ok",
            "stdout": "answer",
            "prompt": "prompt",
        }
        for task_id, variant in expected_keys(tasks)
    ]


class EvalHarnessTests(unittest.TestCase):
    def test_manifest_has_five_tasks(self) -> None:
        tasks = load_tasks(TASKS)
        self.assertEqual(len(tasks), 5)
        self.assertEqual({task["id"] for task in tasks}, {
            "impedance-fit-randles-cpe-warburg",
            "ase-pymatgen-mace-relax",
            "pymatgen-phase-diagram-lifepo4",
            "py4dstem-virtual-image-bragg",
            "openmm-prepare-run-md",
        })

    def test_load_tasks_rejects_malformed_task_objects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([{"id": "bad-task"}]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing required field"):
                load_tasks(manifest)

    def test_load_tasks_rejects_malformed_optional_fields(self) -> None:
        task = {
            "id": "bad-task",
            "skill": "impedance",
            "title": "Bad Task",
            "prompt": "Prompt",
            "success_criteria": ["criterion"],
            "context_skills": "impedance",
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "context_skills"):
                load_tasks(manifest)

    def test_load_tasks_rejects_whitespace_padded_task_identifiers(self) -> None:
        task = {
            "id": "bad-task ",
            "skill": "impedance",
            "title": "Bad Task",
            "prompt": "Prompt",
            "success_criteria": ["criterion"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must not have leading or trailing whitespace"):
                load_tasks(manifest)

    def test_load_tasks_rejects_whitespace_padded_title(self) -> None:
        task = {
            "id": "bad-task",
            "skill": "impedance",
            "title": " Bad Task",
            "prompt": "Prompt",
            "success_criteria": ["criterion"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "title"):
                load_tasks(manifest)

    def test_load_tasks_rejects_whitespace_padded_prompt(self) -> None:
        task = {
            "id": "bad-task",
            "skill": "impedance",
            "title": "Bad Task",
            "prompt": "Prompt ",
            "success_criteria": ["criterion"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "prompt"):
                load_tasks(manifest)

    def test_load_tasks_rejects_unregistered_primary_skill(self) -> None:
        task = {
            "id": "bad-task",
            "skill": "unknown-skill",
            "title": "Bad Task",
            "prompt": "Prompt",
            "success_criteria": ["criterion"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "not registered"):
                load_tasks(manifest)

    def test_load_tasks_rejects_whitespace_padded_context_skills(self) -> None:
        task = {
            "id": "bad-task",
            "skill": "mace",
            "title": "Bad Task",
            "prompt": "Prompt",
            "success_criteria": ["criterion"],
            "context_skills": ["mace", " ase"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must not have leading or trailing whitespace"):
                load_tasks(manifest)

    def test_load_tasks_rejects_unregistered_context_skill(self) -> None:
        task = {
            "id": "bad-task",
            "skill": "mace",
            "title": "Bad Task",
            "prompt": "Prompt",
            "success_criteria": ["criterion"],
            "context_skills": ["mace", "missing-skill"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unregistered skill"):
                load_tasks(manifest)

    def test_load_tasks_rejects_whitespace_padded_success_criteria(self) -> None:
        task = {
            "id": "bad-task",
            "skill": "impedance",
            "title": "Bad Task",
            "prompt": "Prompt",
            "success_criteria": [" criterion"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "success_criteria"):
                load_tasks(manifest)

    def test_load_tasks_rejects_duplicate_success_criteria(self) -> None:
        task = {
            "id": "bad-task",
            "skill": "impedance",
            "title": "Bad Task",
            "prompt": "Prompt",
            "success_criteria": ["criterion", "criterion"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "success_criteria must not contain duplicates"):
                load_tasks(manifest)

    def test_load_tasks_rejects_duplicate_context_skills(self) -> None:
        task = {
            "id": "bad-task",
            "skill": "impedance",
            "title": "Bad Task",
            "prompt": "Prompt",
            "success_criteria": ["criterion"],
            "context_skills": ["impedance", "impedance"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must not contain duplicates"):
                load_tasks(manifest)

    def test_load_tasks_requires_context_skills_to_include_primary_skill(self) -> None:
        task = {
            "id": "bad-task",
            "skill": "mace",
            "title": "Bad Task",
            "prompt": "Prompt",
            "success_criteria": ["criterion"],
            "context_skills": ["ase", "pymatgen"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must include the primary skill"):
                load_tasks(manifest)

    def test_load_tasks_rejects_duplicate_task_ids(self) -> None:
        task = {
            "id": "duplicate-task",
            "skill": "impedance",
            "title": "Duplicate Task",
            "prompt": "Prompt",
            "success_criteria": ["criterion"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "tasks.json"
            manifest.write_text(json.dumps([task, task]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "duplicate task id"):
                load_tasks(manifest)

    def test_each_task_references_existing_skill(self) -> None:
        for task in load_tasks(TASKS):
            self.assertTrue((SKILLS_ROOT / task["skill"] / "SKILL.md").is_file())
            for skill_name in task_context_skills(task):
                self.assertTrue((SKILLS_ROOT / skill_name / "SKILL.md").is_file())
            self.assertGreaterEqual(len(task["success_criteria"]), 5)

    def test_extension_task_manifest_has_hidden_environment_discovery_suite_per_skill(self) -> None:
        tasks = load_tasks(EXTENSION_TASKS)
        by_skill: dict[str, int] = {}
        registry_by_skill = {record.skill_name: record for record in REGISTRY}
        registered = set(registry_by_skill)
        banned_distractors = ("statsmodels", "pyyaml", "tqdm")
        for task in tasks:
            by_skill[task["skill"]] = by_skill.get(task["skill"], 0) + 1
            self.assertEqual(len(task["success_criteria"]), 5)
            self.assertGreaterEqual(len(task["doc_sources"]), 2)
            self.assertGreaterEqual(len(task["rubric_terms"]), 5)
            self.assertTrue(task.get("hide_success_criteria"), task["id"])
            prompt = task["prompt"].lower()
            self.assertIn("available generic python packages", prompt)
            for name in ("numpy", "pandas", "scipy", "scikit-learn", "matplotlib"):
                self.assertIn(name, prompt, task["id"])
            for name in banned_distractors:
                self.assertNotIn(name, prompt, task["id"])
            aliases = {task["skill"], *registry_by_skill[task["skill"]].distributions}
            for alias in aliases:
                pattern = rf"(?<![a-z0-9_]){re.escape(alias.lower())}(?![a-z0-9_])"
                self.assertIsNone(re.search(pattern, prompt), f"{task['id']} exposes {alias!r}")

        self.assertEqual(set(by_skill), registered)
        self.assertEqual(set(by_skill.values()), {3})

    def test_each_registered_skill_has_evaluation_prompts(self) -> None:
        for record in REGISTRY:
            prompts = ROOT / "eval" / record.skill_dir / "prompts.md"
            self.assertTrue(prompts.is_file(), record.skill_name)
            text = prompts.read_text(encoding="utf-8")
            self.assertIn("Prompt", text, record.skill_name)
            self.assertIn("Expected", text, record.skill_name)

    def test_readme_skip_preflight_example_uses_disposable_results(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("--skip-preflight --results /private/tmp/materials-skills-debug-results.jsonl", readme)
        self.assertNotIn("--skip-preflight --results eval/results.jsonl", readme)

    def test_v0_demo_documents_agent_json_field(self) -> None:
        demo = (ROOT / "docs" / "v0-demo.md").read_text(encoding="utf-8")

        self.assertIn("materials-skills install --env tests/fixtures/conda-env.yml --agent all --dry-run --json", demo)
        self.assertIn('"agent": "all"', demo)
        self.assertIn('"targets": [', demo)

    def test_readmes_document_pipeline_json_final_gates(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        eval_readme = (ROOT / "eval" / "README.md").read_text(encoding="utf-8")
        impedance_results = (ROOT / "eval" / "impedance" / "results.md").read_text(encoding="utf-8")
        writeup = (ROOT / "docs" / "writeup.md").read_text(encoding="utf-8")

        self.assertIn("python eval/scripts/run_impedance_pipeline.py --skip-model-run --check-scored --json", readme)
        self.assertIn("python eval/scripts/run_v0_pipeline.py --skip-model-run --check-scored --json", readme)
        self.assertIn("`automation_steps`", readme)
        self.assertIn("`automation_steps`", writeup)
        self.assertIn("same manual-report overwrite guard", readme)
        self.assertIn("direct renderer also refuses to overwrite", eval_readme)
        self.assertIn("direct renderer replaces existing unscored", eval_readme)
        self.assertIn("For automation, add `--json` to that final impedance gate:", eval_readme)
        self.assertIn("unscored dry-run scaffolds are replaced", eval_readme)
        self.assertIn("unscored dry-run scaffolds are replaced", readme)
        self.assertIn("python eval/scripts/run_impedance_pipeline.py \\", eval_readme)
        self.assertIn("For automation, add `--json` to that final gate:", eval_readme)
        self.assertIn("python eval/scripts/run_v0_pipeline.py \\", eval_readme)
        self.assertIn("python eval/scripts/run_impedance_pipeline.py --resume", impedance_results)
        self.assertIn("python eval/scripts/run_impedance_pipeline.py \\", impedance_results)
        self.assertIn("--json", impedance_results)
        self.assertNotIn("PYTHONPATH=src:. python eval/scripts/run_impedance_pipeline.py", impedance_results)

    def test_impedance_manual_task_manifest_has_three_prompts(self) -> None:
        tasks = load_tasks(IMPEDANCE_TASKS)
        prompts_text = (ROOT / "eval" / "impedance" / "prompts.md").read_text(encoding="utf-8")

        self.assertEqual(
            [task["id"] for task in tasks],
            [
                "impedance-fit-randles-cpe-warburg",
                "impedance-validate-before-fitting",
                "impedance-batch-fit-zplot",
            ],
        )
        for task in tasks:
            self.assertEqual(task["skill"], "impedance")
            self.assertTrue((SKILLS_ROOT / task["skill"] / "SKILL.md").is_file())
            self.assertGreaterEqual(len(task["success_criteria"]), 5)
            self.assertIn(task["title"], prompts_text)

    def test_context_skills_support_cross_library_composition(self) -> None:
        tasks = {task["id"]: task for task in load_tasks(TASKS)}
        self.assertEqual(
            task_context_skills(tasks["ase-pymatgen-mace-relax"]),
            ("mace", "ase", "pymatgen"),
        )
        self.assertEqual(task_context_skills(tasks["impedance-fit-randles-cpe-warburg"]), ("impedance",))

    def test_filter_tasks_selects_requested_ids(self) -> None:
        tasks = load_tasks(TASKS)
        selected = filter_tasks(tasks, ["impedance-fit-randles-cpe-warburg"])
        self.assertEqual([task["id"] for task in selected], ["impedance-fit-randles-cpe-warburg"])

    def test_filter_tasks_rejects_unknown_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown task"):
            filter_tasks(load_tasks(TASKS), ["missing-task"])

    def test_runner_reports_missing_task_manifest_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exc:
                    main(["--tasks", str(root / "missing-tasks.json"), "--results", str(root / "results.jsonl")])

            self.assertEqual(exc.exception.code, 2)
            self.assertIn("cannot load task manifest", stderr.getvalue())

    def test_eval_gate_commands_report_missing_task_manifest_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_tasks = root / "missing-tasks.json"
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("", encoding="utf-8")

            commands = [
                (completeness_main, ["--tasks", str(missing_tasks), "--results", str(results)]),
                (score_main, ["--tasks", str(missing_tasks), "--results", str(results), "--report", str(report)]),
                (score_check_main, ["--tasks", str(missing_tasks), "--report", str(report)]),
                (artifact_main, ["--tasks", str(missing_tasks), "--results", str(results), "--report", str(report)]),
            ]
            for command, argv in commands:
                stderr = io.StringIO()
                with self.subTest(command=command.__module__):
                    with contextlib.redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as exc:
                            command(argv)
                    self.assertEqual(exc.exception.code, 2)
                    self.assertIn("cannot load task manifest", stderr.getvalue())

    def test_direct_eval_scripts_bootstrap_repo_import_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_tasks = root / "missing-tasks.json"
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("", encoding="utf-8")
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)
            commands = [
                ["eval/scripts/run_claude_eval.py", "--tasks", str(missing_tasks), "--results", str(results)],
                ["eval/scripts/check_eval_completeness.py", "--tasks", str(missing_tasks), "--results", str(results)],
                ["eval/scripts/score_results.py", "--tasks", str(missing_tasks), "--results", str(results), "--report", str(report)],
                ["eval/scripts/check_score_report.py", "--tasks", str(missing_tasks), "--report", str(report)],
                ["eval/scripts/check_eval_artifacts.py", "--tasks", str(missing_tasks), "--results", str(results), "--report", str(report)],
                ["eval/scripts/run_impedance_pipeline.py", "--tasks", str(missing_tasks)],
                ["eval/scripts/run_v0_pipeline.py", "--tasks", str(missing_tasks)],
            ]
            for command in commands:
                with self.subTest(command=command[0]):
                    result = subprocess.run(
                        [sys.executable, *command],
                        cwd=ROOT,
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    self.assertEqual(result.returncode, 2)
                    self.assertIn("cannot load task manifest", result.stderr)
                    self.assertNotIn("ModuleNotFoundError", result.stderr)

    def test_pipeline_json_final_gates_bootstrap_repo_import_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)
            commands = [
                [
                    "eval/scripts/run_impedance_pipeline.py",
                    "--results",
                    str(root / "missing-impedance-results.jsonl"),
                    "--report",
                    str(root / "missing-impedance-report.md"),
                ],
                [
                    "eval/scripts/run_v0_pipeline.py",
                    "--results",
                    str(root / "missing-v0-results.jsonl"),
                    "--report",
                    str(root / "missing-v0-report.md"),
                ],
            ]
            for command in commands:
                with self.subTest(command=command[0]):
                    result = subprocess.run(
                        [
                            sys.executable,
                            *command,
                            "--skip-model-run",
                            "--check-scored",
                            "--json",
                        ],
                        cwd=ROOT,
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    self.assertEqual(result.returncode, 1)
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["blockers"], ["evaluation", "scoring"])
                    self.assertNotIn("ModuleNotFoundError", result.stderr)
                    self.assertNotIn("Model run skipped", result.stdout)

    def test_iter_variants_adds_kdense_only_when_applicable(self) -> None:
        tasks = {task["id"]: task for task in load_tasks(TASKS)}
        self.assertEqual(
            [variant.name for variant in iter_variants(tasks["impedance-fit-randles-cpe-warburg"], SKILLS_ROOT, None)],
            ["baseline", "package-skill"],
        )
        self.assertEqual(
            [variant.name for variant in iter_variants(tasks["ase-pymatgen-mace-relax"], SKILLS_ROOT, None)],
            ["baseline", "package-skill"],
        )
        self.assertEqual(
            [variant.name for variant in iter_variants(tasks["pymatgen-phase-diagram-lifepo4"], SKILLS_ROOT, None)],
            ["baseline", "package-skill", "kdense"],
        )
        package_variant = iter_variants(tasks["ase-pymatgen-mace-relax"], SKILLS_ROOT, None)[1]
        self.assertEqual(package_variant.context_skills, ("mace", "ase", "pymatgen"))
        self.assertIn("Package Skill: mace", package_variant.context)
        self.assertIn("Package Skill: ase", package_variant.context)
        self.assertIn("Package Skill: pymatgen", package_variant.context)
        kdense_variant = iter_variants(tasks["pymatgen-phase-diagram-lifepo4"], SKILLS_ROOT, ROOT / "eval" / "kdense-public")[2]
        self.assertEqual(kdense_variant.context_skills, ("pymatgen",))

    def test_filter_variants_selects_requested_names(self) -> None:
        task = load_tasks(TASKS)[0]
        variants = iter_variants(task, SKILLS_ROOT, None)
        self.assertEqual([variant.name for variant in filter_variants(variants, ["package-skill"])], ["package-skill"])

    def test_kdense_context_reads_skill_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / "pymatgen"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("K-Dense pymatgen fixture", encoding="utf-8")
            self.assertEqual(kdense_context("pymatgen", root), "K-Dense pymatgen fixture")
            self.assertEqual(kdense_context_status("pymatgen", root), "provided")

    def test_kdense_public_fixture_documents_matching_hash(self) -> None:
        fixture = ROOT / "eval" / "kdense-public" / "pymatgen" / "SKILL.md"
        readme = (ROOT / "eval" / "kdense-public" / "README.md").read_text(encoding="utf-8")
        digest = hashlib.sha256(fixture.read_bytes()).hexdigest()

        self.assertIn("https://github.com/K-Dense-AI/claude-scientific-skills", readme)
        self.assertIn("MIT", readme)
        self.assertIn(digest, readme)

    def test_pymatgen_research_note_points_to_prepared_kdense_comparison(self) -> None:
        tasks = {task["id"]: task for task in load_tasks(TASKS)}
        note = (ROOT / "research" / "pymatgen.md").read_text(encoding="utf-8")

        self.assertTrue(tasks["pymatgen-phase-diagram-lifepo4"]["kdense_applicable"])
        self.assertIn("eval/kdense-public/pymatgen/SKILL.md", note)
        self.assertIn("pymatgen-phase-diagram-lifepo4", note)

    def test_kdense_context_reports_missing_root(self) -> None:
        self.assertIn("not provided", kdense_context("pymatgen", None))
        self.assertEqual(kdense_context_status("pymatgen", None), "missing")

    def test_missing_kdense_context_only_applies_to_selected_kdense_variants(self) -> None:
        tasks = load_tasks(TASKS)
        self.assertEqual(missing_kdense_context_tasks(tasks, None, None), ["pymatgen-phase-diagram-lifepo4"])
        self.assertEqual(missing_kdense_context_tasks(tasks, None, ["baseline", "package-skill"]), [])
        self.assertEqual(missing_kdense_context_tasks(tasks, ROOT / "eval" / "kdense-public", None), [])

    def test_build_prompt_includes_criteria(self) -> None:
        task = load_tasks(TASKS)[0]
        variant = iter_variants(task, SKILLS_ROOT, None)[1]
        prompt = build_prompt(task, variant)
        self.assertIn(task["prompt"], prompt)
        self.assertIn("Evaluation Criteria", prompt)
        self.assertIn("CustomCircuit", prompt)
        self.assertIn("impedance.py", prompt)

    def test_manifest_is_plain_json(self) -> None:
        with TASKS.open(encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertIsInstance(data, list)

    def test_expected_keys_match_eval_matrix(self) -> None:
        keys = expected_keys(load_tasks(TASKS))
        self.assertEqual(len(keys), 11)
        self.assertIn(("pymatgen-phase-diagram-lifepo4", "kdense"), keys)
        self.assertNotIn(("impedance-fit-randles-cpe-warburg", "kdense"), keys)

    def test_check_results_accepts_complete_ok_outputs(self) -> None:
        tasks = load_tasks(TASKS)
        task_by_id = {task["id"]: task for task in tasks}
        records = [
            {
                "task_id": task_id,
                "skill": task_by_id[task_id]["skill"],
                "variant": variant,
                "context_status": "provided" if variant in {"package-skill", "kdense"} else "not-applicable",
                "context_skills": (
                    list(task_context_skills(task_by_id[task_id]))
                    if variant == "package-skill"
                    else [task_by_id[task_id]["skill"]] if variant == "kdense" else []
                ),
                "status": "ok",
                "stdout": "answer",
                "prompt": "prompt",
            }
            for task_id, variant in expected_keys(tasks)
        ]
        payload = check_results(tasks, records)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["expected_count"], 11)
        self.assertEqual(payload["complete_count"], 11)
        self.assertEqual(payload["problems"], [])

    def test_check_results_rejects_wrong_or_missing_skill_metadata(self) -> None:
        tasks = load_tasks(TASKS)
        records = complete_records(tasks)
        records[0]["skill"] = "rdkit"
        del records[1]["skill"]

        payload = check_results(tasks, records)

        self.assertFalse(payload["ok"])
        problem_text = "\n".join(payload["problems"])
        self.assertIn("skill is 'rdkit', expected 'impedance'", problem_text)
        self.assertIn("skill is 'missing'", problem_text)

    def test_check_results_rejects_missing_prompt_metadata(self) -> None:
        tasks = load_tasks(TASKS)
        records = complete_records(tasks)
        del records[0]["prompt"]

        payload = check_results(tasks, records)

        self.assertFalse(payload["ok"])
        self.assertIn("missing prompt", "\n".join(payload["problems"]))

    def test_check_results_rejects_missing_context_for_skill_variants(self) -> None:
        tasks = load_tasks(TASKS)
        task_by_id = {task["id"]: task for task in tasks}
        records = [
            {
                "task_id": task_id,
                "skill": task_by_id[task_id]["skill"],
                "variant": variant,
                "context_status": "provided" if variant in {"package-skill", "kdense"} else "not-applicable",
                "context_skills": (
                    list(task_context_skills(task_by_id[task_id]))
                    if variant == "package-skill"
                    else [task_by_id[task_id]["skill"]] if variant == "kdense" else []
                ),
                "status": "ok",
                "stdout": "answer",
                "prompt": "prompt",
            }
            for task_id, variant in expected_keys(tasks)
        ]
        for record in records:
            if record["variant"] == "kdense":
                record["context_status"] = "missing"
                break
        payload = check_results(tasks, records)
        self.assertFalse(payload["ok"])
        self.assertIn("context_status is 'missing'", "\n".join(payload["problems"]))

    def test_check_results_file_reports_missing_results_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing-results.jsonl"
        payload = check_results_file(load_tasks(TASKS), missing)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["expected_count"], 11)
        self.assertEqual(payload["complete_count"], 0)
        self.assertEqual(payload["record_count"], 0)
        self.assertIn("missing results file", "\n".join(payload["problems"]))

    def test_load_jsonl_reports_malformed_result_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "ok", "variant": "baseline", "status": "ok"}) + "\n{not json}\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "results.jsonl:2: invalid JSON"):
                load_jsonl(results)

    def test_check_results_file_reports_malformed_results_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text("{not json}\n", encoding="utf-8")
            payload = check_results_file(load_tasks(TASKS), results)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["expected_count"], 11)
        self.assertEqual(payload["complete_count"], 0)
        self.assertIn("invalid results file", "\n".join(payload["problems"]))

    def test_load_jsonl_rejects_result_records_missing_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(json.dumps({"task_id": "task-a", "status": "ok"}) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing required field"):
                load_jsonl(results)

    def test_load_jsonl_rejects_whitespace_padded_result_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "task-a ", "variant": "baseline", "status": "ok"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "must not have leading or trailing whitespace"):
                load_jsonl(results)

    def test_load_jsonl_rejects_unknown_result_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "task-a", "variant": "baseline", "status": "success"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "status"):
                load_jsonl(results)

    def test_load_jsonl_rejects_unknown_result_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "task-a", "variant": "experimental", "status": "ok"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "variant"):
                load_jsonl(results)

    def test_load_jsonl_requires_preflight_sentinel_pair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "task-a", "variant": "preflight", "status": "error"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "__preflight__"):
                load_jsonl(results)

            results.write_text(
                json.dumps({"task_id": "__preflight__", "variant": "baseline", "status": "error"}) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "preflight"):
                load_jsonl(results)

    def test_load_jsonl_requires_preflight_status_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "__preflight__", "variant": "preflight", "status": "ok"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "status 'error'"):
                load_jsonl(results)

    def test_load_jsonl_rejects_preflight_context_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": "__preflight__",
                        "variant": "preflight",
                        "status": "error",
                        "context_status": "provided",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "context metadata"):
                load_jsonl(results)

    def test_load_jsonl_rejects_malformed_context_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "variant": "package-skill",
                        "status": "ok",
                        "context_status": " provided",
                        "context_skills": ["impedance"],
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "task_id": "task-b",
                        "variant": "package-skill",
                        "status": "ok",
                        "context_status": "provided",
                        "context_skills": "impedance",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "context_status"):
                load_jsonl(results)

            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-d",
                        "variant": "package-skill",
                        "status": "ok",
                        "context_status": "provided",
                        "context_skills": ["missing-skill"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unregistered skill"):
                load_jsonl(results)

            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-b",
                        "variant": "package-skill",
                        "status": "ok",
                        "context_status": "provided",
                        "context_skills": "impedance",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "context_skills"):
                load_jsonl(results)

            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-c",
                        "variant": "package-skill",
                        "status": "ok",
                        "context_status": "loaded",
                        "context_skills": ["impedance"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "context_status"):
                load_jsonl(results)

    def test_load_jsonl_rejects_malformed_output_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "variant": "baseline",
                        "status": "ok",
                        "stdout": ["not", "text"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "stdout"):
                load_jsonl(results)

            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "variant": "baseline",
                        "status": "ok",
                        "stdout": "answer",
                        "returncode": "0",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "returncode"):
                load_jsonl(results)

            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "variant": "baseline",
                        "status": "ok",
                        "stdout": "answer",
                        "returncode": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "requires returncode 0"):
                load_jsonl(results)

            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "variant": "baseline",
                        "status": "error",
                        "stderr": "failed",
                        "returncode": 0,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "requires nonzero returncode"):
                load_jsonl(results)

    def test_load_jsonl_rejects_malformed_skill_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "variant": "baseline",
                        "status": "ok",
                        "skill": "missing-skill",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "not registered"):
                load_jsonl(results)

            results.write_text(
                json.dumps(
                    {
                        "task_id": "__preflight__",
                        "variant": "preflight",
                        "status": "error",
                        "skill": "impedance",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "empty skill"):
                load_jsonl(results)

    def test_check_results_rejects_wrong_package_context_skills(self) -> None:
        tasks = load_tasks(TASKS)
        task_by_id = {task["id"]: task for task in tasks}
        records = [
            {
                "task_id": task_id,
                "skill": task_by_id[task_id]["skill"],
                "variant": variant,
                "context_status": "provided" if variant in {"package-skill", "kdense"} else "not-applicable",
                "context_skills": (
                    list(task_context_skills(task_by_id[task_id]))
                    if variant == "package-skill"
                    else [task_by_id[task_id]["skill"]] if variant == "kdense" else []
                ),
                "status": "ok",
                "stdout": "answer",
                "prompt": "prompt",
            }
            for task_id, variant in expected_keys(tasks)
        ]
        for record in records:
            if record["task_id"] == "ase-pymatgen-mace-relax" and record["variant"] == "package-skill":
                record["context_skills"] = ["mace"]
                break
        payload = check_results(tasks, records)
        self.assertFalse(payload["ok"])
        self.assertIn("context_skills is ['mace']", "\n".join(payload["problems"]))
        self.assertIn("expected ['mace', 'ase', 'pymatgen']", "\n".join(payload["problems"]))

    def test_check_results_rejects_baseline_records_with_loaded_context(self) -> None:
        tasks = load_tasks(TASKS)
        records = complete_records(tasks)
        baseline_records = [record for record in records if record["variant"] == "baseline"]
        baseline_records[0]["context_status"] = "provided"
        baseline_records[1]["context_skills"] = [tasks[1]["skill"]]

        payload = check_results(tasks, records)

        self.assertFalse(payload["ok"])
        problem_text = "\n".join(payload["problems"])
        self.assertIn("baseline", problem_text)
        self.assertIn("context_status is 'provided', expected 'not-applicable'", problem_text)
        self.assertIn("context_skills is ['mace'], expected []", problem_text)

    def test_check_results_rejects_baseline_records_without_context_skill_metadata(self) -> None:
        tasks = load_tasks(TASKS)
        records = complete_records(tasks)
        baseline = next(record for record in records if record["variant"] == "baseline")
        del baseline["context_skills"]

        payload = check_results(tasks, records)

        self.assertFalse(payload["ok"])
        self.assertIn("context_skills is 'missing', expected []", "\n".join(payload["problems"]))

    def test_check_results_rejects_wrong_kdense_context_skills(self) -> None:
        tasks = load_tasks(TASKS)
        task_by_id = {task["id"]: task for task in tasks}
        records = [
            {
                "task_id": task_id,
                "skill": task_by_id[task_id]["skill"],
                "variant": variant,
                "context_status": "provided" if variant in {"package-skill", "kdense"} else "not-applicable",
                "context_skills": (
                    list(task_context_skills(task_by_id[task_id]))
                    if variant == "package-skill"
                    else [task_by_id[task_id]["skill"]] if variant == "kdense" else []
                ),
                "status": "ok",
                "stdout": "answer",
                "prompt": "prompt",
            }
            for task_id, variant in expected_keys(tasks)
        ]
        for record in records:
            if record["variant"] == "kdense":
                record["context_skills"] = []
                break
        payload = check_results(tasks, records)
        self.assertFalse(payload["ok"])
        self.assertIn("pymatgen-phase-diagram-lifepo4:kdense", "\n".join(payload["problems"]))
        self.assertIn("expected ['pymatgen']", "\n".join(payload["problems"]))

    def test_check_results_rejects_dry_run_missing_and_preflight(self) -> None:
        tasks = load_tasks(TASKS)
        records = [
            {
                "task_id": tasks[0]["id"],
                "variant": "baseline",
                "status": "dry-run",
                "stdout": "",
            },
            {
                "task_id": "__preflight__",
                "variant": "preflight",
                "status": "error",
                "stdout": "Not logged in",
            },
        ]
        payload = check_results(tasks, records)
        self.assertFalse(payload["ok"])
        self.assertIn("status is 'dry-run'", "\n".join(payload["problems"]))
        self.assertIn("missing result", "\n".join(payload["problems"]))
        self.assertIn("unexpected record", "\n".join(payload["problems"]))

    def test_check_results_uses_latest_duplicate_record(self) -> None:
        task_id = "impedance-fit-randles-cpe-warburg"
        records = [
            {"task_id": task_id, "variant": "baseline", "status": "error", "stdout": "old"},
            {
                "task_id": task_id,
                "skill": "impedance",
                "variant": "baseline",
                "status": "ok",
                "stdout": "new",
                "prompt": "prompt",
                "context_status": "not-applicable",
                "context_skills": [],
            },
        ]
        payload = check_results(load_tasks(TASKS)[:1], records)
        self.assertFalse(payload["ok"])
        self.assertNotIn("baseline", "\n".join(payload["problems"]))
        self.assertIn("package-skill", "\n".join(payload["problems"]))

    def test_score_report_marks_dry_run(self) -> None:
        tasks = load_tasks(TASKS)
        records = [
            {
                "task_id": tasks[0]["id"],
                "skill": tasks[0]["skill"],
                "variant": "baseline",
                "status": "dry-run",
            }
        ]
        report = render_report(tasks[:1], records)
        self.assertIn("Evaluation Score Report", report)
        self.assertIn("replace each `not-scored` placeholder with `win`, `tie`, `loss`, or `blocked`", report)
        self.assertIn("Comparison Summary", report)
        self.assertIn("| `impedance-fit-randles-cpe-warburg` | not-scored | not-scored | not applicable |", report)
        self.assertIn("Variant: baseline", report)
        self.assertIn("Dry run only", report)
        self.assertIn("Context status: `unknown`", report)
        self.assertIn("Context skills: `none`", report)
        self.assertIn("Outcome: `not-scored`", report)
        self.assertIn("Allowed outcomes: `win`, `tie`, `loss`, or `blocked`", report)

    def test_score_report_uses_latest_duplicate_task_variant_record(self) -> None:
        tasks = load_tasks(TASKS)[:1]
        task = tasks[0]
        report = render_report(
            tasks,
            [
                {
                    "task_id": task["id"],
                    "skill": task["skill"],
                    "variant": "baseline",
                    "status": "error",
                    "stdout": "old error",
                },
                {
                    "task_id": task["id"],
                    "skill": task["skill"],
                    "variant": "baseline",
                    "status": "ok",
                    "stdout": "new answer",
                },
            ],
        )

        self.assertIn("new answer", report)
        self.assertNotIn("old error", report)
        self.assertEqual(report.count("### Variant: baseline"), 1)

    def test_score_report_output_markdown_does_not_create_sections(self) -> None:
        tasks = load_tasks(TASKS)[:1]
        task = tasks[0]
        report = render_report(
            tasks,
            [
                {
                    "task_id": task["id"],
                    "skill": task["skill"],
                    "variant": "baseline",
                    "status": "ok",
                    "stdout": "```python\nprint('hi')\n```\n### Variant: baseline\n| `impedance-fit-randles-cpe-warburg` |",
                }
            ],
        )

        self.assertIn("````text", report)
        payload = check_report_text(report, tasks)
        problem_text = "\n".join(payload["problems"])
        self.assertNotIn("duplicate variant sections", problem_text)
        self.assertNotIn("duplicate comparison summary rows", problem_text)

    def test_score_report_summary_marks_kdense_applicable_task(self) -> None:
        tasks = [task for task in load_tasks(TASKS) if task["kdense_applicable"]]
        report = render_report(tasks, [])
        self.assertIn("| `pymatgen-phase-diagram-lifepo4` | not-scored | not-scored | not-scored |", report)

    def test_score_report_error_uses_stdout_when_stderr_is_empty(self) -> None:
        text = first_text({"status": "error", "stdout": "Not logged in", "stderr": ""})
        self.assertIn("Not logged in", text)

    def test_score_report_includes_preflight_record(self) -> None:
        tasks = load_tasks(TASKS)
        report = render_report(
            tasks[:1],
            [
                {
                    "task_id": "__preflight__",
                    "skill": "",
                    "variant": "preflight",
                    "status": "error",
                    "stdout": "Not logged in",
                    "stderr": "",
                }
            ],
        )
        self.assertIn("Preflight And Unmatched Records", report)
        self.assertIn("Task ID: `__preflight__`", report)
        self.assertIn("Not logged in", report)

    def test_score_renderer_reports_missing_results_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing-results.jsonl"
            report = root / "score-report.md"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = score_main(["--results", str(missing), "--report", str(report)])

            self.assertEqual(exit_code, 1)
            self.assertFalse(report.exists())
            self.assertIn("missing results file", stderr.getvalue())

    def test_score_renderer_refuses_to_overwrite_manually_scored_report(self) -> None:
        tasks = load_tasks(TASKS)[:1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            scored_report = filled_score_report(tasks)
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            report.write_text(scored_report, encoding="utf-8")
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                exit_code = score_main([
                    "--tasks",
                    str(TASKS),
                    "--results",
                    str(results),
                    "--report",
                    str(report),
                ])

            self.assertEqual(exit_code, 1)
            self.assertEqual(report.read_text(encoding="utf-8"), scored_report)
            self.assertIn("refusing to overwrite manually scored report", stderr.getvalue())

    def test_score_renderer_overwrite_report_replaces_manually_scored_report(self) -> None:
        tasks = load_tasks(TASKS)[:1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            report.write_text(filled_score_report(tasks), encoding="utf-8")

            exit_code = score_main([
                "--tasks",
                str(TASKS),
                "--results",
                str(results),
                "--report",
                str(report),
                "--overwrite-report",
            ])

            self.assertEqual(exit_code, 0)
            self.assertIn("Outcome: `not-scored`", report.read_text(encoding="utf-8"))

    def test_score_renderer_replaces_existing_unscored_report_scaffold(self) -> None:
        tasks = load_tasks(TASKS)[:1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            report.write_text("stale scaffold\nOutcome: `not-scored`\n- [ ] criterion\n", encoding="utf-8")

            exit_code = score_main([
                "--tasks",
                str(TASKS),
                "--results",
                str(results),
                "--report",
                str(report),
            ])

            self.assertEqual(exit_code, 0)
            self.assertNotIn("stale scaffold", report.read_text(encoding="utf-8"))
            self.assertIn("Evaluation Score Report", report.read_text(encoding="utf-8"))

    def test_score_report_gate_rejects_unfilled_template(self) -> None:
        tasks = load_tasks(TASKS)
        report = render_report(
            tasks[:1],
            [
                {
                    "task_id": tasks[0]["id"],
                    "skill": tasks[0]["skill"],
                    "variant": "baseline",
                    "status": "dry-run",
                }
            ],
        )
        payload = check_report_text(report)
        self.assertFalse(payload["ok"])
        self.assertIn("Outcome: `not-scored`", "\n".join(payload["problems"]))
        self.assertIn("- [ ] ", "\n".join(payload["problems"]))

    def test_score_report_gate_accepts_filled_report(self) -> None:
        tasks = load_tasks(TASKS)
        self.assertTrue(check_report_text(filled_score_report(tasks), tasks)["ok"])

    def test_score_report_gate_rejects_missing_variant_audit_fields(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace("Output:\n\n```text\nanswer\n```\n\n", "", 1)

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg:baseline: missing output field",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_missing_prompt_block(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace(f"Prompt:\n\n```text\n{task['prompt']}\n```\n\n", "", 1)

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg:baseline: missing prompt field",
            "\n".join(payload["problems"]),
        )
        self.assertIn(
            "impedance-fit-randles-cpe-warburg:baseline: missing fenced prompt block",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_prompt_mismatch(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace(task["prompt"], "Different prompt", 1)

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg:baseline: prompt block does not include the task manifest prompt",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_empty_output_block(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace("```text\nanswer\n```", "```text\n\n```", 1)

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg:baseline: empty output block",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_non_ok_variant_status(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace("Status: `ok`", "Status: `dry-run`", 1)

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg:baseline: status field must be `ok`",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_context_audit_field_mismatch(self) -> None:
        task = next(item for item in load_tasks(TASKS) if item["id"] == "ase-pymatgen-mace-relax")
        report = filled_score_report([task]).replace(
            "Context skills: `mace, ase, pymatgen`",
            "Context skills: `mace`",
            1,
        )

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        self.assertIn(
            "ase-pymatgen-mace-relax:package-skill: context skills are 'mace', expected 'mace, ase, pymatgen'",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_unparseable_context_audit_fields(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace(
            "Context status: `not-applicable`",
            "Context status: not-applicable",
            1,
        )

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg:baseline: context status is '', expected 'not-applicable'",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_ignores_unfilled_markers_inside_model_output_fences(self) -> None:
        tasks = load_tasks(TASKS)[:1]
        report = (
            filled_score_report(tasks)
            + "\n\n```text\n"
            + "Model-provided checklist:\n"
            + "- [ ] user-facing item, not a scoring checkbox\n"
            + "Outcome: `not-scored` appears in generated prose\n"
            + "```\n"
        )

        self.assertTrue(check_report_text(report, tasks)["ok"])

    def test_score_report_gate_rejects_missing_task_and_variant_sections(self) -> None:
        report = """# Evaluation Score Report

Manual scoring key: mark each criterion pass/fail after reading outputs.

## Comparison Summary

| Task | Baseline | Package Skill | K-Dense | Winner | Notes |
| --- | --- | --- | --- | --- | --- |
| `impedance-fit-randles-cpe-warburg` | loss | win | not applicable | package-skill | Package skill used impedance.py. |

## impedance-fit-randles-cpe-warburg: Fit EIS Spectrum With Equivalent Circuit

### Variant: baseline

Outcome: `loss`
"""
        payload = check_report_text(report, load_tasks(TASKS))
        self.assertFalse(payload["ok"])
        problem_text = "\n".join(payload["problems"])
        self.assertIn("impedance-fit-randles-cpe-warburg:package-skill: missing variant section", problem_text)
        self.assertIn("ase-pymatgen-mace-relax: missing comparison summary row", problem_text)
        self.assertIn("ase-pymatgen-mace-relax: missing task section", problem_text)

    def test_score_report_gate_rejects_duplicate_variant_sections(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace(
            "### Variant: package-skill",
            "### Variant: baseline\n\nOutcome: `loss`\n\n### Variant: package-skill",
            1,
        )
        payload = check_report_text(report, [task])
        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg:baseline: duplicate variant sections (2)",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_unexpected_variant_sections(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]) + "\n### Variant: experimental\n\nOutcome: `win`\n"

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg:experimental: unexpected variant section",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_duplicate_task_sections_and_summary_rows(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task])
        summary_row = next(line for line in report.splitlines() if line.startswith("| `impedance-fit-randles-cpe-warburg` |"))
        report = report.replace(summary_row, summary_row + "\n" + summary_row)
        task_header = "## impedance-fit-randles-cpe-warburg: Fit EIS Spectrum With Equivalent Circuit"
        report = report + "\n" + report[report.index(task_header):]

        payload = check_report_text(report, [task])
        self.assertFalse(payload["ok"])
        problem_text = "\n".join(payload["problems"])
        self.assertIn("impedance-fit-randles-cpe-warburg: duplicate comparison summary rows (2)", problem_text)
        self.assertIn("impedance-fit-randles-cpe-warburg: duplicate task sections (2)", problem_text)

    def test_score_report_gate_rejects_unexpected_task_sections_and_summary_rows(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task])
        summary_row = next(line for line in report.splitlines() if line.startswith("| `impedance-fit-randles-cpe-warburg` |"))
        report = report.replace(
            summary_row,
            summary_row + "\n| `unexpected-task` | win | win | not applicable | tie | Extra. |",
        )
        report += "\n## unexpected-task: Extra Task\n\n### Variant: baseline\n\nOutcome: `win`\n"

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        problem_text = "\n".join(payload["problems"])
        self.assertIn("unexpected-task: unexpected comparison summary row", problem_text)
        self.assertIn("unexpected-task: Extra Task: unexpected task section", problem_text)

    def test_score_report_gate_requires_summary_row_in_summary_section(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task])
        summary_row = next(line for line in report.splitlines() if line.startswith("| `impedance-fit-randles-cpe-warburg` |"))
        report = report.replace(summary_row + "\n", "", 1)
        report += "\n\nReviewer scratch table:\n" + summary_row + "\n"

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg: missing comparison summary row",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_requires_summary_table_header_in_summary_section(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task])
        header = "| Task | Baseline | Package Skill | K-Dense | Winner | Notes |"
        report = report.replace(header + "\n", "", 1)
        report += "\n\nReviewer scratch table:\n" + header + "\n"

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        self.assertIn("missing comparison summary table", "\n".join(payload["problems"]))

    def test_score_report_gate_rejects_duplicate_summary_sections(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]) + "\n## Comparison Summary\n\n"

        payload = check_report_text(report, [task])

        self.assertFalse(payload["ok"])
        self.assertIn("duplicate comparison summary sections (2)", "\n".join(payload["problems"]))

    def test_score_report_gate_rejects_invalid_scored_values(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace("| loss | win |", "| maybe | win |").replace(
            "Outcome: `loss`", "Outcome: `maybe`", 1
        )
        payload = check_report_text(report, [task])
        self.assertFalse(payload["ok"])
        problem_text = "\n".join(payload["problems"])
        self.assertIn("invalid summary outcome 'maybe'", problem_text)
        self.assertIn("invalid outcome 'maybe'", problem_text)

    def test_score_report_gate_rejects_summary_variant_outcome_mismatch(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace("| loss | win |", "| win | win |", 1)
        payload = check_report_text(report, [task])
        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg:baseline: summary outcome 'win' does not match variant outcome 'loss'",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_winner_without_win_outcome(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace("| loss | win | not applicable | package-skill |", "| loss | tie | not applicable | package-skill |")
        payload = check_report_text(report, [task])
        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg: winner 'package-skill' has summary outcome 'tie', expected 'win'",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_inapplicable_kdense_winner(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace("| loss | win | not applicable | package-skill |", "| loss | win | not applicable | kdense |")
        payload = check_report_text(report, [task])
        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg: winner 'kdense' is not applicable for this task",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_tie_winner_without_tied_outcomes(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace("| loss | win | not applicable | package-skill |", "| loss | win | not applicable | tie |")
        payload = check_report_text(report, [task])
        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg: winner 'tie' requires all applicable summary outcomes to match and not be blocked",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_blocked_winner_without_all_blocked_outcomes(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace("| loss | win | not applicable | package-skill |", "| blocked | win | not applicable | blocked |")
        payload = check_report_text(report, [task])
        self.assertFalse(payload["ok"])
        self.assertIn(
            "impedance-fit-randles-cpe-warburg: winner 'blocked' requires all applicable summary outcomes to be blocked",
            "\n".join(payload["problems"]),
        )

    def test_score_report_gate_rejects_missing_checked_criteria(self) -> None:
        task = load_tasks(TASKS)[0]
        report = filled_score_report([task]).replace("[x]", "[ ]", 1)
        payload = check_report_text(report, [task])
        self.assertFalse(payload["ok"])
        problem_text = "\n".join(payload["problems"])
        self.assertIn("found 1 unfilled marker(s): '- [ ] '", problem_text)
        self.assertIn("missing checked criterion", problem_text)

    def test_task_section_returns_single_task_block(self) -> None:
        tasks = load_tasks(TASKS)
        report = render_report(tasks[:2], [])
        section = task_section(report, tasks[0])
        self.assertIn("## impedance-fit-randles-cpe-warburg", section)
        self.assertNotIn("## ase-pymatgen-mace-relax", section)

    def test_score_report_gate_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = check_report(Path(tmp) / "missing.md")
        self.assertFalse(payload["ok"])
        self.assertIn("missing score report", "\n".join(payload["problems"]))

    def test_combined_artifact_gate_accepts_complete_artifacts(self) -> None:
        tasks = load_tasks(TASKS)
        records = complete_records(tasks)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report_path = root / "score-report.md"
            results.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
            report_path.write_text(filled_score_report(tasks), encoding="utf-8")
            payload = check_artifacts(TASKS, results, report_path)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["blockers"], [])
        self.assertTrue(payload["evaluation"]["ok"])
        self.assertTrue(payload["scoring"]["ok"])

    def test_v0_pipeline_stops_when_preflight_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            smoke_results = root / "smoke.jsonl"
            report = root / "score-report.md"
            stdout = io.StringIO()
            with patch("eval.scripts.run_v0_pipeline.run_eval_main", return_value=1) as run_eval:
                with contextlib.redirect_stdout(stdout):
                    exit_code = pipeline_main([
                        "--results",
                        str(results),
                        "--report",
                        str(report),
                        "--smoke-results",
                        str(smoke_results),
                    ])
            self.assertEqual(exit_code, 1)
            self.assertEqual(run_eval.call_count, 1)
            self.assertFalse(results.exists())
            self.assertFalse(smoke_results.exists())
            self.assertFalse(report.exists())
            self.assertIn("Run `claude auth login`", stdout.getvalue())

    def test_v0_pipeline_writes_score_report_after_complete_model_run(self) -> None:
        tasks = load_tasks(TASKS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            with patch("eval.scripts.run_v0_pipeline.run_eval_main", return_value=0) as run_eval:
                exit_code = pipeline_main([
                    "--results",
                    str(results),
                    "--report",
                    str(report),
                    "--smoke-results",
                    str(root / "smoke.jsonl"),
                ])
            self.assertEqual(exit_code, 0)
            self.assertEqual(run_eval.call_count, 3)
            self.assertIn("Evaluation Score Report", report.read_text(encoding="utf-8"))

    def test_v0_pipeline_replaces_existing_unscored_report_scaffold(self) -> None:
        tasks = load_tasks(TASKS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            report.write_text("stale scaffold\nOutcome: `not-scored`\n- [ ] criterion\n", encoding="utf-8")
            with patch("eval.scripts.run_v0_pipeline.run_eval_main", return_value=0):
                exit_code = pipeline_main([
                    "--results",
                    str(results),
                    "--report",
                    str(report),
                    "--smoke-results",
                    str(root / "smoke.jsonl"),
                ])

            self.assertEqual(exit_code, 0)
            self.assertNotIn("stale scaffold", report.read_text(encoding="utf-8"))
            self.assertIn("Evaluation Score Report", report.read_text(encoding="utf-8"))

    def test_v0_pipeline_reports_missing_results_after_nominal_model_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "score-report.md"
            stdout = io.StringIO()
            with (
                patch("eval.scripts.run_v0_pipeline.run_eval_main", return_value=0),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pipeline_main([
                    "--results",
                    str(root / "missing-results.jsonl"),
                    "--report",
                    str(report),
                    "--smoke-results",
                    str(root / "smoke.jsonl"),
                ])

            self.assertEqual(exit_code, 1)
            self.assertFalse(report.exists())
            self.assertIn("missing results file", stdout.getvalue())

    def test_v0_pipeline_refuses_to_overwrite_manually_scored_report(self) -> None:
        tasks = load_tasks(TASKS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            scored_report = filled_score_report(tasks)
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            report.write_text(scored_report, encoding="utf-8")
            with patch("eval.scripts.run_v0_pipeline.run_eval_main", return_value=0):
                exit_code = pipeline_main([
                    "--results",
                    str(results),
                    "--report",
                    str(report),
                    "--smoke-results",
                    str(root / "smoke.jsonl"),
                ])

            self.assertEqual(exit_code, 1)
            self.assertEqual(report.read_text(encoding="utf-8"), scored_report)

    def test_pipeline_manual_score_detector_ignores_fenced_model_output_markers(self) -> None:
        tasks = load_tasks(TASKS)[:1]
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "score-report.md"
            scored_report = filled_score_report(tasks).replace(
                "```text\nanswer\n```",
                "```text\nThe model output mentions a literal checklist:\n- [ ] item\nOutcome: `not-scored`\n```",
                1,
            )
            report.write_text(scored_report, encoding="utf-8")

            self.assertTrue(report_looks_manually_scored(report))

    def test_v0_pipeline_overwrite_report_allows_replacing_scored_report(self) -> None:
        tasks = load_tasks(TASKS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            report.write_text(filled_score_report(tasks), encoding="utf-8")
            with patch("eval.scripts.run_v0_pipeline.run_eval_main", return_value=0):
                exit_code = pipeline_main([
                    "--results",
                    str(results),
                    "--report",
                    str(report),
                    "--smoke-results",
                    str(root / "smoke.jsonl"),
                    "--overwrite-report",
                ])

            self.assertEqual(exit_code, 0)
            self.assertIn("Outcome: `not-scored`", report.read_text(encoding="utf-8"))

    def test_v0_pipeline_check_scored_uses_existing_artifacts_without_model_calls(self) -> None:
        tasks = load_tasks(TASKS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            report.write_text(filled_score_report(tasks), encoding="utf-8")
            with patch("eval.scripts.run_v0_pipeline.run_eval_main") as run_eval:
                exit_code = pipeline_main([
                    "--skip-model-run",
                    "--check-scored",
                    "--results",
                    str(results),
                    "--report",
                    str(report),
                ])
            self.assertEqual(exit_code, 0)
            run_eval.assert_not_called()

    def test_v0_pipeline_check_scored_prints_blockers_for_incomplete_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "score-report.md"
            report.write_text(render_report(load_tasks(TASKS)[:1], []), encoding="utf-8")
            stdout = io.StringIO()
            with (
                patch("eval.scripts.run_v0_pipeline.run_eval_main") as run_eval,
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pipeline_main([
                    "--skip-model-run",
                    "--check-scored",
                    "--results",
                    str(root / "missing-results.jsonl"),
                    "--report",
                    str(report),
                ])

            self.assertEqual(exit_code, 1)
            run_eval.assert_not_called()
            self.assertIn("blockers: evaluation, scoring", stdout.getvalue())

    def test_v0_pipeline_check_scored_json_uses_existing_artifacts_without_model_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "score-report.md"
            report.write_text(render_report(load_tasks(TASKS)[:1], []), encoding="utf-8")
            stdout = io.StringIO()
            with (
                patch("eval.scripts.run_v0_pipeline.run_eval_main") as run_eval,
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pipeline_main([
                    "--skip-model-run",
                    "--check-scored",
                    "--json",
                    "--results",
                    str(root / "missing-results.jsonl"),
                    "--report",
                    str(report),
                ])

            self.assertEqual(exit_code, 1)
            run_eval.assert_not_called()
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["blockers"], ["evaluation", "scoring"])

    def test_v0_pipeline_check_scored_requires_skip_model_run(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                pipeline_main(["--check-scored"])
        self.assertEqual(exc.exception.code, 2)

    def test_v0_pipeline_skip_model_run_requires_check_scored(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                pipeline_main(["--skip-model-run"])
        self.assertEqual(exc.exception.code, 2)

    def test_v0_pipeline_json_requires_final_scored_gate(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                pipeline_main(["--json"])
        self.assertEqual(exc.exception.code, 2)

    def test_v0_pipeline_reports_missing_task_manifest_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exc:
                    pipeline_main(["--tasks", str(root / "missing-tasks.json")])

            self.assertEqual(exc.exception.code, 2)
            self.assertIn("cannot load task manifest", stderr.getvalue())

    def test_impedance_pipeline_stops_when_preflight_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            stdout = io.StringIO()
            with patch("eval.scripts.run_impedance_pipeline.run_eval_main", return_value=1) as run_eval:
                with contextlib.redirect_stdout(stdout):
                    exit_code = impedance_pipeline_main([
                        "--results",
                        str(results),
                        "--report",
                        str(report),
                    ])

            self.assertEqual(exit_code, 1)
            self.assertEqual(run_eval.call_count, 1)
            self.assertFalse(results.exists())
            self.assertFalse(report.exists())
            self.assertIn("Run `claude auth login`", stdout.getvalue())

    def test_impedance_pipeline_writes_score_report_after_complete_model_run(self) -> None:
        tasks = load_tasks(IMPEDANCE_TASKS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            with patch("eval.scripts.run_impedance_pipeline.run_eval_main", return_value=0) as run_eval:
                exit_code = impedance_pipeline_main([
                    "--results",
                    str(results),
                    "--report",
                    str(report),
                ])

            self.assertEqual(exit_code, 0)
            self.assertEqual(run_eval.call_count, 2)
            self.assertIn("Evaluation Score Report", report.read_text(encoding="utf-8"))

    def test_impedance_pipeline_replaces_existing_unscored_report_scaffold(self) -> None:
        tasks = load_tasks(IMPEDANCE_TASKS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            report.write_text("stale scaffold\nOutcome: `not-scored`\n- [ ] criterion\n", encoding="utf-8")
            with patch("eval.scripts.run_impedance_pipeline.run_eval_main", return_value=0):
                exit_code = impedance_pipeline_main([
                    "--results",
                    str(results),
                    "--report",
                    str(report),
                ])

            self.assertEqual(exit_code, 0)
            self.assertNotIn("stale scaffold", report.read_text(encoding="utf-8"))
            self.assertIn("Evaluation Score Report", report.read_text(encoding="utf-8"))

    def test_impedance_pipeline_reports_missing_results_after_nominal_model_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "score-report.md"
            stdout = io.StringIO()
            with (
                patch("eval.scripts.run_impedance_pipeline.run_eval_main", return_value=0),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = impedance_pipeline_main([
                    "--results",
                    str(root / "missing-results.jsonl"),
                    "--report",
                    str(report),
                ])

            self.assertEqual(exit_code, 1)
            self.assertFalse(report.exists())
            self.assertIn("missing results file", stdout.getvalue())

    def test_impedance_pipeline_refuses_to_overwrite_manually_scored_report(self) -> None:
        tasks = load_tasks(IMPEDANCE_TASKS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            scored_report = filled_score_report(tasks)
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            report.write_text(scored_report, encoding="utf-8")
            with patch("eval.scripts.run_impedance_pipeline.run_eval_main", return_value=0):
                exit_code = impedance_pipeline_main([
                    "--results",
                    str(results),
                    "--report",
                    str(report),
                ])

            self.assertEqual(exit_code, 1)
            self.assertEqual(report.read_text(encoding="utf-8"), scored_report)

    def test_impedance_pipeline_overwrite_report_allows_replacing_scored_report(self) -> None:
        tasks = load_tasks(IMPEDANCE_TASKS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            report.write_text(filled_score_report(tasks), encoding="utf-8")
            with patch("eval.scripts.run_impedance_pipeline.run_eval_main", return_value=0):
                exit_code = impedance_pipeline_main([
                    "--results",
                    str(results),
                    "--report",
                    str(report),
                    "--overwrite-report",
                ])

            self.assertEqual(exit_code, 0)
            self.assertIn("Outcome: `not-scored`", report.read_text(encoding="utf-8"))

    def test_impedance_pipeline_check_scored_uses_existing_artifacts_without_model_calls(self) -> None:
        tasks = load_tasks(IMPEDANCE_TASKS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            report = root / "score-report.md"
            results.write_text("\n".join(json.dumps(record) for record in complete_records(tasks)) + "\n", encoding="utf-8")
            report.write_text(filled_score_report(tasks), encoding="utf-8")
            with patch("eval.scripts.run_impedance_pipeline.run_eval_main") as run_eval:
                exit_code = impedance_pipeline_main([
                    "--skip-model-run",
                    "--check-scored",
                    "--results",
                    str(results),
                    "--report",
                    str(report),
                ])

            self.assertEqual(exit_code, 0)
            run_eval.assert_not_called()

    def test_impedance_pipeline_check_scored_prints_blockers_for_incomplete_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "score-report.md"
            report.write_text(render_report(load_tasks(IMPEDANCE_TASKS)[:1], []), encoding="utf-8")
            stdout = io.StringIO()
            with (
                patch("eval.scripts.run_impedance_pipeline.run_eval_main") as run_eval,
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = impedance_pipeline_main([
                    "--skip-model-run",
                    "--check-scored",
                    "--results",
                    str(root / "missing-results.jsonl"),
                    "--report",
                    str(report),
                ])

            self.assertEqual(exit_code, 1)
            run_eval.assert_not_called()
            self.assertIn("blockers: evaluation, scoring", stdout.getvalue())

    def test_impedance_pipeline_check_scored_json_uses_existing_artifacts_without_model_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "score-report.md"
            report.write_text(render_report(load_tasks(IMPEDANCE_TASKS)[:1], []), encoding="utf-8")
            stdout = io.StringIO()
            with (
                patch("eval.scripts.run_impedance_pipeline.run_eval_main") as run_eval,
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = impedance_pipeline_main([
                    "--skip-model-run",
                    "--check-scored",
                    "--json",
                    "--results",
                    str(root / "missing-results.jsonl"),
                    "--report",
                    str(report),
                ])

            self.assertEqual(exit_code, 1)
            run_eval.assert_not_called()
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["blockers"], ["evaluation", "scoring"])

    def test_impedance_pipeline_check_scored_requires_skip_model_run(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                impedance_pipeline_main(["--check-scored"])
        self.assertEqual(exc.exception.code, 2)

    def test_impedance_pipeline_skip_model_run_requires_check_scored(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                impedance_pipeline_main(["--skip-model-run"])
        self.assertEqual(exc.exception.code, 2)

    def test_impedance_pipeline_json_requires_final_scored_gate(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                impedance_pipeline_main(["--json"])
        self.assertEqual(exc.exception.code, 2)

    def test_impedance_pipeline_reports_missing_task_manifest_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exc:
                    impedance_pipeline_main(["--tasks", str(root / "missing-tasks.json")])

            self.assertEqual(exc.exception.code, 2)
            self.assertIn("cannot load task manifest", stderr.getvalue())

    def test_combined_artifact_gate_reports_both_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "score-report.md"
            report_path.write_text(render_report(load_tasks(TASKS)[:1], []), encoding="utf-8")
            payload = check_artifacts(TASKS, root / "missing-results.jsonl", report_path)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["blockers"], ["evaluation", "scoring"])
        self.assertIn("missing results file", "\n".join(payload["evaluation"]["problems"]))
        self.assertIn("not-scored", "\n".join(payload["scoring"]["problems"]))

    def test_combined_artifact_gate_text_output_prints_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "score-report.md"
            report_path.write_text(render_report(load_tasks(TASKS)[:1], []), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = artifact_main([
                    "--results",
                    str(root / "missing-results.jsonl"),
                    "--report",
                    str(report_path),
                ])

        self.assertEqual(exit_code, 1)
        self.assertIn("blockers: evaluation, scoring", stdout.getvalue())

    def test_load_records_and_record_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "task-a", "variant": "baseline", "status": "ok"}) + "\n",
                encoding="utf-8",
            )
            records = load_records(results)
            self.assertEqual(len(records), 1)
            self.assertEqual(record_key(records[0]), ("task-a", "baseline"))

    def test_load_records_rejects_malformed_resume_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text("{not json}\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                load_records(results)

    def test_load_records_rejects_whitespace_padded_resume_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "task-a", "variant": "baseline ", "status": "ok"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "must not have leading or trailing whitespace"):
                load_records(results)

    def test_load_records_rejects_unknown_resume_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "task-a", "variant": "baseline", "status": "success"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "status"):
                load_records(results)

    def test_load_records_rejects_unknown_resume_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "task-a", "variant": "experimental", "status": "ok"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "variant"):
                load_records(results)

    def test_load_records_requires_preflight_sentinel_pair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "task-a", "variant": "preflight", "status": "error"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "__preflight__"):
                load_records(results)

    def test_load_records_requires_preflight_status_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps({"task_id": "__preflight__", "variant": "preflight", "status": "ok"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "status 'error'"):
                load_records(results)

    def test_load_records_rejects_preflight_context_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": "__preflight__",
                        "variant": "preflight",
                        "status": "error",
                        "context_skills": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "context metadata"):
                load_records(results)

    def test_load_records_rejects_malformed_resume_context_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "variant": "package-skill",
                        "status": "ok",
                        "context_status": "provided",
                        "context_skills": ["impedance", "impedance"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "must not contain duplicates"):
                load_records(results)

            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-b",
                        "variant": "package-skill",
                        "status": "ok",
                        "context_status": "loaded",
                        "context_skills": ["impedance"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "context_status"):
                load_records(results)

            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-c",
                        "variant": "package-skill",
                        "status": "ok",
                        "context_status": "provided",
                        "context_skills": ["missing-skill"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unregistered skill"):
                load_records(results)

    def test_load_records_rejects_malformed_resume_output_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "variant": "baseline",
                        "status": "ok",
                        "stderr": ["not", "text"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "stderr"):
                load_records(results)

            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "variant": "baseline",
                        "status": "ok",
                        "stdout": "answer",
                        "returncode": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "requires returncode 0"):
                load_records(results)

    def test_load_records_rejects_malformed_resume_skill_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "variant": "baseline",
                        "status": "ok",
                        "skill": " impedance",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "skill"):
                load_records(results)

    def test_resume_reports_malformed_existing_results_without_preflight(self) -> None:
        failed = subprocess.CompletedProcess(
            args=["claude"],
            returncode=1,
            stdout="",
            stderr="Not logged in",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(json.dumps({"task_id": "task-a", "status": "ok"}) + "\n", encoding="utf-8")
            stderr = io.StringIO()
            with (
                patch("eval.scripts.run_claude_eval.check_claude_ready", return_value=failed) as check_ready,
                contextlib.redirect_stderr(stderr),
            ):
                with self.assertRaises(SystemExit) as exc:
                    main(["--results", str(results), "--resume"])

            self.assertEqual(exc.exception.code, 2)
            check_ready.assert_not_called()
            self.assertIn("cannot load existing results", stderr.getvalue())

    def test_record_count_text(self) -> None:
        self.assertEqual(record_count_text(0), "0 records")
        self.assertEqual(record_count_text(1), "1 record")
        self.assertEqual(record_count_text(2), "2 records")

    def test_record_is_resumable_requires_current_complete_metadata(self) -> None:
        task = load_tasks(TASKS)[0]
        variant = iter_selected_variants(task, SKILLS_ROOT, None, ["baseline"])[0]
        expected = {
            "task_id": task["id"],
            "skill": task["skill"],
            "variant": variant.name,
            "context_status": variant.context_status,
            "context_skills": list(variant.context_skills),
            "prompt": build_prompt(task, variant),
        }
        complete = {
            **expected,
            "status": "ok",
            "returncode": 0,
            "stdout": "answer",
            "stderr": "",
        }

        self.assertTrue(record_is_resumable(complete, expected))

        missing_prompt = {**complete}
        missing_prompt.pop("prompt")
        self.assertFalse(record_is_resumable(missing_prompt, expected))

        stale_prompt = {**complete, "prompt": "old prompt"}
        self.assertFalse(record_is_resumable(stale_prompt, expected))

        missing_stdout = {**complete, "stdout": ""}
        self.assertFalse(record_is_resumable(missing_stdout, expected))

    def test_non_dry_run_fails_fast_when_preflight_fails(self) -> None:
        failed = subprocess.CompletedProcess(
            args=["claude"],
            returncode=1,
            stdout="",
            stderr="Not logged in",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            with (
                patch("eval.scripts.run_claude_eval.check_claude_ready", return_value=failed),
                patch("eval.scripts.run_claude_eval.run_claude") as run_claude,
            ):
                exit_code = main([
                    "--results",
                    str(results),
                    "--kdense-root",
                    str(ROOT / "eval" / "kdense-public"),
                ])
            self.assertEqual(exit_code, 1)
            run_claude.assert_not_called()
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["task_id"], "__preflight__")
            self.assertEqual(records[0]["variant"], "preflight")
            self.assertEqual(records[0]["status"], "error")
            self.assertEqual(records[0]["prompt"], "Reply with OK only.")

    def test_non_dry_run_auth_status_failure_records_auth_check_prompt(self) -> None:
        failed = subprocess.CompletedProcess(
            args=["claude", "auth", "status", "--json"],
            returncode=1,
            stdout=(
                "Claude auth status reports loggedIn=false. "
                "Run `claude auth login`, then retry.\n"
            ),
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            with (
                patch("eval.scripts.run_claude_eval.check_claude_ready", return_value=failed),
                patch("eval.scripts.run_claude_eval.run_claude") as run_claude,
            ):
                exit_code = main([
                    "--results",
                    str(results),
                    "--kdense-root",
                    str(ROOT / "eval" / "kdense-public"),
                ])

            self.assertEqual(exit_code, 1)
            run_claude.assert_not_called()
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(records[0]["task_id"], "__preflight__")
            self.assertEqual(records[0]["prompt"], "claude auth status --json")

    def test_preflight_failure_preserves_existing_records_with_resume(self) -> None:
        failed = subprocess.CompletedProcess(
            args=["claude"],
            returncode=1,
            stdout="",
            stderr="Not logged in",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": "impedance-fit-randles-cpe-warburg",
                        "skill": "impedance",
                        "variant": "baseline",
                        "status": "ok",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with patch("eval.scripts.run_claude_eval.check_claude_ready", return_value=failed):
                exit_code = main([
                    "--results",
                    str(results),
                    "--resume",
                    "--kdense-root",
                    str(ROOT / "eval" / "kdense-public"),
                ])
            self.assertEqual(exit_code, 1)
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["variant"], "baseline")
            self.assertEqual(records[1]["task_id"], "__preflight__")

    def test_preflight_only_success_does_not_write_results(self) -> None:
        ok = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout="OK\n",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            output = io.StringIO()
            with (
                patch("eval.scripts.run_claude_eval.check_claude_ready", return_value=ok),
                patch("eval.scripts.run_claude_eval.run_claude") as run_claude,
                contextlib.redirect_stdout(output),
            ):
                exit_code = main(["--results", str(results), "--preflight-only"])
            self.assertEqual(exit_code, 0)
            self.assertFalse(results.exists())
            run_claude.assert_not_called()
            self.assertIn("preflight succeeded", output.getvalue())

    def test_preflight_only_checks_auth_status_before_model_probe(self) -> None:
        logged_out = subprocess.CompletedProcess(
            args=["claude", "auth", "status", "--json"],
            returncode=1,
            stdout=json.dumps({"loggedIn": False, "authMethod": "none", "apiProvider": "firstParty"}),
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            output = io.StringIO()
            with (
                patch("eval.scripts.run_claude_eval.run_claude_auth_status", return_value=logged_out),
                patch("eval.scripts.run_claude_eval.run_claude") as run_claude,
                contextlib.redirect_stdout(output),
            ):
                exit_code = main(["--results", str(results), "--preflight-only"])

            self.assertEqual(exit_code, 1)
            self.assertFalse(results.exists())
            run_claude.assert_not_called()
            self.assertIn("loggedIn=false", output.getvalue())
            self.assertIn("claude auth login", output.getvalue())

    def test_preflight_only_runs_model_probe_after_auth_status_success(self) -> None:
        logged_in = subprocess.CompletedProcess(
            args=["claude", "auth", "status", "--json"],
            returncode=0,
            stdout=json.dumps({"loggedIn": True, "authMethod": "oauth", "apiProvider": "firstParty"}),
            stderr="",
        )
        ok = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout="OK\n",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            with (
                patch("eval.scripts.run_claude_eval.run_claude_auth_status", return_value=logged_in),
                patch("eval.scripts.run_claude_eval.run_claude", return_value=ok) as run_claude,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--results", str(results), "--preflight-only"])

            self.assertEqual(exit_code, 0)
            self.assertFalse(results.exists())
            run_claude.assert_called_once_with("Reply with OK only.", "0.20")

    def test_preflight_only_failure_does_not_write_results(self) -> None:
        failed = subprocess.CompletedProcess(
            args=["claude"],
            returncode=1,
            stdout="",
            stderr="Not logged in",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            output = io.StringIO()
            with (
                patch("eval.scripts.run_claude_eval.check_claude_ready", return_value=failed),
                contextlib.redirect_stdout(output),
            ):
                exit_code = main(["--results", str(results), "--preflight-only"])
            self.assertEqual(exit_code, 1)
            self.assertFalse(results.exists())
            self.assertIn("preflight failed", output.getvalue())
            self.assertIn("Not logged in", output.getvalue())

    def test_preflight_only_reports_missing_claude_cli_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            output = io.StringIO()
            with (
                patch("eval.scripts.run_claude_eval.subprocess.run", side_effect=FileNotFoundError("claude")),
                contextlib.redirect_stdout(output),
            ):
                exit_code = main(["--results", str(results), "--preflight-only"])

            self.assertEqual(exit_code, 1)
            self.assertFalse(results.exists())
            self.assertIn("Claude preflight failed", output.getvalue())
            self.assertIn("claude", output.getvalue())

    def test_skip_preflight_runs_matrix(self) -> None:
        ok = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout="answer",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            with (
                patch("eval.scripts.run_claude_eval.check_claude_ready") as check_ready,
                patch("eval.scripts.run_claude_eval.run_claude", return_value=ok),
            ):
                exit_code = main([
                    "--results",
                    str(results),
                    "--skip-preflight",
                    "--kdense-root",
                    str(ROOT / "eval" / "kdense-public"),
                ])
            self.assertEqual(exit_code, 0)
            check_ready.assert_not_called()
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 11)
            self.assertTrue(all(record["status"] == "ok" for record in records))

    def test_skip_preflight_records_missing_claude_cli_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            with patch("eval.scripts.run_claude_eval.subprocess.run", side_effect=FileNotFoundError("claude")):
                exit_code = main(
                    [
                        "--results",
                        str(results),
                        "--skip-preflight",
                        "--task",
                        "impedance-fit-randles-cpe-warburg",
                        "--variant",
                        "baseline",
                    ]
                )

            self.assertEqual(exit_code, 1)
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["status"], "error")
            self.assertEqual(records[0]["returncode"], 127)
            self.assertIn("claude", records[0]["stderr"])

    def test_non_dry_run_requires_kdense_context_before_model_calls(self) -> None:
        ok = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout="answer",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            output = io.StringIO()
            with (
                patch("eval.scripts.run_claude_eval.check_claude_ready") as check_ready,
                patch("eval.scripts.run_claude_eval.run_claude", return_value=ok) as run_claude,
                contextlib.redirect_stdout(output),
            ):
                exit_code = main(["--results", str(results), "--skip-preflight"])
            self.assertEqual(exit_code, 1)
            self.assertFalse(results.exists())
            check_ready.assert_not_called()
            run_claude.assert_not_called()
            self.assertIn("Missing K-Dense skill context", output.getvalue())

    def test_non_dry_run_can_run_package_skill_filter_without_kdense_root(self) -> None:
        ok = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout="answer",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            with patch("eval.scripts.run_claude_eval.run_claude", return_value=ok) as run_claude:
                exit_code = main(
                    [
                        "--results",
                        str(results),
                        "--skip-preflight",
                        "--task",
                        "pymatgen-phase-diagram-lifepo4",
                        "--variant",
                        "package-skill",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(run_claude.call_count, 1)
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(records[0]["variant"], "package-skill")

    def test_package_skill_missing_context_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "--dry-run",
                        "--results",
                        str(results),
                        "--skills-root",
                        str(root / "missing-skills"),
                        "--task",
                        "impedance-fit-randles-cpe-warburg",
                        "--variant",
                        "package-skill",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertFalse(results.exists())
            self.assertIn("Missing package skill context", output.getvalue())
            self.assertIn("impedance-fit-randles-cpe-warburg:impedance", output.getvalue())

    def test_baseline_filter_does_not_require_package_skill_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            exit_code = main(
                [
                    "--dry-run",
                    "--results",
                    str(results),
                    "--skills-root",
                    str(root / "missing-skills"),
                    "--task",
                    "impedance-fit-randles-cpe-warburg",
                    "--variant",
                    "baseline",
                ]
            )

            self.assertEqual(exit_code, 0)
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["variant"], "baseline")
            self.assertEqual(records[0]["context_status"], "not-applicable")
            self.assertEqual(records[0]["context_skills"], [])

    def test_task_and_variant_filter_runs_single_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            exit_code = main(
                [
                    "--dry-run",
                    "--results",
                    str(results),
                    "--task",
                    "impedance-fit-randles-cpe-warburg",
                    "--variant",
                    "package-skill",
                ]
            )
            self.assertEqual(exit_code, 0)
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["task_id"], "impedance-fit-randles-cpe-warburg")
            self.assertEqual(records[0]["variant"], "package-skill")
            self.assertEqual(records[0]["context_status"], "provided")
            self.assertEqual(records[0]["context_skills"], ["impedance"])

    def test_impedance_manual_manifest_dry_run_writes_six_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            exit_code = main(
                [
                    "--tasks",
                    str(IMPEDANCE_TASKS),
                    "--dry-run",
                    "--results",
                    str(results),
                ]
            )

            self.assertEqual(exit_code, 0)
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 6)
            self.assertEqual({record["variant"] for record in records}, {"baseline", "package-skill"})
            self.assertEqual({tuple(record["context_skills"]) for record in records if record["variant"] == "package-skill"}, {("impedance",)})

    def test_committed_impedance_dry_run_artifact_matches_manifest(self) -> None:
        tasks = load_tasks(IMPEDANCE_TASKS)
        records = load_jsonl(IMPEDANCE_DRY_RUN_RESULTS)
        payload = check_results(tasks, records)

        self.assertEqual(len(records), 6)
        self.assertEqual(payload["expected_count"], 6)
        self.assertEqual(payload["complete_count"], 0)
        self.assertFalse(payload["ok"])
        self.assertEqual({record["status"] for record in records}, {"dry-run"})
        self.assertEqual({record["variant"] for record in records}, {"baseline", "package-skill"})
        self.assertEqual({tuple(record["context_skills"]) for record in records if record["variant"] == "package-skill"}, {("impedance",)})

    def test_committed_full_dry_run_artifact_matches_manifest(self) -> None:
        tasks = load_tasks(TASKS)
        records = load_jsonl(FULL_DRY_RUN_RESULTS)
        payload = check_results(tasks, records)

        self.assertEqual(len(records), 11)
        self.assertEqual(payload["expected_count"], 11)
        self.assertEqual(payload["complete_count"], 0)
        self.assertFalse(payload["ok"])
        self.assertEqual({record["status"] for record in records}, {"dry-run"})
        self.assertEqual({record_key(record) for record in records}, set(expected_keys(tasks)))
        for record in records:
            task = next(item for item in tasks if item["id"] == record["task_id"])
            if record["variant"] == "baseline":
                self.assertEqual(record["context_status"], "not-applicable")
                self.assertEqual(record["context_skills"], [])
            elif record["variant"] == "package-skill":
                self.assertEqual(record["context_status"], "provided")
                self.assertEqual(record["context_skills"], list(task_context_skills(task)))
            else:
                self.assertEqual(record["variant"], "kdense")
                self.assertEqual(record["context_status"], "provided")
                self.assertEqual(record["context_skills"], [task["skill"]])

    def test_committed_kdense_dry_run_artifact_matches_manifest(self) -> None:
        tasks = load_tasks(TASKS)
        records = load_jsonl(KDENSE_DRY_RUN_RESULTS)
        payload = check_results(tasks, records)

        self.assertEqual(len(records), 11)
        self.assertEqual(payload["expected_count"], 11)
        self.assertEqual(payload["complete_count"], 0)
        self.assertFalse(payload["ok"])
        self.assertEqual({record["status"] for record in records}, {"dry-run"})
        self.assertEqual({record_key(record) for record in records}, set(expected_keys(tasks)))
        kdense = next(record for record in records if record["variant"] == "kdense")
        self.assertEqual(kdense["task_id"], "pymatgen-phase-diagram-lifepo4")
        self.assertEqual(kdense["context_status"], "provided")
        self.assertEqual(kdense["context_skills"], ["pymatgen"])
        self.assertIn("Pymatgen - Python Materials Genomics", kdense["prompt"])

    def test_committed_auth_preflight_artifact_is_sentinel_only(self) -> None:
        records = load_jsonl(AUTH_PREFLIGHT_RESULTS)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["task_id"], "__preflight__")
        self.assertEqual(records[0]["variant"], "preflight")
        self.assertEqual(records[0]["status"], "error")
        self.assertIn("loggedIn=false", records[0]["stdout"])
        self.assertIn("claude auth login", records[0]["stdout"])

    def test_committed_auth_blocked_artifact_matches_manifest(self) -> None:
        tasks = load_tasks(TASKS)
        records = load_jsonl(AUTH_BLOCKED_RESULTS)
        payload = check_results(tasks, records)

        self.assertEqual(len(records), 11)
        self.assertEqual(payload["expected_count"], 11)
        self.assertEqual(payload["complete_count"], 0)
        self.assertFalse(payload["ok"])
        self.assertEqual({record_key(record) for record in records}, set(expected_keys(tasks)))
        self.assertEqual({record["status"] for record in records}, {"error"})
        self.assertEqual({record["returncode"] for record in records}, {1})
        self.assertTrue(all("Not logged in" in record["stdout"] for record in records))
        task_by_id = {task["id"]: task for task in tasks}
        for record in records:
            task = task_by_id[record["task_id"]]
            if record["variant"] == "baseline":
                self.assertEqual(record["context_status"], "not-applicable")
                self.assertEqual(record["context_skills"], [])
            elif record["variant"] == "package-skill":
                self.assertEqual(record["context_status"], "provided")
                self.assertEqual(record["context_skills"], list(task_context_skills(task)))
            else:
                self.assertEqual(record["variant"], "kdense")
                self.assertEqual(record["context_status"], "provided")
                self.assertEqual(record["context_skills"], [task["skill"]])

    def test_impedance_artifact_gate_reports_six_expected_records_when_results_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = check_results_file(load_tasks(IMPEDANCE_TASKS), Path(tmp) / "missing-results.jsonl")

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["expected_count"], 6)
        self.assertEqual(payload["complete_count"], 0)
        self.assertIn("missing results file", "\n".join(payload["problems"]))

    def test_committed_impedance_artifacts_are_complete_and_scored(self) -> None:
        tasks = load_tasks(IMPEDANCE_TASKS)
        report = IMPEDANCE_SCORE_REPORT.read_text(encoding="utf-8")
        completeness = check_results_file(tasks, IMPEDANCE_RESULTS)
        scoring = check_report_text(report, tasks)

        self.assertTrue(completeness["ok"], completeness["problems"])
        self.assertEqual(completeness["complete_count"], 6)
        self.assertTrue(scoring["ok"], scoring["problems"])
        self.assertIn("| `impedance-fit-randles-cpe-warburg` | loss | win |", report)
        self.assertIn("| `impedance-batch-fit-zplot` | loss | win |", report)

    def test_committed_full_artifacts_are_complete_and_scored(self) -> None:
        tasks = load_tasks(TASKS)
        report = FULL_SCORE_REPORT.read_text(encoding="utf-8")
        completeness = check_results_file(tasks, FULL_RESULTS)
        scoring = check_report_text(report, tasks)

        self.assertTrue(completeness["ok"], completeness["problems"])
        self.assertEqual(completeness["complete_count"], 11)
        self.assertTrue(scoring["ok"], scoring["problems"])
        self.assertIn("| `ase-pymatgen-mace-relax` | win | loss |", report)
        self.assertIn("| `pymatgen-phase-diagram-lifepo4` | win | tie | loss | baseline |", report)

    def test_optimizer_scores_results_and_writes_promotion_audit(self) -> None:
        task = next(task for task in load_tasks(EXTENSION_TASKS) if task["skill"] == "matminer")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": task["id"],
                        "skill": task["skill"],
                        "variant": "package-skill",
                        "status": "ok",
                        "stdout": (
                            "matminer Composition ElementProperty magpie featurize_dataframe "
                            "feature_labels train_test_split leakage citations NaN version"
                        ),
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            scored = score_optimization_results([task], results, "matminer", "original", "train")
            write_report(
                root,
                [scored],
                [
                    {
                        "skill": "matminer",
                        "selected": "original",
                        "reason": "dev passed",
                        "promote": "original",
                        "promotion_reason": "no heldout regression",
                    }
                ],
            )

            self.assertEqual(scored.score, 1.0)
            report = (root / "report.md").read_text(encoding="utf-8")
            self.assertIn("promote `original` because no heldout regression", report)
            self.assertIn("Candidates are accepted using train/dev only", report)

    def test_committed_generated_score_reports_match_source_results(self) -> None:
        tasks = load_tasks(TASKS)
        fixtures = (
            (KDENSE_DRY_RUN_RESULTS, KDENSE_DRY_RUN_SCORE_REPORT),
            (AUTH_PREFLIGHT_RESULTS, AUTH_PREFLIGHT_SCORE_REPORT),
            (AUTH_BLOCKED_RESULTS, AUTH_BLOCKED_SCORE_REPORT),
        )

        for results_path, report_path in fixtures:
            with self.subTest(report=report_path.name):
                records = load_jsonl(results_path)
                report = report_path.read_text(encoding="utf-8")

                self.assertEqual(report, render_report(tasks, records))

    def test_resume_skips_existing_ok_records(self) -> None:
        ok = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout="answer",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            task = load_tasks(TASKS)[0]
            variant = iter_selected_variants(task, SKILLS_ROOT, None, ["baseline"])[0]
            existing = {
                "task_id": task["id"],
                "skill": task["skill"],
                "variant": variant.name,
                "context_status": variant.context_status,
                "context_skills": list(variant.context_skills),
                "prompt": build_prompt(task, variant),
                "status": "ok",
                "returncode": 0,
                "stdout": "existing",
                "stderr": "",
            }
            results.write_text(json.dumps(existing) + "\n", encoding="utf-8")
            with patch("eval.scripts.run_claude_eval.run_claude", return_value=ok) as run_claude:
                exit_code = main(
                    [
                        "--results",
                        str(results),
                        "--task",
                        "impedance-fit-randles-cpe-warburg",
                        "--skip-preflight",
                        "--resume",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(run_claude.call_count, 1)
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["stdout"], "existing")
            self.assertEqual(records[1]["variant"], "package-skill")

    def test_resume_reruns_stale_ok_records_missing_gate_metadata(self) -> None:
        ok = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout="answer",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            existing = {
                "task_id": "impedance-fit-randles-cpe-warburg",
                "skill": "impedance",
                "variant": "baseline",
                "status": "ok",
                "stdout": "old answer",
            }
            results.write_text(json.dumps(existing) + "\n", encoding="utf-8")
            with patch("eval.scripts.run_claude_eval.run_claude", return_value=ok) as run_claude:
                exit_code = main(
                    [
                        "--results",
                        str(results),
                        "--task",
                        "impedance-fit-randles-cpe-warburg",
                        "--variant",
                        "baseline",
                        "--skip-preflight",
                        "--resume",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(run_claude.call_count, 1)
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([record["status"] for record in records], ["ok", "ok"])
            self.assertEqual(records[0]["stdout"], "old answer")
            self.assertEqual(records[1]["stdout"], "answer")
            self.assertIn("prompt", records[1])
            self.assertEqual(records[1]["context_status"], "not-applicable")
            self.assertEqual(records[1]["context_skills"], [])

    def test_resume_reruns_existing_error_records(self) -> None:
        ok = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout="answer",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            existing = {
                "task_id": "impedance-fit-randles-cpe-warburg",
                "skill": "impedance",
                "variant": "baseline",
                "status": "error",
                "stdout": "old error",
            }
            results.write_text(json.dumps(existing) + "\n", encoding="utf-8")
            with patch("eval.scripts.run_claude_eval.run_claude", return_value=ok) as run_claude:
                exit_code = main(
                    [
                        "--results",
                        str(results),
                        "--task",
                        "impedance-fit-randles-cpe-warburg",
                        "--variant",
                        "baseline",
                        "--skip-preflight",
                        "--resume",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(run_claude.call_count, 1)
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([record["status"] for record in records], ["error", "ok"])

    def test_runner_persists_each_record_before_next_model_call(self) -> None:
        ok = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout="answer",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            with patch("eval.scripts.run_claude_eval.run_claude", side_effect=[ok, KeyboardInterrupt]):
                with self.assertRaises(KeyboardInterrupt):
                    main(
                        [
                            "--results",
                            str(results),
                            "--task",
                            "impedance-fit-randles-cpe-warburg",
                            "--skip-preflight",
                        ]
                    )
            records = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["task_id"], "impedance-fit-randles-cpe-warburg")
            self.assertEqual(records[0]["variant"], "baseline")
            self.assertEqual(records[0]["status"], "ok")

    def test_inapplicable_variant_filter_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results.jsonl"
            exit_code = main(
                [
                    "--dry-run",
                    "--results",
                    str(results),
                    "--task",
                    "impedance-fit-randles-cpe-warburg",
                    "--variant",
                    "kdense",
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertEqual(results.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()

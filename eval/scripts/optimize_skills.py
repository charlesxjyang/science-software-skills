#!/usr/bin/env python3
"""Black-box skill-file optimizer for package-skill evaluation prompts.

The optimizer deliberately keeps the search small and auditable. It does not
edit canonical skills. It builds candidate skill roots, runs the existing
Claude evaluator on package-skill variants, scores outputs with a fixed rubric,
accepts candidates on train/dev only, and reports heldout scores separately.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from eval.scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from eval.scripts.run_claude_eval import REPO_ROOT, load_tasks


DEFAULT_TASKS = REPO_ROOT / "eval" / "tasks" / "extension_tasks.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "eval" / "optimization"
DEFAULT_SKILLS = (
    "ase",
    "pymatgen",
    "rdkit",
    "mace",
    "impedance",
    "py4dstem",
    "hyperspy",
    "pybamm",
    "pyscf",
    "openmm",
    "matminer",
    "atomate2",
)

RUBRIC_TERMS: dict[str, list[list[str]]] = {
    "ase-env-relax-trajectory": [
        ["ase"],
        ["Atoms"],
        ["calculator"],
        ["BFGS", "trajectory"],
        ["forces", "energy"],
    ],
    "pymatgen-env-phase-diagram": [
        ["pymatgen"],
        ["MPRester"],
        ["PhaseDiagram"],
        ["eV/atom", "hull"],
        ["compatibility", "entries"],
    ],
    "rdkit-env-smiles-fingerprints": [
        ["rdkit"],
        ["MolFromSmiles"],
        ["Morgan", "fingerprint"],
        ["invalid"],
        ["radius", "bit", "version"],
    ],
    "mace-env-mlip-relax": [
        ["MACE"],
        ["MACECalculator"],
        ["ASE", "calculator"],
        ["forces", "energy"],
        ["device", "dtype", "model"],
    ],
    "impedance-env-eis-fit": [
        ["impedance"],
        ["CustomCircuit"],
        ["CPE", "Warburg"],
        ["frequency", "complex"],
        ["Nyquist", "parameter"],
    ],
    "py4dstem-env-virtual-bragg": [
        ["py4DSTEM"],
        ["DataCube"],
        ["shape", "axes"],
        ["virtual", "Bragg"],
        ["calibration", "beam", "threshold"],
    ],
    "hyperspy-env-spectral-map": [
        ["hyperspy"],
        ["hs.load"],
        ["axes", "metadata"],
        ["lazy"],
        ["model", "decomposition"],
    ],
    "pybamm-env-battery-discharge": [
        ["pybamm"],
        ["lithium-ion"],
        ["Experiment"],
        ["Simulation"],
        ["parameter", "solver", "version"],
    ],
    "pyscf-env-molecule-dft": [
        ["pyscf"],
        ["gto"],
        ["basis", "charge", "spin"],
        ["RKS"],
        ["converged", "energy"],
    ],
    "openmm-env-md-setup": [
        ["openmm"],
        ["PDBFile", "Modeller"],
        ["ForceField", "createSystem"],
        ["Langevin", "Simulation"],
        ["reporter", "unit"],
    ],
    "matminer-env-composition-descriptors": [
        ["matminer"],
        ["Composition"],
        ["ElementProperty", "magpie", "featurize_dataframe"],
        ["feature_labels"],
        ["train_test_split", "leak"],
        ["citations", "NaN", "version"],
    ],
    "atomate2-env-workflow-taskdoc": [
        ["atomate2"],
        [".make", "job"],
        ["run_locally"],
        ["task", "document"],
        ["maker", "version", "provenance"],
    ],
}

MUTATION_BLOCKS: dict[str, str] = {
    "matminer": """

## Optimization Candidate Notes

- In examples, explicitly call `feature_labels()` immediately after creating
  the featurizer and use those labels to select model inputs.
- Say that `ignore_errors=True` is not a substitute for auditing failed rows;
  print NaN counts and failed formulas before modeling.
- Keep feature generation target-free, then fit imputation, scaling, feature
  selection, and models only on the training split.
""",
    "atomate2": """

## Optimization Candidate Notes

- Show the distinction between constructing a job or flow with `.make()` and
  executing it with jobflow.
- Inspect the jobflow response or store for a task document; do not treat raw
  stdout as the workflow record.
- Explicitly warn against legacy atomate1 FireWorks `LaunchPad` examples unless
  the user asked for them.
""",
    "mace": """

## Optimization Candidate Notes

- Prefer the documented pretrained or foundation-model calculator path
  (`mace_mp` or `MACECalculator`) before discussing training a new model.
- In examples, show the ASE bridge explicitly: read or build `Atoms`, attach the
  calculator, run optimization/MD/inference, then inspect energy, forces, and
  stress or cell behavior when relevant.
- Record model name/path, model family, device, dtype, cutoff/default settings,
  MACE version, ASE version, units, and whether the structure cell/PBC are
  appropriate for the selected model.
""",
    "pyscf": """

## Optimization Candidate Notes

- For open-shell prompts, make the spin convention impossible to miss: PySCF
  `spin` is `2S = n_alpha - n_beta`, so multiplicity is `spin + 1`; choose
  UHF/UKS or ROHF/ROKS instead of RHF/RKS for radicals and other open-shell
  systems.
- For geometry optimization prompts, use the documented PySCF gradient/optimizer
  path (`pyscf.geomopt.geometric_solver.optimize`, `berny_solver.optimize`, or
  method `.Gradients()` as appropriate) rather than generic `scipy.optimize`.
- Keep examples compact but always print convergence, total energy, charge,
  spin, basis, method/functional, final coordinates, and `<S^2>`/spin
  contamination when an unrestricted reference is used.
""",
}


@dataclass(frozen=True)
class CandidateResult:
    skill: str
    candidate: str
    split: str
    score: float
    passed: int
    total: int
    results: str


def copy_skill_root(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def build_candidate_root(skill: str, candidate: str, skills_root: Path, output_dir: Path) -> Path:
    candidate_root = output_dir / "candidates" / skill / candidate / "skills"
    copy_skill_root(skills_root, candidate_root)
    if candidate == "candidate-notes":
        path = candidate_root / skill / "SKILL.md"
        path.write_text(path.read_text(encoding="utf-8") + MUTATION_BLOCKS[skill], encoding="utf-8")
    return candidate_root


def selected_tasks(tasks: list[dict], skill: str, split: str) -> list[dict]:
    return [task for task in tasks if task["skill"] == skill and task.get("split") == split]


def result_path(output_dir: Path, skill: str, candidate: str, split: str) -> Path:
    return output_dir / "results" / skill / candidate / f"{split}.jsonl"


def run_eval(tasks_path: Path, task_ids: list[str], skills_root: Path, results: Path, max_budget_usd: str, dry_run: bool) -> None:
    results.parent.mkdir(parents=True, exist_ok=True)
    existing = load_jsonl(results)
    complete = {
        record.get("task_id")
        for record in existing
        if record.get("variant") == "package-skill" and record.get("status") == "ok"
    }
    if not dry_run and set(task_ids).issubset(complete):
        return
    command = [
        sys.executable,
        str(REPO_ROOT / "eval" / "scripts" / "run_claude_eval.py"),
        "--tasks",
        str(tasks_path),
        "--skills-root",
        str(skills_root),
        "--variant",
        "package-skill",
        "--results",
        str(results),
        "--resume",
        "--max-budget-usd",
        max_budget_usd,
    ]
    for task_id in task_ids:
        command.extend(["--task", task_id])
    if dry_run:
        command.append("--dry-run")
    completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"evaluation failed for {results} with exit {completed.returncode}\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def record_score(task: dict, record: dict) -> tuple[int, int]:
    output = (record.get("stdout") or "").lower()
    passed = 0
    terms = task.get("rubric_terms", RUBRIC_TERMS.get(task["id"]))
    if terms is None:
        raise KeyError(task["id"])
    for group in terms:
        if all(term.lower() in output for term in group):
            passed += 1
    return passed, len(terms)


def score_results(tasks: list[dict], results: Path, skill: str, candidate: str, split: str) -> CandidateResult:
    task_by_id = {task["id"]: task for task in tasks}
    passed = 0
    total = 0
    for record in load_jsonl(results):
        if record.get("status") != "ok":
            continue
        task = task_by_id.get(record.get("task_id"))
        if task is None:
            continue
        p, t = record_score(task, record)
        passed += p
        total += t
    score = passed / total if total else 0.0
    try:
        display_path = str(results.resolve().relative_to(REPO_ROOT))
    except ValueError:
        display_path = str(results)
    return CandidateResult(skill, candidate, split, score, passed, total, display_path)


def train_dev_gap(train: CandidateResult, dev: CandidateResult) -> float:
    return abs(train.score - dev.score)


def write_report(output_dir: Path, rows: list[CandidateResult], decisions: list[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "rows": [row.__dict__ for row in rows],
        "decisions": decisions,
    }
    (output_dir / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Skill Optimization Report",
        "",
        "This report is generated by `eval/scripts/optimize_skills.py`.",
        "Candidates are accepted using train/dev only; heldout scores are reported but not used for acceptance.",
        "",
        "| Skill | Candidate | Split | Score | Passed | Total | Results |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row.skill}` | `{row.candidate}` | `{row.split}` | "
            f"{row.score:.3f} | {row.passed} | {row.total} | `{row.results}` |"
        )
    lines.extend(["", "## Decisions", ""])
    for decision in decisions:
        lines.append(
            f"- `{decision['skill']}`: selected `{decision['selected']}`; "
            f"train/dev reason: {decision['reason']}; "
            f"promote `{decision['promote']}` because {decision['promotion_reason']}"
        )
    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def optimize(args: argparse.Namespace) -> dict[str, object]:
    tasks = load_tasks(args.tasks)
    rows: list[CandidateResult] = []
    decisions: list[dict] = []

    for skill in args.skill:
        skill_tasks = {split: selected_tasks(tasks, skill, split) for split in ("train", "dev", "heldout")}
        active_splits = [split for split, split_tasks in skill_tasks.items() if split_tasks]
        if not active_splits:
            raise ValueError(f"{skill}: no tasks found")

        candidates = ["original"]
        if skill in MUTATION_BLOCKS:
            candidates.append("candidate-notes")
        candidate_scores: dict[tuple[str, str], CandidateResult] = {}
        for candidate in candidates:
            root = build_candidate_root(skill, candidate, args.skills_root, args.output_dir)
            for split in active_splits:
                split_tasks = skill_tasks[split]
                path = result_path(args.output_dir, skill, candidate, split)
                run_eval(
                    args.tasks,
                    [task["id"] for task in split_tasks],
                    root,
                    path,
                    args.max_budget_usd,
                    args.dry_run,
                )
                scored = score_results(split_tasks, path, skill, candidate, split)
                rows.append(scored)
                candidate_scores[(candidate, split)] = scored

        if "candidate-notes" not in candidates:
            selected = "original"
            reason = "no candidate mutation defined for this skill"
            promote = "original"
            promotion_reason = "diagnostic run only"
        elif "train" in active_splits and "dev" in active_splits:
            original_dev = candidate_scores[("original", "dev")]
            original_heldout = candidate_scores.get(("original", "heldout"))
            candidate_dev = candidate_scores[("candidate-notes", "dev")]
            candidate_train = candidate_scores[("candidate-notes", "train")]
            candidate_heldout = candidate_scores.get(("candidate-notes", "heldout"))
            gap = train_dev_gap(candidate_train, candidate_dev)
            if candidate_dev.score >= original_dev.score and gap <= args.max_gap:
                selected = "candidate-notes"
                reason = (
                    f"dev {candidate_dev.score:.3f} >= original {original_dev.score:.3f}; "
                    f"train/dev gap {gap:.3f} <= {args.max_gap:.3f}"
                )
            else:
                selected = "original"
                reason = (
                    f"candidate dev {candidate_dev.score:.3f}, original dev {original_dev.score:.3f}, "
                    f"candidate train/dev gap {gap:.3f}"
                )
            if (
                selected != "original"
                and original_heldout is not None
                and candidate_heldout is not None
                and candidate_heldout.score < original_heldout.score
            ):
                promote = "original"
                promotion_reason = (
                    f"heldout veto: candidate heldout {candidate_heldout.score:.3f} "
                    f"< original heldout {original_heldout.score:.3f}"
                )
            else:
                promote = selected
                promotion_reason = "no heldout regression"
        else:
            selected = "original"
            reason = f"missing train/dev split; scored splits: {', '.join(active_splits)}"
            promote = "original"
            promotion_reason = "no train/dev selection surface"
        decisions.append(
            {
                "skill": skill,
                "selected": selected,
                "reason": reason,
                "promote": promote,
                "promotion_reason": promotion_reason,
            }
        )

    write_report(args.output_dir, rows, decisions)
    return {"ok": True, "rows": [row.__dict__ for row in rows], "decisions": decisions}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--skills-root", type=Path, default=REPO_ROOT / "skills")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skill", action="append", choices=DEFAULT_SKILLS, default=[])
    parser.add_argument("--max-budget-usd", default="0.50")
    parser.add_argument("--max-gap", type=float, default=0.35)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.skill:
        args.skill = list(DEFAULT_SKILLS)

    try:
        payload = optimize(args)
    except (OSError, ValueError, RuntimeError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        else:
            print(f"ERROR {exc}")
        return 1

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Wrote optimization report to {args.output_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

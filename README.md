# materials-skills

Environment-aware skill discovery for materials and chemistry Python stacks.

The v0 demo maps installed Python packages to package-scoped `SKILL.md` files
and installs the matching skills into agent-specific skill directories.

Current status: CLI, packaged skills, validation, wheel smoke tests, and the
empirical evaluation artifacts are implemented. The first-package impedance
comparison and the five-task v0 baseline/package-skill/K-Dense matrix have real
Claude outputs, manually scored reports, and passing final artifact gates.
`python scripts/check_v0_status.py --json` is the single local command for the
current completion state.

```bash
pip list | materials-skills install --env - --agent claude
materials-skills install --env pip-list.txt --agent claude
materials-skills install --env pip-list.txt --agent all
materials-skills install --env environment.yml --target .cursor/skills
materials-skills install --env conda-env.json --format conda-json --dry-run --json
materials-skills install --env conda-list.txt --format conda-list --target .codex/skills
materials-skills install --env conda-explicit.txt --format conda-list --dry-run --json
materials-skills install --env pip-list.txt --target .claude/skills --force
materials-skills install --dry-run --json
materials-skills registry --json
materials-skills validate --source-root skills
materials-skills --version
```

Install reads exported environments from files, from the current Python
environment when `--env` is omitted, or from stdin with `--env -`. It is
idempotent when an existing skill directory matches the packaged skill. If an
existing skill differs, the CLI exits without overwriting unless `--force` is
passed. Use `--agent all` to install to every built-in convention
(`.claude/skills`, `.cursor/skills`, and `.codex/skills`) unless an explicit
`--target` is supplied. JSON output includes `environment` metadata,
including parsed package versions when present, `target`/`targets`, a `matches`
array showing which installed distribution names and versions triggered each
skill, advisory compatibility status against each skill's declared
`compatible_versions`, the requested `agent`, plus per-skill `actions` with statuses such as
`installed`, `unchanged`,
`overwritten`, `would-install`, `would-error`, and `would-overwrite`.

Current authored skills:

- `ase`: atomistic structures, calculators, trajectories, and simulation setup
- `pymatgen`: materials structures, compositions, Materials Project data, and
  phase-stability analysis
- `rdkit`: cheminformatics, SMILES/SMARTS, descriptors, fingerprints, and
  conformers
- `mace`: MACE machine-learning interatomic potentials and ASE calculators
- `impedance`: electrochemical impedance spectroscopy with impedance.py
- `py4dstem`: 4D-STEM datacubes, virtual imaging, Bragg disk detection, and
  phase-retrieval workflow guidance
- `hyperspy`: multidimensional microscopy/spectroscopy signals, axes, metadata,
  lazy loading, and model/decomposition workflows
- `pybamm`: physics-based battery models, experiments, parameter sets, and
  simulation diagnostics
- `pyscf`: Python-native quantum chemistry and electronic-structure workflows
- `openmm`: molecular dynamics setup, force fields, units, platforms, and
  reporters
- `matminer`: materials-informatics featurization and tabular ML provenance
- `atomate2`: jobflow-based materials workflows, makers, flows, and task docs

Evaluation harness:

```bash
python eval/scripts/run_claude_eval.py --preflight-only
python eval/scripts/run_claude_eval.py --dry-run --kdense-root eval/kdense-public
python eval/scripts/run_claude_eval.py --dry-run --task impedance-fit-randles-cpe-warburg --variant package-skill
python eval/scripts/run_claude_eval.py --kdense-root /path/to/kdense/skills
python eval/scripts/run_claude_eval.py --kdense-root eval/kdense-public --resume --results eval/results.jsonl
python eval/scripts/run_claude_eval.py --kdense-root eval/kdense-public --skip-preflight --results /private/tmp/materials-skills-debug-results.jsonl
python eval/scripts/run_impedance_pipeline.py --resume
python eval/scripts/run_impedance_pipeline.py --skip-model-run --check-scored
python eval/scripts/run_impedance_pipeline.py --skip-model-run --check-scored --json
python eval/scripts/run_v0_pipeline.py --resume
python eval/scripts/run_v0_pipeline.py --skip-model-run --check-scored
python eval/scripts/run_v0_pipeline.py --skip-model-run --check-scored --json
python eval/scripts/score_results.py --results eval/results.jsonl
python eval/scripts/check_eval_completeness.py --results eval/results.jsonl
python eval/scripts/check_score_report.py --report eval/score-report.md
python eval/scripts/check_eval_artifacts.py --results eval/results.jsonl --report eval/score-report.md
python eval/scripts/optimize_skills.py --tasks eval/tasks/extension_tasks.json --output-dir eval/optimization-real --json
python eval/scripts/score_extension_results.py --results eval/extension-results.jsonl
python eval/scripts/run_agent_eval.py --provider codex --tasks eval/tasks/extension_tasks.json --variant baseline --variant package-skill --results eval/codex-extension-results.jsonl --resume
python eval/scripts/run_agent_eval.py --provider gemini --tasks eval/tasks/extension_tasks.json --variant baseline --variant package-skill --results eval/gemini-extension-results.jsonl --resume
```

Non-dry-run evaluation performs a one-call Claude preflight first. If the local
Claude CLI is not authenticated, the runner writes one structured error record
instead of spending the full matrix on repeated auth failures. Use
`--preflight-only` after `claude auth login` to check auth without writing result
records. Package-skill variants can load multiple package skills for
cross-library tasks; the ASE+pymatgen+MACE task records `mace`, `ase`, and
`pymatgen` as loaded context. Real runs fail before model calls if a selected
K-Dense variant lacks a matching `--kdense-root`; dry-runs may still show
missing context for inspection. Use `--resume` to preserve prior result records
and skip task/variant pairs that already have a current complete `ok` result
with matching prompt/context metadata and non-empty stdout. Reserve
`--skip-preflight` for disposable debugging outputs or for deliberately
refreshing auth-blocked fixtures; the normal empirical path should use the
pipeline wrappers below. The completeness check must pass before treating the
empirical comparison as finished. The `run_agent_eval.py` helper reuses the
same prompts for non-Claude providers: Codex uses the local `codex exec` CLI in
a read-only temporary directory, and Gemini uses the REST API with
`GEMINI_API_KEY`. The
`run_v0_pipeline.py` wrapper runs the post-login preflight, smoke test, full
matrix, completeness check, and score-report scaffold in order; after manual
scoring, rerun it with `--skip-model-run --check-scored` for the final artifact
gate. The wrapper requires `--skip-model-run` with `--check-scored` so a
manually scored report is not overwritten, and model-run mode refuses to
replace an already scored report unless `--overwrite-report` is passed. Existing
unscored dry-run scaffolds are replaced after real outputs complete. The direct
`score_results.py` renderer uses the same manual-report overwrite guard. See
`eval/README.md` for the post-login runbook. `python scripts/check_v0_status.py`
prints the current local/empirical status, a concise `blockers` summary, and the
exact remaining sequence, including an auth preflight and manual score-report
checkpoints. JSON output also includes `automation_steps` for the
machine-readable final artifact gates. Its text output prints per-artifact
empirical blockers such as
`evaluation` and `scoring` before the detailed errors.

The extension benchmark in `eval/tasks/extension_tasks.json` is the current
environment-discovery surface. It has five hidden-rubric tasks per active
package skill, with the two newest tasks for each package drawn from documented
examples and recorded in each task's `doc_sources`. User prompts list only
generic distractors (`numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`)
and realistic scientific intent; target package names are hidden from user
prompts and appear only in manifest metadata, rubrics, docs source fields, and
loaded package-skill context. The expanded Codex baseline-vs-package-skill run
is in `eval/codex-extension-results.jsonl` with scores in
`eval/codex-extension-score-report.md`: package skills win 11 of 12 package
suites and tie RDKit, with baseline scoring 143/300 rubric terms and
package-skill context scoring 257/300. The older Claude extension report in
`eval/extension-score-report.md` is retained as the prior three-task suite until
the expanded Claude matrix is rerun. A MACE-only black-box optimizer run is
recorded in `eval/optimization-mace/report.md`. `eval/scripts/optimize_skills.py`
can still test skill-file candidates without mutating canonical skills.

See `docs/v0-demo.md` for a concrete demo transcript using the mixed conda+pip
fixture environment. The checked `registry.json` mirrors
`materials-skills registry --json` for non-Python tooling. See
`docs/design-decisions.md` for the current status of the original open design
questions.

Packaging note: after editing top-level `skills/*/SKILL.md`, sync package data
with:

```bash
python scripts/sync_packaged_skills.py
```

For a non-mutating release/CI check, run:

```bash
python scripts/check_local_v0.py
python scripts/check_v0_status.py --json
```

Or run the package-data, registry, and wheel checks individually:

```bash
python scripts/sync_packaged_skills.py --check
python scripts/check_registry_json.py --registry-json registry.json
python scripts/check_wheel_skills.py dist/materials_skills-0.1.0-py3-none-any.whl --source-root skills --package-root src/materials_skills --console-script materials-skills --pyproject pyproject.toml --readme README.md
python scripts/check_wheel_install.py dist/materials_skills-0.1.0-py3-none-any.whl
python scripts/check_sdist_payload.py dist/materials_skills-0.1.0.tar.gz --source-root skills --package-root src/materials_skills --scripts-root scripts --docs-root docs --eval-root eval --research-root research --tests-root tests --registry-json registry.json --readme README.md --pyproject pyproject.toml
```

After editing the runtime registry, regenerate the checked snapshot with:

```bash
python scripts/check_registry_json.py --registry-json registry.json --write
```

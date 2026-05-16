# v0 Status

## Objective

Bootstrap an environment-aware skills layer for materials and chemistry Python:
detect installed packages, map them to package-scoped skills, install matching
skills into agent directories, and author/audit high-quality skills for the
priority materials and chemistry packages.

## Implemented

- `skills/impedance/SKILL.md`: package-scoped skill focused on impedance.py EIS
  fitting and validation.
- `skills/ase/SKILL.md`: package-scoped skill focused on ASE atomistic
  structures, calculators, file I/O, optimization, and trajectories.
- `skills/pymatgen/SKILL.md`: package-scoped skill focused on pymatgen
  materials structures, compositions, Materials Project data, and phase
  diagrams.
- `skills/rdkit/SKILL.md`: package-scoped skill focused on RDKit
  cheminformatics, SMILES/SMARTS, descriptors, fingerprints, sanitization, and
  conformers.
- `skills/mace/SKILL.md`: package-scoped skill focused on MACE MLIPs,
  foundation models, ASE calculators, training data keys, E0s, and inference.
- `skills/py4dstem/SKILL.md`: package-scoped skill focused on py4DSTEM
  datacubes, virtual imaging, Bragg disk detection, axis/calibration checks, and
  phase-retrieval version boundaries.
- `skills/hyperspy/SKILL.md`: package-scoped skill focused on HyperSpy
  multidimensional signals, navigation/signal axes, metadata, lazy loading,
  decomposition/model fitting, and the HyperSpy/eXSpy split.
- `skills/pybamm/SKILL.md`: package-scoped skill focused on PyBaMM battery
  models, simulations, experiments, parameter sets, solver/mesh choices, and
  diagnostic checks.
- `skills/pyscf/SKILL.md`: package-scoped skill focused on PySCF quantum
  chemistry, SCF/DFT/post-HF workflows, spin/charge/basis conventions, and PBC
  calculations.
- `skills/openmm/SKILL.md`: package-scoped skill focused on OpenMM molecular
  dynamics, force fields, unit-bearing quantities, structure preparation,
  platforms, and reporters.
- `research/impedance.md`: source/evidence notes for the impedance.py skill.
- `research/ase.md`: source/evidence notes for the ASE skill.
- `research/pymatgen.md`: source/evidence notes for the pymatgen skill.
- `research/rdkit.md`: source/evidence notes for the RDKit skill.
- `research/mace.md`: source/evidence notes for the MACE skill.
- `research/py4dstem.md`: source/evidence notes for the py4DSTEM skill.
- `research/hyperspy.md`: source/evidence notes for the HyperSpy skill.
- `research/pybamm.md`: source/evidence notes for the PyBaMM skill.
- `research/pyscf.md`: source/evidence notes for the PySCF skill.
- `research/openmm.md`: source/evidence notes for the OpenMM skill.
- `materials-skills install`: CLI for reading package environments and copying
  matching skills into `.claude/skills`, `.cursor/skills`, `.codex/skills`, or
  an explicit `--target`. It reads environment data from a file, the current
  Python environment when `--env` is omitted, or stdin via `--env -`. Installs
  are idempotent when an existing skill matches package data, and changed
  existing skill directories require `--force` before overwrite. `--agent all`
  installs to all built-in agent directory
  conventions. JSON output includes `environment` metadata with parsed package
  versions when present, `target`/`targets`, match provenance for which
  installed distribution names and versions triggered each skill, plus
  per-skill `actions` with `installed`, `unchanged`, `overwritten`,
  `would-install`, `would-error`, or `would-overwrite` statuses.
- `materials-skills validate`: CLI for checking registry/frontmatter/section
  consistency, non-empty required metadata, related-skill references,
  malformed inline frontmatter lists, canonical URL shape and distinctness,
  skill length, and packaged-vs-source sync.
- `materials-skills registry`: CLI for exporting the central package-to-skill
  registry as text or JSON, independent of skill installation.
- `registry.json`: checked static registry snapshot for non-Python tooling;
  tests verify it matches the runtime `materials-skills registry --json`
  payload, and `scripts/check_registry_json.py --write` can regenerate it.
- `src/materials_skills/skills/`: package-data copy of the 12 authored skills
  for installed CLI usage.
- `scripts/sync_packaged_skills.py`: syncs top-level skills into package data
  and supports `--check` for non-mutating package-data drift detection.
- `scripts/check_wheel_skills.py`: validates that a built wheel includes
  exactly one packaged `SKILL.md` for each registry entry, and can compare the
  wheel payload against the source `skills/` tree and `src/materials_skills/`
  Python modules to catch stale wheels. It can also verify that the installed
  wheel exposes the `materials-skills` console script entry point and that
  source-only directories such as `eval/`, `docs/`, and `tests/` have not leaked
  into the runtime wheel, that `pyproject.toml`, package `__version__`, and
  wheel metadata versions agree, plus that wheel metadata includes the current
  README text.
- `scripts/check_wheel_install.py`: installs the built wheel into a temporary
  venv with `--no-index`, then exercises the installed `materials-skills`
  console script through `--version`, `validate`, `registry`, and a real
  fixture install, verifying that installed skill names, requested-agent
  provenance, `--agent all` dry-run targeting, and target directories match the
  installed registry exactly.
- `scripts/check_sdist_payload.py`: validates that the built source
  distribution carries the current top-level skills, packaged skills, source
  Python modules, release scripts, docs, evaluation harness/artifacts, research
  notes, tests/fixtures, `registry.json`, README, and `pyproject.toml`.
- `scripts/check_local_v0.py`: runs the local non-empirical v0 gate suite:
  tests, skill validation, package-data sync check, registry JSON sync check,
  wheel payload check, installed-wheel smoke check, and source-distribution
  payload check.
- `scripts/check_v0_status.py`: aggregates the local readiness gates, including
  unit tests, plus first-package impedance and full-matrix empirical artifact
  gates without calling Claude. It emits machine-readable `blockers` and
  `next_steps` in JSON mode, plus `automation_steps` for the JSON final-gate
  commands. It prints the same blocker summary plus post-login commands in text
  mode. The empirical sequence includes an explicit `--preflight-only` auth
  check and manual score-report checkpoints before each final `--check-scored`
  gate. Tests verify it calls the impedance and full-matrix artifact gates with
  separate task/result/report paths.
- `scripts/_bootstrap.py`: shared import-path bootstrap so repository helper
  scripts that import `materials_skills` can run directly from a source
  checkout without a manual `PYTHONPATH=src:.` prefix.
- Environment parsers:
  - `pip list` table text
  - `pip freeze`-style lines
  - editable/VCS pip requirements with `#egg=` package names
  - direct-reference pip requirements such as `name @ git+https://...`
  - pip requirements with spaced version operators such as `name == 1.2.3`
  - bare pip wheel URLs such as `https://.../openmm-8.4.0-py3-none-any.whl`
  - `pip list --format=json`
  - `conda env export` YAML with nested `pip:` dependencies
  - `conda env export --json` with nested `pip` dependencies
  - `conda list` table output
  - `conda list --json` package objects
  - `conda list --export` package spec lines
  - explicit conda package URL lockfiles
- Evaluation prompt scaffolds for impedance.py, ASE, pymatgen, RDKit, MACE,
  py4DSTEM, HyperSpy, PyBaMM, PySCF, and OpenMM behavior checks.
- `eval/impedance/prompts.md`, `eval/impedance/tasks.json`, and
  `eval/impedance/results.md`: three impedance.py manual EIS prompts, a
  structured prompt manifest, and blocked baseline/package-skill result
  placeholders for the requested first-package Claude Code iteration, including
  the post-login direct wrapper commands and JSON final artifact gate.
- `eval/tasks/v0_tasks.json`: five-task empirical evaluation manifest.
- `eval/scripts/run_claude_eval.py`: repeatable Claude Code evaluation runner
  for baseline, package-skill, and K-Dense variants, with an auth-status-first
  Claude preflight before non-dry-run matrices, `--preflight-only` auth
  checking that writes no result records, `context_status` metadata proving package/K-Dense
  context was loaded, `context_skills` metadata for composed package-skill
  prompts, a fail-fast guard for selected K-Dense variants without a matching
  `--kdense-root`, and `--task`/`--variant` filters for post-login smoke tests.
  `--resume` preserves prior result records and skips task/variant pairs that
  already have a current complete `ok` result with matching prompt/context
  metadata and non-empty stdout. Completed records are written after each
  task/variant so interrupted runs can resume from the latest completed record.
- `eval/scripts/score_results.py`: manual score-report renderer for evaluation
  JSONL outputs, including a task-level comparison summary for baseline,
  package-skill, K-Dense outcomes, per-variant context status, loaded skills,
  prompt provenance, and model output. It reports missing results files cleanly
  before writing a report and refuses to overwrite an existing manually scored
  report unless `--overwrite-report` is passed.
- `eval/scripts/check_score_report.py`: manual-scoring gate that fails while
  generated score reports still contain `Outcome: not-scored` placeholders,
  unchecked criteria boxes, missing expected task/variant
  sections, missing checked success criteria, or invalid scored outcome/winner
  values. It also rejects summary rows whose baseline/package-skill/K-Dense
  outcomes disagree with the corresponding variant outcome sections, winners
  whose summary outcome is not `win`, inapplicable `kdense` winners, `tie`
  winners without tied applicable outcomes, and `blocked` winners without all
  applicable outcomes blocked. It requires each scored variant section to
  retain a fenced prompt block containing the task manifest prompt.
- `eval/scripts/check_eval_artifacts.py`: combined final artifact gate that
  checks both model-output completeness and manual score-report completion and
  emits a `blockers` list naming `evaluation` and/or `scoring` failures for
  machine-readable status.
- `eval/scripts/run_impedance_pipeline.py`: post-login orchestration wrapper
  for the first-package impedance.py iteration: preflight, six-record
  baseline/package-skill matrix, completeness gate, score-report scaffold, and
  final `--skip-model-run --check-scored` artifact validation after manual
  scoring. Failed scored-artifact validation prints the combined gate's
  `blockers` summary before detailed evaluation/scoring errors, and
  `--skip-model-run --check-scored --json` emits the combined gate payload
  without model calls.
- `eval/scripts/run_v0_pipeline.py`: post-login orchestration wrapper for
  preflight, impedance package-skill smoke test, full matrix/resume,
  completeness gate, score-report scaffold generation, and final
  `--skip-model-run --check-scored` artifact validation after manual scoring.
  It refuses `--check-scored` without `--skip-model-run` to avoid overwriting a
  manually scored report before validation, and refuses `--skip-model-run`
  without `--check-scored` so skipped model runs are still validated. Failed
  scored-artifact validation prints the combined gate's `blockers` summary
  before detailed evaluation/scoring errors, and `--skip-model-run
  --check-scored --json` emits the combined gate payload without model calls.
- `eval/scripts/_bootstrap.py`: shared import-path bootstrap so the evaluation
  entry points can run directly from a source checkout without requiring a
  manual `PYTHONPATH=src:.` prefix.
- `eval/scripts/check_eval_completeness.py`: strict empirical-result gate that
  fails unless every expected baseline/package-skill/K-Dense record has
  `status: "ok"`, non-empty prompt provenance, non-empty output, and provided
  context for package-skill and K-Dense variants. For package-skill records, it
  also requires `context_skills` to exactly match the task manifest; for
  K-Dense records, it requires `context_skills` to name the compared skill.
- `eval/README.md`: post-login empirical-evaluation runbook with smoke test,
  preflight-only auth check, full matrix, resume, completeness gate, manual
  scoring commands, and explicit text/JSON final artifact gates for both the
  impedance and full-matrix wrappers.
- `eval/kdense-public/pymatgen/SKILL.md`: public K-Dense pymatgen fixture used
  for the K-Dense comparison prompt.
- `docs/kdense-pymatgen-comparison.md`: non-empirical audit comparing the public
  K-Dense pymatgen skill against the local compact package skill.
- `docs/v0-demo.md`: concrete CLI demo transcript showing a mixed conda+pip
  fixture environment resolving to 12 skills and three built-in agent targets.
- `docs/design-decisions.md`: concise status of the original open design
  questions, separating v0 evidence from post-v0 risks.

## Verified

- `PYTHONPATH=src:. python -m unittest discover -s tests`
  - 320 tests passing.
- `uv build`
  - Rebuilt `dist/materials_skills-0.1.0.tar.gz` and
    `dist/materials_skills-0.1.0-py3-none-any.whl`.
- `python scripts/check_local_v0.py`
  - Passed: unit tests, skill validation, package-data sync, registry JSON
    sync, wheel payload, installed-wheel smoke, and source-distribution payload
    checks.
- Skill validation:
  - `PYTHONPATH=src python -m materials_skills.cli validate --source-root skills --json`
  - `PYTHONPATH=src python -m materials_skills.cli validate --skills-root skills --json`
  - Both returned `{"ok": true, "errors": []}`.
  - Tests cover missing required sections, frontmatter name mismatch,
    duplicate skill names, missing `related_skills`, empty required
    frontmatter values including empty block-scalar descriptions, malformed
    inline `related_skills` lists, unregistered duplicate, and
    self-referential `related_skills`, non-HTTP or duplicate canonical links,
    normalized duplicate canonical links, canonical links without hosts, malformed
    `version`/`compatible_versions` metadata, inverted compatibility bounds,
    and the 300-line compact-skill
    limit.
  - Current source skill line counts range from 138 to 175 lines, below the
    300-line v0 cap.
- Sync consistency:
  - Tests verify `src/materials_skills/skills/*/SKILL.md` matches top-level
    `skills/*/SKILL.md` for every registry entry.
  - `python scripts/sync_packaged_skills.py --check` returned
    `Packaged skills are in sync`.
  - Tests verify the sync checker reports missing, extra, and out-of-sync
    packaged files, and that sync mode restores a missing destination.
- Registry consistency:
  - Tests verify registry skill names and skill directories are unique.
  - Tests verify normalized distribution aliases do not map across multiple
    skills, while allowing intentional same-skill aliases such as
    `py4DSTEM`/`py4dstem`.
  - Tests verify checked `registry.json` matches the canonical runtime registry
    JSON text, and that the registry JSON writer restores the canonical payload.
- Evidence-note coverage:
  - Tests verify every registered skill has a matching `research/<skill>.md`
    note with `## Sources Reviewed`, `## Extracted Workflow`, a gotchas
    section, `## Open Follow-Ups`, and at least three source URLs.
  - `research/impedance.md` now records a May 12, 2026 freshness check against
    the current impedance.py docs and relevant open GitHub issues.
- Evaluation prompt coverage:
  - Tests verify every registered skill has a matching `eval/<skill>/prompts.md`
    scaffold with prompt and expected-behavior content.
- K-Dense fixture handling:
  - Tests verify `eval/scripts/run_claude_eval.py` loads K-Dense-style
    `SKILL.md` files when a root is provided and emits a clear placeholder when
    no root is provided.
  - Public K-Dense pymatgen skill fixture downloaded from
    `K-Dense-AI/claude-scientific-skills`.
  - Tests verify `eval/kdense-public/README.md` documents the upstream source,
    MIT license note, and SHA-256 hash matching the checked pymatgen fixture.
  - Tests verify `research/pymatgen.md` points to the checked K-Dense fixture
    and that the v0 phase-diagram task remains marked `kdense_applicable`.
- Packaged default install command:
  - Command omitted `--skills-root` so `default_skills_root()` used
    `src/materials_skills/skills`.
  - Output directory: `/private/tmp/materials-skills-packaged-default/.claude/skills`
  - Installed all 12 authored skills.
- v0 demo transcript:
  - Command: `PYTHONPATH=src python -m materials_skills.cli install --env tests/fixtures/conda-env.yml --agent all --skills-root skills --dry-run --json`
  - Output: detected `format: "conda"`, found 16 packages, selected all 12
    skills, recorded `agent: "all"`, and targeted `.claude/skills`,
    `.cursor/skills`, and `.codex/skills`.
  - Documented in `docs/v0-demo.md`; integration tests verify the corresponding
    non-dry-run `--agent all` install creates 30 actions across the three
    built-in target roots.
- Wheel build and installed CLI:
  - Built `dist/materials_skills-0.1.0-py3-none-any.whl` with `uv run --with build --with hatchling python -m build --wheel`.
  - `python scripts/check_wheel_skills.py dist/materials_skills-0.1.0-py3-none-any.whl --source-root skills --package-root src/materials_skills --console-script materials-skills --pyproject pyproject.toml --readme README.md`
    returned `Wheel payload is complete`, verifying each packaged `SKILL.md`
    appears exactly once, source skills match the wheel, and source Python
    modules match the wheel, the console script is present, versions match, and
    wheel metadata includes the current README text.
  - Installed the wheel into `/private/tmp/materials-skills-wheel-venv`,
    `/private/tmp/materials-skills-wheel-venv-condalist`, and
    `/private/tmp/materials-skills-wheel-venv-explicit`, and
    `/private/tmp/materials-skills-wheel-venv-validate-strict`, and
    `/private/tmp/materials-skills-wheel-venv-force`, and
    `/private/tmp/materials-skills-wheel-venv-actions`, and
    `/private/tmp/materials-skills-wheel-venv-dryrun-preview`, and
    `/private/tmp/materials-skills-wheel-venv-match-trace`, and
    `/private/tmp/materials-skills-wheel-venv-agent-all`, and
    `/private/tmp/materials-skills-wheel-venv-stdin`, and
    `/private/tmp/materials-skills-wheel-venv-parse-errors`, and
    `/private/tmp/materials-skills-wheel-venv-condajson`, and
    `/private/tmp/materials-skills-wheel-venv-sync-check`, and
    `/private/tmp/materials-skills-wheel-venv-release-check`,
    `/private/tmp/materials-skills-wheel-venv-version-provenance`, and
    `/private/tmp/materials-skills-wheel-venv-compatibility-status`.
  - Installed console script validated successfully with `materials-skills validate --json`
    and exported registry JSON successfully with `materials-skills registry --json`.
  - Installed console script copied all 12 skills to
    `/private/tmp/materials-skills-wheel-install/.claude/skills`.
  - Rebuilt wheel after tightening metadata validation; installed console script
    validated packaged skills successfully and copied all 12 skills to
    `/private/tmp/materials-skills-wheel-strict-real/.claude/skills`.
  - Rebuilt wheel after adding overwrite protection; installed console script
    verified idempotent reinstall, refused a locally modified existing skill
    without `--force`, then overwrote it successfully with `--force` in
    `/private/tmp/materials-skills-wheel-force-real/.claude/skills`.
  - Rebuilt wheel after adding action-status JSON; installed console script
    reported `installed` on first install, `unchanged` on idempotent reinstall,
    refused a modified skill without `--force`, and reported `overwritten` for
    that skill after forced reinstall in
    `/private/tmp/materials-skills-wheel-actions-real/.claude/skills`.
  - Rebuilt wheel after adding dry-run conflict previews; installed console
    script reported `would-error` for a modified existing skill without
    `--force` and `would-overwrite` with `--force` in
    `/private/tmp/materials-skills-wheel-dryrun-preview-real/.claude/skills`.
  - Rebuilt wheel after adding match-provenance JSON; installed console script
    validated packaged skills and emitted `matches` plus per-action
    `matched_distributions` in
    `/private/tmp/materials-skills-wheel-match-trace-real/.claude/skills`.
  - Rebuilt wheel after adding `--agent all`; installed console script validated
    packaged skills, emitted all three built-in `targets` during dry-run, and
    reported this sandbox's `.codex` write denial as structured JSON rather
    than a traceback before copying skill directories.
  - Rebuilt wheel after adding `--env -`; installed console script validated
    packaged skills and matched all 12 authored skills from a pip-list stream
    piped on stdin.
  - Rebuilt wheel after adding parse-error handling; installed console script
    returned structured JSON errors for a missing environment file and malformed
    pip JSON streamed on stdin.
  - Rebuilt wheel after adding `conda-json`; installed console script matched
    all 12 authored skills from `tests/fixtures/conda-env.json` and matched the
    expected subset from `tests/fixtures/conda-list.json`.
  - Rebuilt wheel after adding JSON-list shape detection; installed console
    script auto-detected `tests/fixtures/conda-list.json` as conda JSON and
    preserved auto-detection of `tests/fixtures/pip-list.json` as pip JSON.
  - Rebuilt wheel after adding environment metadata JSON; installed console
    script reported `environment.source`, `environment.requested_format`,
    `environment.format`, and `environment.package_count` for file and stdin
    inputs.
  - Rebuilt wheel after adding package-version provenance; installed console
    script reported `environment.package_versions`, `matches[*].matched_versions`,
    and `actions[*].matched_versions` from `tests/fixtures/pip-list.json` in
    `/private/tmp/materials-skills-wheel-version-provenance/.claude/skills`.
  - Rebuilt wheel after adding advisory compatibility status; installed console
    script reported `compatible_versions` plus `compatibility: "compatible"` for
    the 10 matched fixture skills in
    `/private/tmp/materials-skills-wheel-compatibility-status/.claude/skills`.
  - Rebuilt wheel after fixing pip direct-reference auto-detection; installed
    console script parsed `/private/tmp/materials-skills-pipreq.txt` as
    `format: "pip"` and selected `mace`, `impedance`, `py4dstem`, `hyperspy`,
    and `pybamm` from pinned, direct-reference, editable `#egg=`, and extras
    requirements.
  - Rebuilt wheel after tightening URL-based inference; installed console
    script parsed `/private/tmp/materials-skills-http-pipreq.txt` as
    `format: "pip"` and selected `impedance` from a bare HTTP wheel URL plus
    `rdkit` from a named HTTP direct reference.
  - Rebuilt wheel after preserving versions from named direct-reference wheel
    URLs; parser tests verify `rdkit @ https://.../rdkit-2026.03.2-...whl`
    records `package_versions["rdkit"] == "2026.03.2"`.
  - Rebuilt wheel after adding package-data sync `--check`; installed console
    script validated packaged skills and dry-run matched all 12 authored skills
    from `tests/fixtures/pip-list.txt` in
    `/private/tmp/materials-skills-wheel-sync-check/.claude/skills`.
  - Installed console script with no `--env` dry-ran the current fresh wheel
    venv, reported `source: "current"` and
    `format: "installed-distributions"`, and selected no skills because that
    venv only had unrelated package distributions.
  - Rebuilt wheel after adding the wheel-payload release check; wheel metadata
    includes the latest README packaging commands, `check_wheel_skills.py`
    returned `Wheel payload is complete`, and the installed console
    script in `/private/tmp/materials-skills-wheel-venv-release-check` dry-run
    matched all 12 authored skills from `tests/fixtures/pip-list.txt`.
  - Installed console script copied all 12 skills from `tests/fixtures/conda-list.txt`
    to `/private/tmp/materials-skills-wheel-condalist-real/.codex/skills`.
  - Installed console script copied all 12 skills from
    `tests/fixtures/conda-explicit.txt` to
    `/private/tmp/materials-skills-wheel-explicit-real/.codex/skills`.
- End-to-end install command:
  - Input: `tests/fixtures/pip-list.txt`
  - Output: `/private/tmp/materials-skills-demo10/.claude/skills/ase/SKILL.md`
  - Output: `/private/tmp/materials-skills-demo10/.claude/skills/pymatgen/SKILL.md`
  - Output: `/private/tmp/materials-skills-demo10/.claude/skills/rdkit/SKILL.md`
  - Output: `/private/tmp/materials-skills-demo10/.claude/skills/mace/SKILL.md`
  - Output: `/private/tmp/materials-skills-demo10/.claude/skills/impedance/SKILL.md`
  - Output: `/private/tmp/materials-skills-demo10/.claude/skills/py4dstem/SKILL.md`
  - Output: `/private/tmp/materials-skills-demo10/.claude/skills/hyperspy/SKILL.md`
  - Output: `/private/tmp/materials-skills-demo10/.claude/skills/pybamm/SKILL.md`
  - Output: `/private/tmp/materials-skills-demo10/.claude/skills/pyscf/SKILL.md`
  - Output: `/private/tmp/materials-skills-demo10/.claude/skills/openmm/SKILL.md`
- Stdin dry-run command:
  - Command: `cat tests/fixtures/pip-list.txt | /usr/bin/env PYTHONPATH=src python -m materials_skills.cli install --env - --target /private/tmp/materials-skills-stdin-demo/.claude/skills --skills-root skills --dry-run --json`
  - Output skill match: `["ase", "pymatgen", "rdkit", "mace", "impedance", "py4dstem", "hyperspy", "pybamm", "pyscf", "openmm"]`
- Current-environment detection:
  - Tests verify `metadata.distributions()` is used without shelling out when
    installed distribution names are available.
  - Tests verify fallback to `python -m pip list --format=json` when
    distribution metadata yields no names.
  - Tests verify the top-level `install` command uses the current environment
    when `--env` is omitted and reports `source: "current"` plus
    `format: "installed-distributions"` in JSON output.
- Conda JSON dry-run command:
  - Input: `tests/fixtures/conda-env.json`
  - Output skill match: `["ase", "pymatgen", "rdkit", "mace", "impedance", "py4dstem", "hyperspy", "pybamm", "pyscf", "openmm"]`
  - Input: `tests/fixtures/conda-list.json`
  - Output skill match: `["ase", "pymatgen", "rdkit", "mace", "impedance", "py4dstem", "hyperspy", "openmm"]`
  - Auto-detection distinguishes pip JSON lists from conda JSON lists using
    conda-specific package metadata such as `build_string`.
- Environment metadata:
  - JSON install output reports `environment.source`,
    `environment.requested_format`, `environment.format`, and
    `environment.package_count`, plus `environment.package_versions` when the
    input format carries versions.
  - Verified for stdin pip-list input and auto-detected conda-list JSON input.
- Environment parse error handling:
  - Missing `--env` file returns structured JSON with `ok: false`.
  - Malformed `--format pip-json` input from stdin returns structured JSON
    with the JSON parser error.
- Install overwrite safety:
  - Tests verify a repeated install is idempotent when the existing skill
    matches package data.
  - Tests verify `--agent all` fans out to `.claude/skills`, `.cursor/skills`,
    and `.codex/skills`; explicit `--target` still overrides the agent choice.
  - Tests verify install-time OS errors are reported as structured JSON errors
    instead of tracebacks when `--json` is used.
  - Tests verify missing environment files and malformed JSON environment
    inputs are reported as structured JSON errors instead of tracebacks.
  - Tests verify target-root creation is preflighted before copying skills, so
    multi-target permission failures do not leave partially populated installs.
  - Tests verify overwrite conflicts are preflighted before creating empty
    target roots for untouched agents in an `--agent all` install.
  - Tests verify JSON action statuses report `installed`, `unchanged`,
    `overwritten`, `would-install`, `would-error`, and `would-overwrite`.
  - Tests verify JSON match provenance preserves original installed
    distribution names while matching aliases such as `rdkit_pypi`,
    `pybamm_base`, and `py4DSTEM`.
  - Manual dry-run preview verified modified existing skills report
    `would-error` without `--force` and `would-overwrite` with `--force`.
  - Tests verify a locally modified existing skill causes a nonzero JSON error
    unless `--force` is supplied.
  - Tests verify `--force` overwrites a modified existing skill with the
    packaged skill.
- Dry-run JSON command:
  - Input: `tests/fixtures/conda-env.yml`
  - Output skill match: `["ase", "pymatgen", "rdkit", "mace", "impedance", "py4dstem", "hyperspy", "pybamm", "pyscf", "openmm"]`
  - Output match provenance includes each installed distribution name and the
    registered aliases for the matching skill.
- Conda-list dry-run JSON commands:
  - Input: `tests/fixtures/conda-list.txt`
  - Input: `tests/fixtures/conda-list-export.txt`
  - Input: `tests/fixtures/conda-explicit.txt`
  - Output skill match for all three: `["ase", "pymatgen", "rdkit", "mace", "impedance", "py4dstem", "hyperspy", "pybamm", "pyscf", "openmm"]`
- Registry JSON command:
  - Command: `PYTHONPATH=src python -m materials_skills.cli registry --json`
  - Output: 10 registry entries including distribution aliases such as
    `rdkit-pypi`, `mace-torch`, and `pybamm-base`.
- Cursor-style install command:
  - Input: `tests/fixtures/conda-env.yml`
  - Output directory: `/private/tmp/materials-skills-demo10-cursor/.cursor/skills`
  - Installed all 12 authored skills.
- Evaluation dry-run:
  - Command: `PYTHONPATH=src:. python eval/scripts/run_claude_eval.py --dry-run --kdense-root eval/kdense-public --results eval/dry-run-results.jsonl`
  - Output: 11 records covering 5 baseline runs, 5 package-skill runs, and 1
    K-Dense comparison slot, with `context_status` metadata for each variant and
    `context_skills` showing the ASE+pymatgen+MACE task loaded `mace`, `ase`,
    and `pymatgen`.
- Filtered evaluation dry-run:
  - Command: `PYTHONPATH=src:. python eval/scripts/run_claude_eval.py --dry-run --task impedance-fit-randles-cpe-warburg --variant package-skill --results /private/tmp/materials-skills-single-dry-run.jsonl`
  - Output: one package-skill record for the impedance.py task.
- impedance.py manual prompt set:
  - `eval/impedance/prompts.md` contains three EIS prompts for equivalent
    circuit fitting, validation before fitting, and batch fitting ZPlot files.
  - `eval/impedance/tasks.json` contains the same three prompts in
    machine-readable form with success criteria; tests keep it aligned with
    `prompts.md`.
  - Tests verify the impedance manifest dry-runs through
    `run_claude_eval.py` to exactly 6 records: baseline and package-skill for
    each of the three prompts.
  - Tests verify the committed `eval/impedance/dry-run-results.jsonl` artifact
    still matches the manifest and remains an intentionally incomplete dry-run
    with 0/6 complete records.
  - Dry-run command
    `PYTHONPATH=src:. python eval/scripts/run_claude_eval.py --tasks eval/impedance/tasks.json --dry-run --results eval/impedance/dry-run-results.jsonl`
    wrote 6 baseline/package-skill records.
  - Completeness command
    `PYTHONPATH=src:. python eval/scripts/check_eval_completeness.py --tasks eval/impedance/tasks.json --results eval/impedance/dry-run-results.jsonl --json`
    correctly rejected the dry-run with 0/6 complete records.
  - The committed `eval/impedance/score-report.md` now contains the real
    six-record manual scoring result rather than the dry-run scaffold.
  - `eval/impedance/results.md` records the first-package observations: two
    package-skill wins and one tie.
  - Tests verify the committed impedance results have 6 complete records and
    the committed score report passes the manual-scoring gate.
- Resumable evaluation behavior:
  - Tests verify cross-library package-skill composition through the
    ASE+pymatgen+MACE task's `context_skills`.
  - Tests verify the completeness gate rejects package-skill records whose
    `context_skills` do not match the task manifest.
  - Tests verify the completeness gate rejects K-Dense records whose
    `context_skills` do not name the compared skill.
  - Tests verify the completeness gate rejects baseline records that have
    loaded skill context or missing context-skill metadata; baseline records
    must have `context_status: "not-applicable"` and explicit empty
    `context_skills`.
  - Tests verify the completeness gate rejects records whose `skill` metadata
    is missing or does not match the task manifest.
  - Tests verify real non-dry-run matrices fail before model calls when a
    selected K-Dense variant has no matching `--kdense-root`.
  - Tests verify `--preflight-only` checks Claude readiness without writing
    evaluation records.
  - Tests verify `--preflight-only` reports a missing `claude` executable as a
    clean preflight failure instead of raising a traceback.
  - Tests verify direct model calls with `--skip-preflight` record missing
    `claude` executable failures as error records instead of raising tracebacks.
  - Tests verify missing package-skill context under `--skills-root` fails
    cleanly before writing results, and that baseline-only filtered runs do not
    require package-skill files.
  - Tests verify a missing task manifest path is reported as an argparse error
    instead of raising a filesystem traceback.
  - Tests verify task manifests are schema-checked for required fields,
    whitespace-padded IDs, skill names, titles, and prompts, malformed optional fields such as
    `context_skills`, reject unregistered primary and composed context skills,
    reject duplicate task IDs before result keys can collide, reject duplicate
    or whitespace-padded success criteria, reject duplicate or whitespace-padded
    composed context skills, and require composed package-skill contexts to
    include the primary task skill.
  - Tests verify the completeness, score-rendering, score-checking, and
    combined artifact gate commands share the same missing-task-manifest
    argparse failure behavior.
  - Tests verify the completeness gate rejects package-skill/K-Dense records
    whose `context_status` is not `provided`.
  - Tests verify the completeness gate reports a missing results file as
    structured JSON instead of raising a traceback.
  - Tests verify malformed evaluation JSONL records include line-numbered
    parser errors and are reported by the completeness gate as invalid results
    files instead of raising tracebacks.
  - Tests verify evaluation JSONL records must include non-empty `task_id`,
    allowlisted `variant`, and allowlisted `status` fields before scoring or
    artifact checks use them.
  - Tests verify `variant: "preflight"` is only accepted with the sentinel
    `task_id: "__preflight__"`, and that the sentinel task ID is only accepted
    for preflight records.
  - Tests verify preflight result records must have `status: "error"`.
  - Tests verify preflight result records must not include task context
    metadata.
  - Tests verify optional result `context_status` values are allowlisted before
    score rendering or resume logic uses them.
  - Tests verify optional result `context_skills` metadata names registered
    skills before score rendering or resume logic uses it.
  - Tests verify result `returncode` metadata is consistent with `status` when
    present.
  - Tests verify expected completed result records include non-empty `prompt`
    provenance before the completeness gate accepts them.
  - Tests verify committed full dry-run, K-Dense dry-run, auth-preflight, and
    auth-blocked JSONL artifacts match the current task manifest shape,
    expected statuses, context metadata, and auth sentinel semantics.
  - Tests verify the README direct `--skip-preflight` example writes to a
    disposable result file instead of the canonical `eval/results.jsonl`.
  - Tests verify `--resume` validates existing result files before preflight and
    reports malformed existing JSONL as an argparse error.
  - Tests verify existing `ok` task/variant records are preserved and skipped.
  - Tests verify existing `error` task/variant records are preserved but rerun.
  - Tests verify preflight failure with `--resume` preserves existing records
    before appending the `__preflight__` error.
  - Tests verify completed model-call records are persisted before the next
    model call, preserving progress from interrupted runs.
- K-Dense dry-run:
  - Command: `PYTHONPATH=src:. python eval/scripts/run_claude_eval.py --dry-run --kdense-root eval/kdense-public --results eval/kdense-dry-run-results.jsonl`
  - Output: 11 records, with the K-Dense variant using the public K-Dense
    pymatgen skill.
- K-Dense missing-context guard:
  - Command: `PYTHONPATH=src:. python eval/scripts/run_claude_eval.py --results /private/tmp/materials-skills-no-kdense-root-real.jsonl --skip-preflight --max-budget-usd 0.01`
  - Output: nonzero exit before model calls with `Missing K-Dense skill
    context...`; no result file was written.
- Evaluation score report:
  - Tests verify the score-report renderer uses the latest record for duplicate
    task/variant pairs, matching resume/completeness semantics and avoiding
    stale rerun output in manual scoring.
  - Tests verify the renderer refuses to overwrite a manually scored report
    without `--overwrite-report`, allows intentional replacement with
    `--overwrite-report`, and replaces existing unscored scaffolds.
  - Tests verify committed full-matrix, K-Dense dry-run, auth-preflight, and
    auth-blocked score reports exactly match their source JSONL artifacts.
  - Tests verify model output containing Markdown fences, variant-looking
    headings, or summary-looking rows is fenced safely and ignored by report
    structure checks.
  - Tests verify unfilled scoring markers inside fenced model output, such as
    model-provided checklists or literal `Outcome: not-scored` text, do not
    falsely block an otherwise completed manual score report.
  - Tests verify the score-report gate rejects manually edited variant sections
    that drop generated audit fields: status, context status, context skills,
    prompt provenance, or model output.
  - Tests verify the score-report gate rejects prompt audit blocks that do not
    include the corresponding task manifest prompt.
  - Tests verify the score-report gate rejects scored variant sections whose
    retained status field is not `ok`.
  - Tests verify the score-report gate rejects retained context status or
    context skills that are unparseable or no longer match the expected
    baseline, package-skill, or K-Dense variant context.
  - Tests verify the score-report gate rejects variant sections whose retained
    model output block is missing or empty.
  - Tests verify the score-report gate rejects unexpected variant sections
    inside a task.
  - Tests verify the score-report gate rejects unexpected task sections and
    unexpected comparison summary rows outside the task manifest.
  - Tests verify expected comparison summary rows must appear in the actual
    `## Comparison Summary` section, not in reviewer notes elsewhere in the
    report.
  - Tests verify the comparison summary table header must also appear in that
    section.
  - Tests verify duplicate comparison summary sections are rejected.
  - Missing-results behavior is covered by tests with temporary paths; the
    committed `eval/results.jsonl` now exists and contains the real 11-record
    full matrix.
  - Command: `PYTHONPATH=src:. python eval/scripts/score_results.py --results eval/dry-run-results.jsonl --report eval/score-report.md`
  - Output: `eval/score-report.md` with a comparison summary table, criteria
    checklists, context status, loaded context skills, and blocked/dry-run
    outputs.
  - Command: `PYTHONPATH=src:. python eval/scripts/score_results.py --results eval/auth-preflight-results.jsonl --report eval/auth-preflight-score-report.md`
  - Output: `eval/auth-preflight-score-report.md` with the same comparison
    summary plus the auth preflight error.
- Score-report gate:
  - Tests verify duplicate task sections and duplicate comparison summary rows
    in manually edited reports are rejected.
  - Tests verify duplicate variant sections in a manually edited score report
    are rejected instead of silently checking only the first section.
  - Command: `python eval/scripts/check_score_report.py --report eval/score-report.md --json`
  - Output: `{"ok": true, "problems": []}` for the committed manually scored
    full-matrix report.
- Combined artifact gate:
  - Command: `PYTHONPATH=src:. python eval/scripts/check_eval_artifacts.py --results eval/dry-run-results.jsonl --report eval/score-report.md --json`
  - Output: nonzero exit combining the dry-run model-output failures with the
    unfilled score-report failures; JSON includes `blockers: ["evaluation",
    "scoring"]`.
  - Command: `PYTHONPATH=src:. python eval/scripts/check_eval_artifacts.py --tasks eval/tasks/v0_tasks.json --results eval/auth-blocked-results.jsonl --report eval/auth-blocked-score-report.md --json`
  - Output: nonzero exit with 0/11 expected records complete because every
    variant has `status: "error"` from missing Claude auth, plus the unfilled
    manual-scoring placeholders.
- Evaluation completeness gate:
  - Command: `python eval/scripts/check_eval_completeness.py --results eval/results.jsonl --json`
  - Output: `ok: true`, `expected_count: 11`, `complete_count: 11`, and no
    problems for the committed full-matrix results.
  - Command: `PYTHONPATH=src:. python eval/scripts/check_eval_completeness.py --results eval/dry-run-results.jsonl --json`
  - Output: nonzero exit with 11 dry-run status problems.
  - Command: `PYTHONPATH=src:. python eval/scripts/check_eval_completeness.py --results eval/auth-preflight-results.jsonl --json`
  - Output: nonzero exit with 11 missing expected results plus one unexpected
    `__preflight__` error record.
- Evaluation runbook:
  - `eval/README.md` documents the exact post-login preflight-only auth check,
    first-package impedance pipeline, smoke test, full
    baseline/package-skill/K-Dense matrix run, resumable rerun, completeness
    gate, manual score-report commands, and `run_v0_pipeline.py` wrapper.
  - Tests verify the wrapper stops after a failed preflight without writing the
    full results JSONL, smoke-results JSONL, or score report, writes a score
    report scaffold after complete model outputs, and can run the final scored
    artifact gate without re-calling Claude or overwriting the report. Tests
    verify a nominally successful model run that fails to write a results file
    is reported as an incomplete evaluation instead of raising a traceback.
    Tests also verify `--check-scored` is rejected unless `--skip-model-run` is set,
    `--skip-model-run` is rejected unless `--check-scored` is set, and that
    model-run mode refuses to overwrite an already manually scored report
    unless `--overwrite-report` is passed. The impedance-specific wrapper has
    matching preflight-no-artifact, missing-results, and overwrite-protection
    tests.
  - Dry-run of the runbook full-matrix command wrote 11 records to
    `/private/tmp/materials-skills-runbook-dry-run.jsonl`.
  - Completeness gate rejected that dry-run result because all 11 records had
    `status: "dry-run"`, confirming the runbook still requires real model
    outputs.
  - Score-report generation succeeded for the runbook dry-run at
    `/private/tmp/materials-skills-runbook-score-report.md`.
- Auth-blocked evaluation attempt:
  - Command: `PYTHONPATH=src:. python eval/scripts/run_claude_eval.py --kdense-root eval/kdense-public --results eval/auth-blocked-results.jsonl --max-budget-usd 0.05 --skip-preflight`
  - Output: 11 structured error records, each returning `Not logged in - Please
    run /login`, while preserving baseline, package-skill, and K-Dense context
    metadata for the attempted records.
  - Score report: `eval/auth-blocked-score-report.md`.
- Claude preflight failure path:
  - Command: `PYTHONPATH=src:. python eval/scripts/run_v0_pipeline.py --results /private/tmp/materials-skills-pipeline-auth-check.jsonl --report /private/tmp/materials-skills-pipeline-auth-check.md --smoke-results /private/tmp/materials-skills-pipeline-smoke.jsonl --max-budget-usd 0.01`
  - Output: stopped at `Step 1/4: Claude preflight` after the evaluator reported
    `loggedIn=false` from `claude auth status --json`, then printed the explicit
    remedy: `Run claude auth login, then rerun this pipeline command`; no smoke
    test, matrix run, or report generation ran.
    Tests assert the wrapper-level login remedy for both the full v0 and
    impedance-specific pipelines while preserving the no-artifact behavior.
  - Command: `PYTHONPATH=src:. python eval/scripts/run_claude_eval.py --preflight-only --results /private/tmp/materials-skills-preflight-only-results.jsonl --max-budget-usd 0.01`
  - Output: nonzero exit with `Claude auth status reports loggedIn=false` and no
    result file written.
  - Command: `PYTHONPATH=src:. python eval/scripts/run_claude_eval.py --kdense-root eval/kdense-public --results eval/auth-preflight-results.jsonl --max-budget-usd 0.01`
  - Output: one structured `__preflight__` error record reporting
    `loggedIn=false` from `claude auth status --json`, proving the harness now
    fails fast before a model probe when Claude auth is missing.
  - Score report: `eval/auth-preflight-score-report.md`, including the
    preflight failure message before the missing task variants.

## Not Yet Complete

- Hosted/shared registry distribution is not implemented; the tested v0 shape
  is a hybrid of package-shipped skills plus a JSON-exportable registry.
- Empirical evidence is one real Claude run per task/variant, not a statistical
  evaluation. It is enough for the v0 demo and concrete behavioral examples,
  but not for broad claims about model families or repeatability.
- Cross-library composition needs a follow-up bridge-artifact test: the
  ASE+pymatgen+MACE package-skill variant loaded all intended context but lost
  to baseline on conversion-check rigor.
- All 10 requested package skills exist.
- Registry maps the full initial Tier A/B/C target set.
- Hybrid registry plus package-shipped skills is implemented and tested locally:
  the package ships skill content, while `materials-skills registry --json`
  exposes the package-to-skill map as a central artifact. A hosted/shared
  registry has not been tested.
- Short contribution writeup, first-package impedance results, full v0 results,
  and manually scored score reports exist and pass their artifact gates.

# Completion Audit

## Objective Restated

Build a v0 demo of an environment-aware materials/chemistry skills layer:

1. Read an installed Python environment or exported environment file.
2. Map installed packages to package-scoped skills.
3. Install matching skills into agent directories such as `.claude/skills` and
   `.cursor/skills`.
4. Provide 8-10 high-quality package skills for the priority stack.
5. Empirically compare baseline, K-Dense where applicable, and these skills on
   representative tasks.
6. Write up the contribution and unresolved design questions.

## Prompt-To-Artifact Checklist

| Requirement | Evidence | Status |
| --- | --- | --- |
| Working CLI `materials-skills install` | `src/materials_skills/cli.py`, factored helpers in `environment.py`, `install.py`, `validation.py`, and `versions.py`, `pyproject.toml` script entry, thin-CLI line-count regression test | Implemented; `cli.py` is 181 lines |
| Package-data skills for installed CLI | `src/materials_skills/skills/*/SKILL.md`, `scripts/sync_packaged_skills.py --check`, sync consistency and drift-detection tests | Source-tree verified |
| Wheel/sdist build and installed CLI | `dist/materials_skills-0.1.0-py3-none-any.whl`, `dist/materials_skills-0.1.0.tar.gz`, `materials-skills --version`, `scripts/check_wheel_skills.py`, `scripts/check_wheel_install.py`, `scripts/check_sdist_payload.py`, `/private/tmp/materials-skills-wheel-venv`, `/private/tmp/materials-skills-wheel-venv-condalist`, `/private/tmp/materials-skills-wheel-venv-explicit`, `/private/tmp/materials-skills-wheel-venv-validate-strict`, `/private/tmp/materials-skills-wheel-venv-force`, `/private/tmp/materials-skills-wheel-venv-actions`, `/private/tmp/materials-skills-wheel-venv-dryrun-preview`, `/private/tmp/materials-skills-wheel-venv-match-trace`, `/private/tmp/materials-skills-wheel-venv-agent-all`, `/private/tmp/materials-skills-wheel-venv-stdin`, `/private/tmp/materials-skills-wheel-venv-parse-errors`, `/private/tmp/materials-skills-wheel-venv-condajson`, `/private/tmp/materials-skills-wheel-venv-http-pipreq-wheelname`, `/private/tmp/materials-skills-wheel-venv-sync-check`, `/private/tmp/materials-skills-wheel-venv-release-check`, `/private/tmp/materials-skills-wheel-venv-version-provenance`, `/private/tmp/materials-skills-wheel-venv-compatibility-status` install tests | Verified; wheel checker also rejects source-only `eval/`, `docs/`, `research/`, `scripts/`, `skills/`, and `tests/` payload leakage |
| Skill validation gate | `materials-skills validate`, validation tests for required sections/frontmatter, non-empty required metadata, related skills, malformed inline lists, canonical URLs, sync | Verified |
| Registry export | `materials-skills registry --json`, `registry.json`, `scripts/check_registry_json.py`, registry tests, registry uniqueness and static-registry sync/write tests | Verified |
| Reads pip list/freeze/direct refs | `parse_pip_list`, `tests/fixtures/pip-list.txt`, unit tests for tables, pins, spaced version operators, editable/VCS `#egg=`, extras, `name @ git+...`, and bare wheel URL forms | Verified |
| Reads pip JSON | `parse_pip_json`, `tests/fixtures/pip-list.json`, unit tests | Verified |
| Reads conda env with pip block | `parse_conda_export`, `tests/fixtures/conda-env.yml`, unit tests including editable/VCS pip requirements | Verified |
| Reads conda list table/export/explicit | `parse_conda_list`, `tests/fixtures/conda-list.txt`, `tests/fixtures/conda-list-export.txt`, `tests/fixtures/conda-explicit.txt`, unit tests | Verified |
| Reads conda JSON env/list output | `parse_conda_json`, JSON shape auto-detection, `tests/fixtures/conda-env.json`, `tests/fixtures/conda-list.json`, unit tests, dry-run install | Verified |
| Reads environment from stdin | `--env -`, parser and install-command tests, manual pipe dry-run | Verified |
| Reads current Python environment | `detect_current_environment_details`, `metadata.distributions()` tests, pip JSON fallback test, no-`--env` install-command test | Verified |
| Maps env packages to skills | `src/materials_skills/registry.py`, registry uniqueness, alias-conflict, and match-provenance tests | Verified |
| Reports env/source/format/version/agent provenance | install JSON `environment` object with `package_versions`, top-level `agent`, `load_environment` tests, current-env version tests, requested-agent tests, manual stdin and conda JSON dry-runs | Verified |
| Writes to `.claude/skills` style target | end-to-end install to `/private/tmp/materials-skills-demo10/.claude/skills` | Verified |
| Supports `.cursor/skills` style target | copied to `/private/tmp/materials-skills-demo10-cursor/.cursor/skills` | Verified |
| Supports built-in multi-agent install | `--agent all`, target-selection and integration tests for `.claude/skills`, `.cursor/skills`, `.codex/skills` | Verified |
| Avoids silent overwrite of edited skills | idempotent install tests, action-status JSON tests, dry-run conflict previews, modified-skill error test, `--force` overwrite test, preflight conflict tests that prevent partial copying within one target and across `--agent all`, including no empty target roots for untouched agents after a conflict | Verified |
| Reports install failures cleanly | JSON error tests for missing env files, malformed env input, overwrite conflicts, and install-time OS errors; target-root and install-action preflight tests prevent partial copies | Verified |
| Explains why skills matched | install JSON `matches`, per-action `matched_distributions`/`matched_versions`, `compatible_versions` and advisory `compatibility`, alias-preservation and compatibility-status tests | Verified |
| Concrete v0 CLI demo | `docs/v0-demo.md`, mixed conda+pip fixture dry-run documenting `"agent": "all"`, `--agent all` install test | Implemented |
| 8-10 skills | `skills/{ase,pymatgen,rdkit,mace,impedance,py4dstem,hyperspy,pybamm,pyscf,openmm}/SKILL.md` | Implemented, 12 total |
| Skills stay compact | `validate_skills` 300-line cap, line-limit regression test, `wc -l skills/*/SKILL.md` | Verified; current skills are 138-175 lines |
| Evidence notes for skills | `research/*.md` for all 12 skills, research-note coverage test | Verified |
| Evaluation prompts | `eval/*/prompts.md` for all 12 skills; prompt-coverage test; `eval/impedance/prompts.md` and `eval/impedance/tasks.json` have 3 EIS prompts | Implemented |
| Five representative empirical tasks | `eval/tasks/v0_tasks.json` | Implemented |
| Empirical runner | `eval/scripts/run_claude_eval.py`, `eval/dry-run-results.jsonl`, filtered dry-run, composed `context_skills`, context-status metadata, K-Dense missing-context guard, task-manifest schema guard, preflight-only, auth-status-first fail-fast preflight, incremental result persistence, and resume tests | Dry-run, filtering, composed context skills, context status, K-Dense guard, task-manifest validation, preflight-only, auth-status-first preflight, incremental persistence, resume, and committed JSONL artifact shape verified |
| Empirical scorer | `eval/scripts/score_results.py`, `eval/score-report.md`, `eval/auth-preflight-score-report.md` | Dry-run, K-Dense dry-run, auth-preflight, and auth-blocked reports verified with exact regeneration from source JSONL, comparison summary, context status, loaded skill lists, prompt provenance, and model output; missing results file path fails cleanly; direct renderer refuses to overwrite manually scored reports without `--overwrite-report` while allowing unscored scaffold regeneration |
| Manual scoring gate | `eval/scripts/check_score_report.py`, score-report gate tests, current dry-run report failure | Verified failing until there is exactly one `## Comparison Summary` section, only expected task/variant sections exist exactly once, the comparison table header and every expected summary row are in the summary section, all success criteria are checked, manual outcomes are filled, generated status/context/prompt/output audit fields remain parseable with `Status: ok`, expected context values, prompt blocks containing the manifest prompt, and non-empty fenced output, scored values are valid, summary outcomes match variant outcomes, and winner/tie/blocked semantics are internally consistent; fenced model output is ignored for scoring-template markers and report structure |
| Empirical completeness gate | `eval/scripts/check_eval_completeness.py`, completeness tests, missing-results/dry-run/auth-preflight/skill-metadata/prompt-provenance/context-status/baseline-context/package-context-skills/K-Dense-context-skills failures | Verified failing until real outputs exist, prompt provenance is present, skill metadata matches the task manifest, baseline records explicitly prove they are context-free, and package/K-Dense records have intended context |
| Combined empirical artifact gate | `eval/scripts/check_eval_artifacts.py`, combined-gate tests | Verified failing until both empirical gates pass; JSON includes `blockers` naming `evaluation` and/or `scoring` failures |
| Local non-empirical gate wrapper | `scripts/check_local_v0.py`, wrapper command-list test | Verified |
| Combined v0 status command | `scripts/check_v0_status.py`, status aggregation tests, real workspace run | Verified reporting local `ok: true` only when unit tests, skill validation, package-data sync, registry JSON sync, wheel payload, wheel install smoke, and source-distribution payload checks are clean; checks impedance and full-matrix artifact gates with separate paths; now reports overall `ok: true` after both empirical artifact gates pass; tests still cover incomplete-artifact blockers, post-login `next_steps`, `automation_steps`, text-mode nested empirical blockers, and missing task manifests as argparse errors without tracebacks |
| Direct script execution from checkout | `scripts/_bootstrap.py`, `eval/scripts/_bootstrap.py`, direct-execution tests for release helpers, v0 status, and evaluation entry points | Verified no manual `PYTHONPATH=src:.` prefix is needed for current release/status/evaluation script commands |
| Post-login empirical runbook | `eval/README.md` impedance/full/resume/gate/scoring commands, `eval/scripts/run_impedance_pipeline.py`, and `eval/scripts/run_v0_pipeline.py` wrappers | Implemented; first-package and full-matrix wrappers stop on failed preflight before writing result/report artifacts, print the `claude auth login` remedy, fail cleanly on missing task manifests, and final scored gates plus model-run/skip-run guards prevent accidental report overwrite or skipped validation; failed final gates print the combined artifact `blockers` summary and support JSON output for automation |
| Empirical baseline vs skills | `eval/results.jsonl`, `eval/score-report.md`, `python eval/scripts/run_v0_pipeline.py --skip-model-run --check-scored` | Complete; 11 real Claude records and manually scored full-matrix artifact gate pass |
| First-package manual EIS testing | `eval/impedance/results.jsonl`, `eval/impedance/score-report.md`, `eval/impedance/results.md`, `python eval/scripts/run_impedance_pipeline.py --skip-model-run --check-scored` | Complete; six real Claude records, two package-skill wins, one tie |
| K-Dense comparison | Public K-Dense pymatgen fixture in `eval/kdense-public/pymatgen/SKILL.md`, `eval/results.jsonl`, `eval/score-report.md` | Complete for v0; K-Dense pymatgen variant ran and was manually scored loss against the baseline/package-skill outputs |
| K-Dense pymatgen audit | `docs/kdense-pymatgen-comparison.md`, `research/pymatgen.md`, and `EvalHarnessTests.test_pymatgen_research_note_points_to_prepared_kdense_comparison` | Implemented; regression test verifies the research note points to the prepared K-Dense fixture and the v0 manifest marks the phase-diagram task as K-Dense applicable |
| Short contribution writeup | `docs/writeup.md` | Implemented with empirical results and limitations |
| Open design-question status | `docs/design-decisions.md`, docs coverage test | Implemented with post-v0 risks separated from achieved v0 evidence |
| Extension environment-discovery benchmark | `eval/tasks/extension_tasks.json`, `eval/scripts/score_extension_results.py`, `eval/extension-results.jsonl`, `eval/extension-score-report.md` | Implemented and rerun; three hidden-rubric baseline/package-skill prompts with documentation sources exist for each active skill. Current full run: baseline 109/180, package-skill 165/180, with 11 package-skill suite wins and one baseline win |
| Black-box skill optimization harness | `eval/scripts/optimize_skills.py`, `eval/optimization-mace/report.md` | Implemented; MACE candidate-notes scored 11/15 vs 10/15 original on heldout. Generic notes were folded into the canonical MACE skill, while automatic promotion still requires a train/dev selection split |

## Latest Verification

```bash
PYTHONPATH=src:. python -m unittest discover -s tests
```

Result: 320 tests passing.

```bash
python scripts/check_local_v0.py
```

Result: local non-empirical v0 checks passed: unit tests, skill validation,
package-data sync, registry JSON sync, wheel payload, installed-wheel smoke, and
source-distribution payload checks.

```bash
uv build
```

Result: rebuilt `dist/materials_skills-0.1.0.tar.gz` and
`dist/materials_skills-0.1.0-py3-none-any.whl`.

```bash
python scripts/check_v0_status.py --json
```

Result: returned zero with `local.ok: true`, `empirical.ok: true`, empty
`blockers`, empty `next_steps`, and empty `automation_steps` after
`eval/impedance/results.jsonl`, `eval/results.jsonl`, and their manually scored
reports were generated and validated.

```bash
PYTHONPATH=src python -m materials_skills.cli validate \
  --source-root skills \
  --json
```

Result: `{"ok": true, "errors": []}`.

Additional May 13, 2026 prompt-to-artifact spot checks:

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-audit-real \
  --force \
  --json
```

Result: parsed the pip-list fixture as `format: "pip"`, matched all 12
registered package skills, reported matched distribution names, matched
versions, compatible-version metadata, and advisory `compatibility:
"compatible"` for each skill, and wrote all 12 skill directories under the
temporary target.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/conda-env.yml \
  --agent all \
  --dry-run \
  --json
```

Result: parsed the mixed conda+pip fixture as `format: "conda"`, matched all
10 registered package skills, and planned installs for all three built-in
targets: `.claude/skills`, `.cursor/skills`, and `.codex/skills`.

```bash
python eval/scripts/check_eval_artifacts.py \
  --tasks eval/impedance/tasks.json \
  --results eval/impedance/results.jsonl \
  --report eval/impedance/score-report.md \
  --json
```

Result: passes after the real six-record impedance matrix and manual score
report were generated.

The validation tests cover missing required sections, frontmatter name
mismatch, duplicate skill names, missing `related_skills`, empty required
frontmatter values including empty block-scalar descriptions, malformed inline
`related_skills` lists, unregistered duplicate, and self-referential
related-skill references, malformed or duplicate canonical links, normalized
duplicate canonical links, canonical links without hosts, malformed
`version`/`compatible_versions` metadata, inverted compatibility bounds, the
300-line compact-skill cap, and
packaged-vs-source sync.

Research-evidence tests verify every registered skill has a matching
`research/<skill>.md` note with reviewed sources, extracted workflow notes,
a gotchas section, open follow-ups, and at least three source URLs.
`research/impedance.md` additionally records a May 12, 2026 freshness check
against current impedance.py docs and issue pages.
`research/pymatgen.md` is also tied by regression test to the prepared
K-Dense fixture at `eval/kdense-public/pymatgen/SKILL.md` and to the
`pymatgen-phase-diagram-lifepo4` K-Dense comparison row in the v0 manifest.

Release and evaluation script direct-execution tests remove `PYTHONPATH` from
the environment, then run representative `scripts/*.py` and `eval/scripts/*.py`
entry points from the checkout. These tests verify that expected argparse or
missing-artifact errors are reached without `ModuleNotFoundError`.

```bash
python scripts/sync_packaged_skills.py --check
```

Result: `Packaged skills are in sync`. Tests also verify this checker fails on
missing, extra, and changed packaged skill files before sync mode restores the
destination.

```bash
python scripts/check_wheel_skills.py \
  dist/materials_skills-0.1.0-py3-none-any.whl \
  --source-root skills \
  --package-root src/materials_skills \
  --console-script materials-skills \
  --pyproject pyproject.toml \
  --readme README.md
```

Result: `Wheel payload is complete`. Tests also verify this checker accepts
complete wheel payloads and rejects missing, extra, or stale skill files
relative to the source `skills/` tree, plus missing, extra, or stale Python
modules relative to `src/materials_skills/`, and a missing console-script
entry point, inconsistent package/wheel versions, or stale README metadata.

```bash
python scripts/check_sdist_payload.py \
  dist/materials_skills-0.1.0.tar.gz \
  --source-root skills \
  --package-root src/materials_skills \
  --scripts-root scripts \
  --docs-root docs \
  --eval-root eval \
  --research-root research \
  --tests-root tests \
  --registry-json registry.json \
  --readme README.md \
  --pyproject pyproject.toml
```

Result: `Source distribution payload is complete`. Tests also verify this
checker rejects missing, extra, or stale source skill files, packaged skill
files, Python modules, release scripts, docs content, evaluation harness and
artifact content, research-note content, test and fixture content, registry JSON
content, README content, `pyproject.toml` content, and duplicate archive paths.

```bash
python scripts/check_wheel_install.py \
  dist/materials_skills-0.1.0-py3-none-any.whl
```

Result: installed the wheel into a temporary venv with `--no-index`, then
exercised the installed `materials-skills` console script through `--version`,
`validate`, `registry`, a real install from `tests/fixtures/pip-list.txt`, and
an `--agent all --dry-run --json` targeting check. Tests also verify that
malformed installed JSON shapes, missing installed agent provenance, malformed
installed `--agent all` dry-run provenance, malformed skill-name values,
same-count but wrong-name installed skill selections, and extra target skill
directories are rejected.

```bash
PYTHONPATH=src python -m materials_skills.cli registry --json
```

Result: emitted 10 registry records mapping installed distribution names and
aliases to package-scoped skill directories.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-packaged-default/.claude/skills \
  --json
```

Result: installed all 12 authored skills using the default packaged skills root
without passing `--skills-root`.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-match-trace/.claude/skills \
  --skills-root skills \
  --dry-run \
  --json
```

Result: matched all 12 authored skills and emitted `matches` provenance showing
which installed distribution names triggered each skill and which registered
aliases were considered.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/pip-list.txt \
  --agent all \
  --skills-root skills \
  --dry-run \
  --json
```

Result: matched all 12 authored skills for each built-in agent target and
emitted `targets: [".claude/skills", ".cursor/skills", ".codex/skills"]`.

```bash
cat tests/fixtures/pip-list.txt | /usr/bin/env PYTHONPATH=src \
  python -m materials_skills.cli install \
  --env - \
  --target /private/tmp/materials-skills-stdin-demo/.claude/skills \
  --skills-root skills \
  --dry-run \
  --json
```

Result: stdin input auto-inferred as a pip-list style environment and matched
all 12 authored skills.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/conda-env.json \
  --target /private/tmp/materials-skills-conda-json/.codex/skills \
  --skills-root skills \
  --dry-run \
  --json
```

Result: `conda env export --json` style input with nested pip dependencies
matched all 12 authored skills.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/conda-list.json \
  --target /private/tmp/materials-skills-conda-list-json-auto/.codex/skills \
  --skills-root skills \
  --dry-run \
  --json

PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/pip-list.json \
  --target /private/tmp/materials-skills-pip-json-auto/.claude/skills \
  --skills-root skills \
  --dry-run \
  --json
```

Result: auto-detection now distinguishes conda list JSON from pip JSON list
using conda-specific package metadata while preserving pip JSON behavior.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/conda-list.json \
  --target /private/tmp/materials-skills-env-metadata/.codex/skills \
  --skills-root skills \
  --dry-run \
  --json

cat tests/fixtures/pip-list.txt | /usr/bin/env PYTHONPATH=src \
  python -m materials_skills.cli install \
  --env - \
  --target /private/tmp/materials-skills-env-metadata-stdin/.claude/skills \
  --skills-root skills \
  --dry-run \
  --json
```

Result: install JSON now includes `environment.source`,
`environment.requested_format`, `environment.format`, and
`environment.package_count`; newer runs also include
`environment.package_versions` when the input format carries versions.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env /private/tmp/materials-skills-missing-env.txt \
  --target /private/tmp/materials-skills-parse-error/.claude/skills \
  --json

printf '{not json\n' | /usr/bin/env PYTHONPATH=src \
  python -m materials_skills.cli install \
  --env - \
  --format pip-json \
  --target /private/tmp/materials-skills-parse-error/.claude/skills \
  --json
```

Result: missing environment files and malformed JSON input return structured
`{"ok": false, "error": ...}` responses instead of tracebacks.

```bash
uv run --with build --with hatchling python -m build --wheel
/private/tmp/materials-skills-wheel-venv/bin/materials-skills validate --json
/private/tmp/materials-skills-wheel-venv/bin/materials-skills install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-wheel-install/.claude/skills \
  --json
```

Result: built the wheel, validated the installed console script, and installed
all 12 skills from wheel package data.

```bash
/private/tmp/materials-skills-wheel-venv-http-pipreq-wheelname/bin/materials-skills install \
  --env /private/tmp/materials-skills-http-pipreq.txt \
  --target /private/tmp/materials-skills-wheel-http-pipreq-wheelname-real/.claude/skills \
  --dry-run \
  --json
```

Result: rebuilt wheel parsed the HTTP requirements file as `format: "pip"` and
selected both `impedance` from a bare wheel URL and `rdkit` from a named HTTP
direct reference. Parser regression coverage now also verifies that named
direct-reference wheel URLs preserve the version, for example
`package_versions["rdkit"] == "2026.03.2"`.

```bash
/private/tmp/materials-skills-wheel-venv-sync-check/bin/materials-skills validate --json
/private/tmp/materials-skills-wheel-venv-sync-check/bin/materials-skills install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-wheel-sync-check/.claude/skills \
  --dry-run \
  --json
```

Result: rebuilt wheel validated packaged skills and dry-run matched all 12
authored skills from the installed console script.

```bash
rg -n "check_wheel_skills" \
  /private/tmp/materials-skills-wheel-inspect-latest/materials_skills-0.1.0.dist-info/METADATA
/private/tmp/materials-skills-wheel-venv-release-check/bin/materials-skills validate --json
/private/tmp/materials-skills-wheel-venv-release-check/bin/materials-skills install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-wheel-release-check/.claude/skills \
  --dry-run \
  --json
```

Result: rebuilt wheel metadata includes the latest README packaging command,
installed console script validated packaged skills, and dry-run matched all 12
authored skills from `tests/fixtures/pip-list.txt`.

```bash
/private/tmp/materials-skills-wheel-venv-sync-check/bin/materials-skills install \
  --target /private/tmp/materials-skills-wheel-current-env/.claude/skills \
  --dry-run \
  --json
```

Result: installed console script used the current fresh wheel venv when `--env`
was omitted, reported `source: "current"` and
`format: "installed-distributions"`, and selected no skills because only
unrelated packages were installed in that venv.

```bash
/private/tmp/materials-skills-wheel-venv-match-trace/bin/materials-skills validate --json
/private/tmp/materials-skills-wheel-venv-match-trace/bin/materials-skills install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-wheel-match-trace-real/.claude/skills \
  --dry-run \
  --json
```

Result: rebuilt wheel carried match-provenance JSON; installed console script
validated package data and emitted `matches` plus per-action
`matched_distributions`.

```bash
/private/tmp/materials-skills-wheel-venv-agent-all/bin/materials-skills validate --json
/private/tmp/materials-skills-wheel-venv-agent-all/bin/materials-skills install \
  --env /Users/charl/Programming/science-software-skills/tests/fixtures/pip-list.txt \
  --agent all \
  --dry-run \
  --json
```

Result: rebuilt wheel carried `--agent all`; installed console script validated
package data and emitted all three built-in targets. A real write attempt in
this Codex sandbox hit a `.codex` permission denial and returned structured
JSON before copying any skill directories:
`{"ok": false, "error": "[Errno 1] Operation not permitted: .../.codex"}`.

```bash
/private/tmp/materials-skills-wheel-venv-stdin/bin/materials-skills validate --json
cat tests/fixtures/pip-list.txt | \
  /private/tmp/materials-skills-wheel-venv-stdin/bin/materials-skills install \
  --env - \
  --target /private/tmp/materials-skills-wheel-stdin-real/.claude/skills \
  --dry-run \
  --json
```

Result: rebuilt wheel carried stdin support; installed console script validated
package data and matched all 12 authored skills from pip-list text piped to
stdin.

```bash
/private/tmp/materials-skills-wheel-venv-parse-errors/bin/materials-skills validate --json
/private/tmp/materials-skills-wheel-venv-parse-errors/bin/materials-skills install \
  --env /private/tmp/materials-skills-missing-env.txt \
  --target /private/tmp/materials-skills-wheel-parse-errors/.claude/skills \
  --json

printf '{not json\n' | \
  /private/tmp/materials-skills-wheel-venv-parse-errors/bin/materials-skills install \
  --env - \
  --format pip-json \
  --target /private/tmp/materials-skills-wheel-parse-errors/.claude/skills \
  --json
```

Result: rebuilt wheel carried environment parse-error handling; installed
console script returned structured JSON errors for both missing files and
malformed pip JSON.

```bash
/private/tmp/materials-skills-wheel-venv-condajson/bin/materials-skills validate --json
/private/tmp/materials-skills-wheel-venv-condajson/bin/materials-skills install \
  --env tests/fixtures/conda-env.json \
  --target /private/tmp/materials-skills-wheel-condajson-real/.codex/skills \
  --dry-run \
  --json
/private/tmp/materials-skills-wheel-venv-condajson/bin/materials-skills install \
  --env tests/fixtures/conda-list.json \
  --format conda-json \
  --target /private/tmp/materials-skills-wheel-condalistjson-real/.codex/skills \
  --dry-run \
  --json
```

Result: rebuilt wheel carried `conda-json`; installed console script matched
all 12 authored skills from the conda environment JSON fixture and the expected
subset from the conda list JSON fixture.

```bash
/private/tmp/materials-skills-wheel-venv-condajson/bin/materials-skills install \
  --env tests/fixtures/conda-list.json \
  --target /private/tmp/materials-skills-wheel-condalistjson-auto/.codex/skills \
  --dry-run \
  --json
/private/tmp/materials-skills-wheel-venv-condajson/bin/materials-skills install \
  --env tests/fixtures/pip-list.json \
  --target /private/tmp/materials-skills-wheel-pipjson-auto/.claude/skills \
  --dry-run \
  --json
```

Result: rebuilt wheel carried JSON-list shape detection; installed console
script auto-detected conda list JSON while preserving pip JSON list behavior.

```bash
/private/tmp/materials-skills-wheel-venv-condalist/bin/materials-skills registry --json
/private/tmp/materials-skills-wheel-venv-condalist/bin/materials-skills install \
  --env tests/fixtures/conda-list.txt \
  --target /private/tmp/materials-skills-wheel-condalist-real/.codex/skills \
  --json
```

Result: installed wheel exported the 12-entry registry and copied all 12
packaged skills from a `conda list` input.

```bash
/private/tmp/materials-skills-wheel-venv-explicit/bin/materials-skills install \
  --env tests/fixtures/conda-explicit.txt \
  --target /private/tmp/materials-skills-wheel-explicit-real/.codex/skills \
  --json
```

Result: installed wheel copied all 12 packaged skills from an explicit conda
package URL lockfile.

```bash
/private/tmp/materials-skills-wheel-venv-validate-strict/bin/materials-skills validate --json
/private/tmp/materials-skills-wheel-venv-validate-strict/bin/materials-skills install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-wheel-strict-real/.claude/skills \
  --json
```

Result: rebuilt wheel carried the stricter metadata validator and copied all 12
packaged skills from a pip-list input.

```bash
/private/tmp/materials-skills-wheel-venv-force/bin/materials-skills install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-wheel-force-real/.claude/skills \
  --json
/private/tmp/materials-skills-wheel-venv-force/bin/materials-skills install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-wheel-force-real/.claude/skills \
  --force \
  --json
```

Result: rebuilt wheel carried overwrite protection; installed console script
reinstalled idempotently, refused a modified skill without `--force`, and then
restored it with `--force`.

```bash
/private/tmp/materials-skills-wheel-venv-actions/bin/materials-skills install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-wheel-actions-real/.claude/skills \
  --json
/private/tmp/materials-skills-wheel-venv-actions/bin/materials-skills install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-wheel-actions-real/.claude/skills \
  --force \
  --json
```

Result: rebuilt wheel carried action-status JSON; installed console script
reported `installed`, `unchanged`, and `overwritten` statuses in the expected
cases.

```bash
/private/tmp/materials-skills-wheel-venv-dryrun-preview/bin/materials-skills install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-wheel-dryrun-preview-real/.claude/skills \
  --dry-run \
  --json
/private/tmp/materials-skills-wheel-venv-dryrun-preview/bin/materials-skills install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-wheel-dryrun-preview-real/.claude/skills \
  --dry-run \
  --force \
  --json
```

Result: rebuilt wheel carried dry-run conflict previews; installed console
script reported `would-error` for a modified skill without `--force` and
`would-overwrite` with `--force`.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/pip-list.txt \
  --target /private/tmp/materials-skills-demo10/.claude/skills \
  --skills-root skills \
  --json
```

Result: installed `ase`, `pymatgen`, `rdkit`, `mace`, `impedance`,
`py4dstem`, `hyperspy`, `pybamm`, `pyscf`, and `openmm`.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/conda-env.yml \
  --target /private/tmp/materials-skills-demo10-cursor/.cursor/skills \
  --skills-root skills \
  --json
```

Result: installed the same authored skills into a Cursor-style target.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/conda-list.txt \
  --target /private/tmp/materials-skills-conda-list/.codex/skills \
  --skills-root skills \
  --dry-run \
  --json
```

Result: matched all 12 authored skills from `conda list` table output.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/conda-list-export.txt \
  --target /private/tmp/materials-skills-conda-list-export/.codex/skills \
  --skills-root skills \
  --dry-run \
  --json
```

Result: matched all 12 authored skills from `conda list --export` package
specs.

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/conda-explicit.txt \
  --target /private/tmp/materials-skills-conda-explicit/.codex/skills \
  --skills-root skills \
  --dry-run \
  --json
```

Result: matched all 12 authored skills from an explicit conda package URL
lockfile.

```bash
python eval/scripts/run_claude_eval.py \
  --dry-run \
  --kdense-root eval/kdense-public \
  --results eval/dry-run-results.jsonl
```

Result: wrote 11 dry-run records for 5 baseline variants, 5 package-skill
variants, and 1 K-Dense variant, with `context_status` metadata showing whether
package-skill/K-Dense context was loaded and `context_skills` showing that the
ASE+pymatgen+MACE task composed `mace`, `ase`, and `pymatgen`.

```bash
sed -n '1,220p' eval/README.md
```

Result: the runbook documents the post-login preflight-only auth check, smoke
test, full matrix, resumable rerun, strict completeness gate, and manual
scoring report workflow.

```bash
python eval/scripts/run_claude_eval.py \
  --dry-run \
  --kdense-root eval/kdense-public \
  --results /private/tmp/materials-skills-runbook-dry-run.jsonl

python eval/scripts/check_eval_completeness.py \
  --results /private/tmp/materials-skills-runbook-dry-run.jsonl \
  --json

python eval/scripts/score_results.py \
  --results /private/tmp/materials-skills-runbook-dry-run.jsonl \
  --report /private/tmp/materials-skills-runbook-score-report.md
```

Result: the runbook matrix dry-run wrote 11 records, the completeness gate
correctly rejected them because they were `dry-run` records, and the score
report renderer succeeded.

```bash
python eval/scripts/check_eval_completeness.py \
  --results eval/results.jsonl \
  --json
```

Result: passes with `expected_count: 11`, `complete_count: 11`, and no
problems for the committed real model outputs.

```bash
python eval/scripts/run_claude_eval.py \
  --dry-run \
  --task impedance-fit-randles-cpe-warburg \
  --variant package-skill \
  --results /private/tmp/materials-skills-single-dry-run.jsonl
```

Result: wrote one dry-run package-skill record for the impedance.py task,
verifying the post-login smoke-test path.

```bash
PYTHONPATH=src:. python -m unittest tests.test_eval_harness
```

Result: verified filtered runs, composed `context_skills`, `context_status`
metadata, K-Dense missing-context fail-fast behavior before model calls,
`--preflight-only`, missing-`claude` preflight failure without a traceback,
direct-call missing-`claude` error records under `--skip-preflight`, fail-fast
auth preflight, `--resume` skipping existing complete current `ok` records,
rerunning stale `ok` records that lack gate metadata, rerunning existing
`error` records, preserving existing records when preflight fails, missing
package-skill files under `--skills-root`, baseline-only filtering without
package-skill files, missing task manifest paths without filesystem tracebacks
across the runner and evaluation gates, task-manifest schema validation for
required fields, optional fields, whitespace-padded task IDs, skill names,
titles, and prompts,
unregistered primary and composed context skills, duplicate task IDs, duplicate
or whitespace-padded success criteria, duplicate or whitespace-padded composed
context skills, and composed contexts that omit the primary task skill,
malformed result JSONL with line-numbered invalid-results reporting, required
and whitespace-checked result fields (`task_id`, `variant`, `status`),
allowlisted result variants and statuses, the `__preflight__`/`preflight`
sentinel-pair invariant, error-only preflight result records, context-free
preflight result records,
shared score/resume validation for optional `context_status` and
`context_skills` metadata, allowlisted optional `context_status` values, typed
optional `skill`, `prompt`, `stdout`, `stderr`, and `returncode` output metadata,
`returncode`/`status` consistency when return codes are present,
registered non-preflight `skill` metadata and empty preflight skill metadata,
registered optional result `context_skills` metadata,
non-empty `prompt` provenance for expected completed result records,
resume-time validation of complete current prompt/context/stdout metadata in existing result
files before preflight, latest-record score-report rendering for duplicate
task/variant pairs, and rejecting package-skill/K-Dense records whose context
was not provided or whose package-skill `context_skills` do not match the task
manifest, and rejecting K-Dense records whose `context_skills` do not name the
compared skill.

```bash
python eval/scripts/run_claude_eval.py \
  --results /private/tmp/materials-skills-no-kdense-root-real.jsonl \
  --skip-preflight \
  --max-budget-usd 0.01
```

Result: failed before model calls with `Missing K-Dense skill context...` and
did not write `/private/tmp/materials-skills-no-kdense-root-real.jsonl`.

```bash
python eval/scripts/run_claude_eval.py \
  --preflight-only \
  --results /private/tmp/materials-skills-preflight-only-results.jsonl \
  --max-budget-usd 0.01
```

Result: failed cleanly with `Claude auth status reports loggedIn=false` and did not
write `/private/tmp/materials-skills-preflight-only-results.jsonl`.

```bash
python eval/scripts/run_claude_eval.py \
  --dry-run \
  --kdense-root eval/kdense-public \
  --results eval/kdense-dry-run-results.jsonl
```

Result: wrote 11 dry-run records using the public K-Dense pymatgen skill for
the K-Dense comparison variant.

```bash
python eval/scripts/score_results.py \
  --results eval/results.jsonl \
  --report /private/tmp/materials-skills-missing-score-report.md
```

Result: failed cleanly with `ERROR missing results file: eval/results.jsonl`
and did not write a report.

```bash
python eval/scripts/score_results.py \
  --results eval/dry-run-results.jsonl \
  --report eval/score-report.md

python eval/scripts/score_results.py \
  --results eval/auth-preflight-results.jsonl \
  --report eval/auth-preflight-score-report.md
```

Result: wrote manual score reports with a task-level comparison summary,
criteria checklists, per-variant context status, loaded context skills, prompt
provenance, dry-run placeholders, and auth-preflight error surfacing. The
renderer uses safe Markdown fences for prompt and model output blocks containing
backticks, and the scoring gate ignores fenced output when checking report
structure or scoring-template markers such as unchecked checklist items.

```bash
python eval/scripts/check_score_report.py \
  --report eval/score-report.md \
  --json
```

Result: failed with 11 `Outcome: not-scored` placeholders, 25 unchecked
criteria boxes, invalid placeholder summary/outcome/winner values, and missing
checked success criteria in the current dry-run score report. The gate also has
regression coverage for rejecting duplicate, misplaced, or unexpected summary
rows, plus unexpected task sections and variant sections in manually edited
reports.

```bash
python eval/scripts/check_eval_artifacts.py \
  --results eval/dry-run-results.jsonl \
  --report eval/score-report.md \
  --json
```

Result: failed with both categories of blocker: dry-run evaluation records and
unfilled, unchecked, or invalid manual scoring values. JSON includes
`blockers: ["evaluation", "scoring"]`.

```bash
python eval/scripts/run_v0_pipeline.py --skip-model-run
```

Result: rejected the invocation with an argparse error because `--skip-model-run`
now requires `--check-scored`; skipped model runs must still run the final
artifact validation.

```bash
python eval/scripts/check_eval_artifacts.py \
  --tasks eval/tasks/v0_tasks.json \
  --results eval/auth-blocked-results.jsonl \
  --report eval/auth-blocked-score-report.md \
  --json
```

Result: failed with 0/11 expected records complete because every attempted
task/variant has `status: "error"` from missing Claude auth, plus unfilled
manual-scoring placeholders.

```bash
python eval/scripts/check_eval_completeness.py \
  --results eval/dry-run-results.jsonl \
  --json
```

Result: failed with 11 expected records present but still `status: "dry-run"`.

```bash
python eval/scripts/run_v0_pipeline.py \
  --results /private/tmp/materials-skills-pipeline-auth-check.jsonl \
  --report /private/tmp/materials-skills-pipeline-auth-check.md \
  --smoke-results /private/tmp/materials-skills-pipeline-smoke.jsonl \
  --max-budget-usd 0.01
```

Result: stopped at `Step 1/4: Claude preflight` with `Not logged in - Please
run /login`; the wrapper did not run the smoke test, full matrix, or report
generation while auth was missing. Tests also verify this preflight-failure path
does not create the full results JSONL, smoke-results JSONL, or score report.

The wrapper is also tested for the defensive case where a nominally successful
model run does not produce a results file; it reports an incomplete evaluation
with `missing results file` instead of raising a traceback or writing a report.

```bash
python eval/scripts/run_claude_eval.py \
  --kdense-root eval/kdense-public \
  --results eval/auth-preflight-results.jsonl \
  --max-budget-usd 0.01
```

Result: wrote one structured `__preflight__` error record and stopped because
`claude auth status --json` reported `loggedIn=false`. The generated
`eval/auth-preflight-score-report.md` surfaces that standalone preflight error
before the task matrix.

```bash
python eval/scripts/check_eval_completeness.py \
  --results eval/auth-preflight-results.jsonl \
  --json
```

Result: failed with 11 missing expected result records plus one unexpected
`__preflight__` error record.

```bash
python eval/scripts/check_eval_artifacts.py \
  --tasks eval/impedance/tasks.json \
  --results eval/impedance/results.jsonl \
  --report eval/impedance/score-report.md \
  --json
```

Result: failed with `expected_count: 6`, `complete_count: 0`, missing
`eval/impedance/results.jsonl`, and the unfilled impedance score-report
scaffold. This verifies the first-package impedance iteration is explicitly
blocked, not silently treated as a zero-record evaluation.

The first-package impedance.py path also has a post-login wrapper:

```bash
python eval/scripts/run_impedance_pipeline.py --resume
python eval/scripts/run_impedance_pipeline.py \
  --skip-model-run \
  --check-scored
python eval/scripts/run_impedance_pipeline.py \
  --skip-model-run \
  --check-scored \
  --json
```

Tests verify the wrapper stops after failed preflight without creating the
results JSONL or score report, writes the score-report scaffold after complete
six-record model output, reports missing result files after nominal model runs
without writing a report, validates already scored artifacts without calling
Claude, emits a clean JSON payload for the final artifact gate, and rejects
`--check-scored` without `--skip-model-run` or `--skip-model-run` without
`--check-scored`. Tests also verify that model-run mode refuses to overwrite an
already manually scored impedance report unless `--overwrite-report` is passed.

```bash
python eval/scripts/run_claude_eval.py \
  --kdense-root eval/kdense-public \
  --results eval/auth-blocked-results.jsonl \
  --max-budget-usd 0.05 \
  --skip-preflight
```

Result: wrote 11 structured error records with baseline, package-skill, and
K-Dense context metadata preserved; each Claude invocation returned
`Not logged in - Please run /login`.

## Missing Or Weakly Verified

- The empirical run is complete for v0, but it is still only one model/run
  sample per task/variant. It supports concrete behavioral observations, not a
  statistical claim.
- Cross-library composition is weakly verified: the ASE+pymatgen+MACE
  package-skill variant loaded all intended context, but lost to baseline on
  conversion-check rigor. A bridge artifact for that boundary remains a
  post-v0 experiment.
- K-Dense comparison is represented by one public pymatgen fixture and one
  phase-diagram task. That is enough for the v0 comparison row but not a broad
  audit of K-Dense scientific skills.
- Hosted registry distribution is not implemented; the tested v0 shape is a
  hybrid of package-shipped skills plus a JSON-exportable registry.

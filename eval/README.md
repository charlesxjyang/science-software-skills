# v0 Evaluation Runbook

Use this after the local Claude CLI is authenticated. The empirical comparison
is not complete until the strict completeness gate passes on real model output.

## Matrix

The manifest is `eval/tasks/v0_tasks.json`. It expands to 11 expected records:

- 5 `baseline` records
- 5 `package-skill` records
- 1 `kdense` record for `pymatgen-phase-diagram-lifepo4`

The K-Dense comparison uses the public pymatgen fixture under
`eval/kdense-public/pymatgen/SKILL.md`.

Package-skill variants usually load one package skill. Cross-library tasks can
load a task-specific skill set; the ASE+pymatgen+MACE task loads `mace`, `ase`,
and `pymatgen`, and records that list as `context_skills`.

Real non-dry-run matrices fail before model calls if a selected K-Dense variant
does not have a matching `--kdense-root`.

## Preflight

Authenticate first:

```bash
claude auth login
claude auth status --json
```

Then verify that the evaluator can call Claude without writing any result
records. This first checks `claude auth status --json`; if that reports
`loggedIn=false`, the evaluator stops before sending any model probe:

```bash
python eval/scripts/run_claude_eval.py \
  --preflight-only \
  --max-budget-usd 0.05
```

Then run a one-task smoke test:

```bash
python eval/scripts/run_claude_eval.py \
  --task impedance-fit-randles-cpe-warburg \
  --variant package-skill \
  --results /private/tmp/materials-skills-smoke-results.jsonl \
  --max-budget-usd 0.05
```

If this writes a `__preflight__` error or reports `loggedIn=false`, stop and
fix Claude auth before running the full matrix.

## First-Package Impedance Iteration

The original impedance.py iteration has a separate three-prompt manifest at
`eval/impedance/tasks.json`. It expands to six records: baseline and
package-skill variants for fitting, validation, and batch ZPlot workflows.

Dry-run it before calling Claude:

```bash
python eval/scripts/run_claude_eval.py \
  --tasks eval/impedance/tasks.json \
  --dry-run \
  --results eval/impedance/dry-run-results.jsonl
```

After `claude auth login`, run the real manual impedance comparison:

```bash
python eval/scripts/run_impedance_pipeline.py --resume
```

This wrapper runs a preflight, the six-record baseline/package-skill impedance
matrix, the completeness gate, and score-report scaffold generation. Use
`eval/impedance/results.md` for short human observations; keep full model
outputs in the JSONL file. Existing unscored dry-run scaffolds are replaced
after real outputs complete; manually scored reports are protected unless
`--overwrite-report` is passed.

The underlying commands are useful for debugging or partial reruns. To check
real-output completeness directly:

```bash
python eval/scripts/check_eval_completeness.py \
  --tasks eval/impedance/tasks.json \
  --results eval/impedance/results.jsonl \
  --json
```

To regenerate the manual scoring scaffold directly:

```bash
python eval/scripts/score_results.py \
  --tasks eval/impedance/tasks.json \
  --results eval/impedance/results.jsonl \
  --report eval/impedance/score-report.md
```

This direct renderer also refuses to overwrite a report that already looks
manually scored. Pass `--overwrite-report` only when you intentionally want to
replace scored notes with a fresh scaffold.

Then check that the scaffold has been fully scored:

```bash
python eval/scripts/run_impedance_pipeline.py \
  --skip-model-run \
  --check-scored
```

For automation, add `--json` to that final impedance gate:

```bash
python eval/scripts/run_impedance_pipeline.py \
  --skip-model-run \
  --check-scored \
  --json
```

## Full Run

The wrapper below is the shortest post-login path. It runs the preflight, the
impedance package-skill smoke test, the full 11-record matrix with the local
K-Dense fixture, the completeness gate, and score-report scaffold generation:

```bash
python eval/scripts/run_v0_pipeline.py --resume
```

After manually filling `eval/score-report.md`, run the final combined gate
without re-calling Claude or overwriting the report:

```bash
python eval/scripts/run_v0_pipeline.py \
  --skip-model-run \
  --check-scored
```

For automation, add `--json` to that final gate:

```bash
python eval/scripts/run_v0_pipeline.py \
  --skip-model-run \
  --check-scored \
  --json
```

The wrapper rejects `--check-scored` unless `--skip-model-run` is also present;
that final check is meant for already generated outputs and an already filled
score report. Model-run mode also refuses to overwrite a report that already
looks manually scored; pass `--overwrite-report` only when you intentionally
want to regenerate the scaffold. Existing unscored dry-run scaffolds are
replaced after real outputs complete.

The underlying commands are listed below for debugging or partial reruns.

Use a fresh result file for the first full run:

```bash
python eval/scripts/run_claude_eval.py \
  --kdense-root eval/kdense-public \
  --results eval/results.jsonl \
  --max-budget-usd 0.50
```

The runner writes the result file after each completed task/variant, so a local
interruption should preserve completed records from that process. Resume without
overwriting completed `ok` records:

```bash
python eval/scripts/run_claude_eval.py \
  --kdense-root eval/kdense-public \
  --results eval/results.jsonl \
  --max-budget-usd 0.50 \
  --resume
```

## Gate

Dry-runs, auth-preflight failures, and partial result files do not count. The
required gate is:

```bash
python eval/scripts/check_eval_completeness.py \
  --results eval/results.jsonl \
  --json
```

Success means:

- `ok: true`
- `expected_count: 11`
- `complete_count: 11`
- no `__preflight__` or other unexpected records
- each record's `skill` matches the task manifest
- each expected completed record includes the prompt text used to produce that
  output
- baseline records have `context_status: "not-applicable"` and explicit empty
  `context_skills`
- package-skill and K-Dense records have `context_status: "provided"`
- package-skill records have `context_skills` exactly matching the task
  manifest, including `["mace", "ase", "pymatgen"]` for the cross-library MACE
  task
- K-Dense records have `context_skills` naming the compared skill, currently
  `["pymatgen"]`

## Manual Scoring

After the completeness gate passes, generate the scoring report:

```bash
python eval/scripts/score_results.py \
  --results eval/results.jsonl \
  --report eval/score-report.md
```

Like the pipeline wrappers, the direct renderer replaces existing unscored
scaffolds but refuses to overwrite a report that already looks manually scored
unless `--overwrite-report` is passed.

For each task, mark every success criterion as reviewed and assign each variant
an outcome: `win`, `tie`, `loss`, or `blocked`. `not-scored` is only a temporary
placeholder in generated reports; the final gate rejects it.

Then verify the report still has all expected task/variant sections, retains
the generated status/context/prompt/output fields for each variant, keeps each
expected variant status as `ok`, keeps context status and context skills aligned
with the task manifest, keeps each prompt block tied to the manifest prompt,
keeps the fenced model output non-empty, and has replaced manual scoring
placeholders and unchecked criteria boxes with valid scored values:

```bash
python eval/scripts/check_score_report.py \
  --report eval/score-report.md \
  --json
```

The writeup should only make empirical claims after this scoring pass is filled
in with real outputs and the score-report gate passes.

## Final Artifact Check

After both gates pass independently, this combined check gives one final status
for the empirical artifacts. Its text and JSON output include `blockers` naming
`evaluation` and/or `scoring` when either side is incomplete:

```bash
python eval/scripts/check_eval_artifacts.py \
  --results eval/results.jsonl \
  --report eval/score-report.md \
  --json
```

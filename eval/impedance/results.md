# impedance.py Evaluation Results

## Setup

- Date: 2026-05-13
- Skill under test: `skills/impedance/SKILL.md`
- Claude command: `claude -p --max-budget-usd 0.50 --tools "" --permission-mode dontAsk ...`
- Baseline command: same command without injected skill context
- Status: complete for the first-package impedance matrix; full model outputs
  are in `eval/impedance/results.jsonl` and manual scoring is in
  `eval/impedance/score-report.md`

## Prompt 1: Fit A Battery EIS Spectrum

- Baseline result: reached for impedance.py and covered the requested workflow,
  but used `names = circuit.get_param_names()` as if it returned a flat list.
  Current impedance.py returns `(names, units)`, so the parameter table code is
  malformed.
- With skill result: used the current `names, units = circuit.get_param_names()`
  convention and paired `parameters_` and `conf_` correctly.
- Outcome: package-skill win.

## Prompt 2: Validate Before Fitting

- Baseline result: correctly used `impedance.validation.linKK`, explained
  causality/linearity/stability, plotted real and imaginary residuals, discussed
  `c`/`max_M`, and avoided treating Lin-KK as circuit validation.
- With skill result: also satisfied all criteria, with a slightly clearer note
  on `M` hitting `max_M` and preprocessing.
- Outcome: tie.

## Prompt 3: Batch Fit Many ZPlot Files

- Baseline result: used `readZPlot`, one fresh `CustomCircuit` per file,
  `get_param_names`, `parameters_`, and `predict`, but called
  `plot_nyquist(ax, Z, ...)`, reversing the impedance.py plotting API.
- With skill result: used native `readZPlot`, independent per-file circuits,
  labeled parameter/confidence columns, `predict`, and correct
  `plot_nyquist(Z, ax=ax, ...)` overlays.
- Outcome: package-skill win.

## Notes

- The first-package wrapper performed the Claude preflight, the six-record
  baseline/package-skill matrix, the completeness gate, and score-report
  scaffold generation:

```bash
python eval/scripts/run_impedance_pipeline.py --resume
```

- It runs each prompt twice, once without injected skill context and once with
  `skills/impedance/SKILL.md` prepended as package-skill context. The
  underlying completeness check is:

```bash
python eval/scripts/check_eval_completeness.py \
  --tasks eval/impedance/tasks.json \
  --results eval/impedance/results.jsonl \
  --json
```

- Validate the completed first-package artifacts without re-calling Claude:

```bash
python eval/scripts/run_impedance_pipeline.py \
  --skip-model-run \
  --check-scored
```

- For automation, use the JSON form of the same final gate:

```bash
python eval/scripts/run_impedance_pipeline.py \
  --skip-model-run \
  --check-scored \
  --json
```

- The scored result is two package-skill wins and one tie. The wins are
  concrete API-correctness wins, not just better style: the package skill
  steered the model to the current `get_param_names()` tuple convention and the
  correct `plot_nyquist(Z, ax=...)` plotting API.

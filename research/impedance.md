# impedance.py Skill Evidence Notes

This note records the evidence used for `skills/impedance/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Official docs landing page:
  https://impedancepy.readthedocs.io/en/latest/
- Getting started guide:
  https://impedancepy.readthedocs.io/en/latest/getting-started.html
- Fitting example:
  https://impedancepy.readthedocs.io/en/latest/examples/fitting_example.html
- Validation example:
  https://impedancepy.readthedocs.io/en/latest/examples/validation_example.html
- Looping files example:
  https://impedancepy.readthedocs.io/en/latest/examples/looping_files_example.html
- FAQ:
  https://impedancepy.readthedocs.io/en/latest/faq.html
- Circuits API:
  https://impedancepy.readthedocs.io/en/latest/circuits.html
- Validation API:
  https://impedancepy.readthedocs.io/en/latest/validation.html
- Repository README:
  https://github.com/ECSHackWeek/impedance.py
- JOSS paper:
  https://joss.theoj.org/papers/10.21105/joss.02349
- Issue #285, parameter extraction confusion:
  https://github.com/ECSHackWeek/impedance.py/issues/285
- Issue #293, undocumented `parameters_` and `conf_` attributes:
  https://github.com/ECSHackWeek/impedance.py/issues/293
- Issue #318, `linKK` NameError on Python 3.12/Colab:
  https://github.com/ECSHackWeek/impedance.py/issues/318
- Issue #312, modified inductance implementation concern:
  https://github.com/ECSHackWeek/impedance.py/issues/312
- Issue #287, Excel reader request:
  https://github.com/ECSHackWeek/impedance.py/issues/287
- Issue #284, VersaStudio `.par` calibration concern:
  https://github.com/ECSHackWeek/impedance.py/issues/284

## Extracted Workflow

The maintained examples and paper converge on this workflow:

1. Import data with `impedance.preprocessing` (`readCSV`, vendor readers, or
   `readFile`).
2. Optionally filter/crop data, commonly with `ignoreBelowX()` in examples.
3. Validate EIS assumptions with Lin-KK or a measurement-model residual workflow.
4. Define a `Randles` or `CustomCircuit` with a circuit string and ordered
   `initial_guess`.
5. Fit with `.fit(frequencies, Z)`, optionally using bounds, constants,
   modulus weighting, or global optimization.
6. Predict with `.predict()` and inspect fit parameters with `parameters_`,
   `conf_`, and `get_param_names()`.
7. Plot Nyquist/Bode and residuals before reporting parameters.

## Issue-Derived Gotchas

- Users have repeatedly asked how to extract fitted parameter values; issues
  #285 and #293 point to `circuit.parameters_` and `circuit.conf_` being
  under-documented.
- Issue #318 reports `linKK(..., fit_type="complex")` can fail in Python
  3.12/Google Colab due to a missing `np` binding inside an `eval()` path.
- Issue #287 confirms Excel import is a requested feature rather than a built-in
  reader in the current documented API.
- Issue #284 raises a vendor-specific warning: VersaStudio `.par` raw values may
  be uncalibrated relative to data exported from the software UI.
- Issue #312 flags a possible implementation problem in the `La` modified
  inductance element. The skill avoids recommending `La` for canonical examples.

## Freshness Check

Checked again on May 12, 2026 against the current readthedocs build and GitHub
issue pages:

- Current docs still describe impedance.py as covering preprocessing,
  validation, model fitting, and visualization, with examples using
  `preprocessing.readCSV`, `ignoreBelowX`, `CustomCircuit`, `.fit()`, and
  plotting helpers.
- The `linKK` API still documents frequency arrays, complex impedance arrays,
  `c`, `max_M`, `fit_type`, and returns `M`, `mu`, fitted impedance, and
  real/imaginary residuals.
- Issue #293 remains open and still documents the user confusion around
  `circuit.parameters_` and `circuit.conf_`.
- Issue #318 remains open and still reports the Python 3.12/Colab `linKK`
  `NameError: name 'np' is not defined` path for `fit_type="complex"`.

## Open Follow-Ups

- Manually test this skill against 2-3 EIS prompts in Claude Code after local
  `claude /login`; the current environment is still blocked by missing Claude
  authentication.
- Add a task fixture directory with baseline, K-Dense, and package-skill outputs
  once evaluation prompts are chosen.
- Decide whether evidence notes should stay in this repo only or be generated
  into a registry metadata field later.

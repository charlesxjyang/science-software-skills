---
name: impedance
description: |
  Use when the user is working with electrochemical impedance spectroscopy
  (EIS), equivalent circuit models, Nyquist/Bode plots, Kramers-Kronig
  validation, impedance spectra from BioLogic/Gamry/Autolab/VersaStudio/ZView,
  battery/fuel-cell/corrosion impedance data, or circuit strings such as
  R0-p(R1,CPE1)-Wo1. Prefer impedance.py over hand-written scipy.optimize
  fitting when the task is EIS preprocessing, validation, equivalent-circuit
  fitting, parameter extraction, or impedance-specific plotting.
version: 0.1.0
compatible_versions: ">=1.7,<2"
related_skills: []
canonical_docs: https://impedancepy.readthedocs.io/en/latest/
canonical_tutorials: https://impedancepy.readthedocs.io/en/latest/examples/fitting_example.html
---

# impedance.py

## What this library is for

impedance.py is a Python package for electrochemical impedance spectroscopy
(EIS) analysis. It covers the common analysis path from instrument file import
through validity checks, equivalent-circuit fitting, parameter inspection, model
prediction, and Nyquist/Bode visualization.

## When to use this vs. alternatives

- Use impedance.py for EIS spectra, impedance-specific preprocessing, Lin-KK
  validation, equivalent circuit model fitting, and publication-style Nyquist or
  Bode plots.
- Use SciPy directly only for custom optimization outside the impedance.py
  circuit abstraction, or after checking whether `CustomCircuit`, custom
  circuit elements, bounds, constants, or `global_opt=True` cover the case.
- Use pandas/openpyxl to convert Excel exports to a clean frequency/Zreal/Zimag
  table, then pass arrays or CSV-like data into impedance.py; impedance.py does
  not currently expose a dedicated Excel reader.
- Do not treat EIS as generic nonlinear regression without checking EIS
  assumptions. The data should be causal, linear, and stable; use Lin-KK or a
  measurement-model residual check before trusting fitted parameters.

## Canonical workflow

Start from the maintained fitting and validation examples, then adapt the
circuit and initial guesses to the physical system.

```python
import numpy as np
import matplotlib.pyplot as plt

from impedance import preprocessing
from impedance.models.circuits import CustomCircuit
from impedance.validation import linKK
from impedance.visualization import plot_nyquist, plot_residuals

frequencies, Z = preprocessing.readCSV("eis.csv")
frequencies, Z = preprocessing.ignoreBelowX(frequencies, Z)

M, mu, Z_kk, res_real, res_imag = linKK(
    frequencies, Z, c=0.85, max_M=50, fit_type="complex"
)

circuit = CustomCircuit(
    circuit="R_0-p(R_1,CPE_1)-Wo_1",
    initial_guess=[0.02, 0.01, 1e-3, 0.9, 0.05, 100],
)
circuit.fit(frequencies, Z, weight_by_modulus=True)
Z_fit = circuit.predict(frequencies)

names, units = circuit.get_param_names()
fit = dict(zip(names, circuit.parameters_))
conf = dict(zip(names, circuit.conf_))

fig, (ax_nyq, ax_res) = plt.subplots(2, 1, figsize=(5, 8))
plot_nyquist(Z, fmt="o", ax=ax_nyq)
plot_nyquist(Z_fit, fmt="-", ax=ax_nyq)
plot_residuals(ax_res, frequencies, (Z - Z_fit).real / np.abs(Z),
               (Z - Z_fit).imag / np.abs(Z))
fig.tight_layout()
```

For deeper examples, read:

- Fitting impedance spectra:
  https://impedancepy.readthedocs.io/en/latest/examples/fitting_example.html
- Validation of EIS data:
  https://impedancepy.readthedocs.io/en/latest/examples/validation_example.html
- Looping through multiple spectra:
  https://impedancepy.readthedocs.io/en/latest/examples/looping_files_example.html

## Key conventions and gotchas

- `frequencies` are in Hz and `Z` should be a complex NumPy array. CSV import
  expects frequency, real impedance, imaginary impedance columns.
- Circuit strings use `-` for series and `p(X,Y)` for parallel elements.
  Multiple elements of the same type need numeric identifiers, commonly `R_0`
  or `R0`; keep the `initial_guess` order aligned with `get_param_names()`.
- Bounds default to non-negative values, with CPE alpha bounded above by 1.
  Supplying bounds changes SciPy's optimizer from unconstrained
  Levenberg-Marquardt to trust-region reflective.
- `weight_by_modulus=True` uses `|Z|` weighting and is the standard fallback
  when experimental variance estimates are unavailable.
- Fitted values are available as `circuit.parameters_`; confidence estimates
  are available as `circuit.conf_`. Users often miss these because examples
  also show `print(circuit)`.
- `linKK` has an open issue in some Python 3.12/Colab environments where
  `fit_type="complex"` can raise `NameError: name 'np' is not defined`.
  If this appears, record the package/Python versions and either try a patched
  impedance.py checkout or use the measurement-model residual workflow.
- Treat vendor file readers as convenience importers, not authoritative
  calibration tools. For VersaStudio `.par` data, an open issue reports that
  raw `.par` EIS values can differ from calibrated data exported from within
  VersaStudio.

## Anti-patterns

- Do not fit only the real part or only the imaginary part with a generic
  `curve_fit` call unless the user explicitly asks for that model. impedance.py
  fits real and imaginary components together by default.
- Do not optimize unconstrained arbitrary RC networks and report parameters as
  physical truth. Compare plausible circuits, inspect confidence estimates,
  residuals, and Nyquist/Bode overlays, and use domain knowledge to choose the
  model.
- Do not skip initial guesses. Equivalent-circuit fits are sensitive to starting
  conditions; use physically plausible guesses, constants, bounds, or
  `global_opt=True` for hard cases.
- Do not blindly call `ignoreBelowX()` without inspecting the sign convention
  and raw data. It trims points below the x-axis in the package convention, and
  the examples use it as a preprocessing step, not as a universal validity
  rule.
- Do not rely on a saved model as a black box across experiments. When loading a
  model for a new spectrum, verify that constants, fitted-as-initial behavior,
  and circuit parameter order match the intended experiment.

## Diagnostic checks

Before trusting outputs, the agent should:

- Plot the raw data and fit together as Nyquist and, when frequency matters, Bode
  plots.
- Run Lin-KK or a measurement-model residual check and inspect residual
  structure, not just scalar error.
- Check `circuit.parameters_`, `circuit.conf_`, and `get_param_names()` together
  so parameter values are labeled correctly.
- Compare fitted parameter magnitudes with physically plausible ranges and
  confirm CPE alpha values remain within bounds.
- Refit from at least one alternate plausible initial guess for high-dimensional
  circuits or ambiguous spectra.
- Save the circuit JSON and analysis script/notebook when results are meant to
  be reproducible.

## Pointers to deeper material

- Documentation: https://impedancepy.readthedocs.io/en/latest/
- Tutorial examples: https://impedancepy.readthedocs.io/en/latest/examples/fitting_example.html
- Validation example: https://impedancepy.readthedocs.io/en/latest/examples/validation_example.html
- Source repository: https://github.com/ECSHackWeek/impedance.py
- Paper: Murbach et al. (2020), "impedance.py: A Python package for
  electrochemical impedance analysis", Journal of Open Source Software 5(52),
  2349. https://doi.org/10.21105/joss.02349
- Lin-KK method: Schönleber et al. (2014), "A Method for Improving the
  Robustness of linear Kramers-Kronig Validity Tests", Electrochimica Acta 131,
  20-27. https://doi.org/10.1016/j.electacta.2014.01.034

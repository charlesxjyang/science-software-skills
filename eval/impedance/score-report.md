# Evaluation Score Report

Manual scoring key: mark every criterion reviewed, then replace each `not-scored` placeholder with `win`, `tie`, `loss`, or `blocked`.

## Comparison Summary

| Task | Baseline | Package Skill | K-Dense | Winner | Notes |
| --- | --- | --- | --- | --- | --- |
| `impedance-fit-randles-cpe-warburg` | loss | win | not applicable | package-skill | Package skill used the current `get_param_names()` tuple API correctly; baseline treated it as a flat list. |
| `impedance-validate-before-fitting` | tie | tie | not applicable | tie | Both variants used `linKK`, inspected real/imaginary residuals, and preserved the caveat that Lin-KK does not validate the circuit. |
| `impedance-batch-fit-zplot` | loss | win | not applicable | package-skill | Package skill used the correct `plot_nyquist(Z, ax=...)` call; baseline reversed positional arguments. |

## impedance-fit-randles-cpe-warburg: Fit A Battery EIS Spectrum

Skill: `impedance`

Criteria:
- [x] Uses impedance.preprocessing.readCSV or clearly creates the equivalent complex Z array
- [x] Uses impedance.py CustomCircuit rather than hand-rolled scipy.optimize.curve_fit
- [x] Mentions ordered initial_guess, get_param_names, parameters_, and conf_
- [x] Plots raw data and predicted fit with plot_nyquist
- [x] Flags initial-guess sensitivity and residual inspection

### Variant: baseline

Status: `ok`

Context status: `not-applicable`

Context skills: `none`

Prompt:

```text
You are answering a scientific Python coding prompt. Use only the context provided here plus your general knowledge.

## Variant
baseline

## Context
No package-specific skill context provided.

## User Prompt
I have a CSV exported from a potentiostat with columns frequency, Zreal, Zimag. Fit it to R_0-p(R_1,CPE_1)-Wo_1, plot the Nyquist data and fit, and give me a small table of fitted parameter values with uncertainties. Write Python code I can adapt.

## Evaluation Criteria
- Uses impedance.preprocessing.readCSV or clearly creates the equivalent complex Z array
- Uses impedance.py CustomCircuit rather than hand-rolled scipy.optimize.curve_fit
- Mentions ordered initial_guess, get_param_names, parameters_, and conf_
- Plots raw data and predicted fit with plot_nyquist
- Flags initial-guess sensitivity and residual inspection

Return a concise but complete answer with code where appropriate.
```

Output:

````text
## EIS Circuit Fitting with impedance.py

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from impedance.models.circuits import CustomCircuit
from impedance.preprocessing import readCSV
from impedance.visualization import plot_nyquist

# ── 1. Load data ───────────────────────────────────────────────────────────────
# Option A: impedance.py's reader (expects columns: freq, Zreal, Zimag)
frequencies, Z = readCSV('your_data.csv')

# Option B: manual (use if column names differ or readCSV chokes)
# df = pd.read_csv('your_data.csv')
# frequencies = df['frequency'].values
# Z = df['Zreal'].values + 1j * df['Zimag'].values
# Zimag is negative for capacitive arcs; verify sign with a quick Nyquist sanity check:
# plt.plot(Z.real, -Z.imag); plt.show()

# Keep only positive frequencies and finite Z
mask = (frequencies > 0) & np.isfinite(Z)
frequencies, Z = frequencies[mask], Z[mask]

# ── 2. Define circuit and initial guess ────────────────────────────────────────
# Circuit: R0 - [R1 ∥ CPE1] - Wo1
# CPE impedance: 1 / (Q * (jω)^n)   → params [Q, n]
# Warburg-open (Wo): R_w * tanh(√(jωτ)) / √(jωτ) → params [R_w, τ]
circuit_str = 'R0-p(R1,CPE1)-Wo1'

# get_param_names() tells you the exact order BEFORE fitting:
probe = CustomCircuit(circuit_str, initial_guess=[1]*6)
print("Parameter names (in order):", probe.get_param_names())
# → ['R0', 'R1', 'CPE1_0', 'CPE1_1', 'Wo1_0', 'Wo1_1']
#     series R  parallel R    Q         n       R_w       τ

# !! Initial guesses are the single biggest source of fit failure.
# Start with values physically reasonable for your system.
initial_guess = [
    50,      # R0  – solution/contact resistance [Ω]
    200,     # R1  – charge-transfer resistance [Ω]
    1e-4,    # CPE1_0 (Q) – pseudo-capacitance [F·s^(n-1)]
    0.85,    # CPE1_1 (n) – ideality (1=pure cap, 0=pure R)
    300,     # Wo1_0 (R_w) – diffusion resistance [Ω]
    10,      # Wo1_1 (τ)   – diffusion time constant [s]
]

circuit = CustomCircuit(circuit_str, initial_guess=initial_guess)

# ── 3. Fit ─────────────────────────────────────────────────────────────────────
circuit.fit(frequencies, Z)

# ── 4. Results table ───────────────────────────────────────────────────────────
names  = circuit.get_param_names()   # ordered list of names
params = circuit.parameters_          # fitted values (same order)
conf   = circuit.conf_                # 1-σ uncertainties from covariance

print(f"\n{'Parameter':<12} {'Value':>14} {'±1σ':>12} {'%err':>8}")
print("-" * 50)
for n, p, c in zip(names, params, conf):
    pct = abs(c / p) * 100 if p != 0 else float('nan')
    print(f"{n:<12} {p:>14.4g} {c:>12.4g} {pct:>7.1f}%")

# ── 5. Nyquist plot ────────────────────────────────────────────────────────────
Z_fit = circuit.predict(frequencies)

fig, ax = plt.subplots(figsize=(7, 5))
plot_nyquist(Z,     ax=ax, fmt='o', label='Data')
plot_nyquist(Z_fit, ax=ax, fmt='-', label='Fit')
ax.legend()
ax.set_title(f'Nyquist — {circuit_str}')
plt.tight_layout()
plt.show()

# ── 6. Residual inspection (don't skip this) ───────────────────────────────────
residuals = Z - Z_fit
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].semilogx(frequencies, residuals.real, 'o')
axes[0].set(xlabel='Frequency (Hz)', ylabel="ΔZ' (Ω)", title='Real residuals')
axes[1].semilogx(frequencies, residuals.imag, 'o')
axes[1].set(xlabel='Frequency (Hz)', ylabel='ΔZ" (Ω)', title='Imag residuals')
plt.tight_layout()
plt.show()
```

---

### Key points to adapt this

| Concern | What to do |
|---|---|
| **`readCSV` fails** | Use Option B; impedance.py expects `freq, Zreal, Zimag` with Zimag negative for capacitive arcs |
| **`get_param_names()`** | Always call this first — it gives the exact order your `initial_guess` list must follow |
| **`parameters_` / `conf_`** | Available only after `.fit()`; `conf_` is 1-σ from the covariance matrix |
| **Initial-guess sensitivity** | Fit can converge to a local minimum; retry with ±order-of-magnitude variants if `%err` is huge or residuals are structured |
| **Structured residuals** | A systematic bowl/trend in the residual plots means the circuit model is wrong, not just a bad guess |
| **CPE_1 n ≈ 1** | CPE collapses to a pure capacitor — simplify to `R0-p(R1,C1)-Wo1` and refit |
````

Outcome: `loss`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Strong domain answer, but the code assigns `names = circuit.get_param_names()`
  and then zips it directly with `parameters_` and `conf_`. Current
  impedance.py returns `(names, units)`, so the fitted-parameter table is
  malformed despite the otherwise correct workflow.

### Variant: package-skill

Status: `ok`

Context status: `provided`

Context skills: `impedance`

Prompt:

````text
You are answering a scientific Python coding prompt. Use only the context provided here plus your general knowledge.

## Variant
package-skill

## Context
## Package Skill: impedance

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


## User Prompt
I have a CSV exported from a potentiostat with columns frequency, Zreal, Zimag. Fit it to R_0-p(R_1,CPE_1)-Wo_1, plot the Nyquist data and fit, and give me a small table of fitted parameter values with uncertainties. Write Python code I can adapt.

## Evaluation Criteria
- Uses impedance.preprocessing.readCSV or clearly creates the equivalent complex Z array
- Uses impedance.py CustomCircuit rather than hand-rolled scipy.optimize.curve_fit
- Mentions ordered initial_guess, get_param_names, parameters_, and conf_
- Plots raw data and predicted fit with plot_nyquist
- Flags initial-guess sensitivity and residual inspection

Return a concise but complete answer with code where appropriate.
````

Output:

````text
```python
import numpy as np
import matplotlib.pyplot as plt

from impedance import preprocessing
from impedance.models.circuits import CustomCircuit
from impedance.visualization import plot_nyquist

# --- Load data ---
frequencies, Z = preprocessing.readCSV("your_data.csv")
# readCSV expects columns: frequency, Zreal, Zimag
# It returns frequencies (Hz) and Z as a complex numpy array

# Optional: drop inductive tail (points below x-axis in impedance convention)
frequencies, Z = preprocessing.ignoreBelowX(frequencies, Z)

# --- Define circuit and fit ---
# Circuit: series R, then parallel (R || CPE), then Warburg open
# Parameter order must match get_param_names() output:
#   R_0, R_1, CPE_1_0 (Q), CPE_1_1 (alpha), Wo_1_0 (W), Wo_1_1 (tau)
circuit = CustomCircuit(
    circuit="R_0-p(R_1,CPE_1)-Wo_1",
    initial_guess=[0.01, 0.05, 1e-3, 0.85, 0.1, 50.0],
)

circuit.fit(frequencies, Z, weight_by_modulus=True)
Z_fit = circuit.predict(frequencies)

# --- Extract parameters ---
names, units = circuit.get_param_names()
params = circuit.parameters_
confs  = circuit.conf_          # 1-sigma confidence estimates

print(f"{'Parameter':<12} {'Unit':<10} {'Value':>12} {'±':>4} {'Conf (1σ)':>12}")
print("-" * 54)
for name, unit, val, conf in zip(names, units, params, confs):
    print(f"{name:<12} {unit:<10} {val:>12.4e} {'±':>4} {conf:>12.4e}")

# --- Nyquist plot ---
fig, ax = plt.subplots(figsize=(5, 4))
plot_nyquist(Z,     fmt="o", ax=ax, label="Data")
plot_nyquist(Z_fit, fmt="-", ax=ax, label="Fit")
ax.legend()
ax.set_title("Nyquist plot")
fig.tight_layout()
plt.savefig("nyquist.png", dpi=150)
plt.show()
```

**What each piece does and what to watch:**

| Step | Key point |
|---|---|
| `readCSV` | Expects `frequency, Zreal, Zimag` columns; returns `Z` as complex array. If your export has a header row or different column order, pass `header=1` or reorder manually. |
| `initial_guess` | Order must match `get_param_names()` exactly — run `print(circuit.get_param_names())` before fitting to verify. Bad guesses are the most common cause of nonsense fits. |
| `weight_by_modulus=True` | Standard fallback when you don't have experimental variance; weights residuals by `\|Z\|` so high-impedance points don't dominate. |
| `parameters_` / `conf_` | Fitted values and 1-sigma confidence from the covariance matrix. Large `conf_` relative to `parameters_` signals a poorly constrained parameter. |
| Residual check | After confirming the Nyquist overlay looks reasonable, add a residual plot to catch systematic structure: `(Z - Z_fit).real / np.abs(Z)` vs frequency. Structured residuals mean the model is wrong, even if the overlay looks passable. |

**Before trusting the numbers:**

1. Try at least one alternate `initial_guess` to confirm the optimizer isn't stuck in a local minimum.
2. Check that `CPE_1_1` (alpha) is between 0 and 1 — values outside that range are unphysical.
3. Run `linKK` on the raw data first if you haven't already, to confirm the spectrum satisfies Kramers-Kronig before fitting any circuit model.
````

Outcome: `win`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Meets every criterion and uses the current `names, units =
  circuit.get_param_names()` convention before pairing `parameters_` and
  `conf_`, so the generated table is directly adaptable.

## impedance-validate-before-fitting: Validate Before Fitting

Skill: `impedance`

Criteria:
- [x] Uses impedance.validation.linKK
- [x] Explains causality, linearity, and stability as EIS assumptions
- [x] Plots or inspects real and imaginary residuals rather than relying only on one scalar
- [x] Notes c, max_M, and possible under- or over-fitting behavior
- [x] Avoids claiming Lin-KK proves the model circuit is correct

### Variant: baseline

Status: `ok`

Context status: `not-applicable`

Context skills: `none`

Prompt:

```text
You are answering a scientific Python coding prompt. Use only the context provided here plus your general knowledge.

## Variant
baseline

## Context
No package-specific skill context provided.

## User Prompt
Before fitting my EIS spectrum, I want to check whether the data are physically consistent. I have arrays f and Z. What should I run in Python, and what should I inspect before trusting equivalent-circuit parameters?

## Evaluation Criteria
- Uses impedance.validation.linKK
- Explains causality, linearity, and stability as EIS assumptions
- Plots or inspects real and imaginary residuals rather than relying only on one scalar
- Notes c, max_M, and possible under- or over-fitting behavior
- Avoids claiming Lin-KK proves the model circuit is correct

Return a concise but complete answer with code where appropriate.
```

Output:

````text
## EIS Data Validation with Lin-KK

### Why validation matters first

EIS is only interpretable if three physical assumptions hold:

| Assumption | Meaning | Failure sign |
|---|---|---|
| **Causality** | Response is due only to the applied perturbation | Noise, drift, interference |
| **Linearity** | System is in a pseudo-linear regime (small-signal) | Amplitude too large |
| **Stability** | System doesn't change during measurement | Corrosion, SEI growth, non-stationarity |

Lin-KK tests all three simultaneously by checking whether your impedance data satisfy the Kramers–Kronig relations — a mathematical consequence of those three properties.

---

### Code

```python
import numpy as np
import matplotlib.pyplot as plt
from impedance.validation import linKK

# f  : frequency array (Hz), Z : complex impedance array (Ohm)
# c controls the upper bound on M (number of RC elements) relative to
# the number of data points; c=0.85 is a common starting point.
# max_M caps the search to avoid severe overfitting.

M, mu, Z_fit, res_real, res_imag = linKK(
    f, Z,
    c=0.85,
    max_M=50,
    fit_type='complex',   # fits both real and imaginary parts
    add_cap=True          # adds a series capacitor for low-f divergence
)

print(f"Optimal RC elements M = {M}")
print(f"mu = {mu:.4f}  (target < 0.85 for good fit, closer to 0 is better)")

# --- inspect residuals ---
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(8, 5))

ax1.plot(f, res_real * 100, 'o-', ms=4)
ax1.axhline(0, color='k', lw=0.8)
ax1.set_ylabel("Re residual (%)")
ax1.set_ylim(-2, 2)          # flag anything outside ±1–2 %

ax2.plot(f, res_imag * 100, 's-', ms=4, color='C1')
ax2.axhline(0, color='k', lw=0.8)
ax2.set_ylabel("Im residual (%)")
ax2.set_xlabel("Frequency (Hz)")
ax2.set_ylim(-2, 2)
ax2.set_xscale('log')

plt.tight_layout()
plt.show()
```

---

### What to inspect

**`mu` (the regularization metric)**
- `mu < 0.85` — fit is well-regularised; KK-compliant data likely
- `mu → 1` — M is too large, overfitting noise; reduce `max_M` or `c`
- If even `M=1` gives large residuals, the data violate KK and are not trustworthy

**Residual plots — look at both Re and Im**
- Random scatter within **±1–2 %** across all frequencies → data pass
- Systematic trends (curved, oscillatory, or large spikes at endpoints) → violation at those frequencies; consider trimming or re-measuring
- High-frequency noise is common and often acceptable; low-frequency drift is more serious

**`c` and `max_M` sensitivity**
- Re-run with `c` in [0.7, 0.9] and check whether conclusions change; robust data should pass across a range
- Increasing `max_M` that gives lower residuals but rising `mu` is a sign of overfitting noise, not a real improvement

---

### Critical caveat

Lin-KK **cannot** tell you which equivalent circuit is correct. It only tells you the data are *consistent enough to be worth fitting*. A dataset can pass Lin-KK and still be badly described by a Randles circuit or any other specific model. Validate the *model* separately (e.g., compare fitted vs. measured Nyquist/Bode, check parameter confidence intervals, test alternative circuits).
````

Outcome: `tie`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Complete and usable Lin-KK answer. It covers the assumptions, residual plots,
  `c`/`max_M`, overfitting, and the caveat that Lin-KK does not identify the
  right equivalent circuit.

### Variant: package-skill

Status: `ok`

Context status: `provided`

Context skills: `impedance`

Prompt:

````text
You are answering a scientific Python coding prompt. Use only the context provided here plus your general knowledge.

## Variant
package-skill

## Context
## Package Skill: impedance

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


## User Prompt
Before fitting my EIS spectrum, I want to check whether the data are physically consistent. I have arrays f and Z. What should I run in Python, and what should I inspect before trusting equivalent-circuit parameters?

## Evaluation Criteria
- Uses impedance.validation.linKK
- Explains causality, linearity, and stability as EIS assumptions
- Plots or inspects real and imaginary residuals rather than relying only on one scalar
- Notes c, max_M, and possible under- or over-fitting behavior
- Avoids claiming Lin-KK proves the model circuit is correct

Return a concise but complete answer with code where appropriate.
````

Output:

````text
## EIS Data Validation with Lin-KK

### The three assumptions Lin-KK tests

Equivalent-circuit fitting is only meaningful if your system satisfies the **Kramers-Kronig (KK) relations**, which hold when the system is:

- **Causal** — the response arises only from the applied perturbation, not from external signals or drift.
- **Linear** — the perturbation amplitude is small enough that the response is linear (check your AC amplitude, typically ≤10 mV).
- **Stable (time-invariant)** — the system doesn't change state during the measurement. A drifting electrode or ongoing reaction violates this.

Lin-KK (Schönleber et al. 2014) tests KK-consistency without assuming a physical circuit, by fitting a ladder of RC elements that are KK-compliant by construction. Large residuals mean the data violate at least one assumption.

### Run Lin-KK

```python
import numpy as np
import matplotlib.pyplot as plt
from impedance import preprocessing
from impedance.validation import linKK

# Ensure inductive tails at low frequency don't confuse the fit
frequencies, Z = preprocessing.ignoreBelowX(f, Z)

M, mu, Z_kk, res_real, res_imag = linKK(
    frequencies, Z,
    c=0.85,        # target ratio of RC time constants to frequency range
    max_M=50,      # upper limit on number of RC elements
    fit_type="complex",   # fits real and imaginary simultaneously
    add_cap=True,  # adds a capacitor element for low-frequency tails
)

print(f"RC elements used: {M},  mu = {mu:.4f}")
```

**Key parameters to understand:**

| Parameter | What it controls | Risk if wrong |
|-----------|-----------------|---------------|
| `c` (0–1) | Density of RC time constants across the frequency range | Too low → underfitting, residuals have structure; too high → overfitting, fits noise |
| `max_M` | Cap on RC element count | If `M` hits `max_M`, increase it and recheck |
| `mu` | Regularization measure of overfitting (Schönleber eq. 3) | `mu` near 1 suggests overfitting |

### Inspect residuals — not just a scalar error

```python
fig, axes = plt.subplots(2, 1, figsize=(7, 6), sharex=True)

axes[0].plot(frequencies, res_real * 100, "o-", label="Real residual")
axes[0].axhline(0, color="k", lw=0.8)
axes[0].set_ylabel("Δ$Z'$ / |Z| (%)")
axes[0].legend()

axes[1].plot(frequencies, res_imag * 100, "s-", color="C1", label="Imaginary residual")
axes[1].axhline(0, color="k", lw=0.8)
axes[1].set_ylabel("Δ$Z''$ / |Z| (%)")
axes[1].set_xlabel("Frequency (Hz)")
axes[1].legend()

axes[0].set_xscale("log")
fig.suptitle(f"Lin-KK residuals  (M={M}, μ={mu:.3f})")
fig.tight_layout()
plt.show()
```

**What to look for:**

- **Random scatter ≲ 1%** → data are KK-consistent; proceed to fitting.
- **Systematic structure** (a hump, trend, or sign reversal at a particular frequency range) → that frequency region violates causality/linearity/stability. Consider trimming those points or re-measuring with a smaller perturbation amplitude or shorter scan.
- **Both `res_real` and `res_imag` must be inspected.** A good real-part fit can mask imaginary-part drift, and vice versa.
- **`mu` close to 1** — overfitting; lower `c` or `max_M`.
- **`M` at the `max_M` ceiling** — underfitting; raise `max_M`.

### Critical caveat

Lin-KK passing **does not mean your equivalent circuit is correct.** It only confirms the data are internally self-consistent and KK-compliant. You still need to:

1. Justify your circuit topology from physical knowledge of the system.
2. Check fitted residuals and confidence intervals (`circuit.parameters_`, `circuit.conf_`) after fitting.
3. Compare at least one alternative plausible circuit.

A KK-consistent spectrum can still be fit poorly by the wrong circuit, and an ambiguous spectrum can be over-parameterized by a circuit with too many elements.
````

Outcome: `tie`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Also complete and usable. The package-skill version adds preprocessing and a
  slightly clearer interpretation of `M` hitting `max_M`, but the practical
  result is not materially better than baseline.

## impedance-batch-fit-zplot: Batch Fit Many ZPlot Files

Skill: `impedance`

Criteria:
- [x] Uses glob plus impedance.preprocessing.readZPlot
- [x] Creates one CustomCircuit per file with the same circuit string and initial guess
- [x] Extracts labeled parameters via get_param_names and parameters_
- [x] Uses predict and plot_nyquist for overlays
- [x] Does not parse .z files manually unless impedance.py cannot read them

### Variant: baseline

Status: `ok`

Context status: `not-applicable`

Context skills: `none`

Prompt:

```text
You are answering a scientific Python coding prompt. Use only the context provided here plus your general knowledge.

## Variant
baseline

## Context
No package-specific skill context provided.

## User Prompt
I have a folder of Scribner ZPlot .z files from replicate circuit measurements. Write Python that loops over the files, fits each to R0-p(R1,C1), saves the parameters to a DataFrame, and makes per-circuit Nyquist overlays.

## Evaluation Criteria
- Uses glob plus impedance.preprocessing.readZPlot
- Creates one CustomCircuit per file with the same circuit string and initial guess
- Extracts labeled parameters via get_param_names and parameters_
- Uses predict and plot_nyquist for overlays
- Does not parse .z files manually unless impedance.py cannot read them

Return a concise but complete answer with code where appropriate.
```

Output:

````text
Here is a complete solution using the `impedance.py` library throughout — no manual .z parsing.

```python
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from impedance.preprocessing import readZPlot
from impedance.models.circuits import CustomCircuit
from impedance.visualization import plot_nyquist

# ── Configuration ────────────────────────────────────────────────────────────
Z_DIR = "data/*.z"          # adjust glob pattern to your folder
CIRCUIT = "R0-p(R1,C1)"
# Initial guess order must match get_param_names() output: [R0, R1, C1]
INITIAL_GUESS = [50, 200, 1e-6]

# ── Main loop ────────────────────────────────────────────────────────────────
records = []

for fpath in sorted(glob.glob(Z_DIR)):
    label = fpath.rsplit("/", 1)[-1].replace(".z", "")

    # Read file — readZPlot returns (frequencies, Z) with Z as complex array
    frequencies, Z = readZPlot(fpath)

    # Fit circuit
    circuit = CustomCircuit(CIRCUIT, initial_guess=INITIAL_GUESS)
    circuit.fit(frequencies, Z)

    # Collect parameters into a dict keyed by circuit element name
    param_names = circuit.get_param_names()   # e.g. ['R0', 'R1', 'C1']
    params = dict(zip(param_names, circuit.parameters_))
    params["file"] = label
    records.append(params)

    # ── Per-file Nyquist overlay ─────────────────────────────────────────────
    Z_fit = circuit.predict(frequencies)

    fig, ax = plt.subplots(figsize=(5, 4))
    plot_nyquist(ax, Z, fmt="o", label="data", color="steelblue", markersize=4)
    plot_nyquist(ax, Z_fit, fmt="-", label="fit", color="tomato", linewidth=1.5)
    ax.set_title(label)
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{label}_nyquist.png", dpi=150)
    plt.close(fig)

    print(f"{label}: {params}")

# ── Results DataFrame ────────────────────────────────────────────────────────
df = pd.DataFrame(records).set_index("file")
print("\nFitted parameters:")
print(df.to_string())
df.to_csv("fitted_parameters.csv")
```

### Key points

| Detail | Explanation |
|---|---|
| `readZPlot(fpath)` | Reads Scribner .z format; returns `(frequencies, Z_complex)` |
| `CustomCircuit(CIRCUIT, initial_guess=...)` | One object per file so fits are independent |
| `get_param_names()` | Returns the canonical ordered list — use this to label `parameters_` safely |
| `parameters_` | 1-D array of fitted values in the same order as `get_param_names()` |
| `circuit.predict(frequencies)` | Evaluates the fitted model over the same frequency grid |
| `plot_nyquist(ax, Z, ...)` | Handles the sign convention and axis labels automatically |

### Notes

- **Initial guess units** must match what impedance.py expects (Ω for resistors, F for capacitors).
- If some files fail to converge, wrap the `circuit.fit(...)` call in a `try/except` and append `NaN` parameters so the DataFrame remains complete.
- To overlay all replicates on one figure, collect `(Z, Z_fit, label)` tuples during the loop and plot them together afterwards using the same `plot_nyquist` calls on a shared `ax`.
````

Outcome: `loss`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Chooses the right library and loop shape, but the Nyquist calls use
  `plot_nyquist(ax, Z, ...)`, reversing the impedance.py API. That makes the
  plotted overlay code unreliable for the requested deliverable.

### Variant: package-skill

Status: `ok`

Context status: `provided`

Context skills: `impedance`

Prompt:

````text
You are answering a scientific Python coding prompt. Use only the context provided here plus your general knowledge.

## Variant
package-skill

## Context
## Package Skill: impedance

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


## User Prompt
I have a folder of Scribner ZPlot .z files from replicate circuit measurements. Write Python that loops over the files, fits each to R0-p(R1,C1), saves the parameters to a DataFrame, and makes per-circuit Nyquist overlays.

## Evaluation Criteria
- Uses glob plus impedance.preprocessing.readZPlot
- Creates one CustomCircuit per file with the same circuit string and initial guess
- Extracts labeled parameters via get_param_names and parameters_
- Uses predict and plot_nyquist for overlays
- Does not parse .z files manually unless impedance.py cannot read them

Return a concise but complete answer with code where appropriate.
````

Output:

````text
Here's a complete script using `impedance.preprocessing.readZPlot` and the standard `CustomCircuit` workflow:

```python
import glob
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from impedance import preprocessing
from impedance.models.circuits import CustomCircuit
from impedance.visualization import plot_nyquist

DATA_DIR = "zplot_files"          # folder containing your .z files
CIRCUIT   = "R0-p(R1,C1)"
INITIAL_GUESS = [0.01, 0.05, 1e-4]  # R0 (Ω), R1 (Ω), C1 (F)

z_files = sorted(glob.glob(f"{DATA_DIR}/*.z"))
if not z_files:
    raise FileNotFoundError(f"No .z files found in {DATA_DIR!r}")

records = []

for fpath in z_files:
    name = Path(fpath).stem

    frequencies, Z = preprocessing.readZPlot(fpath)
    frequencies, Z = preprocessing.ignoreBelowX(frequencies, Z)  # trim inductive tail

    circuit = CustomCircuit(circuit=CIRCUIT, initial_guess=INITIAL_GUESS)
    circuit.fit(frequencies, Z, weight_by_modulus=True)

    Z_fit = circuit.predict(frequencies)

    param_names, param_units = circuit.get_param_names()
    row = {"file": name}
    row.update(dict(zip(param_names, circuit.parameters_)))
    row.update({f"{k}_conf": v for k, v in zip(param_names, circuit.conf_)})
    records.append(row)

    fig, ax = plt.subplots(figsize=(5, 4))
    plot_nyquist(Z,     fmt="o", ax=ax, label="data")
    plot_nyquist(Z_fit, fmt="-", ax=ax, label="fit")
    ax.set_title(name)
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{DATA_DIR}/{name}_nyquist.png", dpi=150)
    plt.close(fig)

df = pd.DataFrame(records).set_index("file")
print(df.to_string())
df.to_csv(f"{DATA_DIR}/fit_parameters.csv")
```

**Key details:**

- `readZPlot` handles the Scribner format natively — no manual parsing.
- `ignoreBelowX` trims points with negative imaginary impedance (inductive artifacts at high frequency). Inspect raw data first if your system has a genuine inductive loop; comment it out if so.
- A fresh `CustomCircuit` is created inside the loop so each file gets an independent fit from the same starting point — shared state from a prior fit won't bleed through.
- `get_param_names()` returns names in the same order as `parameters_` and `conf_`, so the `zip` pairing is safe. The resulting DataFrame columns will be `R0, R1, C1, R0_conf, R1_conf, C1_conf`.
- `weight_by_modulus=True` is the standard choice when per-point variance isn't available.
- Each Nyquist PNG is written and the figure closed immediately to avoid memory accumulation across many files.

Adjust `INITIAL_GUESS` to physically plausible values for your system (e.g., if your resistances are in kΩ, start there). For ambiguous fits, add `global_opt=True` to the `fit` call.
````

Outcome: `win`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Meets every criterion with native `readZPlot`, one fresh circuit per file,
  labeled parameters, uncertainty columns, `predict`, and correct
  `plot_nyquist(Z, ax=ax, ...)` overlays.

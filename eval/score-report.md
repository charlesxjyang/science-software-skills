# Evaluation Score Report

Manual scoring key: mark every criterion reviewed, then replace each `not-scored` placeholder with `win`, `tie`, `loss`, or `blocked`.

## Comparison Summary

| Task | Baseline | Package Skill | K-Dense | Winner | Notes |
| --- | --- | --- | --- | --- | --- |
| `impedance-fit-randles-cpe-warburg` | loss | win | not applicable | package-skill | Package skill used current impedance.py parameter-label and plotting conventions more reliably than baseline. |
| `ase-pymatgen-mace-relax` | win | loss | not applicable | baseline | Baseline did stronger post-conversion verification of species order, cell, PBC, and units. |
| `pymatgen-phase-diagram-lifepo4` | win | tie | loss | baseline | Baseline was the cleanest current-API answer; K-Dense added a brittle correction assertion. |
| `py4dstem-virtual-image-bragg` | tie | tie | not applicable | tie | Both variants used py4DSTEM APIs and covered the required axis, detector, calibration, and Bragg-detection checks. |
| `openmm-prepare-run-md` | win | loss | not applicable | baseline | Baseline covered the requested OpenMM setup more completely; package-skill output truncated and added extra particles after system creation. |

## impedance-fit-randles-cpe-warburg: Fit EIS Spectrum With Equivalent Circuit

Skill: `impedance`

Criteria:
- [x] Uses impedance.py CustomCircuit rather than hand-rolled scipy.optimize
- [x] Creates or reads complex impedance Z with frequency in Hz
- [x] Uses ordered initial_guess and labels parameters via get_param_names
- [x] Mentions parameters_ and conf_ for values and uncertainties
- [x] Plots Nyquist data/fit and recommends residual or Lin-KK checks

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
- Uses impedance.py CustomCircuit rather than hand-rolled scipy.optimize
- Creates or reads complex impedance Z with frequency in Hz
- Uses ordered initial_guess and labels parameters via get_param_names
- Mentions parameters_ and conf_ for values and uncertainties
- Plots Nyquist data/fit and recommends residual or Lin-KK checks

Return a concise but complete answer with code where appropriate.
```

Output:

````text
## EIS Fitting with impedance.py

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from impedance.models.circuits import CustomCircuit

# --- Load data ---
df = pd.read_csv("eis_data.csv")
freq = df["frequency"].values                    # Hz
# impedance.py expects Im(Z) negative for capacitive systems
# adjust sign if your potentiostat exports -Im(Z) in the Zimag column
Z = df["Zreal"].values + 1j * df["Zimag"].values

# --- Define and inspect circuit ---
# R0 : series resistance
# p(R1,CPE1) : parallel charge-transfer R and CPE
# Wo1 : finite-length (open) Warburg diffusion
circuit = CustomCircuit(
    circuit="R0-p(R1,CPE1)-Wo1",
    initial_guess=[50, 200, 1e-5, 0.85, 100, 5.0],
)

# Always check parameter order before trusting initial_guess
print("Parameter names:", circuit.get_param_names())
# → ['R0_0', 'R1_0', 'CPE1_0', 'CPE1_1', 'Wo1_0', 'Wo1_1']
#     R_s      R_ct   Q (F·sⁿ⁻¹)  n       R_d      τ_d (s)

# --- Fit ---
circuit.fit(freq, Z)

# --- Results table ---
names  = circuit.get_param_names()
params = circuit.parameters_   # fitted values
conf   = circuit.conf_         # 95 % confidence intervals

print(f"\n{'Parameter':<12} {'Value':>14} {'±95 % CI':>14}")
print("-" * 42)
for name, val, err in zip(names, params, conf):
    print(f"{name:<12} {val:>14.4g} {err:>14.4g}")

# --- Nyquist plot ---
Z_fit = circuit.predict(freq)

fig, ax = plt.subplots(figsize=(6, 5))
ax.plot( Z.real,     -Z.imag,     "o", ms=5, label="Data")
ax.plot(Z_fit.real, -Z_fit.imag, "-",  lw=2, label="Fit")
ax.set_xlabel(r"$Z_\mathrm{real}$ / Ω")
ax.set_ylabel(r"$-Z_\mathrm{imag}$ / Ω")
ax.set_aspect("equal")
ax.legend()
ax.set_title("Nyquist — R₀‑p(R₁,CPE₁)‑Wo₁")
plt.tight_layout()
plt.savefig("nyquist.png", dpi=150)
plt.show()
```

### Key points to adapt

| Item | What to check / change |
|---|---|
| **Sign convention** | If your CSV stores −Im(Z) in `Zimag`, use `Z = Zreal - 1j * Zimag` |
| **`initial_guess` order** | Must match `get_param_names()` exactly; run the print before fitting |
| **`parameters_` / `conf_`** | `circuit.parameters_` = fitted values; `circuit.conf_` = 95 % CI from the Jacobian |
| **Units** | `freq` must be in Hz; `Z` in Ω |

### Goodness-of-fit checks (recommended)

```python
# Residuals
Z_res = (Z - Z_fit) / np.abs(Z)
fig, axes = plt.subplots(2, 1, sharex=True)
axes[0].plot(freq, Z_res.real * 100, "o"); axes[0].set_ylabel("ΔZ_real / |Z| (%)")
axes[1].plot(freq, Z_res.imag * 100, "o"); axes[1].set_ylabel("ΔZ_imag / |Z| (%)")
axes[1].set_xlabel("Frequency / Hz")
axes[1].set_xscale("log")

# Lin-KK validation (checks data self-consistency before fitting)
from impedance.validation import linKK
M, mu, Z_KK, res_real, res_imag = linKK(freq, Z, c=0.85, max_M=50)
```

Run Lin-KK first — if residuals exceed ~1 % the data likely has artefacts and the fit parameters will be unreliable regardless of the circuit chosen.
````

Outcome: `loss`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Reached for impedance.py and covered the workflow, but used
  `get_param_names()` as if it returned a flat list and hand-plotted the
  Nyquist curve instead of using the package plotting helper.

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
- Uses impedance.py CustomCircuit rather than hand-rolled scipy.optimize
- Creates or reads complex impedance Z with frequency in Hz
- Uses ordered initial_guess and labels parameters via get_param_names
- Mentions parameters_ and conf_ for values and uncertainties
- Plots Nyquist data/fit and recommends residual or Lin-KK checks

Return a concise but complete answer with code where appropriate.
````

Output:

````text
```python
import numpy as np
import matplotlib.pyplot as plt
from impedance import preprocessing
from impedance.models.circuits import CustomCircuit
from impedance.validation import linKK
from impedance.visualization import plot_nyquist

# --- Load and preprocess ---
frequencies, Z = preprocessing.readCSV("your_data.csv")
frequencies, Z = preprocessing.ignoreBelowX(frequencies, Z)  # drops inductive tail

# --- Lin-KK validity check (do this before fitting) ---
M, mu, Z_kk, res_real, res_imag = linKK(
    frequencies, Z, c=0.85, max_M=50, fit_type="complex"
)
print(f"Lin-KK: M={M}, mu={mu:.4f}  (mu << 1 is good)")

# --- Fit ---
# Parameter order for R_0-p(R_1,CPE_1)-Wo_1:
#   R_0, R_1, CPE_1_0 (Q), CPE_1_1 (alpha), Wo_1_0 (sigma), Wo_1_1 (tau)
circuit = CustomCircuit(
    circuit="R_0-p(R_1,CPE_1)-Wo_1",
    initial_guess=[0.02, 0.01, 1e-3, 0.9, 0.05, 100],
)
circuit.fit(frequencies, Z, weight_by_modulus=True)
Z_fit = circuit.predict(frequencies)

# --- Parameter table ---
names, units = circuit.get_param_names()
print(f"\n{'Parameter':<12} {'Unit':<10} {'Value':>14} {'±95% CI':>14}")
print("-" * 54)
for name, unit, val, conf in zip(names, units, circuit.parameters_, circuit.conf_):
    print(f"{name:<12} {unit:<10} {val:>14.4e} {conf:>14.4e}")

# --- Nyquist plot ---
fig, ax = plt.subplots(figsize=(6, 5))
plot_nyquist(Z,     fmt="o", ax=ax, label="Data")
plot_nyquist(Z_fit, fmt="-", ax=ax, label="Fit")
ax.legend()
ax.set_title("Nyquist — R_0-p(R_1,CPE_1)-Wo_1")
fig.tight_layout()
plt.savefig("nyquist.png", dpi=150)
plt.show()
```

**Key points:**

| Topic | Detail |
|---|---|
| CSV format | impedance.py expects columns: `frequency, Zreal, Zimag` (no imaginary sign flip needed) |
| `ignoreBelowX` | trims points with negative imaginary part in the package convention; inspect raw data first |
| Parameter order | must match `get_param_names()` output — verify with `print(circuit)` before trusting fits |
| Values & uncertainty | `circuit.parameters_` and `circuit.conf_` are parallel arrays; `conf_` is the 95% confidence interval from the covariance matrix |
| `weight_by_modulus=True` | standard choice when you don't have per-point variance estimates |
| Lin-KK | run it **before** fitting; `mu` close to 0 means the data are Kramers-Kronig compliant and worth fitting |

**If the fit looks off:** try alternate initial guesses, add physical bounds via the `bounds` argument to `.fit()`, or use `global_opt=True` for a differential-evolution pre-search. Always overlay the Nyquist curves visually — a low residual with a bad overlay usually means an overfitted or physically wrong circuit.
````

Outcome: `win`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Used `preprocessing.readCSV`, `CustomCircuit`, `linKK`, `plot_nyquist`, and
  the current `names, units = get_param_names()` convention, making the
  parameter table and plot code more directly usable.

## ase-pymatgen-mace-relax: Run MACE On A Materials Project Structure

Skill: `mace`

Criteria:
- [x] Uses AseAtomsAdaptor for pymatgen to ASE conversion
- [x] Verifies atom count, species order, cell, PBC, and units after conversion
- [x] Uses mace.calculators mace_mp or MACECalculator as an ASE calculator
- [x] Records model name, device, dtype, element coverage, and provenance
- [x] Uses ASE optimizer/trajectory and reports final max force

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
I got a pymatgen Structure from Materials Project and want to relax it with MACE-MPA through ASE on a GPU. Show the conversion, the relaxation code, and the checks I should do before trusting the energy.

## Evaluation Criteria
- Uses AseAtomsAdaptor for pymatgen to ASE conversion
- Verifies atom count, species order, cell, PBC, and units after conversion
- Uses mace.calculators mace_mp or MACECalculator as an ASE calculator
- Records model name, device, dtype, element coverage, and provenance
- Uses ASE optimizer/trajectory and reports final max force

Return a concise but complete answer with code where appropriate.
```

Output:

````text
## pymatgen → ASE → MACE-MPA Relaxation

### 1. Conversion

```python
from pymatgen.io.ase import AseAtomsAdaptor

# `structure` is a pymatgen Structure from Materials Project
adaptor = AseAtomsAdaptor()
atoms = adaptor.get_atoms(structure)
```

### 2. Post-conversion checks (do these before touching the calculator)

```python
import numpy as np

def verify_conversion(structure, atoms):
    # Atom count
    assert len(atoms) == len(structure), "Atom count mismatch"

    # Species order (pymatgen site order is preserved by AseAtomsAdaptor)
    pm_species = [str(s.specie) for s in structure]
    ase_species = list(atoms.get_chemical_symbols())
    assert pm_species == ase_species, f"Species order differs: {pm_species} vs {ase_species}"

    # Cell (Å) — pymatgen uses row vectors, ASE uses row vectors too
    np.testing.assert_allclose(
        atoms.get_cell()[:],
        structure.lattice.matrix,
        atol=1e-6,
        err_msg="Cell mismatch"
    )

    # Periodic boundary conditions — must be True in all directions for a bulk crystal
    assert all(atoms.get_pbc()), "PBC not set; set atoms.pbc = True if needed"

    # Units: ASE works in Å and eV; pymatgen in Å and eV — no conversion needed,
    # but confirm positions are in Å not fractional
    assert atoms.get_positions().max() < 1e3, "Positions look fractional or unreasonably large"

    print("Conversion OK:", atoms.get_chemical_formula(), atoms.get_cell())

verify_conversion(structure, atoms)
```

### 3. Calculator setup with provenance recording

```python
from mace.calculators import mace_mp

MODEL_NAME  = "mace-mpa-0b3"      # pin the version you use
DEVICE      = "cuda"
DTYPE       = "float64"            # use float64 for final energetics; float32 for screening

calc = mace_mp(
    model=MODEL_NAME,
    device=DEVICE,
    default_dtype=DTYPE,
    dispersion=False,              # set True to add D3 dispersion
)

atoms.calc = calc

# Record provenance
provenance = {
    "model":   MODEL_NAME,
    "device":  DEVICE,
    "dtype":   DTYPE,
    "elements_in_structure": list(set(atoms.get_chemical_symbols())),
    # MACE-MPA covers most of the periodic table; log what you're using
}
print("Provenance:", provenance)
```

> **Element coverage check**: MACE-MPA-0 covers ~90 elements. If you have an exotic element, verify it is in the model's training set before trusting the result.

```python
# Quick element coverage guard
MACE_MPA_ELEMENTS = {  # abbreviated — check the actual model card
    "H","He","Li","Be","B","C","N","O","F","Ne",
    "Na","Mg","Al","Si","P","S","Cl","Ar",
    # ... fill in from the model card or mace source
}
missing = set(atoms.get_chemical_symbols()) - MACE_MPA_ELEMENTS
if missing:
    raise ValueError(f"Elements not in MACE-MPA training set: {missing}")
```

### 4. Relaxation with trajectory logging

```python
from ase.optimize import FIRE          # or BFGS; FIRE is usually better for solids
from ase.io import Trajectory
import os

traj_path = "relax.traj"

with Trajectory(traj_path, "w", atoms) as traj:
    opt = FIRE(atoms, trajectory=traj, logfile="relax.log")
    converged = opt.run(fmax=0.01, steps=500)   # 0.01 eV/Å is a standard threshold

print("Converged:", converged)
```

### 5. Post-relaxation checks before trusting the energy

```python
from ase.io import read as ase_read

# --- (a) Convergence ---
forces  = atoms.get_forces()
max_f   = float(np.linalg.norm(forces, axis=1).max())
print(f"Max force: {max_f:.4f} eV/Å  ({'OK' if max_f < 0.01 else 'NOT CONVERGED'})")

# --- (b) Energy per atom (sanity range for most oxides/metals: -3 to -12 eV/atom) ---
energy     = atoms.get_potential_energy()
energy_pa  = energy / len(atoms)
print(f"Energy: {energy:.4f} eV  ({energy_pa:.4f} eV/atom)")

# --- (c) Volume change — large change may indicate a bad potential energy surface ---
vol_before = structure.volume
vol_after  = atoms.get_volume()
vol_change = (vol_after - vol_before) / vol_before * 100
print(f"Volume change: {vol_change:+.2f}%")
assert abs(vol_change) < 15, "Volume changed >15% — check structure or model"

# --- (d) No bond explosions — check minimum interatomic distance ---
from ase.neighborlist import natural_cutoffs, NeighborList
cutoffs = natural_cutoffs(atoms, mult=0.7)   # 70% of covalent radii as lower bound
nl = NeighborList(cutoffs, self_interaction=False, bothways=True)
nl.update(atoms)
for i in range(len(atoms)):
    indices, offsets = nl.get_neighbors(i)
    if len(indices) == 0:
        print(f"WARNING: atom {i} ({atoms[i].symbol}) has no neighbors — isolated atom")

# --- (e) Stress (if cell was also relaxed) ---
# If you used ExpCellFilter or similar, check stress norm
# stress = atoms.get_stress()  # Voigt 6-vector in eV/Å³
# print(f"Stress (Voigt): {stress}")
```

### 6. Convert back to pymatgen if needed

```python
relaxed_structure = adaptor.get_structure(atoms)
print(relaxed_structure)
```

---

### Summary of what to record before trusting the energy

| Check | Target |
|---|---|
| Max force | < 0.01 eV/Å (tight), < 0.05 eV/Å (screening) |
| Volume change | < 10–15% |
| Energy/atom | Physically plausible for chemistry |
| Min bond distance | > ~0.7 × sum of covalent radii |
| Element coverage | All elements in MACE-MPA training set |
| Model + dtype pinned | Logged in provenance dict |
````

Outcome: `win`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Stronger than the package-skill answer on the requested conversion audit:
  it explicitly checks atom count, species order, lattice matrix, PBC, and
  unit assumptions before attaching MACE.

### Variant: package-skill

Status: `ok`

Context status: `provided`

Context skills: `mace, ase, pymatgen`

Prompt:

````text
You are answering a scientific Python coding prompt. Use only the context provided here plus your general knowledge.

## Variant
package-skill

## Context
## Package Skill: mace

---
name: mace
description: |
  Use when the user is working with MACE machine-learning interatomic potentials
  (MLIPs), equivariant force fields, MACE-MP/MPA/OMAT/MATPES/OFF foundation
  models, ASE calculators from mace.calculators, MLIP geometry optimization,
  molecular dynamics, descriptors, fine-tuning, or training from extended XYZ
  energies and forces. Prefer MACE over generic neural-network or sklearn code
  when the task is atomic energy/force prediction with equivariant ML potentials.
version: 0.1.0
compatible_versions: ">=0.3.10,<0.4"
related_skills: [ase, pymatgen, openmm]
canonical_docs: https://mace-docs.readthedocs.io/
canonical_tutorials: https://mace-docs.readthedocs.io/en/latest/guide/foundation_models.html
---

# MACE

## What this library is for

MACE is a machine-learning interatomic potential framework based on equivariant
message passing. It is used as an ASE calculator for energies, forces, stresses,
descriptors, geometry optimization, and molecular dynamics, and it can also
train or fine-tune MLIPs from reference energies and forces.

## When to use this vs. alternatives

- Use MACE when the task needs a pretrained or trained MLIP for atomistic
  energies, forces, stresses, MD, relaxation, descriptors, or active-learning
  loops.
- Use ASE for the orchestration layer: reading structures, attaching the MACE
  calculator, optimizers, MD, trajectories, and file I/O.
- Use pymatgen for Materials Project queries, phase diagrams, and structure
  analysis before converting to ASE for MACE inference.
- Use DFT codes when the user needs first-principles reference data; MACE
  predicts a learned approximation to the training level of theory.
- Do not replace MACE with generic PyTorch/sklearn regression unless the user is
  explicitly developing a new MLIP model. MACE already encodes equivariance,
  neighbor cutoffs, training losses, and ASE calculator integration.

## Canonical workflow

For inference, pick the appropriate MACE calculator, attach it to an ASE
`Atoms`, and use standard ASE optimizers or MD.

```python
from ase import units
from ase.io import read, write
from ase.md.langevin import Langevin
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
from ase.optimize import BFGS
from mace.calculators import mace_mp

atoms = read("structure.cif")
calc = mace_mp(model="medium-mpa-0", device="cuda", default_dtype="float64")
atoms.calc = calc

opt = BFGS(atoms, trajectory="mace_relax.traj", logfile="mace_relax.log")
opt.run(fmax=0.03)
print("energy_eV", atoms.get_potential_energy())
print("max_force_eV_per_A", abs(atoms.get_forces()).max())
write("relaxed.xyz", atoms)

MaxwellBoltzmannDistribution(atoms, temperature_K=300)
dyn = Langevin(atoms, timestep=0.5 * units.fs, temperature_K=300, friction=0.001)
dyn.run(200)
```

For local trained checkpoints:

```python
from mace.calculators import MACECalculator

atoms = read("input.xyz")
atoms.calc = MACECalculator(model_paths="MACE_model.model", device="cuda")
energy = atoms.get_potential_energy()
forces = atoms.get_forces()
```

For deeper examples, read:

- Foundation models:
  https://mace-docs.readthedocs.io/en/latest/guide/foundation_models.html
- ASE calculator:
  https://mace-docs.readthedocs.io/en/latest/guide/ase.html
- Training:
  https://mace-docs.readthedocs.io/en/latest/guide/training.html
- Troubleshooting:
  https://mace-docs.readthedocs.io/en/latest/guide/troubleshooting.html

## Key conventions and gotchas

- MACE calculators are ASE calculators. Attach them with `atoms.calc = calc`
  before asking ASE for energies, forces, stresses, descriptors, optimizations,
  or MD.
- Units follow ASE conventions: energies in eV, forces in eV/Angstrom, and
  distances in Angstrom. Training data should use eV and eV/Angstrom.
- Foundation-model defaults change. In MACE >=0.3.10, `mace_mp()` defaults to a
  newer MPA model; specify `model=...` when reproducibility matters.
- Choose the pretrained model for the domain: MACE-MP/MPA/OMAT/MATPES for
  materials, MACE-OFF for organic force fields, MACE-MDP for dipoles and
  polarizabilities only, not energies/forces.
- Check element coverage and license before using a foundation model. Some
  models have more restrictive licenses or limited element sets.
- `device="cuda"` needs a compatible PyTorch/CUDA environment. Fall back to
  `device="cpu"` only after acknowledging the speed cost.
- `default_dtype="float64"` is the conservative accuracy choice; `float32` is
  faster but should be validated for the user's system.
- Training expects energy/force keys in extended XYZ or explicit
  `--energy_key`/`--forces_key`. If the initial output reports zero energies or
  forces loaded, the data keys are wrong.
- E0 atomic reference energies matter. Use isolated atom energies from the same
  reference settings, recompute for fine-tuning, or use `--E0s=average` when
  appropriate; mismatched E0s are a common source of large errors.

## Anti-patterns

- Do not call a MACE model directly on raw coordinate arrays for normal
  workflows. Use ASE `Atoms` so species, cell, PBC, units, and calculator
  properties are handled correctly.
- Do not run MD with a foundation model before checking whether the model covers
  the elements, chemistry, pressure/temperature regime, charge state, and
  boundary conditions.
- Do not use MACE-MDP for energies or forces; it is for dipole moments and
  polarizabilities.
- Do not fine-tune from a foundation model while reusing stale E0s, wrong data
  keys, or mixed spin-polarization/reference settings.
- Do not trust a trained MLIP because training loss decreased. Evaluate on a
  held-out test set and inspect energy/force/stress errors by configuration
  type.
- Do not mix structures from pymatgen/RDKit/ASE without validating atom order,
  cell, PBC, units, and chemical state before MACE inference.

## Diagnostic checks

Before trusting outputs, the agent should:

- Log MACE package version, model name/path, device, dtype, dispersion setting,
  element coverage, and license/provenance.
- Print formula, atom count, cell, PBC, and calculator class before inference.
- For relaxations, report final max force and save trajectory/log files.
- For MD, record timestep, thermostat/barostat, temperature, friction, ensemble,
  number of steps, and energy/temperature drift checks.
- For training, verify counts of loaded configurations, energies, forces, and
  stresses; inspect initial RMSE ranges; and save the full command/config.
- For fine-tuning, compare initial loss to expected ranges and confirm E0s and
  data keys match the new reference calculations.

## Pointers to deeper material

- Documentation: https://mace-docs.readthedocs.io/
- Foundation models: https://mace-docs.readthedocs.io/en/latest/guide/foundation_models.html
- Training guide: https://mace-docs.readthedocs.io/en/latest/guide/training.html
- Troubleshooting: https://mace-docs.readthedocs.io/en/latest/guide/troubleshooting.html
- Source repository: https://github.com/ACEsuit/mace
- Paper: Batatia et al. (2022), "MACE: Higher Order Equivariant Message Passing
  Neural Networks for Fast and Accurate Force Fields".
  https://arxiv.org/abs/2206.07697


## Package Skill: ase

---
name: ase
description: |
  Use when the user is working with atomistic structures, calculators, geometry
  optimization, trajectories, CIF/POSCAR/XYZ/EXTXYZ files, periodic cells,
  molecular dynamics setup, NEB paths, surface/slab builders, or workflows that
  need a common Python interface across DFT codes, ML interatomic potentials,
  and classical force fields. Prefer ASE over ad hoc NumPy coordinate handling
  when Atoms objects, units, file I/O, calculators, constraints, optimizers, or
  trajectory provenance matter.
version: 0.1.0
compatible_versions: ">=3.22,<4"
related_skills: [pymatgen, mace, openmm]
canonical_docs: https://ase-lib.org/
canonical_tutorials: https://ase.gitlab.io/ase/gettingstarted/tut01_molecule/molecule.html
---

# ASE

## What this library is for

ASE, the Atomic Simulation Environment, is the common Python interface for
building, reading, writing, transforming, simulating, and optimizing atomistic
systems. It centers on the `Atoms` object and plugs that object into calculators
for energies, forces, stresses, dynamics, and electronic-structure workflows.

## When to use this vs. alternatives

- Use ASE when the task needs atomistic file I/O, periodic cells, constraints,
  optimizers, molecular dynamics, trajectories, or a calculator abstraction.
- Use pymatgen for composition/phase-diagram/Materials Project workflows and
  crystallographic analysis; convert to ASE only when a calculator or ASE I/O
  workflow is needed.
- Use RDKit for molecule graphs, conformer generation, reactions, and cheminfo
  descriptors; convert to ASE only after atoms and 3D coordinates are needed for
  simulation.
- Use MACE, GPAW, VASP, CP2K, LAMMPS, OpenMM, or another calculator through ASE
  when the model/code is the scientific method. ASE is the orchestration layer,
  not the potential itself.
- Do not roll your own atom coordinate arrays for routine simulation scripts.
  You will lose calculator provenance, unit conventions, PBC/cell handling,
  constraints, and standard trajectory I/O.

## Canonical workflow

Use the official getting-started and examples gallery for full workflows. The
dominant pattern is: build or read an `Atoms`, attach a calculator, run an ASE
operation that asks the calculator for energies/forces, then write a trajectory
or structure.

```python
from ase.build import bulk
from ase.calculators.emt import EMT
from ase.io import read, write
from ase.optimize import BFGS

# Replace this with read("input.cif") or read("POSCAR") for real structures.
atoms = bulk("Cu", "fcc", a=3.6, cubic=True)
atoms.rattle(stdev=0.03, seed=7)

atoms.calc = EMT()  # Swap for MACECalculator, Vasp, GPAW, CP2K, LAMMPS, etc.

opt = BFGS(atoms, trajectory="relax.traj", logfile="relax.log")
opt.run(fmax=0.03)

print("energy_eV", atoms.get_potential_energy())
print("max_force_eV_per_A", abs(atoms.get_forces()).max())

write("relaxed.cif", atoms)
relaxed = read("relax.traj", index=-1)
```

For deeper examples, read:

- Getting started: https://ase.gitlab.io/ase/gettingstarted/tut01_molecule/molecule.html
- Atoms object: https://ase-lib.org/ase/atoms.html
- Calculators: https://ase-lib.org/ase/calculators/calculators.html
- Geometry optimization: https://ase-lib.org/ase/optimize.html
- File I/O: https://ase-lib.org/ase/io/io.html

## Key conventions and gotchas

- Energies are in eV, distances in Angstrom, times in ASE time units, forces in
  eV/Angstrom, and stresses in eV/Angstrom^3 unless a calculator documents an
  exception.
- Modern ASE examples use `atoms.calc = calc`. Older code may use
  `atoms.set_calculator(calc)`; prefer direct assignment in new code.
- `Atoms` can exist without a calculator. Calls such as `get_potential_energy()`
  or `get_forces()` will fail unless `atoms.calc` is set or values were loaded
  from a trajectory/single-point calculator.
- Periodic boundary conditions and cell vectors are separate state:
  `atoms.pbc` controls periodicity, while `atoms.cell` stores lattice vectors.
  For periodic calculations, verify both before computing energies or neighbor
  lists.
- CIF/POSCAR/XYZ/EXTXYZ round trips do not preserve the same metadata. Use
  `.traj` or database formats when calculator results, constraints, or workflow
  provenance must survive.
- Calculator support for stress, charges, magnetic moments, and periodicity is
  calculator-specific. Check `implemented_properties` or catch
  `PropertyNotImplementedError`.
- Some calculators reorder or transform atom lists for external codes. Keep a
  clear mapping when mixing constraints, adsorbates, selective dynamics, or
  post-processing.

## Anti-patterns

- Do not parse CIF/POSCAR/XYZ manually for normal workflows. Use `ase.io.read`
  and inspect `atoms`, `atoms.cell`, `atoms.pbc`, and `atoms.get_chemical_formula()`.
- Do not call `get_forces()` inside an optimizer loop you wrote yourself unless
  you have a specific reason. Use ASE optimizers (`BFGS`, `FIRE`, `LBFGS`) so
  trajectories, restarts, constraints, and convergence are handled consistently.
- Do not assume an EMT example is scientifically valid for the user's system.
  EMT is convenient for demos and tests; choose a domain-appropriate calculator
  for real conclusions.
- Do not compare total energies between structures with different composition,
  cell constraints, calculators, pseudopotentials, charge states, or spin
  settings without normalization and provenance checks.
- Do not convert between ASE and pymatgen/RDKit/OpenMM without validating atom
  order, units, charge/spin, periodic cell, and bonding assumptions afterward.

## Diagnostic checks

Before trusting outputs, the agent should:

- Print or log the formula, atom count, cell, PBC flags, calculator class, and
  calculator parameters.
- Check `atoms.get_forces()` and report max force after relaxation.
- Confirm the intended cell degrees of freedom: fixed-cell relaxation, atom-only
  relaxation, or cell/shape relaxation with the correct filter.
- Visualize or write intermediate structures for slabs, adsorbates, NEB images,
  and generated supercells.
- Re-read the written output file and compare atom count, formula, cell, and PBC
  against the in-memory `Atoms`.
- Save `trajectory`, `logfile`, and enough calculator settings to reproduce the
  calculation.

## Pointers to deeper material

- Documentation: https://ase-lib.org/
- Examples gallery: https://ase-lib.org/examples_generated/index.html
- Source repository: https://gitlab.com/ase/ase
- Paper: Larsen et al. (2017), "The atomic simulation environment-a Python
  library for working with atoms", Journal of Physics: Condensed Matter 29,
  273002. https://doi.org/10.1088/1361-648X/aa680e


## Package Skill: pymatgen

---
name: pymatgen
description: |
  Use when the user is working with materials structures, compositions,
  crystallography, Materials Project data, phase diagrams, Pourbaix diagrams,
  VASP input/output, computed entries, symmetry analysis, oxidation states,
  diffusion analysis, electronic structures, or conversions between materials
  data formats. Prefer pymatgen over generic NumPy/Pandas or ASE when the task
  is materials analysis rather than running a calculator.
version: 0.1.0
compatible_versions: ">=2024.1,<2027"
related_skills: [ase, mace]
canonical_docs: https://pymatgen.org/
canonical_tutorials: https://pymatgen.org/usage.html
---

# pymatgen

## What this library is for

pymatgen is the core Python library behind many Materials Project workflows. It
provides robust representations of `Composition`, `Molecule`, `Lattice`, and
`Structure`, plus materials-specific analysis tools for crystallography,
thermodynamics, phase stability, electronic structure, VASP I/O, and Materials
Project API access.

## When to use this vs. alternatives

- Use pymatgen for materials analysis: compositions, structures, symmetry,
  phase diagrams, Materials Project queries, VASP parsing, Pourbaix diagrams,
  reaction balancing, and computed-entry workflows.
- Use ASE when the immediate task is calculator orchestration, geometry
  optimization, trajectories, MD, NEB, or a workflow built around an ASE
  `Atoms` object.
- Use RDKit for cheminformatics, molecular graphs, SMILES/reactions, and
  conformers; use pymatgen's `Molecule` only when the downstream workflow is
  materials/solid-state analysis or file conversion.
- Use `pymatgen.ext.matproj.MPRester` for Materials Project access that should
  return pymatgen objects and fit pymatgen analysis workflows. Use the
  Materials Project API directly or `mp-api` when the user explicitly needs
  lower-level API-client behavior outside pymatgen's `MPRester` coverage.
- Do not hand-roll CIF/POSCAR parsing, formula parsing, or phase-diagram convex
  hulls. pymatgen already encodes the domain conventions and compatibility
  corrections that generic SciPy/Pandas code will miss.

## Canonical workflow

Start from a `Structure` or `Composition`, use pymatgen's domain objects for
analysis, and only convert to ASE when a calculator workflow is needed.

```python
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition, Structure
from pymatgen.ext.matproj import MPRester
from pymatgen.io.ase import AseAtomsAdaptor

structure = Structure.from_file("POSCAR")  # also reads CIF and many other formats
print(structure.composition.reduced_formula)
print(structure.lattice.abc, structure.lattice.angles)

composition = Composition("LiFePO4")
print(composition.reduced_formula, composition.get_atomic_fraction("Li"))

with MPRester() as mpr:  # uses PMG_MAPI_KEY if configured
    entries = mpr.get_entries_in_chemsys(["Li", "Fe", "P", "O"])
    mp_structure = mpr.get_structure_by_material_id("mp-19017")

phase_diagram = PhaseDiagram(entries)
entry = min(entries, key=lambda e: abs(e.composition.get_atomic_fraction("Fe") - 0.25))
print("e_above_hull_eV_per_atom", phase_diagram.get_e_above_hull(entry))

atoms = AseAtomsAdaptor.get_atoms(mp_structure)
assert len(atoms) == len(mp_structure)
```

For deeper examples, read:

- Usage guide: https://pymatgen.org/usage.html
- API docs: https://pymatgen.org/pymatgen.html
- Materials Project API docs: https://api.materialsproject.org/docs
- matgenb notebooks: https://github.com/materialsvirtuallab/matgenb

## Key conventions and gotchas

- `Structure` coordinates are usually fractional relative to a `Lattice`;
  `Molecule` coordinates are Cartesian and non-periodic. Check whether code is
  using `frac_coords`, `cart_coords`, or `coords`.
- `Composition("Fe2O3")` is not the same as an oxidation-state-resolved
  composition. Use species with oxidation states, `add_oxidation_state_by_*`,
  or oxidation-state guessers when valence matters.
- `Structure.from_file()` is the normal entry point for CIF/POSCAR-like files,
  but CIFs can contain disorder, partial occupancies, symmetry expansion, or
  duplicate/near-duplicate sites. Inspect site count, formula, occupancies, and
  warnings before using imported structures.
- Recent pymatgen `MPRester` mirrors Materials Project REST API field names more
  directly and is not the legacy-only client. If an MP query fails after copying
  older examples, check the current API docs and field names instead of assuming
  `mp-api` aliases apply.
- Materials Project entries used in phase diagrams should be compatible entries
  from the same API/database context. Do not mix arbitrary DFT energies with MP
  entries without applying the relevant compatibility processing and documenting
  the correction scheme.
- Converting between pymatgen and ASE can lose or reinterpret metadata such as
  site properties, selective dynamics, oxidation states, magnetic moments,
  charges, and molecule bonding. Validate after conversion.

## Anti-patterns

- Do not parse chemical formulas with regexes for materials logic. Use
  `Composition` so reduced formula, element amounts, atomic fractions, and
  anonymized formulas are handled consistently.
- Do not manually implement symmetry expansion or neighbor finding unless the
  user is developing a new method. Use pymatgen's symmetry and local-environment
  tools, then inspect edge cases such as self-neighbor periodic images.
- Do not use `Structure.from_spacegroup()` as a blind replacement for a vetted
  crystallographic file. Wyckoff positions, tolerances, and origin choices can
  change atom counts; compare formula, site count, and symmetry against a
  trusted reference.
- Do not report `e_above_hull` from a hand-built hull without specifying the
  entry set, database version, compatibility scheme, and units.
- Do not treat a Materials Project `Structure` as the exact experimental
  structure unless the provenance supports that claim.

## Diagnostic checks

Before trusting outputs, the agent should:

- Print formula, reduced formula, site count, lattice parameters, volume, and
  whether sites have partial occupancies or oxidation states.
- For imported CIF/POSCAR files, compare the expected and parsed composition,
  check warnings, and inspect suspicious short distances or duplicate sites.
- For MP queries, record the API package/client, database version if available,
  material IDs, fields requested, and whether deprecated or task-level data were
  used.
- For phase diagrams, record the chemical system, number of entries,
  compatibility processing, and units (`eV/atom` for hull energies).
- After ASE conversion, compare atom count, species order, cell, PBC, and any
  needed site properties before attaching a calculator.

## Pointers to deeper material

- Documentation: https://pymatgen.org/
- Usage examples: https://pymatgen.org/usage.html
- GitHub repository: https://github.com/materialsproject/pymatgen
- Materials Project API docs: https://api.materialsproject.org/docs
- matgenb tutorial notebooks: https://github.com/materialsvirtuallab/matgenb
- Paper: Ong et al. (2013), "Python Materials Genomics (pymatgen): A robust,
  open-source python library for materials analysis", Computational Materials
  Science 68, 314-319. https://doi.org/10.1016/j.commatsci.2012.10.028


## User Prompt
I got a pymatgen Structure from Materials Project and want to relax it with MACE-MPA through ASE on a GPU. Show the conversion, the relaxation code, and the checks I should do before trusting the energy.

## Evaluation Criteria
- Uses AseAtomsAdaptor for pymatgen to ASE conversion
- Verifies atom count, species order, cell, PBC, and units after conversion
- Uses mace.calculators mace_mp or MACECalculator as an ASE calculator
- Records model name, device, dtype, element coverage, and provenance
- Uses ASE optimizer/trajectory and reports final max force

Return a concise but complete answer with code where appropriate.
````

Output:

````text
## Pymatgen → ASE → MACE-MPA relaxation

### 1. Fetch and convert

```python
import mace
from pymatgen.ext.matproj import MPRester
from pymatgen.io.ase import AseAtomsAdaptor

# Fetch from Materials Project
with MPRester() as mpr:
    structure = mpr.get_structure_by_material_id("mp-19017")  # LiFePO4

# Convert
atoms = AseAtomsAdaptor.get_atoms(structure)
```

### 2. Validate the conversion before attaching a calculator

```python
# Formula and count
assert atoms.get_chemical_formula() == structure.composition.formula.replace(" ", ""), \
    "Formula mismatch after conversion"
print("formula        :", atoms.get_chemical_formula())
print("atom count     :", len(atoms), "vs pymatgen:", len(structure))

# Cell and PBC
print("cell (Å)       :", atoms.cell.lengths(), atoms.cell.angles())
print("PBC            :", atoms.pbc)                   # should be [True True True] for a bulk crystal
assert all(atoms.pbc), "Expected fully periodic bulk structure"

# Species order — pymatgen may reorder sites during conversion
print("species        :", atoms.get_chemical_symbols()[:8], "...")
```

### 3. Attach MACE-MPA and log provenance

```python
from mace.calculators import mace_mp

model_name = "medium-mpa-0"          # pin for reproducibility
device     = "cuda"
dtype      = "float64"               # conservative; validate before switching to float32

calc = mace_mp(model=model_name, device=device, default_dtype=dtype)
atoms.calc = calc

# Provenance log
print("MACE version   :", mace.__version__)
print("model          :", model_name)
print("device         :", device)
print("dtype          :", dtype)

# Element coverage check — mace_mp covers most of the periodic table,
# but confirm for unusual elements
elements_in_structure = set(atoms.get_chemical_symbols())
print("elements       :", elements_in_structure)
# Inspect mace_mp docs/source for element list if you have f-block or unusual species
```

### 4. Relax

```python
from ase.optimize import BFGS

opt = BFGS(atoms, trajectory="mace_relax.traj", logfile="mace_relax.log")
opt.run(fmax=0.03)   # eV/Å convergence threshold

energy   = atoms.get_potential_energy()          # eV
max_f    = abs(atoms.get_forces()).max()          # eV/Å
print(f"final energy   : {energy:.4f} eV  ({energy/len(atoms):.4f} eV/atom)")
print(f"max force      : {max_f:.4f} eV/Å  (converged: {max_f < 0.03})")
```

### 5. Write outputs and re-verify

```python
from ase.io import read, write

write("relaxed.xyz", atoms)

# Round-trip check
atoms_check = read("relaxed.xyz")
assert len(atoms_check) == len(atoms), "Atom count changed on write/read"
assert atoms_check.get_chemical_formula() == atoms.get_chemical_formula()
```

---

### Checklist before trusting the energy

| Check | What to look for |
|---|---|
| Atom count & formula | Matches pymatgen source after conversion |
| PBC | `[True True True]` for periodic bulk |
| Cell vectors | Match pymatgen lattice parameters |
| Element coverage | All species in structure are in the MACE-MPA training set |
| Model/dtype pinned | `model="medium-mpa-0"`, `float64` logged |
| Optimizer converged | `max_force < fmax` (here 0.03 eV/Å) |
| Energy/atom range | Sanity-check against MP DFT value; MACE-MPA ≈ PBE, not exact match |
| Trajectory saved | `mace_relax.traj` / `.log` for auditing |

The two most common failure modes are (1) `atoms.pbc` coming out `False` for a bulk crystal — check after `AseAtomsAdaptor.get_atoms` and set `atoms.pbc = True; atoms.cell = ...` if needed — and (2) a mismatched `default_dtype` causing silent loss of precision on geometries with soft modes.
````

Outcome: `loss`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Uses the right libraries and records MACE provenance, but the conversion
  checks are weaker: species order is only printed, cell equality is not
  asserted against the pymatgen lattice, and unit verification is mostly
  implicit.

## pymatgen-phase-diagram-lifepo4: Materials Project Phase Diagram

Skill: `pymatgen`

Criteria:
- [x] Uses pymatgen MPRester or explicitly justified current Materials Project API client
- [x] Retrieves entries for the Li-Fe-P-O chemical system rather than scraping JSON
- [x] Builds a PhaseDiagram and reports eV/atom energy above hull
- [x] Records API key/client, material IDs or composition target, entry set, database/provenance, and compatibility assumptions
- [x] Avoids mixing arbitrary DFT total energies with MP entries without compatibility processing

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
Write Python that gets Li-Fe-P-O entries from Materials Project, builds a phase diagram, and reports the energy above hull for LiFePO4. Include the checks I should record for reproducibility.

## Evaluation Criteria
- Uses pymatgen MPRester or explicitly justified current Materials Project API client
- Retrieves entries for the Li-Fe-P-O chemical system rather than scraping JSON
- Builds a PhaseDiagram and reports eV/atom energy above hull
- Records API key/client, material IDs or composition target, entry set, database/provenance, and compatibility assumptions
- Avoids mixing arbitrary DFT total energies with MP entries without compatibility processing

Return a concise but complete answer with code where appropriate.
```

Output:

````text
## Li-Fe-P-O Phase Diagram with Materials Project

### Installation

```bash
pip install mp-api pymatgen
```

### Code

```python
import os
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram

# ── configuration ──────────────────────────────────────────────────────────────
API_KEY = os.environ.get("MP_API_KEY")          # never hardcode
CHEMSYS = ["Li", "Fe", "P", "O"]
TARGET_FORMULA = "LiFePO4"

# ── fetch entries ──────────────────────────────────────────────────────────────
with MPRester(API_KEY) as mpr:
    # compatible_only=True applies MaterialsProject2020Compatibility corrections
    # (energy adjustments + anion corrections) before returning entries.
    entries = mpr.get_entries_in_chemsys(
        elements=CHEMSYS,
        compatible_only=True,
    )

print(f"Entries retrieved: {len(entries)}")

# ── build phase diagram ────────────────────────────────────────────────────────
pd = PhaseDiagram(entries)

# ── report energy above hull for every LiFePO4 entry ──────────────────────────
target_entries = [
    e for e in entries
    if e.composition.reduced_formula == TARGET_FORMULA
]

if not target_entries:
    raise ValueError(f"No {TARGET_FORMULA} entries found in retrieved set.")

print(f"\n{'Entry ID':<20} {'Formula':<20} {'e_above_hull (eV/atom)'}")
print("-" * 60)
for entry in sorted(target_entries, key=lambda e: pd.get_e_above_hull(e)):
    e_hull = pd.get_e_above_hull(entry)
    print(f"{entry.entry_id:<20} {entry.composition.formula:<20} {e_hull:.4f}")
```

---

### Reproducibility checks to record

| Item | What to record | Why |
|---|---|---|
| **API client & version** | `mp-api.__version__`, `pymatgen.__version__` | Compatibility corrections change between releases |
| **API key tier** | Whether you used a personal key (not the key itself) | MP serves different data to different access tiers |
| **Query date** | ISO 8601 timestamp | MP database is live; entries are updated/added |
| **Entry IDs** | Full list of `entry.entry_id` in the retrieved set | Lets you reconstruct the exact entry set later |
| **Entry count** | `len(entries)` per chemsys | Quick sanity check that the query was complete |
| **Compatibility scheme** | `compatible_only=True` → `MaterialsProject2020Compatibility` | Uses oxide/sulfide anion corrections and Hubbard U corrections for transition metals including Fe; mixing entries from other DFT codes or settings without running them through the same pipeline will corrupt hull energies |
| **LiFePO4 entry ID** | The specific `mp-XXXXX` you are reporting | Multiple polymorphs or calculation types can exist |
| **e_above_hull value** | eV/atom with 4 decimal places | Stable phase = 0.000; MP considers < ~0.025 eV/atom metastable but synthesisable |

---

### Key pitfall to avoid

Do **not** mix externally computed DFT energies with MP entries by constructing a `PDEntry` directly from a raw total energy. Raw VASP energies are not comparable to MP corrected energies. If you must add your own structure, run it through the same compatibility pipeline first:

```python
from pymatgen.entries.compatibility import MaterialsProject2020Compatibility

compat = MaterialsProject2020Compatibility()
my_entry = compat.process_entry(my_computed_entry)  # returns None if rejected
```
````

Outcome: `win`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Clean current-API answer using `mp_api.client.MPRester`, compatible entries,
  `PhaseDiagram`, eV/atom hull energies, entry IDs, version/date provenance,
  and an explicit warning against mixing raw DFT energies.

### Variant: kdense

Status: `ok`

Context status: `provided`

Context skills: `pymatgen`

Prompt:

````text
You are answering a scientific Python coding prompt. Use only the context provided here plus your general knowledge.

## Variant
kdense

## Context
---
name: pymatgen
description: Materials science toolkit. Crystal structures (CIF, POSCAR), phase diagrams, band structure, DOS, Materials Project integration, format conversion, for computational materials science.
license: MIT license
metadata:
    skill-author: K-Dense Inc.
---

# Pymatgen - Python Materials Genomics

## Overview

Pymatgen is a comprehensive Python library for materials analysis that powers the Materials Project. Create, analyze, and manipulate crystal structures and molecules, compute phase diagrams and thermodynamic properties, analyze electronic structure (band structures, DOS), generate surfaces and interfaces, and access Materials Project's database of computed materials. Supports 100+ file formats from various computational codes.

## When to Use This Skill

This skill should be used when:
- Working with crystal structures or molecular systems in materials science
- Converting between structure file formats (CIF, POSCAR, XYZ, etc.)
- Analyzing symmetry, space groups, or coordination environments
- Computing phase diagrams or assessing thermodynamic stability
- Analyzing electronic structure data (band gaps, DOS, band structures)
- Generating surfaces, slabs, or studying interfaces
- Accessing the Materials Project database programmatically
- Setting up high-throughput computational workflows
- Analyzing diffusion, magnetism, or mechanical properties
- Working with VASP, Gaussian, Quantum ESPRESSO, or other computational codes

## Quick Start Guide

### Installation

```bash
# Core pymatgen
uv pip install pymatgen

# With Materials Project API access
uv pip install pymatgen mp-api

# Optional dependencies for extended functionality
uv pip install pymatgen[analysis]  # Additional analysis tools
uv pip install pymatgen[vis]       # Visualization tools
```

### Basic Structure Operations

```python
from pymatgen.core import Structure, Lattice

# Read structure from file (automatic format detection)
struct = Structure.from_file("POSCAR")

# Create structure from scratch
lattice = Lattice.cubic(3.84)
struct = Structure(lattice, ["Si", "Si"], [[0,0,0], [0.25,0.25,0.25]])

# Write to different format
struct.to(filename="structure.cif")

# Basic properties
print(f"Formula: {struct.composition.reduced_formula}")
print(f"Space group: {struct.get_space_group_info()}")
print(f"Density: {struct.density:.2f} g/cm³")
```

### Materials Project Integration

```bash
# Set up API key
export MP_API_KEY="your_api_key_here"
```

```python
from mp_api.client import MPRester

with MPRester() as mpr:
    # Get structure by material ID
    struct = mpr.get_structure_by_material_id("mp-149")

    # Search for materials
    materials = mpr.materials.summary.search(
        formula="Fe2O3",
        energy_above_hull=(0, 0.05)
    )
```

## Core Capabilities

### 1. Structure Creation and Manipulation

Create structures using various methods and perform transformations.

**From files:**
```python
# Automatic format detection
struct = Structure.from_file("structure.cif")
struct = Structure.from_file("POSCAR")
mol = Molecule.from_file("molecule.xyz")
```

**From scratch:**
```python
from pymatgen.core import Structure, Lattice

# Using lattice parameters
lattice = Lattice.from_parameters(a=3.84, b=3.84, c=3.84,
                                  alpha=120, beta=90, gamma=60)
coords = [[0, 0, 0], [0.75, 0.5, 0.75]]
struct = Structure(lattice, ["Si", "Si"], coords)

# From space group
struct = Structure.from_spacegroup(
    "Fm-3m",
    Lattice.cubic(3.5),
    ["Si"],
    [[0, 0, 0]]
)
```

**Transformations:**
```python
from pymatgen.transformations.standard_transformations import (
    SupercellTransformation,
    SubstitutionTransformation,
    PrimitiveCellTransformation
)

# Create supercell
trans = SupercellTransformation([[2,0,0],[0,2,0],[0,0,2]])
supercell = trans.apply_transformation(struct)

# Substitute elements
trans = SubstitutionTransformation({"Fe": "Mn"})
new_struct = trans.apply_transformation(struct)

# Get primitive cell
trans = PrimitiveCellTransformation()
primitive = trans.apply_transformation(struct)
```

**Reference:** See `references/core_classes.md` for comprehensive documentation of Structure, Lattice, Molecule, and related classes.

### 2. File Format Conversion

Convert between 100+ file formats with automatic format detection.

**Using convenience methods:**
```python
# Read any format
struct = Structure.from_file("input_file")

# Write to any format
struct.to(filename="output.cif")
struct.to(filename="POSCAR")
struct.to(filename="output.xyz")
```

**Using the conversion script:**
```bash
# Single file conversion
python scripts/structure_converter.py POSCAR structure.cif

# Batch conversion
python scripts/structure_converter.py *.cif --output-dir ./poscar_files --format poscar
```

**Reference:** See `references/io_formats.md` for detailed documentation of all supported formats and code integrations.

### 3. Structure Analysis and Symmetry

Analyze structures for symmetry, coordination, and other properties.

**Symmetry analysis:**
```python
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

sga = SpacegroupAnalyzer(struct)

# Get space group information
print(f"Space group: {sga.get_space_group_symbol()}")
print(f"Number: {sga.get_space_group_number()}")
print(f"Crystal system: {sga.get_crystal_system()}")

# Get conventional/primitive cells
conventional = sga.get_conventional_standard_structure()
primitive = sga.get_primitive_standard_structure()
```

**Coordination environment:**
```python
from pymatgen.analysis.local_env import CrystalNN

cnn = CrystalNN()
neighbors = cnn.get_nn_info(struct, n=0)  # Neighbors of site 0

print(f"Coordination number: {len(neighbors)}")
for neighbor in neighbors:
    site = struct[neighbor['site_index']]
    print(f"  {site.species_string} at {neighbor['weight']:.3f} Å")
```

**Using the analysis script:**
```bash
# Comprehensive analysis
python scripts/structure_analyzer.py POSCAR --symmetry --neighbors

# Export results
python scripts/structure_analyzer.py structure.cif --symmetry --export json
```

**Reference:** See `references/analysis_modules.md` for detailed documentation of all analysis capabilities.

### 4. Phase Diagrams and Thermodynamics

Construct phase diagrams and analyze thermodynamic stability.

**Phase diagram construction:**
```python
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter

# Get entries from Materials Project
with MPRester() as mpr:
    entries = mpr.get_entries_in_chemsys("Li-Fe-O")

# Build phase diagram
pd = PhaseDiagram(entries)

# Check stability
from pymatgen.core import Composition
comp = Composition("LiFeO2")

# Find entry for composition
for entry in entries:
    if entry.composition.reduced_formula == comp.reduced_formula:
        e_above_hull = pd.get_e_above_hull(entry)
        print(f"Energy above hull: {e_above_hull:.4f} eV/atom")

        if e_above_hull > 0.001:
            # Get decomposition
            decomp = pd.get_decomposition(comp)
            print("Decomposes to:", decomp)

# Plot
plotter = PDPlotter(pd)
plotter.show()
```

**Using the phase diagram script:**
```bash
# Generate phase diagram
python scripts/phase_diagram_generator.py Li-Fe-O --output li_fe_o.png

# Analyze specific composition
python scripts/phase_diagram_generator.py Li-Fe-O --analyze "LiFeO2" --show
```

**Reference:** See `references/analysis_modules.md` (Phase Diagrams section) and `references/transformations_workflows.md` (Workflow 2) for detailed examples.

### 5. Electronic Structure Analysis

Analyze band structures, density of states, and electronic properties.

**Band structure:**
```python
from pymatgen.io.vasp import Vasprun
from pymatgen.electronic_structure.plotter import BSPlotter

# Read from VASP calculation
vasprun = Vasprun("vasprun.xml")
bs = vasprun.get_band_structure()

# Analyze
band_gap = bs.get_band_gap()
print(f"Band gap: {band_gap['energy']:.3f} eV")
print(f"Direct: {band_gap['direct']}")
print(f"Is metal: {bs.is_metal()}")

# Plot
plotter = BSPlotter(bs)
plotter.save_plot("band_structure.png")
```

**Density of states:**
```python
from pymatgen.electronic_structure.plotter import DosPlotter

dos = vasprun.complete_dos

# Get element-projected DOS
element_dos = dos.get_element_dos()
for element, element_dos_obj in element_dos.items():
    print(f"{element}: {element_dos_obj.get_gap():.3f} eV")

# Plot
plotter = DosPlotter()
plotter.add_dos("Total DOS", dos)
plotter.show()
```

**Reference:** See `references/analysis_modules.md` (Electronic Structure section) and `references/io_formats.md` (VASP section).

### 6. Surface and Interface Analysis

Generate slabs, analyze surfaces, and study interfaces.

**Slab generation:**
```python
from pymatgen.core.surface import SlabGenerator

# Generate slabs for specific Miller index
slabgen = SlabGenerator(
    struct,
    miller_index=(1, 1, 1),
    min_slab_size=10.0,      # Å
    min_vacuum_size=10.0,    # Å
    center_slab=True
)

slabs = slabgen.get_slabs()

# Write slabs
for i, slab in enumerate(slabs):
    slab.to(filename=f"slab_{i}.cif")
```

**Wulff shape construction:**
```python
from pymatgen.analysis.wulff import WulffShape

# Define surface energies
surface_energies = {
    (1, 0, 0): 1.0,
    (1, 1, 0): 1.1,
    (1, 1, 1): 0.9,
}

wulff = WulffShape(struct.lattice, surface_energies)
print(f"Surface area: {wulff.surface_area:.2f} Ų")
print(f"Volume: {wulff.volume:.2f} ų")

wulff.show()
```

**Adsorption site finding:**
```python
from pymatgen.analysis.adsorption import AdsorbateSiteFinder
from pymatgen.core import Molecule

asf = AdsorbateSiteFinder(slab)

# Find sites
ads_sites = asf.find_adsorption_sites()
print(f"On-top sites: {len(ads_sites['ontop'])}")
print(f"Bridge sites: {len(ads_sites['bridge'])}")
print(f"Hollow sites: {len(ads_sites['hollow'])}")

# Add adsorbate
adsorbate = Molecule("O", [[0, 0, 0]])
ads_struct = asf.add_adsorbate(adsorbate, ads_sites["ontop"][0])
```

**Reference:** See `references/analysis_modules.md` (Surface and Interface section) and `references/transformations_workflows.md` (Workflows 3 and 9).

### 7. Materials Project Database Access

Programmatically access the Materials Project database.

**Setup:**
1. Get API key from https://next-gen.materialsproject.org/
2. Set environment variable: `export MP_API_KEY="your_key_here"`

**Search and retrieve:**
```python
from mp_api.client import MPRester

with MPRester() as mpr:
    # Search by formula
    materials = mpr.materials.summary.search(formula="Fe2O3")

    # Search by chemical system
    materials = mpr.materials.summary.search(chemsys="Li-Fe-O")

    # Filter by properties
    materials = mpr.materials.summary.search(
        chemsys="Li-Fe-O",
        energy_above_hull=(0, 0.05),  # Stable/metastable
        band_gap=(1.0, 3.0)            # Semiconducting
    )

    # Get structure
    struct = mpr.get_structure_by_material_id("mp-149")

    # Get band structure
    bs = mpr.get_bandstructure_by_material_id("mp-149")

    # Get entries for phase diagram
    entries = mpr.get_entries_in_chemsys("Li-Fe-O")
```

**Reference:** See `references/materials_project_api.md` for comprehensive API documentation and examples.

### 8. Computational Workflow Setup

Set up calculations for various electronic structure codes.

**VASP input generation:**
```python
from pymatgen.io.vasp.sets import MPRelaxSet, MPStaticSet, MPNonSCFSet

# Relaxation
relax = MPRelaxSet(struct)
relax.write_input("./relax_calc")

# Static calculation
static = MPStaticSet(struct)
static.write_input("./static_calc")

# Band structure (non-self-consistent)
nscf = MPNonSCFSet(struct, mode="line")
nscf.write_input("./bandstructure_calc")

# Custom parameters
custom = MPRelaxSet(struct, user_incar_settings={"ENCUT": 600})
custom.write_input("./custom_calc")
```

**Other codes:**
```python
# Gaussian
from pymatgen.io.gaussian import GaussianInput

gin = GaussianInput(
    mol,
    functional="B3LYP",
    basis_set="6-31G(d)",
    route_parameters={"Opt": None}
)
gin.write_file("input.gjf")

# Quantum ESPRESSO
from pymatgen.io.pwscf import PWInput

pwin = PWInput(struct, control={"calculation": "scf"})
pwin.write_file("pw.in")
```

**Reference:** See `references/io_formats.md` (Electronic Structure Code I/O section) and `references/transformations_workflows.md` for workflow examples.

### 9. Advanced Analysis

**Diffraction patterns:**
```python
from pymatgen.analysis.diffraction.xrd import XRDCalculator

xrd = XRDCalculator()
pattern = xrd.get_pattern(struct)

# Get peaks
for peak in pattern.hkls:
    print(f"2θ = {peak['2theta']:.2f}°, hkl = {peak['hkl']}")

pattern.plot()
```

**Elastic properties:**
```python
from pymatgen.analysis.elasticity import ElasticTensor

# From elastic tensor matrix
elastic_tensor = ElasticTensor.from_voigt(matrix)

print(f"Bulk modulus: {elastic_tensor.k_voigt:.1f} GPa")
print(f"Shear modulus: {elastic_tensor.g_voigt:.1f} GPa")
print(f"Young's modulus: {elastic_tensor.y_mod:.1f} GPa")
```

**Magnetic ordering:**
```python
from pymatgen.transformations.advanced_transformations import MagOrderingTransformation

# Enumerate magnetic orderings
trans = MagOrderingTransformation({"Fe": 5.0})
mag_structs = trans.apply_transformation(struct, return_ranked_list=True)

# Get lowest energy magnetic structure
lowest_energy_struct = mag_structs[0]['structure']
```

**Reference:** See `references/analysis_modules.md` for comprehensive analysis module documentation.

## Bundled Resources

### Scripts (`scripts/`)

Executable Python scripts for common tasks:

- **`structure_converter.py`**: Convert between structure file formats
  - Supports batch conversion and automatic format detection
  - Usage: `python scripts/structure_converter.py POSCAR structure.cif`

- **`structure_analyzer.py`**: Comprehensive structure analysis
  - Symmetry, coordination, lattice parameters, distance matrix
  - Usage: `python scripts/structure_analyzer.py structure.cif --symmetry --neighbors`

- **`phase_diagram_generator.py`**: Generate phase diagrams from Materials Project
  - Stability analysis and thermodynamic properties
  - Usage: `python scripts/phase_diagram_generator.py Li-Fe-O --analyze "LiFeO2"`

All scripts include detailed help: `python scripts/script_name.py --help`

### References (`references/`)

Comprehensive documentation loaded into context as needed:

- **`core_classes.md`**: Element, Structure, Lattice, Molecule, Composition classes
- **`io_formats.md`**: File format support and code integration (VASP, Gaussian, etc.)
- **`analysis_modules.md`**: Phase diagrams, surfaces, electronic structure, symmetry
- **`materials_project_api.md`**: Complete Materials Project API guide
- **`transformations_workflows.md`**: Transformations framework and common workflows

Load references when detailed information is needed about specific modules or workflows.

## Common Workflows

### High-Throughput Structure Generation

```python
from pymatgen.transformations.standard_transformations import SubstitutionTransformation
from pymatgen.io.vasp.sets import MPRelaxSet

# Generate doped structures
base_struct = Structure.from_file("POSCAR")
dopants = ["Mn", "Co", "Ni", "Cu"]

for dopant in dopants:
    trans = SubstitutionTransformation({"Fe": dopant})
    doped_struct = trans.apply_transformation(base_struct)

    # Generate VASP inputs
    vasp_input = MPRelaxSet(doped_struct)
    vasp_input.write_input(f"./calcs/Fe_{dopant}")
```

### Band Structure Calculation Workflow

```python
# 1. Relaxation
relax = MPRelaxSet(struct)
relax.write_input("./1_relax")

# 2. Static (after relaxation)
relaxed = Structure.from_file("1_relax/CONTCAR")
static = MPStaticSet(relaxed)
static.write_input("./2_static")

# 3. Band structure (non-self-consistent)
nscf = MPNonSCFSet(relaxed, mode="line")
nscf.write_input("./3_bandstructure")

# 4. Analysis
from pymatgen.io.vasp import Vasprun
vasprun = Vasprun("3_bandstructure/vasprun.xml")
bs = vasprun.get_band_structure()
bs.get_band_gap()
```

### Surface Energy Calculation

```python
# 1. Get bulk energy
bulk_vasprun = Vasprun("bulk/vasprun.xml")
bulk_E_per_atom = bulk_vasprun.final_energy / len(bulk)

# 2. Generate and calculate slabs
slabgen = SlabGenerator(bulk, (1,1,1), 10, 15)
slab = slabgen.get_slabs()[0]

MPRelaxSet(slab).write_input("./slab_calc")

# 3. Calculate surface energy (after calculation)
slab_vasprun = Vasprun("slab_calc/vasprun.xml")
E_surf = (slab_vasprun.final_energy - len(slab) * bulk_E_per_atom) / (2 * slab.surface_area)
E_surf *= 16.021766  # Convert eV/Ų to J/m²
```

**More workflows:** See `references/transformations_workflows.md` for 10 detailed workflow examples.

## Best Practices

### Structure Handling

1. **Use automatic format detection**: `Structure.from_file()` handles most formats
2. **Prefer immutable structures**: Use `IStructure` when structure shouldn't change
3. **Check symmetry**: Use `SpacegroupAnalyzer` to reduce to primitive cell
4. **Validate structures**: Check for overlapping atoms or unreasonable bond lengths

### File I/O

1. **Use convenience methods**: `from_file()` and `to()` are preferred
2. **Specify formats explicitly**: When automatic detection fails
3. **Handle exceptions**: Wrap file I/O in try-except blocks
4. **Use serialization**: `as_dict()`/`from_dict()` for version-safe storage

### Materials Project API

1. **Use context manager**: Always use `with MPRester() as mpr:`
2. **Batch queries**: Request multiple items at once
3. **Cache results**: Save frequently used data locally
4. **Filter effectively**: Use property filters to reduce data transfer

### Computational Workflows

1. **Use input sets**: Prefer `MPRelaxSet`, `MPStaticSet` over manual INCAR
2. **Check convergence**: Always verify calculations converged
3. **Track transformations**: Use `TransformedStructure` for provenance
4. **Organize calculations**: Use clear directory structures

### Performance

1. **Reduce symmetry**: Use primitive cells when possible
2. **Limit neighbor searches**: Specify reasonable cutoff radii
3. **Use appropriate methods**: Different analysis tools have different speed/accuracy tradeoffs
4. **Parallelize when possible**: Many operations can be parallelized

## Units and Conventions

Pymatgen uses atomic units throughout:
- **Lengths**: Angstroms (Å)
- **Energies**: Electronvolts (eV)
- **Angles**: Degrees (°)
- **Magnetic moments**: Bohr magnetons (μB)
- **Time**: Femtoseconds (fs)

Convert units using `pymatgen.core.units` when needed.

## Integration with Other Tools

Pymatgen integrates seamlessly with:
- **ASE** (Atomic Simulation Environment)
- **Phonopy** (phonon calculations)
- **BoltzTraP** (transport properties)
- **Atomate/Fireworks** (workflow management)
- **AiiDA** (provenance tracking)
- **Zeo++** (pore analysis)
- **OpenBabel** (molecule conversion)

## Troubleshooting

**Import errors**: Install missing dependencies
```bash
uv pip install pymatgen[analysis,vis]
```

**API key not found**: Set MP_API_KEY environment variable
```bash
export MP_API_KEY="your_key_here"
```

**Structure read failures**: Check file format and syntax
```python
# Try explicit format specification
struct = Structure.from_file("file.txt", fmt="cif")
```

**Symmetry analysis fails**: Structure may have numerical precision issues
```python
# Increase tolerance
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
sga = SpacegroupAnalyzer(struct, symprec=0.1)
```

## Additional Resources

- **Documentation**: https://pymatgen.org/
- **Materials Project**: https://materialsproject.org/
- **GitHub**: https://github.com/materialsproject/pymatgen
- **Forum**: https://matsci.org/
- **Example notebooks**: https://matgenb.materialsvirtuallab.org/

## Version Notes

This skill is designed for pymatgen 2024.x and later. For the Materials Project API, use the `mp-api` package (separate from legacy `pymatgen.ext.matproj`).

Requirements:
- Python 3.10 or higher
- pymatgen >= 2023.x
- mp-api (for Materials Project access)



## User Prompt
Write Python that gets Li-Fe-P-O entries from Materials Project, builds a phase diagram, and reports the energy above hull for LiFePO4. Include the checks I should record for reproducibility.

## Evaluation Criteria
- Uses pymatgen MPRester or explicitly justified current Materials Project API client
- Retrieves entries for the Li-Fe-P-O chemical system rather than scraping JSON
- Builds a PhaseDiagram and reports eV/atom energy above hull
- Records API key/client, material IDs or composition target, entry set, database/provenance, and compatibility assumptions
- Avoids mixing arbitrary DFT total energies with MP entries without compatibility processing

Return a concise but complete answer with code where appropriate.
````

Output:

````text
```python
"""
Phase diagram for Li-Fe-P-O and energy above hull for LiFePO4.

Reproducibility checklist (record these before each run):
  - pymatgen version   : pip show pymatgen | grep Version
  - mp-api version     : pip show mp-api   | grep Version
  - MP API key hash    : hashlib.sha256(os.environ["MP_API_KEY"].encode()).hexdigest()[:12]
  - Run date           : datetime.date.today().isoformat()
  - Compatibility scheme confirmed in output (see assert below)
"""

import datetime
import hashlib
import os

from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition

# ── Reproducibility header ────────────────────────────────────────────────────
import pymatgen
import mp_api

key_fingerprint = hashlib.sha256(
    os.environ["MP_API_KEY"].encode()
).hexdigest()[:12]

print("=== Reproducibility Record ===")
print(f"Date        : {datetime.date.today().isoformat()}")
print(f"pymatgen    : {pymatgen.__version__}")
print(f"mp-api      : {mp_api.__version__}")
print(f"API key     : …{key_fingerprint}  (first 12 hex of SHA-256)")
print(f"Chem system : Li-Fe-P-O")
print()

# ── Fetch entries ─────────────────────────────────────────────────────────────
TARGET = Composition("LiFePO4")
CHEMSYS = "Li-Fe-P-O"

with MPRester() as mpr:
    entries = mpr.get_entries_in_chemsys(
        CHEMSYS,
        additional_criteria={"thermo_types": ["GGA_GGA+U"]},
    )

print(f"Entries retrieved : {len(entries)}")

# Confirm every entry carries a compatibility correction (no bare DFT energies).
# MP applies MaterialsProject2020Compatibility automatically via get_entries_in_chemsys;
# this assertion guards against a silent API change.
for e in entries:
    assert e.correction != 0 or e.composition.is_element, (
        f"Entry {e.entry_id} for {e.composition.reduced_formula} has no "
        "energy correction — compatibility scheme may not have been applied."
    )

# Record the material IDs actually used.
entry_ids = sorted(e.entry_id for e in entries)
print(f"Entry ID range    : {entry_ids[0]} … {entry_ids[-1]}")
print(f"Total unique IDs  : {len(entry_ids)}")
print()

# ── Build phase diagram ───────────────────────────────────────────────────────
pd = PhaseDiagram(entries)

# ── Find LiFePO4 entry and report hull energy ─────────────────────────────────
lifepo4_entries = [
    e for e in entries
    if e.composition.reduced_formula == TARGET.reduced_formula
]

if not lifepo4_entries:
    raise ValueError("No LiFePO4 entry found in retrieved set.")

print(f"{'Material ID':<16} {'Formula':<20} {'E above hull (eV/atom)'}")
print("-" * 56)
for e in sorted(lifepo4_entries, key=lambda x: x.entry_id):
    e_hull = pd.get_e_above_hull(e)
    stable = "← stable" if e_hull < 1e-3 else ""
    print(f"{e.entry_id:<16} {e.composition.reduced_formula:<20} {e_hull:+.6f}  {stable}")

# ── Decomposition for the ground-state entry ──────────────────────────────────
gs = min(lifepo4_entries, key=lambda e: pd.get_e_above_hull(e))
decomp, e_hull_gs = pd.get_decomp_and_e_above_hull(gs)

print()
print(f"Ground-state entry : {gs.entry_id}")
if e_hull_gs < 1e-3:
    print("LiFePO4 is on the convex hull (thermodynamically stable).")
else:
    print(f"LiFePO4 decomposes to:")
    for phase, fraction in decomp.items():
        print(f"  {phase.composition.reduced_formula:20s}  fraction = {fraction:.4f}")
```

---

### Reproducibility checks to record

| What | How to capture |
|---|---|
| **Library versions** | `pip show pymatgen mp-api` — commit to a `requirements.txt` or lock file |
| **API key identity** | The SHA-256 fingerprint printed above (never log the key itself) |
| **Database snapshot** | MP data is versioned; note the run date — results can shift as MP re-relaxes structures |
| **Chemical system** | `"Li-Fe-P-O"` — order-independent, but record it explicitly |
| **Entry IDs** | Print and save `entry_ids`; re-running with the same IDs lets you reproduce the diagram exactly even if new entries are later added |
| **Compatibility scheme** | `get_entries_in_chemsys` applies `MaterialsProject2020Compatibility` (GGA/GGA+U mixing corrections and anion corrections). The `assert` in the code confirms this hasn't silently changed |
| **thermo_types filter** | `["GGA_GGA+U"]` — excludes r2SCAN entries so you don't mix functionals without an explicit mixing scheme |

The key correctness constraint is the `assert` on `e.correction`: if you mix raw DFT total energies (zero correction) with corrected MP entries into the same `PhaseDiagram`, hull positions will be wrong. The assertion catches that before any results are reported.
````

Outcome: `loss`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Mostly addresses the prompt, but the blanket `e.correction != 0` assertion is
  brittle because some compatible non-element entries can legitimately have no
  correction. That can reject valid MP entries before the phase diagram is
  built.

### Variant: package-skill

Status: `ok`

Context status: `provided`

Context skills: `pymatgen`

Prompt:

````text
You are answering a scientific Python coding prompt. Use only the context provided here plus your general knowledge.

## Variant
package-skill

## Context
## Package Skill: pymatgen

---
name: pymatgen
description: |
  Use when the user is working with materials structures, compositions,
  crystallography, Materials Project data, phase diagrams, Pourbaix diagrams,
  VASP input/output, computed entries, symmetry analysis, oxidation states,
  diffusion analysis, electronic structures, or conversions between materials
  data formats. Prefer pymatgen over generic NumPy/Pandas or ASE when the task
  is materials analysis rather than running a calculator.
version: 0.1.0
compatible_versions: ">=2024.1,<2027"
related_skills: [ase, mace]
canonical_docs: https://pymatgen.org/
canonical_tutorials: https://pymatgen.org/usage.html
---

# pymatgen

## What this library is for

pymatgen is the core Python library behind many Materials Project workflows. It
provides robust representations of `Composition`, `Molecule`, `Lattice`, and
`Structure`, plus materials-specific analysis tools for crystallography,
thermodynamics, phase stability, electronic structure, VASP I/O, and Materials
Project API access.

## When to use this vs. alternatives

- Use pymatgen for materials analysis: compositions, structures, symmetry,
  phase diagrams, Materials Project queries, VASP parsing, Pourbaix diagrams,
  reaction balancing, and computed-entry workflows.
- Use ASE when the immediate task is calculator orchestration, geometry
  optimization, trajectories, MD, NEB, or a workflow built around an ASE
  `Atoms` object.
- Use RDKit for cheminformatics, molecular graphs, SMILES/reactions, and
  conformers; use pymatgen's `Molecule` only when the downstream workflow is
  materials/solid-state analysis or file conversion.
- Use `pymatgen.ext.matproj.MPRester` for Materials Project access that should
  return pymatgen objects and fit pymatgen analysis workflows. Use the
  Materials Project API directly or `mp-api` when the user explicitly needs
  lower-level API-client behavior outside pymatgen's `MPRester` coverage.
- Do not hand-roll CIF/POSCAR parsing, formula parsing, or phase-diagram convex
  hulls. pymatgen already encodes the domain conventions and compatibility
  corrections that generic SciPy/Pandas code will miss.

## Canonical workflow

Start from a `Structure` or `Composition`, use pymatgen's domain objects for
analysis, and only convert to ASE when a calculator workflow is needed.

```python
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition, Structure
from pymatgen.ext.matproj import MPRester
from pymatgen.io.ase import AseAtomsAdaptor

structure = Structure.from_file("POSCAR")  # also reads CIF and many other formats
print(structure.composition.reduced_formula)
print(structure.lattice.abc, structure.lattice.angles)

composition = Composition("LiFePO4")
print(composition.reduced_formula, composition.get_atomic_fraction("Li"))

with MPRester() as mpr:  # uses PMG_MAPI_KEY if configured
    entries = mpr.get_entries_in_chemsys(["Li", "Fe", "P", "O"])
    mp_structure = mpr.get_structure_by_material_id("mp-19017")

phase_diagram = PhaseDiagram(entries)
entry = min(entries, key=lambda e: abs(e.composition.get_atomic_fraction("Fe") - 0.25))
print("e_above_hull_eV_per_atom", phase_diagram.get_e_above_hull(entry))

atoms = AseAtomsAdaptor.get_atoms(mp_structure)
assert len(atoms) == len(mp_structure)
```

For deeper examples, read:

- Usage guide: https://pymatgen.org/usage.html
- API docs: https://pymatgen.org/pymatgen.html
- Materials Project API docs: https://api.materialsproject.org/docs
- matgenb notebooks: https://github.com/materialsvirtuallab/matgenb

## Key conventions and gotchas

- `Structure` coordinates are usually fractional relative to a `Lattice`;
  `Molecule` coordinates are Cartesian and non-periodic. Check whether code is
  using `frac_coords`, `cart_coords`, or `coords`.
- `Composition("Fe2O3")` is not the same as an oxidation-state-resolved
  composition. Use species with oxidation states, `add_oxidation_state_by_*`,
  or oxidation-state guessers when valence matters.
- `Structure.from_file()` is the normal entry point for CIF/POSCAR-like files,
  but CIFs can contain disorder, partial occupancies, symmetry expansion, or
  duplicate/near-duplicate sites. Inspect site count, formula, occupancies, and
  warnings before using imported structures.
- Recent pymatgen `MPRester` mirrors Materials Project REST API field names more
  directly and is not the legacy-only client. If an MP query fails after copying
  older examples, check the current API docs and field names instead of assuming
  `mp-api` aliases apply.
- Materials Project entries used in phase diagrams should be compatible entries
  from the same API/database context. Do not mix arbitrary DFT energies with MP
  entries without applying the relevant compatibility processing and documenting
  the correction scheme.
- Converting between pymatgen and ASE can lose or reinterpret metadata such as
  site properties, selective dynamics, oxidation states, magnetic moments,
  charges, and molecule bonding. Validate after conversion.

## Anti-patterns

- Do not parse chemical formulas with regexes for materials logic. Use
  `Composition` so reduced formula, element amounts, atomic fractions, and
  anonymized formulas are handled consistently.
- Do not manually implement symmetry expansion or neighbor finding unless the
  user is developing a new method. Use pymatgen's symmetry and local-environment
  tools, then inspect edge cases such as self-neighbor periodic images.
- Do not use `Structure.from_spacegroup()` as a blind replacement for a vetted
  crystallographic file. Wyckoff positions, tolerances, and origin choices can
  change atom counts; compare formula, site count, and symmetry against a
  trusted reference.
- Do not report `e_above_hull` from a hand-built hull without specifying the
  entry set, database version, compatibility scheme, and units.
- Do not treat a Materials Project `Structure` as the exact experimental
  structure unless the provenance supports that claim.

## Diagnostic checks

Before trusting outputs, the agent should:

- Print formula, reduced formula, site count, lattice parameters, volume, and
  whether sites have partial occupancies or oxidation states.
- For imported CIF/POSCAR files, compare the expected and parsed composition,
  check warnings, and inspect suspicious short distances or duplicate sites.
- For MP queries, record the API package/client, database version if available,
  material IDs, fields requested, and whether deprecated or task-level data were
  used.
- For phase diagrams, record the chemical system, number of entries,
  compatibility processing, and units (`eV/atom` for hull energies).
- After ASE conversion, compare atom count, species order, cell, PBC, and any
  needed site properties before attaching a calculator.

## Pointers to deeper material

- Documentation: https://pymatgen.org/
- Usage examples: https://pymatgen.org/usage.html
- GitHub repository: https://github.com/materialsproject/pymatgen
- Materials Project API docs: https://api.materialsproject.org/docs
- matgenb tutorial notebooks: https://github.com/materialsvirtuallab/matgenb
- Paper: Ong et al. (2013), "Python Materials Genomics (pymatgen): A robust,
  open-source python library for materials analysis", Computational Materials
  Science 68, 314-319. https://doi.org/10.1016/j.commatsci.2012.10.028


## User Prompt
Write Python that gets Li-Fe-P-O entries from Materials Project, builds a phase diagram, and reports the energy above hull for LiFePO4. Include the checks I should record for reproducibility.

## Evaluation Criteria
- Uses pymatgen MPRester or explicitly justified current Materials Project API client
- Retrieves entries for the Li-Fe-P-O chemical system rather than scraping JSON
- Builds a PhaseDiagram and reports eV/atom energy above hull
- Records API key/client, material IDs or composition target, entry set, database/provenance, and compatibility assumptions
- Avoids mixing arbitrary DFT total energies with MP entries without compatibility processing

Return a concise but complete answer with code where appropriate.
````

Output:

````text
```python
"""
Reproducibility record (fill in after running):
  - pymatgen version:      pymatgen.__version__
  - mp-api version:        importlib.metadata.version("mp-api")
  - API client:            MPRester from pymatgen.ext.matproj
  - Chemical system:       Li-Fe-P-O
  - Compatibility scheme:  MaterialsProject2020Compatibility (applied automatically by MPRester)
  - MP database snapshot:  mpr.get_database_version() — record output
  - Target material ID:    printed below
  - Entry count:           printed below
  - Hull energy units:     eV/atom
"""

import importlib.metadata

import pymatgen
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition
from pymatgen.ext.matproj import MPRester

TARGET_FORMULA = "LiFePO4"

with MPRester() as mpr:  # reads PMG_MAPI_KEY from environment
    db_version = mpr.get_database_version()
    print(f"pymatgen version : {pymatgen.__version__}")
    print(f"mp-api version   : {importlib.metadata.version('mp-api')}")
    print(f"MP database      : {db_version}")

    # Retrieve all compatible entries in the quaternary chemical system.
    # MPRester applies MaterialsProject2020Compatibility automatically,
    # so energies are on the same footing — do not mix in raw DFT total energies.
    entries = mpr.get_entries_in_chemsys(
        ["Li", "Fe", "P", "O"],
        additional_criteria={"is_stable": False},  # include metastable entries
    )
    print(f"Entries retrieved : {len(entries)}")

    # Locate the LiFePO4 entry (prefer the lowest-energy one if multiple exist).
    target_comp = Composition(TARGET_FORMULA)
    candidates = [
        e for e in entries
        if e.composition.reduced_composition == target_comp.reduced_composition
    ]
    if not candidates:
        raise ValueError(f"No entries found for {TARGET_FORMULA} in retrieved set.")

    target_entry = min(candidates, key=lambda e: e.energy_per_atom)
    print(f"\nTarget entry")
    print(f"  material_id  : {target_entry.entry_id}")
    print(f"  formula      : {target_entry.composition.reduced_formula}")
    print(f"  sites        : {len(target_entry.structure.sites) if hasattr(target_entry, 'structure') else 'N/A'}")
    print(f"  energy/atom  : {target_entry.energy_per_atom:.6f} eV/atom")

# Build the phase diagram outside the context manager (entries are plain objects).
pd = PhaseDiagram(entries)

e_above_hull = pd.get_e_above_hull(target_entry)
print(f"\nPhase diagram")
print(f"  chemical system : Li-Fe-P-O")
print(f"  stable phases   : {len(pd.stable_entries)}")
print(f"  is stable       : {target_entry in pd.stable_entries}")
print(f"\nEnergy above hull for {TARGET_FORMULA}")
print(f"  {e_above_hull:.4f} eV/atom")

# Diagnostic: check the decomposition products if not on the hull.
if e_above_hull > 1e-3:
    decomp, energy = pd.get_decomp_and_e_above_hull(target_entry)
    products = {e.composition.reduced_formula: f"{amt:.3f}" for e, amt in decomp.items()}
    print(f"  decomposition   : {products}")
```

**Key reproducibility checks to record after running:**

| Item | How to get it |
|---|---|
| pymatgen version | `pymatgen.__version__` (printed) |
| mp-api version | `importlib.metadata.version("mp-api")` (printed) |
| MP database snapshot | `mpr.get_database_version()` (printed) |
| Target material ID | `target_entry.entry_id` (printed) |
| Entry count | printed |
| Compatibility scheme | `MaterialsProject2020Compatibility`, applied automatically by `MPRester.get_entries_in_chemsys` — do not mix raw DFT energies with these entries |
| Hull energy units | eV/atom throughout |

**Three things to watch for:**

1. `get_entries_in_chemsys` returns *compatible* entries by default. If you later add your own DFT energies, you must run them through the same `MaterialsProject2020Compatibility` correction scheme before calling `PhaseDiagram`, or the hull will be wrong.
2. Multiple MP entries can match `LiFePO4` (different calculation settings, polymorphs). The code picks the lowest-energy one; inspect `candidates` if you want a specific polymorph.
3. Hull stability (`e_above_hull ≈ 0`) can shift between database versions. Always pin the `db_version` string in your records.
````

Outcome: `tie`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Satisfies the requested workflow and provenance checks. It is acceptable, but
  less clearly current than the baseline because it uses
  `pymatgen.ext.matproj.MPRester` rather than `mp_api.client.MPRester`.

## py4dstem-virtual-image-bragg: 4D-STEM Virtual Imaging And Bragg Detection

Skill: `py4dstem`

Criteria:
- [x] Uses py4DSTEM read/import_file and locates a DataCube
- [x] Prints datacube shape and identifies scan and diffraction axes
- [x] Inspects mean/max diffraction pattern before choosing detector geometry
- [x] Uses py4DSTEM virtual image and Bragg disk APIs rather than arbitrary NumPy sums
- [x] Mentions beam center, calibration, masks, probe/template, thresholds, and version boundaries

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
I have a 4D-STEM HDF5 file and want to make virtual bright-field and annular dark-field images, then detect Bragg disks for later strain mapping. Write a py4DSTEM workflow and list the checks before trusting results.

## Evaluation Criteria
- Uses py4DSTEM read/import_file and locates a DataCube
- Prints datacube shape and identifies scan and diffraction axes
- Inspects mean/max diffraction pattern before choosing detector geometry
- Uses py4DSTEM virtual image and Bragg disk APIs rather than arbitrary NumPy sums
- Mentions beam center, calibration, masks, probe/template, thresholds, and version boundaries

Return a concise but complete answer with code where appropriate.
```

Output:

````text
## py4DSTEM 4D-STEM Workflow: VBF/ADF + Bragg Disk Detection

### 0. Imports and version pin

```python
import py4DSTEM          # tested against ≥0.14.0; API broke at 0.13
import numpy as np
import matplotlib.pyplot as plt

print(py4DSTEM.__version__)   # log this — several APIs changed at 0.13 and 0.14
```

---

### 1. Load and inspect the DataCube

```python
# py4DSTEM native HDF5 → use read(); foreign HDF5/EMD/DM4 → use import_file()
data = py4DSTEM.read("data.h5")

# read() may return a single DataCube or a list of objects
if isinstance(data, py4DSTEM.DataCube):
    dc = data
else:
    # inspect what's in the file, pick the DataCube
    print(data)
    dc = data["datacube_0"]          # adjust key as needed

print("Full shape  :", dc.shape)     # (Rx, Ry, Qx, Qy)
print("Scan shape  :", dc.Rshape)    # (Rx, Ry)  – real-space axes
print("Diff shape  :", dc.Qshape)    # (Qx, Qy)  – reciprocal-space axes
print("dtype       :", dc.data.dtype)
```

**Why this matters:** confirm that the slow (scan) axes come first. A transposed load produces nonsense images silently.

---

### 2. Inspect mean and max diffraction patterns

```python
mean_dp = dc.get_dp_mean()   # averaged over all probe positions
max_dp  = dc.get_dp_max()    # pixel-wise max — shows weak peaks

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].imshow(np.log1p(mean_dp.data), cmap="gray"); axes[0].set_title("log(mean DP)")
axes[1].imshow(np.log1p(max_dp.data),  cmap="gray"); axes[1].set_title("log(max DP)")
plt.tight_layout(); plt.show()
```

Use these to:
- identify the direct beam position (beam center)
- choose inner/outer radii for the ADF detector
- spot saturation, hot pixels, or camera artifacts before any further processing

---

### 3. Find the beam center

```python
# rough centre from mean DP; refine iteratively if needed
from py4DSTEM.process.utils import get_CoM

qx0, qy0 = get_CoM(mean_dp.data)
print(f"Beam center: ({qx0:.1f}, {qy0:.1f}) px")

# store in the calibration object so every subsequent step uses it
dc.calibration.set_origin([qx0, qy0])
```

---

### 4. Virtual bright-field and annular dark-field

Choose radii from the diffraction pattern inspection above.

```python
R_BF      = 20    # px; should sit inside the direct-beam disk
R_ADF_in  = 40    # px; just outside the direct beam + any diffuse BF scatter
R_ADF_out = 120   # px; set by camera edge or diffraction ring of interest

# Virtual bright-field (disk detector)
vbf = dc.get_virtual_image(
    mode     = "disk",
    geometry = (qx0, qy0, R_BF),
    name     = "VBF",
)

# Annular dark-field
adf = dc.get_virtual_image(
    mode     = "annulus",
    geometry = (qx0, qy0, R_ADF_in, R_ADF_out),
    name     = "ADF",
)

fig, axes = plt.subplots(1, 2, figsize=(10, 5))
axes[0].imshow(vbf.data, cmap="gray"); axes[0].set_title("VBF")
axes[1].imshow(adf.data, cmap="gray"); axes[1].set_title("ADF")
plt.tight_layout(); plt.show()
```

---

### 5. Bragg disk detection

```python
# --- 5a. Build a probe template ---
# Option A: from a vacuum scan position (best)
vacuum_dp = dc.data[0, 0]          # or average a known vacuum region
probe = py4DSTEM.process.diskdetection.get_probe_kernel_from_dp(
    vacuum_dp,
    r             = R_BF,
    origin        = (qx0, qy0),
)

# Option B: synthetic Gaussian probe (fallback)
# probe = py4DSTEM.process.diskdetection.get_probe_kernel_synthetic(
#     R_BF, dc.Qshape
# )

# --- 5b. Detect Bragg disks across the full DataCube ---
bragg_peaks = dc.find_Bragg_disks(
    probe                  = probe,
    corrPower              = 1.0,      # 1 = cross-correlation, <1 = power
    sigma                  = 2,        # Gaussian blur before correlation
    edgeBoundary           = 20,       # px; ignore detections near DP edge
    minRelativeIntensity   = 0.005,    # fraction of brightest peak
    minAbsoluteIntensity   = 0,
    minPeakSpacing         = 60,       # px; prevents duplicates
    maxNumPeaks            = 70,
    subpixel               = "multicorr",  # 'none'|'poly'|'multicorr'
    upsample_factor        = 16,       # sub-pixel precision
)

# --- 5c. Quick sanity plot on one scan pixel ---
rx, ry = dc.Rshape[0] // 2, dc.Rshape[1] // 2
peaks_here = bragg_peaks.get_pointlist(rx, ry)
fig, ax = plt.subplots()
ax.imshow(np.log1p(dc.data[rx, ry]), cmap="gray")
ax.scatter(peaks_here.data["qy"], peaks_here.data["qx"],
           s=40, c="red", lw=0, alpha=0.7)
ax.set_title(f"Detected peaks at scan pos ({rx},{ry})")
plt.show()

print("Mean peaks per probe position:",
      np.mean([bragg_peaks.get_pointlist(r, c).length
               for r in range(dc.Rshape[0])
               for c in range(dc.Rshape[1])]))
```

---

### 6. Checks before trusting any result

| # | Check | What to look for |
|---|-------|-----------------|
| 1 | **Shape / axis order** | Scan axes first `(Rx, Ry, Qx, Qy)`; swap if transposed |
| 2 | **Beam center accuracy** | Center of BF disk in mean DP should equal `(qx0, qy0)` to <1 px; re-run CoM on a cropped region around the beam if off |
| 3 | **Saturation / hot pixels** | Max DP should not show clipped values; mask before correlation if present |
| 4 | **Calibration set** | `dc.calibration` holds pixel size (Å⁻¹/px); required for physical strain values — verify against a known standard |
| 5 | **VBF/ADF radius choice** | BF radius < disk radius; ADF inner radius > disk radius; visualise both rings on mean DP |
| 6 | **Probe template quality** | Probe should look like a clean, symmetric disk; asymmetry inflates strain errors |
| 7 | **Correlation power** | `corrPower < 1` suppresses strong direct-beam artefacts; check with and without |
| 8 | **Peak count stability** | Plot peak count per scan position as a 2D map; sudden drops at scan edges or drift regions indicate parameter issues |
| 9 | **Edge boundary** | `edgeBoundary` must be ≥ probe radius to avoid ghost peaks from wrap-around correlation |
| 10 | **py4DSTEM version** | `get_virtual_image`, `find_Bragg_disks`, and calibration APIs all ch
````

Outcome: `tie`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Meets the criteria with py4DSTEM loading, shape/axis inspection, mean/max
  diffraction checks, virtual BF/ADF APIs, beam-center calibration, probe
  construction, threshold tuning, and Bragg overlay diagnostics.

### Variant: package-skill

Status: `ok`

Context status: `provided`

Context skills: `py4dstem`

Prompt:

````text
You are answering a scientific Python coding prompt. Use only the context provided here plus your general knowledge.

## Variant
package-skill

## Context
## Package Skill: py4dstem

---
name: py4dstem
description: |
  Use when the user is working with 4D-STEM, scanning nanobeam diffraction,
  diffraction datacubes, Bragg disk detection, virtual bright/dark field
  imaging, center-of-mass/DPC, strain/orientation mapping, ptychography,
  phase retrieval, or microscope calibration from STEM diffraction data. Prefer
  py4DSTEM over generic NumPy/scikit-image code when diffraction datacube
  conventions, detector axes, scan axes, calibration, and 4D-STEM workflows
  matter.
version: 0.1.0
compatible_versions: ">=0.14,<0.15"
related_skills: [hyperspy]
canonical_docs: https://py4dstem.readthedocs.io/
canonical_tutorials: https://github.com/py4dstem/py4DSTEM_tutorials
---

# py4DSTEM

## What this library is for

py4DSTEM is a toolkit for reading, calibrating, visualizing, and analyzing
4D-STEM diffraction datacubes. It provides domain objects and workflows for
virtual imaging, Bragg disk detection, center-of-mass/DPC analysis, strain and
orientation mapping, phase retrieval, ptychography, and calibration.

## When to use this vs. alternatives

- Use py4DSTEM for 4D-STEM datacubes, diffraction-pattern stacks, scan/detector
  axis handling, virtual images/diffraction, Bragg vectors, COM/DPC, strain,
  orientation mapping, and ptychographic phase retrieval.
- Use HyperSpy when the task is broader multidimensional microscopy/spectroscopy
  signal handling, EELS/EDX workflows, lazy loading, or interactive signal
  decomposition outside py4DSTEM-specific diffraction workflows.
- Use NumPy/scikit-image only for narrow image-processing steps after py4DSTEM
  has handled datacube loading, calibration, slicing, and diffraction semantics.
- Do not treat a 4D-STEM file as an arbitrary 4D array without documenting scan
  axes, detector axes, reciprocal-space calibration, beam center, and masks.

## Canonical workflow

Start by loading a datacube, inspecting dimensions, setting or checking
calibration, building virtual detectors/images, then moving to Bragg/COM/strain
workflows only after the raw data and masks make sense.

```python
import py4DSTEM

py4DSTEM.print_h5_tree("scan_4dstem.h5")
datacube = py4DSTEM.read("scan_4dstem.h5", datapath="root/datacube")
# For non-native microscope formats, use py4DSTEM.import_file(...) instead.

print(datacube.data.shape)  # typically (scan_y, scan_x, q_y, q_x)
datacube.calibration

# Average diffraction pattern and virtual bright-field image.
dp_mean = datacube.get_dp_mean()
bf = datacube.get_virtual_image(
    mode="circle",
    geometry=((0, 0), 20),
    centered=True,
)

# Inspect before quantitative analysis.
py4DSTEM.show(dp_mean)
py4DSTEM.show(bf)

# Bragg disk workflows need a probe/kernel and detection parameters chosen from
# the actual diffraction pattern, not copied blindly from an example.
probe = datacube.get_vacuum_probe()
bragg_peaks = datacube.find_Bragg_disks(template=probe, corrPower=1.0, sigma=2)
```

For deeper examples, read:

- Tutorial notebooks: https://github.com/py4dstem/py4DSTEM_tutorials
- First steps: https://py4dstem.readthedocs.io/en/latest/examples/first_steps.html
- Virtual imaging: https://py4dstem.readthedocs.io/en/latest/examples/virtual_imaging.html
- Bragg disk detection: https://py4dstem.readthedocs.io/en/latest/examples/bragg_disk_detection.html

## Key conventions and gotchas

- py4DSTEM v0.14 is a major workflow/API boundary. Older pre-0.14 examples can
  be structurally misleading; check the docs version before copying code.
- Phase-retrieval APIs were reorganized in v0.14.9 with shortened class names.
  If ptychography examples fail at import time, verify the installed py4DSTEM
  version and current phase-retrieval class names.
- Datacube axes are domain-significant. Confirm scan axes and diffraction axes
  before indexing, reshaping, summing, or exporting arrays.
- Virtual detector geometry is in detector/reciprocal-space pixel coordinates
  unless calibration-specific code says otherwise. Do not use a copied radius or
  center without checking the beam center and diffraction pattern scale.
- Quantitative Bragg/strain/orientation workflows depend on probe/kernel choice,
  thresholds, masks, calibration, elliptical distortion correction, and scan
  distortions. Do not report quantitative strain from raw peaks without these
  checks.
- py4DSTEM data can be large. Prefer the package's readers, tree objects, and
  tutorial patterns over loading entire HDF5 datasets into ad hoc arrays.

## Anti-patterns

- Do not write generic NumPy code that assumes shape order without printing and
  naming `(R_y, R_x, Q_y, Q_x)` or the corresponding py4DSTEM dimensions.
- Do not run Bragg disk detection with tutorial thresholds on a new dataset.
  Inspect the mean/max diffraction pattern, mask saturated/hot pixels, choose a
  probe/template, and validate peaks visually.
- Do not average or crop diffraction patterns before recording calibration and
  beam-center assumptions.
- Do not mix py4DSTEM v0.13 notebooks with v0.14+ code unless deliberately
  porting the workflow.
- Do not use phase-retrieval examples without checking whether the class names
  match the installed version.

## Diagnostic checks

Before trusting outputs, the agent should:

- Log py4DSTEM version, file path, tree keys, datacube shape, dtype, and whether
  data are loaded eagerly or lazily.
- Show the mean or max diffraction pattern and at least one scan-position
  diffraction pattern before quantitative processing.
- Verify scan/detector axis order, beam center, calibration units, detector
  mask, and virtual detector geometry.
- For Bragg workflows, overlay detected peaks on representative diffraction
  patterns and record probe/template, thresholds, and masks.
- For strain/orientation outputs, record calibration, reference lattice/peaks,
  distortion corrections, and uncertainty or residual checks.
- Save intermediate py4DSTEM objects or output files with enough metadata to
  reproduce detector geometry and calibration choices.

## Pointers to deeper material

- Documentation: https://py4dstem.readthedocs.io/
- Tutorial repository: https://github.com/py4dstem/py4DSTEM_tutorials
- Source repository: https://github.com/py4dstem/py4DSTEM
- Paper: Savitzky et al. (2021), "py4DSTEM: A Software Package for Four-
  Dimensional Scanning Transmission Electron Microscopy Data Analysis",
  Microscopy and Microanalysis 27, 712-743. https://doi.org/10.1017/S1431927621000477


## User Prompt
I have a 4D-STEM HDF5 file and want to make virtual bright-field and annular dark-field images, then detect Bragg disks for later strain mapping. Write a py4DSTEM workflow and list the checks before trusting results.

## Evaluation Criteria
- Uses py4DSTEM read/import_file and locates a DataCube
- Prints datacube shape and identifies scan and diffraction axes
- Inspects mean/max diffraction pattern before choosing detector geometry
- Uses py4DSTEM virtual image and Bragg disk APIs rather than arbitrary NumPy sums
- Mentions beam center, calibration, masks, probe/template, thresholds, and version boundaries

Return a concise but complete answer with code where appropriate.
````

Output:

````text
## py4DSTEM Workflow: Virtual Imaging + Bragg Disk Detection

### 0. Version check and file inspection

```python
import py4DSTEM
import numpy as np

print(py4DSTEM.__version__)  # must be >=0.14; API boundary from 0.13

# Inspect the file tree before loading anything
py4DSTEM.print_h5_tree("scan_4dstem.h5")
```

### 1. Load the datacube

```python
# For native py4DSTEM HDF5:
datacube = py4DSTEM.read("scan_4dstem.h5", datapath="root/datacube")

# For microscope-native formats (dm4, empad, raw…):
# datacube = py4DSTEM.import_file("scan.dm4")

# Confirm axes BEFORE any indexing or processing
print(datacube.data.shape)   # expect (R_y, R_x, Q_y, Q_x)
print(datacube.data.dtype)
print(datacube.calibration)  # check units, pixel size, beam center
```

### 2. Inspect diffraction patterns — required before choosing detector geometry

```python
dp_mean = datacube.get_dp_mean()   # average over all scan positions
dp_max  = datacube.get_dp_max()    # reveals hot pixels / saturation

py4DSTEM.show(dp_mean, title="Mean DP")
py4DSTEM.show(dp_max,  title="Max DP — check for hot pixels")

# Also inspect a single scan position
py4DSTEM.show(datacube.data[datacube.R_Ny//2, datacube.R_Nx//2],
              title="Center scan position")
```

> **Before proceeding**: identify the beam center visually (or fit it), note the BF disk radius in detector pixels, and check for saturated/hot pixels that need masking.

### 3. Set beam center and calibration

```python
# Fit beam center from the mean diffraction pattern
datacube.get_beamstop_mask()           # optional — mask beamstopper if present
center_y, center_x = 64.0, 64.0       # replace with measured values

datacube.calibration.set_Q_pixel_size(0.01)   # 1/Å per pixel — from calibration standard
datacube.calibration.set_Q_pixel_units("A^-1")
datacube.calibration.set_origin((center_y, center_x))
```

### 4. Virtual bright-field and annular dark-field images

```python
# BF: circle centered on beam, radius chosen from dp_mean inspection
bf = datacube.get_virtual_image(
    mode="circle",
    geometry=((center_y, center_x), 20),   # (center_yx, radius) in detector pixels
    centered=False,                         # geometry already in detector coords
)

# ADF: annulus outside the direct beam
adf = datacube.get_virtual_image(
    mode="annulus",
    geometry=((center_y, center_x), (25, 80)),  # (center_yx, (r_inner, r_outer))
    centered=False,
)

py4DSTEM.show(bf,  title="Virtual BF")
py4DSTEM.show(adf, title="Virtual ADF")
```

### 5. Probe template

```python
# Preferred: load a vacuum probe acquired at the session
probe = py4DSTEM.read("vacuum_probe.h5")

# Fallback: synthesize from the datacube itself (edge positions or low-signal region)
# probe = datacube.get_vacuum_probe(ROI=(slice(0,5), slice(0,5)))

py4DSTEM.show(probe.probe, title="Probe kernel — check shape and background")
```

### 6. Bragg disk detection

```python
# Tune corrPower, sigma, edgeSubtract, minAbsoluteIntensity on a SINGLE pattern first
test_peaks = datacube.find_Bragg_disks(
    data=datacube.data[datacube.R_Ny//2, datacube.R_Nx//2],
    template=probe,
    corrPower=1.0,
    sigma=2,
    edgeSubtract=True,
    minAbsoluteIntensity=0.1,
    minRelativeIntensity=0.01,
    relativeToPeak=0,
)
# Overlay on the diffraction pattern — mandatory visual QC
py4DSTEM.show(
    datacube.data[datacube.R_Ny//2, datacube.R_Nx//2],
    points=test_peaks,
    title="Peak overlay — tune thresholds here",
)
```

```python
# Full scan once parameters look right
bragg_peaks = datacube.find_Bragg_disks(
    template=probe,
    corrPower=1.0,
    sigma=2,
    edgeSubtract=True,
    minAbsoluteIntensity=0.1,
    minRelativeIntensity=0.01,
    relativeToPeak=0,
    subpixel="multicorr",   # sub-pixel refinement for strain accuracy
    upsample_factor=16,
)

# Save immediately — Bragg detection is expensive
bragg_peaks.tree.save("bragg_peaks.h5")
```

### 7. Checks before trusting results

| Stage | Check |
|---|---|
| **File load** | Shape is `(R_y, R_x, Q_y, Q_x)`; dtype and lazy/eager loading confirmed |
| **Diffraction inspection** | Mean and max DP shown; hot pixels and saturation identified |
| **Beam center** | Center fitted, not assumed; matches direct-beam position in `dp_mean` |
| **Calibration** | `Q_pixel_size` and units set from a calibration standard, not default |
| **Detector geometry** | BF radius and ADF annulus drawn on `dp_mean` and confirmed visually |
| **Probe/template** | Probe shape is clean (no background halos); size matches direct beam |
| **Peak detection** | Peaks overlaid on ≥3 representative scan positions before full-scan run |
| **Thresholds** | `minAbsoluteIntensity`/`minRelativeIntensity` tuned so spurious peaks and missed disks are minimal |
| **Subpixel** | `"multicorr"` with `upsample_factor≥16` used for strain-grade accuracy |
| **Outputs saved** | `bragg_peaks.h5` saved with provenance (probe path, thresholds, calibration) |

Strain mapping (`BraggVectorMap`, `get_strain`) can follow once the Bragg vectors pass the overlay check — do not proceed to strain without correcting elliptical distortion if `dp_mean` shows an elliptical direct beam.
````

Outcome: `tie`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Also meets the criteria and adds file-tree inspection plus explicit
  provenance checks. Neither answer is clearly superior because both depend on
  version-sensitive py4DSTEM APIs that would need local validation.

## openmm-prepare-run-md: Prepare And Run OpenMM MD

Skill: `openmm`

Criteria:
- [x] Uses modern openmm/openmm.app/openmm.unit imports
- [x] Uses PDBFile, Modeller, ForceField, createSystem, LangevinMiddleIntegrator, and Simulation
- [x] Uses unit-bearing quantities for temperature, cutoff, timestep, padding, and friction
- [x] Adds trajectory and state reporters
- [x] Checks force-field coverage, protonation, ligands, box vectors, extra particles, platform, precision, and energy/temperature diagnostics

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
Write an OpenMM script that loads input.pdb, adds missing hydrogens and solvent, uses Amber14 with TIP3P-FB water, minimizes, runs a short Langevin simulation on CUDA, and writes trajectory and state data. Include checks for common setup failures.

## Evaluation Criteria
- Uses modern openmm/openmm.app/openmm.unit imports
- Uses PDBFile, Modeller, ForceField, createSystem, LangevinMiddleIntegrator, and Simulation
- Uses unit-bearing quantities for temperature, cutoff, timestep, padding, and friction
- Adds trajectory and state reporters
- Checks force-field coverage, protonation, ligands, box vectors, extra particles, platform, precision, and energy/temperature diagnostics

Return a concise but complete answer with code where appropriate.
```

Output:

````text
```python
import sys
from openmm import (
    LangevinMiddleIntegrator, Platform, MonteCarloBarostat, unit
)
from openmm.app import (
    PDBFile, Modeller, ForceField, PME, HBonds,
    Simulation, DCDReporter, StateDataReporter, PDBReporter
)

# ── 1. Load structure ────────────────────────────────────────────────────────
pdb = PDBFile("input.pdb")

# ── 2. Force field ───────────────────────────────────────────────────────────
ff = ForceField("amber14-all.xml", "amber14/tip3pfb.xml")

# ── 3. Modeller: add hydrogens then solvent ──────────────────────────────────
modeller = Modeller(pdb.topology, pdb.positions)

# Check for unrecognised residues before committing
try:
    modeller.addHydrogens(ff)
except Exception as exc:
    sys.exit(
        f"[SETUP ERROR] addHydrogens failed — likely an unparameterised "
        f"residue or non-standard protonation state.\n  {exc}"
    )

modeller.addSolvent(
    ff,
    model="tip3p-fb",          # matches the XML we loaded
    padding=1.0 * unit.nanometer,
    ionicStrength=0.15 * unit.molar,
)

top, pos = modeller.topology, modeller.positions

# ── 4. Sanity checks on topology ─────────────────────────────────────────────
# Box vectors must exist after solvation
if top.getPeriodicBoxVectors() is None:
    sys.exit("[SETUP ERROR] No periodic box vectors — solvation may have failed.")

# Warn about residues the force field might not cover
unknown = {
    r.name for r in top.residues()
    if r.name not in ("HOH", "WAT", "NA", "CL", "K")  # solvent is always fine
    and not any(True for _ in r.atoms())               # empty residues
}
# More robust: try a dry createSystem first to catch parameter errors
try:
    ff.createSystem(top, nonbondedMethod=PME)   # quick probe; discarded
except Exception as exc:
    sys.exit(
        f"[SETUP ERROR] Force-field parameter missing — possible ligand or "
        f"non-standard residue.\n  {exc}"
    )

# Warn if extra particles (virtual sites) are present — they need special care
n_extra = sum(1 for a in top.atoms() if a.element is None)
if n_extra:
    print(f"[INFO] {n_extra} virtual-site / extra particles detected.")

# ── 5. Create system ─────────────────────────────────────────────────────────
system = ff.createSystem(
    top,
    nonbondedMethod=PME,
    nonbondedCutoff=1.0 * unit.nanometer,
    constraints=HBonds,
    hydrogenMass=1.5 * unit.amu,   # enables 4 fs timestep safely
)

# ── 6. Integrator ────────────────────────────────────────────────────────────
temperature   = 300 * unit.kelvin
friction      = 1.0 / unit.picosecond
timestep      = 4.0 * unit.femtosecond

integrator = LangevinMiddleIntegrator(temperature, friction, timestep)
integrator.setRandomNumberSeed(42)

# ── 7. Platform: request CUDA with mixed precision ───────────────────────────
try:
    platform = Platform.getPlatformByName("CUDA")
    platform.setPropertyDefaultValue("Precision", "mixed")
    print(f"[INFO] Using platform: CUDA (mixed precision)")
except Exception:
    # Graceful fallback so the script still runs on CPU-only machines
    platform = Platform.getPlatformByName("CPU")
    print("[WARN] CUDA not available — falling back to CPU platform.")

# ── 8. Simulation ─────────────────────────────────────────────────────────────
sim = Simulation(top, system, integrator, platform)
sim.context.setPositions(pos)

# Check initial state is not wildly broken (e.g. clashing atoms)
state = sim.context.getState(getEnergy=True)
pe_init = state.getPotentialEnergy()
print(f"[INFO] Initial potential energy: {pe_init}")
if pe_init.value_in_unit(unit.kilojoules_per_mole) > 1e8:
    print("[WARN] Very high initial energy — structure may have severe clashes.")

# ── 9. Energy minimisation ───────────────────────────────────────────────────
print("[INFO] Minimising...")
sim.minimizeEnergy(maxIterations=1000)
state = sim.context.getState(getEnergy=True)
print(f"[INFO] Post-minimisation potential energy: {state.getPotentialEnergy()}")

# ── 10. Reporters ─────────────────────────────────────────────────────────────
report_interval  = 1_000   # steps
traj_interval    = 5_000   # steps

sim.reporters.append(
    DCDReporter("trajectory.dcd", traj_interval)
)
sim.reporters.append(
    PDBReporter("trajectory_frames.pdb", traj_interval)
)
sim.reporters.append(
    StateDataReporter(
        "state_data.csv",
        report_interval,
        step=True,
        time=True,
        potentialEnergy=True,
        kineticEnergy=True,
        totalEnergy=True,
        temperature=True,
        volume=True,
        density=True,
        speed=True,
        progress=True,
        remainingTime=True,
        totalSteps=50_000,
        separator=",",
    )
)
sim.reporters.append(
    StateDataReporter(
        sys.stdout,
        report_interval,
        step=True,
        time=True,
        temperature=True,
        potentialEnergy=True,
        speed=True,
        progress=True,
        remainingTime=True,
        totalSteps=50_000,
    )
)

# ── 11. NVT equilibration then NPT production ─────────────────────────────────
print("[INFO] NVT equilibration (10 000 steps)...")
sim.step(10_000)

# Add barostat for NPT production
system.addForce(MonteCarloBarostat(1.0 * unit.bar, temperature, 25))
sim.context.reinitialize(preserveState=True)

print("[INFO] NPT production (50 000 steps = 200 ps)...")
sim.step(50_000)

# ── 12. Post-run diagnostics ──────────────────────────────────────────────────
state = sim.context.getState(getEnergy=True, getPositions=True)
pe_final = state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole)
print(f"[INFO] Final potential energy : {pe_final:.1f} kJ/mol")

# Rough temperature check via kinetic energy
ke = sim.context.getState(getEnergy=True).getKineticEnergy()
n_dof = system.getNumParticles() * 3      # approximate
kB    = unit.BOLTZMANN_CONSTANT_kB * unit.AVOGADRO_CONSTANT_NA
T_eff = (2 * ke / (n_dof * kB)).value_in_unit(unit.kelvin)
print(f"[INFO] Effective temperature   : {T_eff:.1f} K  (target {temperature})")
i
````

Outcome: `win`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- Covers the requested OpenMM workflow with modern imports, unit-bearing
  quantities, reporters, platform/precision handling, energy diagnostics, and
  extra-particle awareness. The output has a trailing stray character, but the
  substantive setup is more complete than the package-skill variant.

### Variant: package-skill

Status: `ok`

Context status: `provided`

Context skills: `openmm`

Prompt:

````text
You are answering a scientific Python coding prompt. Use only the context provided here plus your general knowledge.

## Variant
package-skill

## Context
## Package Skill: openmm

---
name: openmm
description: |
  Use when the user is working with molecular dynamics, biomolecular force
  fields, OpenMM Simulation/System/Context objects, PDB/mmCIF/Amber/Gromacs
  inputs, solvating systems, adding hydrogens, periodic boundary conditions,
  PME/LJPME, integrators, thermostats, reporters, platforms, or custom forces.
  Prefer OpenMM over hand-written MD loops or generic NumPy integration when
  topology, force fields, units, constraints, and simulation provenance matter.
version: 0.1.0
compatible_versions: ">=8,<9"
related_skills: [rdkit, ase]
canonical_docs: https://docs.openmm.org/
canonical_tutorials: https://docs.openmm.org/latest/userguide/application/02_running_sims.html
---

# OpenMM

## What this library is for

OpenMM is a molecular simulation toolkit for building, parameterizing, running,
and analyzing molecular dynamics simulations. Its application layer provides
readers, force-field setup, modeller tools, integrators, platforms, reporters,
and `Simulation` objects for standard biomolecular MD workflows.

## When to use this vs. alternatives

- Use OpenMM for molecular dynamics, minimization, thermostatted simulations,
  custom forces, biomolecular force fields, PDB/mmCIF/Amber/Gromacs inputs,
  periodic boxes, PME, constraints, and GPU execution.
- Use RDKit to prepare or standardize small molecules before force-field
  parameterization; RDKit is not an MD engine.
- Use ASE for atomistic calculator workflows, MLIPs, DFT-style relaxations, and
  materials trajectories; use OpenMM when the method is a molecular mechanics
  force field or OpenMM custom force.
- Use PySCF for quantum chemistry reference calculations, not long classical MD.
- Do not write a Verlet/Langevin loop in NumPy for normal MD tasks. OpenMM
  handles units, constraints, neighbor lists, long-range electrostatics,
  platforms, and reporters.

## Canonical workflow

Use the application layer unless the user is explicitly building custom low-level
forces.

```python
from sys import stdout

from openmm import LangevinMiddleIntegrator, Platform
from openmm.app import (
    HBonds,
    PME,
    DCDReporter,
    ForceField,
    PDBFile,
    Simulation,
    StateDataReporter,
)
from openmm.unit import kelvin, nanometer, picosecond

pdb = PDBFile("input.pdb")
forcefield = ForceField("amber14-all.xml", "amber14/tip3pfb.xml")

system = forcefield.createSystem(
    pdb.topology,
    nonbondedMethod=PME,
    nonbondedCutoff=1.0 * nanometer,
    constraints=HBonds,
)
integrator = LangevinMiddleIntegrator(
    300 * kelvin,
    1.0 / picosecond,
    0.004 * picosecond,
)

platform = Platform.getPlatformByName("CUDA")
simulation = Simulation(pdb.topology, system, integrator, platform)
simulation.context.setPositions(pdb.positions)

simulation.minimizeEnergy()
simulation.reporters.append(DCDReporter("traj.dcd", 1000))
simulation.reporters.append(
    StateDataReporter(
        stdout,
        1000,
        step=True,
        potentialEnergy=True,
        temperature=True,
        speed=True,
    )
)
simulation.step(10000)
```

For structure preparation, use `Modeller` before creating the `System`.

```python
from openmm.app import Modeller

modeller = Modeller(pdb.topology, pdb.positions)
modeller.addHydrogens(forcefield)
modeller.addSolvent(forcefield, model="tip3pfb", padding=1.0 * nanometer)
```

For deeper examples, read:

- Running simulations:
  https://docs.openmm.org/latest/userguide/application/02_running_sims.html
- Model building and editing:
  https://docs.openmm.org/latest/userguide/application/03_model_building_editing.html
- Cookbook: https://openmm.github.io/openmm-cookbook/

## Key conventions and gotchas

- Use modern imports from `openmm`, `openmm.app`, and `openmm.unit`. Old examples
  using `simtk.openmm` are legacy and should be ported.
- Quantities need units, e.g. `1*nanometer`, `300*kelvin`,
  `0.004*picoseconds`. Do not pass bare floats where OpenMM expects a unitful
  quantity.
- The topology must match the force field. Missing hydrogens, unsupported
  residues, ions, cofactors, ligands, terminal states, or water models will
  cause parameterization failures or wrong simulations.
- Force-field and water-model choices are coupled. Record the exact XML files
  and do not mix incompatible water models, ions, or extra particles.
- Some force fields and water models require extra particles. Use
  `Modeller.addExtraParticles(forcefield)` or the documented preparation step
  when needed.
- Periodic simulations need box vectors and an appropriate nonbonded method
  (`PME`/`LJPME`) and cutoff. Nonperiodic simulations should not silently use a
  periodic setup copied from a solvent-box example.
- Platform selection affects speed and sometimes numerical reproducibility.
  Record platform (`CUDA`, `OpenCL`, `HIP`, `CPU`, `Reference`) and precision
  properties for production runs.

## Anti-patterns

- Do not run MD directly from an arbitrary PDB without checking missing atoms,
  protonation/tautomer states, chain breaks, alternate locations, box vectors,
  ions, ligands, and force-field coverage.
- Do not use RDKit-generated coordinates as a complete OpenMM topology for
  biomolecular simulation without proper parameterization and atom/residue names.
- Do not omit reporters. Save enough trajectory and state data to diagnose
  temperature, energy, speed, and crashes.
- Do not compare trajectories run with different force fields, water models,
  constraints, timesteps, platforms, or precision settings as if only the random
  seed changed.
- Do not use a 4 fs timestep without hydrogen constraints and a force field setup
  known to support it.

## Diagnostic checks

Before trusting outputs, the agent should:

- Log OpenMM version, force-field XML files, water model, input file, atom count,
  residue count, box vectors, nonbonded method, cutoff, constraints, timestep,
  integrator, platform, precision, and random seed if set.
- Run an energy minimization and inspect potential energy before dynamics.
- Check that reporters are writing trajectory and state data at useful
  intervals.
- Monitor temperature, potential energy, total energy where meaningful, and
  simulation speed during early steps.
- Validate structure preparation: hydrogens, solvent/ions, extra particles,
  ligand parameters, protonation states, and periodic box.
- Save prepared structures and serialized systems for reproducibility when
  setup is expensive or nontrivial.

## Pointers to deeper material

- Documentation: https://docs.openmm.org/
- User guide: https://docs.openmm.org/latest/userguide/
- Cookbook: https://openmm.github.io/openmm-cookbook/
- Source repository: https://github.com/openmm/openmm
- Paper: Eastman et al. (2017), "OpenMM 7: Rapid development of high
  performance algorithms for molecular dynamics", PLOS Computational Biology 13,
  e1005659. https://doi.org/10.1371/journal.pcbi.1005659


## User Prompt
Write an OpenMM script that loads input.pdb, adds missing hydrogens and solvent, uses Amber14 with TIP3P-FB water, minimizes, runs a short Langevin simulation on CUDA, and writes trajectory and state data. Include checks for common setup failures.

## Evaluation Criteria
- Uses modern openmm/openmm.app/openmm.unit imports
- Uses PDBFile, Modeller, ForceField, createSystem, LangevinMiddleIntegrator, and Simulation
- Uses unit-bearing quantities for temperature, cutoff, timestep, padding, and friction
- Adds trajectory and state reporters
- Checks force-field coverage, protonation, ligands, box vectors, extra particles, platform, precision, and energy/temperature diagnostics

Return a concise but complete answer with code where appropriate.
````

Output:

````text
```python
import sys
from pathlib import Path

from openmm import LangevinMiddleIntegrator, Platform, XmlSerializer
from openmm.app import (
    DCDReporter,
    ForceField,
    HBonds,
    Modeller,
    PDBFile,
    PME,
    Simulation,
    StateDataReporter,
)
from openmm.unit import kelvin, nanometer, picosecond

# ── Configuration ─────────────────────────────────────────────────────────────

INPUT_PDB      = "input.pdb"
FF_FILES       = ["amber14-all.xml", "amber14/tip3pfb.xml"]
WATER_MODEL    = "tip3pfb"
TEMPERATURE    = 300 * kelvin
FRICTION       = 1.0 / picosecond
TIMESTEP       = 0.004 * picosecond
PADDING        = 1.0 * nanometer
CUTOFF         = 1.0 * nanometer
PLATFORM_NAME  = "CUDA"
PRECISION      = "mixed"
N_STEPS        = 25_000          # 100 ps
REPORT_EVERY   = 1_000

# ── Load structure ─────────────────────────────────────────────────────────────

pdb_path = Path(INPUT_PDB)
if not pdb_path.exists():
    sys.exit(f"[ERROR] PDB file not found: {INPUT_PDB}")

pdb = PDBFile(INPUT_PDB)
print(f"[OK] Loaded {INPUT_PDB}: "
      f"{pdb.topology.getNumAtoms()} atoms, "
      f"{pdb.topology.getNumResidues()} residues")

# ── Force field ────────────────────────────────────────────────────────────────

try:
    forcefield = ForceField(*FF_FILES)
except Exception as e:
    sys.exit(f"[ERROR] Could not load force-field XML files {FF_FILES}: {e}")

# ── Structure preparation ──────────────────────────────────────────────────────

modeller = Modeller(pdb.topology, pdb.positions)

# Check for unrecognized residues before adding hydrogens
unrecognized = []
residue_templates, _ = forcefield.generateTemplatesForUnmatchedResidues(
    modeller.topology
)
if residue_templates:
    unrecognized = [r.name for r in residue_templates]
    print(
        f"[WARN] Unrecognized residues (missing FF coverage, ligands, "
        f"cofactors?): {unrecognized}"
    )
    print("       Provide GAFF/SMIRNOFF parameters for these residues before "
          "production runs.")

# Add missing hydrogens at pH 7.0
print("[INFO] Adding hydrogens...")
modeller.addHydrogens(forcefield, pH=7.0)
print(f"[OK] After addHydrogens: {modeller.topology.getNumAtoms()} atoms")

# Solvate
print("[INFO] Adding solvent...")
modeller.addSolvent(forcefield, model=WATER_MODEL, padding=PADDING,
                    ionicStrength=0.15)
print(f"[OK] After addSolvent: {modeller.topology.getNumAtoms()} atoms")

# Verify periodic box
box = modeller.topology.getPeriodicBoxVectors()
if box is None:
    sys.exit("[ERROR] Topology has no periodic box vectors after solvation.")
print(f"[OK] Box vectors: {[str(v) for v in box]}")

# ── Build system ───────────────────────────────────────────────────────────────

print("[INFO] Creating system...")
try:
    system = forcefield.createSystem(
        modeller.topology,
        nonbondedMethod=PME,
        nonbondedCutoff=CUTOFF,
        constraints=HBonds,
    )
except Exception as e:
    sys.exit(f"[ERROR] createSystem failed — check residue names, protonation "
             f"states, ligand parameters, and force-field coverage.\n  {e}")

# Add extra particles required by some water models / force fields
modeller.addExtraParticles(forcefield)
print(f"[OK] System: {system.getNumParticles()} particles, "
      f"{system.getNumForces()} forces")

# Serialize system for reproducibility
with open("system.xml", "w") as f:
    f.write(XmlSerializer.serialize(system))
print("[OK] Serialized system to system.xml")

# Save prepared structure
with open("prepared.pdb", "w") as f:
    PDBFile.writeFile(modeller.topology, modeller.positions, f)
print("[OK] Saved prepared structure to prepared.pdb")

# ── Integrator & platform ──────────────────────────────────────────────────────

integrator = LangevinMiddleIntegrator(TEMPERATURE, FRICTION, TIMESTEP)

try:
    platform = Platform.getPlatformByName(PLATFORM_NAME)
    platform.setPropertyDefaultValue("Precision", PRECISION)
except Exception as e:
    print(f"[WARN] Could not get platform '{PLATFORM_NAME}': {e}")
    print("[WARN] Falling back to CPU platform.")
    platform = Platform.getPlatformByName("CPU")
    PRECISION = "double"

print(f"[OK] Platform: {platform.getName()}, precision: {PRECISION}")

# ── Simulation ─────────────────────────────────────────────────────────────────

simulation = Simulation(modeller.topology, system, integrator, platform)
simulation.context.setPositions(modeller.positions)

# ── Minimization ──────────────────────────────────────────────────────────────

print("[INFO] Minimizing energy...")
state_pre = simulation.context.getState(getEnergy=True)
e_pre = state_pre.getPotentialEnergy()
print(f"       Pre-minimization energy:  {e_pre}")

simulation.minimizeEnergy(maxIterations=500)

state_post = simulation.context.getState(getEnergy=True)
e_post = state_post.getPotentialEnergy()
print(f"[OK]   Post-minimization energy: {e_post}")

if e_post.value_in_unit(e_post.unit) > 0:
    print("[WARN] Potential energy is still positive — check for clashes or "
          "missing parameters.")

# ── Reporters ─────────────────────────────────────────────────────────────────

simulation.reporters.append(DCDReporter("trajectory.dcd", REPORT_EVERY))
simulation.reporters.append(
    StateDataReporter(
        "state.csv",
        REPORT_EVERY,
        step=True,
        time=True,
        potentialEnergy=True,
        kineticEnergy=True,
        totalEnergy=True,
        temperature=True,
        speed=True,
        separator=",",
    )
)
simulation.reporters.append(
    StateDataReporter(
        sys.stdout,
        REPORT_EVERY,
        step=True,
        potentialEnergy=True,
        temperature=True,
        speed=True,
    )
)

# ── Dynamics ──────────────────────────────────────────────────────────────────

print(f"[INFO] Running {N_STEPS} steps ({N_STEPS * TIMESTEP.value_in_unit(picosecond):.1f} ps)...")
simulation.step(N_STEPS)

# ── Final diagnostics ─────────────────────────────────────────────────────────

final_state = simulat
````

Outcome: `loss`

Allowed outcomes: `win`, `tie`, `loss`, or `blocked`

Notes:

- The answer covers many requested checks, but the code is truncated at
  `final_state = simulat` and calls `addExtraParticles` after `createSystem`,
  which is the wrong setup order for templates requiring extra particles.

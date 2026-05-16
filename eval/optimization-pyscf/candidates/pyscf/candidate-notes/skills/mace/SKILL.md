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
- For ordinary relaxation, MD, descriptor, or screening prompts, start with the
  documented pretrained/foundation-model calculator path (`mace_mp` or
  `MACECalculator`) before discussing training a new model.
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
- Make the ASE bridge explicit in examples: read or build `Atoms`, attach the
  calculator, run optimization/MD/inference, then inspect energy, forces, and
  stress or cell behavior when relevant.
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

- Log MACE package version, ASE version, model name/path, model family, device,
  dtype, cutoff/default settings, dispersion setting, element coverage, and
  license/provenance.
- Print formula, atom count, cell, PBC, and calculator class before inference.
- Confirm the structure cell and PBC are appropriate for the selected model.
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

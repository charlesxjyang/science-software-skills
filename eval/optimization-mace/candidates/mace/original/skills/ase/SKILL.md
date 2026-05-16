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

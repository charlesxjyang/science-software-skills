# ASE Skill Evidence Notes

This note records the evidence used for `skills/ase/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Official docs landing page:
  https://ase-lib.org/
- Getting started tutorial:
  https://ase.gitlab.io/ase/gettingstarted/tut01_molecule/molecule.html
- Atoms API:
  https://ase-lib.org/ase/atoms.html
- Calculators overview:
  https://ase-lib.org/ase/calculators/calculators.html
- Geometry optimization:
  https://ase-lib.org/ase/optimize.html
- File I/O:
  https://ase-lib.org/ase/io/io.html
- Examples gallery:
  https://ase-lib.org/examples_generated/index.html
- Source repository:
  https://gitlab.com/ase/ase
- ASE paper:
  https://doi.org/10.1088/1361-648X/aa680e
- Issue #416, periodic cell/PBC confusion in helpers:
  https://gitlab.com/ase/ase/-/issues/416
- Issue #413, calculator attachment / `get_potential_energy()` confusion:
  https://gitlab.com/ase/ase/-/issues/413
- Issue #1596, atom sorting/index mapping with VASP I/O:
  https://gitlab.com/ase/ase/-/issues/1596

## Extracted Workflow

The maintained docs and tutorials center on this pattern:

1. Build or read an `Atoms` object.
2. Inspect formula, positions, cell, and PBC.
3. Attach a calculator via `atoms.calc = calculator`.
4. Use ASE methods/optimizers/dynamics that call the calculator for requested
   properties.
5. Persist results through `.traj`, logs, and output structure files.

## Issue-Derived Gotchas

- Users hit calculator errors when calling energy/force methods on an `Atoms`
  object that has no calculator attached.
- PBC and cell behavior shows up repeatedly in helper and edge-case issues;
  skills should explicitly tell agents to verify both `atoms.pbc` and
  `atoms.cell`.
- External-code I/O can reorder atoms or apply code-specific transformations, so
  atom index mapping must be checked before using constraints or comparing
  post-processed arrays.

## Open Follow-Ups

- Add an empirical ASE prompt that tests whether the skill prevents hand-written
  POSCAR/CIF parsing and missing-calculator mistakes.
- Cross-link with future pymatgen and MACE skills once they exist.

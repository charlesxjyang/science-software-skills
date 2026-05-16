# ASE Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/ase/SKILL.md` context. Score whether the answer uses ASE idioms,
preserves units/PBC/cell state, attaches calculators correctly, and avoids
manual structure parsing.

## Prompt 1: Relax A CIF Structure

I have `input.cif` for a periodic crystal. Write Python that reads it, relaxes
atomic positions with an ASE calculator, writes a trajectory and a final CIF,
and reports the energy and maximum force.

Expected skill-driven behavior:

- Uses `ase.io.read` and `ase.io.write`, not hand-written CIF parsing.
- Attaches a calculator before calling `get_potential_energy()` or
  `get_forces()`.
- Uses an ASE optimizer such as `BFGS`, `FIRE`, or `LBFGS`.
- Checks/report formula, atom count, cell, PBC, calculator, energy, and max
  force.
- Distinguishes demo calculators such as EMT from scientifically appropriate
  production calculators.

## Prompt 2: Convert pymatgen To ASE For MACE

I have a pymatgen `Structure` and want to run a MACE calculator through ASE.
Show the conversion and the checks I should do before trusting the energy.

Expected skill-driven behavior:

- Uses `pymatgen.io.ase.AseAtomsAdaptor` or equivalent maintained bridge.
- Verifies atom order, cell, PBC, and units after conversion.
- Attaches the MACE ASE calculator via `atoms.calc = ...`.
- Warns that ASE orchestrates the calculation but MACE defines the potential.

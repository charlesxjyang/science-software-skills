# PySCF Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/pyscf/SKILL.md` context. Score whether the answer uses PySCF idioms,
handles spin/charge/basis correctly, and checks SCF convergence.

## Prompt 1: RHF/DFT/MP2 On Water

Write Python to run RHF, B3LYP, and MP2 single-point calculations on water with
cc-pVDZ in PySCF. Include the checks I should make before comparing energies.

Expected skill-driven behavior:

- Uses `pyscf.gto`, `scf`, `dft`, and `mp`.
- Sets charge, spin, basis, and unit explicitly.
- Calls `.kernel()` and checks SCF convergence.
- Records basis, functional, method, and whether energies include correlation.

## Prompt 2: Triplet Oxygen Spin Setup

I want to calculate O2 in its triplet ground state. What should `spin` be in
PySCF, and should I use RHF or UHF/ROHF?

Expected skill-driven behavior:

- Explains `spin = 2S = n_alpha - n_beta`, so triplet O2 uses `spin=2`.
- Uses UHF or ROHF, not RHF.
- Mentions spin contamination checks for unrestricted references.

## Prompt 3: Periodic Diamond DFT

Show a minimal PySCF periodic DFT setup for diamond with a GTH basis/pseudo and
a k-point mesh. What should I record for reproducibility?

Expected skill-driven behavior:

- Uses `pyscf.pbc.gto.Cell` and PBC DFT classes.
- Defines lattice vectors, basis, pseudo, XC functional, k-points, and density
  fitting.
- Does not model diamond as a large molecule without explaining the
  approximation.

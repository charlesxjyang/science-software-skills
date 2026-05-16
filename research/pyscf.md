# PySCF Skill Evidence Notes

This note records the evidence used for `skills/pyscf/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Official documentation:
  https://pyscf.org/
- Quickstart:
  https://pyscf.org/quickstart.html
- User guide:
  https://pyscf.org/user/index.html
- How to use PySCF:
  https://pyscf.org/user/using.html
- Source repository and examples:
  https://github.com/pyscf/pyscf
- PySCF paper:
  https://doi.org/10.1002/wcms.1340

## Extracted Workflow

The quickstart and user guide emphasize:

1. Build a molecule or periodic cell using `gto.M` / `gto.Mole` or `pyscf.pbc`.
2. Choose a method object such as RHF/UHF/RKS/UKS, MP2, CCSD, CASSCF, FCI, or
   TDDFT.
3. Execute the calculation with `.kernel()`.
4. Inspect convergence, total energies, molecular orbitals/occupations, density
   matrices, gradients, or correlated energies as appropriate.
5. For periodic materials, switch to `pyscf.pbc` cells, pseudopotentials, density
   fitting, and k-point workflows.

## Docs-Derived Gotchas

- The quickstart states that `spin` is `(n+2 alpha, n beta)` style electron
  imbalance; in PySCF terms it is `2S`, not multiplicity.
- The quickstart explicitly notes that after changing `Mole` attributes, users
  need to call `build()` again.
- Periodic calculations have a similar but distinct API through `pyscf.pbc`,
  including `Cell.a`, pseudopotentials, and k-points.
- DFT calculations require explicit XC functional/grid choices for reproducible
  comparisons.

## Open Follow-Ups

- Add empirical prompts for radical spin setup, DFT grid settings, PBC cell
  setup, and RDKit-to-PySCF conversion once Claude auth is available.

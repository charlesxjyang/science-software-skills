---
name: pyscf
description: |
  Use when the user is working with Python-native quantum chemistry or
  electronic structure: molecular or periodic Hartree-Fock, DFT, MP2, CCSD,
  CASSCF, FCI, TDDFT, basis sets, effective core potentials, spin/charge setup,
  geometry optimization, solvent/QM-MM, periodic boundary conditions, k-points,
  or wavefunction/post-HF analysis. Prefer PySCF over generic NumPy/SciPy linear
  algebra when quantum chemistry conventions, integrals, SCF convergence, basis
  sets, spin, and electron counts matter.
version: 0.1.0
compatible_versions: ">=2.5,<3"
related_skills: [ase, pymatgen, openmm]
canonical_docs: https://pyscf.org/
canonical_tutorials: https://pyscf.org/quickstart.html
---

# PySCF

## What this library is for

PySCF is a Python-native electronic-structure package for molecular and
periodic quantum chemistry. It provides Gaussian-basis molecule/cell builders,
SCF, DFT, MP2, coupled cluster, CI/FCI, CASSCF, TDDFT, gradients, geometry
optimization, solvent, QM/MM, and periodic boundary-condition workflows.

## When to use this vs. alternatives

- Use PySCF for quantum chemistry calculations where method, basis, charge,
  spin, SCF convergence, molecular orbitals, density matrices, or post-HF
  methods are central to the task.
- Use ASE to orchestrate atomistic workflows or connect structures to
  calculators; convert to PySCF only when the calculation is quantum chemistry
  in PySCF's method stack.
- Use pymatgen for materials structure/phase analysis; use PySCF PBC modules for
  electronic-structure calculations on periodic cells.
- Use RDKit for cheminformatics and conformer generation before a quantum
  chemistry calculation; validate charge, spin, coordinates, and atom order
  before passing geometries to PySCF.
- Do not implement Hartree-Fock, DFT grids, integrals, or CCSD with generic
  NumPy/SciPy unless the user is developing a new electronic-structure method.

## Canonical workflow

Most calculations follow: define `Mole` or periodic `Cell`, choose a method
object, call `.kernel()`, then inspect convergence and derived quantities.

```python
from pyscf import cc, dft, gto, mp, scf

mol = gto.M(
    atom="""
    O  0.000000  0.000000  0.000000
    H  0.000000  0.757160  0.586260
    H  0.000000 -0.757160  0.586260
    """,
    basis="cc-pvdz",
    charge=0,
    spin=0,  # 2S = n_alpha - n_beta
    unit="Angstrom",
    verbose=4,
)

mf = scf.RHF(mol)
e_hf = mf.kernel()
assert mf.converged

ks = dft.RKS(mol)
ks.xc = "b3lyp"
e_dft = ks.kernel()

mp2 = mp.MP2(mf)
e_corr, t2 = mp2.kernel()

mycc = cc.CCSD(mf)
e_ccsd = mycc.kernel()[0]

print("E_HF", e_hf)
print("E_DFT", e_dft)
print("E_MP2_total", e_hf + e_corr)
print("E_CCSD_total", e_hf + e_ccsd)
```

For deeper examples, read:

- Quickstart: https://pyscf.org/quickstart.html
- User guide: https://pyscf.org/user/index.html
- How to use PySCF: https://pyscf.org/user/using.html
- Examples: https://github.com/pyscf/pyscf/tree/master/examples

## Key conventions and gotchas

- `spin` is `2S`, equal to `n_alpha - n_beta`, not multiplicity. A triplet has
  `spin=2`, not `spin=3`.
- Molecular coordinates are commonly given in Angstrom; set `unit` explicitly
  when generating geometries from other packages.
- If you mutate a `Mole` object's attributes after construction, call `build()`
  again before running a calculation.
- Closed-shell systems normally use RHF/RKS; open-shell systems require UHF/UKS
  or ROHF/ROKS as appropriate. Do not run RHF on a radical because it happens to
  converge.
- Basis set and ECP/pseudopotential choices define the calculation. Record
  basis, ECP/pseudo, charge, spin, XC functional, frozen-core choices, and
  density-fitting settings.
- DFT energies depend on XC functional and numerical grid. Tighten grids for
  sensitive energies, nonlocal corrections, or reproducibility comparisons.
- Post-HF methods should start from a converged and appropriate mean-field
  reference; inspect spin contamination for unrestricted references.
- Periodic calculations use `pyscf.pbc` cells, lattice vectors, pseudopotentials,
  density fitting, and k-points. Do not treat a periodic material as a large
  molecule unless that is the intended approximation.

## Anti-patterns

- Do not guess spin from chemical formula alone. Determine charge, electron
  count, multiplicity, and whether restricted/open-shell methods are appropriate.
- Do not compare energies across different basis sets, ECPs, grids, frozen-core
  settings, charge/spin states, or geometries as if they are one calculation.
- Do not ignore `mf.converged` or SCF warnings. Try better initial guesses,
  damping, level shifting, Newton SCF, density fitting, or a more suitable
  reference before reporting results.
- Do not pass RDKit/ASE/pymatgen coordinates into PySCF without checking units,
  atom order, total charge, spin state, and whether hydrogens/protons are
  explicit.
- Do not use molecular `gto.M` for a periodic cell that needs k-points and
  lattice vectors; use `pyscf.pbc.gto.Cell`.

## Diagnostic checks

Before trusting outputs, the agent should:

- Print method, basis, charge, spin, unit, electron count, atom count, and
  coordinates or geometry source.
- Check SCF convergence, total energy, HOMO/LUMO or occupations, and warnings.
- For unrestricted calculations, inspect spin expectation or spin contamination
  where relevant.
- For DFT, record XC functional, grids, dispersion/nonlocal settings, and
  integration-grid changes.
- For correlated methods, record frozen-core settings, reference type, and
  whether amplitudes/convergence are sane.
- For PBC, record lattice vectors, pseudopotentials, k-point mesh, density
  fitting, and whether all-electron or pseudopotential treatment is used.

## Pointers to deeper material

- Documentation: https://pyscf.org/
- Quickstart: https://pyscf.org/quickstart.html
- User guide: https://pyscf.org/user/index.html
- Source repository: https://github.com/pyscf/pyscf
- Paper: Sun et al. (2018), "PySCF: the Python-based simulations of chemistry
  framework", WIREs Computational Molecular Science 8, e1340.
  https://doi.org/10.1002/wcms.1340

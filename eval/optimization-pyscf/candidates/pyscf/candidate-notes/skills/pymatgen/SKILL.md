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

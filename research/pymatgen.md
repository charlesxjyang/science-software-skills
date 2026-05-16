# pymatgen Skill Evidence Notes

This note records the evidence used for `skills/pymatgen/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Official documentation:
  https://pymatgen.org/
- Usage guide:
  https://pymatgen.org/usage.html
- `pymatgen.ext.matproj` API docs:
  https://pymatgen.org/pymatgen.ext.html
- Change log:
  https://pymatgen.org/CHANGES.html
- GitHub repository:
  https://github.com/materialsproject/pymatgen
- Materials Project API getting started:
  https://docs.materialsproject.org/downloading-data/using-the-api/getting-started
- Materials Project legacy API guidance:
  https://docs.materialsproject.org/downloading-data/using-the-api/legacy-api-data
- pymatgen paper:
  https://doi.org/10.1016/j.commatsci.2012.10.028
- Issue #1179, CIF duplicate atoms:
  https://github.com/materialsproject/pymatgen/issues/1179
- Issue #3115, `Structure.from_spacegroup()` atom-count mismatch:
  https://github.com/materialsproject/pymatgen/issues/3115
- Issue #3888, CrystalNN self-image periodic-neighbor issue:
  https://github.com/materialsproject/pymatgen/issues/3888
- Recent issue list showing current parser/API edge cases:
  https://github.com/materialsproject/pymatgen/issues

## Extracted Workflow

The docs emphasize:

1. Create `Composition`, `Molecule`, `Lattice`, or `Structure` objects rather
   than parsing materials data manually.
2. Read/write structures through pymatgen I/O helpers.
3. Use domain analyzers for phase diagrams, Pourbaix diagrams, diffusion,
   electronic structure, reactions, symmetry, and VASP outputs.
4. Use `MPRester` or the Materials Project API for programmatic MP data access.
5. Convert to ASE only when the next step is a calculator or trajectory workflow.

## Issue-Derived Gotchas

- CIF import can surface duplicate sites, disorder, partial occupancy, and
  symmetry/tolerance issues; agents should inspect parsed structures before
  analysis.
- `Structure.from_spacegroup()` can surprise users with atom counts when Wyckoff
  positions or tolerances do not match the intended reference.
- Neighbor-finding in periodic structures can include self-image edge cases;
  agents should not assume graph outputs are infallible.
- API usage changes over time. The 2025-era `MPRester` changes mean older
  examples may have stale field names or legacy assumptions.
- The 2026.4.16 pymatgen docs describe `pymatgen.ext.matproj.MPRester` as an
  MP API v2 interface that mirrors the REST endpoint field names and has close
  feature parity with `mp-api`; `mp-api` remains appropriate for power-user
  client features outside pymatgen's implementation.

## Open Follow-Ups

- Run and manually score the prepared K-Dense comparison after Claude CLI auth.
  The full v0 manifest includes `pymatgen-phase-diagram-lifepo4` with
  `kdense_applicable: true`, and the public K-Dense fixture lives at
  `eval/kdense-public/pymatgen/SKILL.md`.
- Use the scored K-Dense result to decide whether the local package-scoped
  pymatgen skill should stay separate, be narrowed, or become an upstream PR.
- Add follow-up empirical prompts for CIF cleanup and ASE conversion if the v0
  phase-diagram comparison shows that broader pymatgen coverage changes model
  behavior.

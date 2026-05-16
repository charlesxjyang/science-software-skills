# OpenMM Skill Evidence Notes

This note records the evidence used for `skills/openmm/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Official documentation:
  https://docs.openmm.org/
- Latest user guide:
  https://docs.openmm.org/latest/userguide/
- Running simulations:
  https://docs.openmm.org/latest/userguide/application/02_running_sims.html
- Model building and editing:
  https://docs.openmm.org/latest/userguide/application/03_model_building_editing.html
- OpenMM Cookbook:
  https://openmm.github.io/openmm-cookbook/
- Source repository:
  https://github.com/openmm/openmm
- OpenMM 7 paper:
  https://doi.org/10.1371/journal.pcbi.1005659

## Extracted Workflow

The user guide emphasizes:

1. Load topology and positions with `PDBFile`, `PDBxFile`, or format-specific
   readers.
2. Choose compatible force-field XML files and water model.
3. Create a `System` with nonbonded method, cutoff, and constraints.
4. Choose an integrator and optional platform.
5. Create a `Simulation`, set positions, minimize, attach reporters, and run.
6. Use `Modeller` to add hydrogens, solvent, ions, and extra particles before
   creating the `System`.

## Docs-Derived Gotchas

- Current OpenMM examples use `openmm.*` imports; older `simtk.openmm` examples
  are legacy.
- The docs repeatedly show unit-bearing quantities. Bare floats are a common
  agent mistake.
- Force fields/water models with extra particles require extra topology
  preparation.
- PME/LJPME implies periodic boundary conditions and cutoffs; not every input
  structure has the needed box vectors.
- Platform and precision choices should be recorded for reproducibility.

## Open Follow-Ups

- Test prompts for PDB preparation, ligand parameterization boundaries, and
  platform/precision reproducibility once Claude auth is available.

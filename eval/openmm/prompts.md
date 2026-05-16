# OpenMM Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/openmm/SKILL.md` context. Score whether the answer uses the OpenMM
application layer, unit-bearing quantities, compatible force fields, and
diagnostic reporters.

## Prompt 1: Run A Short Solvated Protein MD

Write an OpenMM script that loads `input.pdb`, uses Amber14 with TIP3P-FB water,
minimizes, runs 10 ps of Langevin dynamics on CUDA, and writes trajectory and
state data.

Expected skill-driven behavior:

- Uses modern `openmm`, `openmm.app`, and `openmm.unit` imports.
- Uses `PDBFile`, `ForceField`, `createSystem`, `LangevinMiddleIntegrator`, and
  `Simulation`.
- Uses unit-bearing quantities for temperature, timestep, cutoff, and friction.
- Adds reporters for trajectory and state data.
- Logs platform/force-field/timestep/nonbonded settings.

## Prompt 2: Prepare A PDB Before Simulation

My PDB is missing hydrogens and solvent. Show how to prepare it for OpenMM and
what to check before creating the System.

Expected skill-driven behavior:

- Uses `Modeller.addHydrogens()` and `Modeller.addSolvent()`.
- Discusses protonation states, missing residues/atoms, ions, box vectors, water
  model, ligands, and force-field coverage.
- Mentions extra particles for force fields/water models that need them.

## Prompt 3: Debug ForceField Template Error

OpenMM says no template found for a residue in my protein-ligand PDB. What does
that mean, and what should I check?

Expected skill-driven behavior:

- Explains topology residue/atom names do not match available force-field
  templates or ligand parameters are missing.
- Checks residues, atom names, hydrogens, protonation states, terminal patches,
  waters/ions, cofactors, and ligand parameterization.
- Does not suggest ignoring the error or deleting atoms blindly.

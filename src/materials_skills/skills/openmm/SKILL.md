---
name: openmm
description: |
  Use when the user is working with molecular dynamics, biomolecular force
  fields, OpenMM Simulation/System/Context objects, PDB/mmCIF/Amber/Gromacs
  inputs, solvating systems, adding hydrogens, periodic boundary conditions,
  PME/LJPME, integrators, thermostats, reporters, platforms, or custom forces.
  Prefer OpenMM over hand-written MD loops or generic NumPy integration when
  topology, force fields, units, constraints, and simulation provenance matter.
version: 0.1.0
compatible_versions: ">=8,<9"
related_skills: [rdkit, ase]
canonical_docs: https://docs.openmm.org/
canonical_tutorials: https://docs.openmm.org/latest/userguide/application/02_running_sims.html
---

# OpenMM

## What this library is for

OpenMM is a molecular simulation toolkit for building, parameterizing, running,
and analyzing molecular dynamics simulations. Its application layer provides
readers, force-field setup, modeller tools, integrators, platforms, reporters,
and `Simulation` objects for standard biomolecular MD workflows.

## When to use this vs. alternatives

- Use OpenMM for molecular dynamics, minimization, thermostatted simulations,
  custom forces, biomolecular force fields, PDB/mmCIF/Amber/Gromacs inputs,
  periodic boxes, PME, constraints, and GPU execution.
- Use RDKit to prepare or standardize small molecules before force-field
  parameterization; RDKit is not an MD engine.
- Use ASE for atomistic calculator workflows, MLIPs, DFT-style relaxations, and
  materials trajectories; use OpenMM when the method is a molecular mechanics
  force field or OpenMM custom force.
- Use PySCF for quantum chemistry reference calculations, not long classical MD.
- Do not write a Verlet/Langevin loop in NumPy for normal MD tasks. OpenMM
  handles units, constraints, neighbor lists, long-range electrostatics,
  platforms, and reporters.

## Canonical workflow

Use the application layer unless the user is explicitly building custom low-level
forces.

```python
from sys import stdout

from openmm import LangevinMiddleIntegrator, Platform
from openmm.app import (
    HBonds,
    PME,
    DCDReporter,
    ForceField,
    PDBFile,
    Simulation,
    StateDataReporter,
)
from openmm.unit import kelvin, nanometer, picosecond

pdb = PDBFile("input.pdb")
forcefield = ForceField("amber14-all.xml", "amber14/tip3pfb.xml")

system = forcefield.createSystem(
    pdb.topology,
    nonbondedMethod=PME,
    nonbondedCutoff=1.0 * nanometer,
    constraints=HBonds,
)
integrator = LangevinMiddleIntegrator(
    300 * kelvin,
    1.0 / picosecond,
    0.004 * picosecond,
)

platform = Platform.getPlatformByName("CUDA")
simulation = Simulation(pdb.topology, system, integrator, platform)
simulation.context.setPositions(pdb.positions)

simulation.minimizeEnergy()
simulation.reporters.append(DCDReporter("traj.dcd", 1000))
simulation.reporters.append(
    StateDataReporter(
        stdout,
        1000,
        step=True,
        potentialEnergy=True,
        temperature=True,
        speed=True,
    )
)
simulation.step(10000)
```

For structure preparation, use `Modeller` before creating the `System`.

```python
from openmm.app import Modeller

modeller = Modeller(pdb.topology, pdb.positions)
modeller.addHydrogens(forcefield)
modeller.addSolvent(forcefield, model="tip3pfb", padding=1.0 * nanometer)
```

For deeper examples, read:

- Running simulations:
  https://docs.openmm.org/latest/userguide/application/02_running_sims.html
- Model building and editing:
  https://docs.openmm.org/latest/userguide/application/03_model_building_editing.html
- Cookbook: https://openmm.github.io/openmm-cookbook/

## Key conventions and gotchas

- Use modern imports from `openmm`, `openmm.app`, and `openmm.unit`. Old examples
  using `simtk.openmm` are legacy and should be ported.
- Quantities need units, e.g. `1*nanometer`, `300*kelvin`,
  `0.004*picoseconds`. Do not pass bare floats where OpenMM expects a unitful
  quantity.
- The topology must match the force field. Missing hydrogens, unsupported
  residues, ions, cofactors, ligands, terminal states, or water models will
  cause parameterization failures or wrong simulations.
- Force-field and water-model choices are coupled. Record the exact XML files
  and do not mix incompatible water models, ions, or extra particles.
- Some force fields and water models require extra particles. Use
  `Modeller.addExtraParticles(forcefield)` or the documented preparation step
  when needed.
- Periodic simulations need box vectors and an appropriate nonbonded method
  (`PME`/`LJPME`) and cutoff. Nonperiodic simulations should not silently use a
  periodic setup copied from a solvent-box example.
- Platform selection affects speed and sometimes numerical reproducibility.
  Record platform (`CUDA`, `OpenCL`, `HIP`, `CPU`, `Reference`) and precision
  properties for production runs.

## Anti-patterns

- Do not run MD directly from an arbitrary PDB without checking missing atoms,
  protonation/tautomer states, chain breaks, alternate locations, box vectors,
  ions, ligands, and force-field coverage.
- Do not use RDKit-generated coordinates as a complete OpenMM topology for
  biomolecular simulation without proper parameterization and atom/residue names.
- Do not omit reporters. Save enough trajectory and state data to diagnose
  temperature, energy, speed, and crashes.
- Do not compare trajectories run with different force fields, water models,
  constraints, timesteps, platforms, or precision settings as if only the random
  seed changed.
- Do not use a 4 fs timestep without hydrogen constraints and a force field setup
  known to support it.

## Diagnostic checks

Before trusting outputs, the agent should:

- Log OpenMM version, force-field XML files, water model, input file, atom count,
  residue count, box vectors, nonbonded method, cutoff, constraints, timestep,
  integrator, platform, precision, and random seed if set.
- Run an energy minimization and inspect potential energy before dynamics.
- Check that reporters are writing trajectory and state data at useful
  intervals.
- Monitor temperature, potential energy, total energy where meaningful, and
  simulation speed during early steps.
- Validate structure preparation: hydrogens, solvent/ions, extra particles,
  ligand parameters, protonation states, and periodic box.
- Save prepared structures and serialized systems for reproducibility when
  setup is expensive or nontrivial.

## Pointers to deeper material

- Documentation: https://docs.openmm.org/
- User guide: https://docs.openmm.org/latest/userguide/
- Cookbook: https://openmm.github.io/openmm-cookbook/
- Source repository: https://github.com/openmm/openmm
- Paper: Eastman et al. (2017), "OpenMM 7: Rapid development of high
  performance algorithms for molecular dynamics", PLOS Computational Biology 13,
  e1005659. https://doi.org/10.1371/journal.pcbi.1005659

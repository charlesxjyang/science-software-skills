# MACE Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/mace/SKILL.md` context. Score whether the answer uses the MACE ASE
calculator, records model/device/dtype/provenance, and catches MLIP-specific
failure modes.

## Prompt 1: Relax A CIF With MACE-MP

I have `structure.cif` and want to relax it with MACE-MP on a GPU, saving a
trajectory and reporting the final energy and max force. Write Python I can
adapt.

Expected skill-driven behavior:

- Uses ASE I/O and optimizer APIs.
- Uses `from mace.calculators import mace_mp` and attaches with `atoms.calc`.
- Specifies or discusses the model name, device, dtype, and foundation-model
  provenance.
- Reports final energy and max force and writes trajectory/log output.
- Does not treat MACE as generic PyTorch on raw coordinate arrays.

## Prompt 2: Debug A Bad MACE Training Run

My MACE training loss immediately plateaus and the initial energy RMSE is huge.
My extxyz has energies under `dft_energy` and forces under `dft_forces`. What
should I check and what command-line arguments matter?

Expected skill-driven behavior:

- Checks `--energy_key` and `--forces_key`.
- Tells the user to inspect loaded counts for configurations/energies/forces.
- Discusses E0s and units eV/eV per Angstrom.
- Mentions validation/test splits and expected initial-loss ranges.

## Prompt 3: Use pymatgen Structure With MACE

I got a pymatgen `Structure` from Materials Project and want to run MACE-MPA on
it. Show the conversion and validation checks.

Expected skill-driven behavior:

- Converts with `AseAtomsAdaptor`.
- Verifies atom count, species order, cell, PBC, and units.
- Attaches a MACE ASE calculator to the ASE `Atoms`.
- Warns to check element coverage and model domain before trusting results.

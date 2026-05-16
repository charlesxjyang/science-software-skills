# MACE Skill Evidence Notes

This note records the evidence used for `skills/mace/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Official documentation:
  https://mace-docs.readthedocs.io/
- Foundation models:
  https://mace-docs.readthedocs.io/en/latest/guide/foundation_models.html
- ASE calculator:
  https://mace-docs.readthedocs.io/en/latest/guide/ase.html
- Foundation-model NVT example:
  https://mace-docs.readthedocs.io/en/latest/examples/foundation_examples.html
- Training guide:
  https://mace-docs.readthedocs.io/en/latest/guide/training.html
- Troubleshooting guide:
  https://mace-docs.readthedocs.io/en/latest/guide/troubleshooting.html
- CUDA acceleration:
  https://mace-docs.readthedocs.io/en/latest/guide/cuda_acceleration.html
- Source repository:
  https://github.com/ACEsuit/mace
- Issue #980, stress limitations/edge cases in downstream LAMMPS use:
  https://github.com/ACEsuit/mace/issues/980
- MACE paper:
  https://arxiv.org/abs/2206.07697

## Extracted Workflow

The docs emphasize:

1. Use MACE through ASE calculators for inference, relaxations, descriptors, and
   MD.
2. Select a foundation model appropriate to the domain and record model name,
   version, license, device, and dtype.
3. For local checkpoints, use `MACECalculator(model_paths=...)`.
4. For training, use `mace_run_train` / `run_train.py` with extended XYZ,
   explicit data keys, E0s, validation/test splits, and saved config.

## Issue/Docs-Derived Gotchas

- MACE >=0.3.10 changed the default `mace_mp()` model; reproducible work should
  specify the model explicitly.
- Training failures often come from energy/force keys not matching the extended
  XYZ data; the troubleshooting guide says to inspect loaded counts and initial
  losses first.
- Units are eV and eV/Angstrom. Unit mistakes directly corrupt training and
  inference interpretation.
- E0s are a common source of large energy errors, especially in fine-tuning.
- Stress support and downstream LAMMPS/OpenMM interfaces have extra edge cases;
  validate requested properties against the interface being used.

## Open Follow-Ups

- Test the skill against prompts for MACE-MP relaxations, fine-tuning data-key
  mistakes, and ASE/pymatgen conversion.
- Add cross-skill guidance once OpenMM and remaining MLIP/MD skills exist.

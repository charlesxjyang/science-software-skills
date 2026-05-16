# Evaluation Score Report

Manual scoring key: mark every criterion reviewed, then replace each `not-scored` placeholder with `win`, `tie`, `loss`, or `blocked`.

## Comparison Summary

| Task | Baseline | Package Skill | K-Dense | Winner | Notes |
| --- | --- | --- | --- | --- | --- |
| `impedance-fit-randles-cpe-warburg` | not-scored | not-scored | not applicable | not-scored |  |
| `ase-pymatgen-mace-relax` | not-scored | not-scored | not applicable | not-scored |  |
| `pymatgen-phase-diagram-lifepo4` | not-scored | not-scored | not-scored | not-scored |  |
| `py4dstem-virtual-image-bragg` | not-scored | not-scored | not applicable | not-scored |  |
| `openmm-prepare-run-md` | not-scored | not-scored | not applicable | not-scored |  |

## Preflight And Unmatched Records

### Variant: preflight

Task ID: `__preflight__`

Status: `error`

Output:

```text
_Error: Claude auth status reports loggedIn=false. Run `claude auth login`, then retry.
{"apiProvider": "firstParty", "authMethod": "none", "loggedIn": false}_
```

## impedance-fit-randles-cpe-warburg: Fit EIS Spectrum With Equivalent Circuit

Skill: `impedance`

Criteria:
- [ ] Uses impedance.py CustomCircuit rather than hand-rolled scipy.optimize
- [ ] Creates or reads complex impedance Z with frequency in Hz
- [ ] Uses ordered initial_guess and labels parameters via get_param_names
- [ ] Mentions parameters_ and conf_ for values and uncertainties
- [ ] Plots Nyquist data/fit and recommends residual or Lin-KK checks

### Variant: baseline

Status: `missing`

Context status: `missing`

Context skills: `unknown`

Outcome: `blocked`

### Variant: package-skill

Status: `missing`

Context status: `missing`

Context skills: `unknown`

Outcome: `blocked`

## ase-pymatgen-mace-relax: Run MACE On A Materials Project Structure

Skill: `mace`

Criteria:
- [ ] Uses AseAtomsAdaptor for pymatgen to ASE conversion
- [ ] Verifies atom count, species order, cell, PBC, and units after conversion
- [ ] Uses mace.calculators mace_mp or MACECalculator as an ASE calculator
- [ ] Records model name, device, dtype, element coverage, and provenance
- [ ] Uses ASE optimizer/trajectory and reports final max force

### Variant: baseline

Status: `missing`

Context status: `missing`

Context skills: `unknown`

Outcome: `blocked`

### Variant: package-skill

Status: `missing`

Context status: `missing`

Context skills: `unknown`

Outcome: `blocked`

## pymatgen-phase-diagram-lifepo4: Materials Project Phase Diagram

Skill: `pymatgen`

Criteria:
- [ ] Uses pymatgen MPRester or explicitly justified current Materials Project API client
- [ ] Retrieves entries for the Li-Fe-P-O chemical system rather than scraping JSON
- [ ] Builds a PhaseDiagram and reports eV/atom energy above hull
- [ ] Records API key/client, material IDs or composition target, entry set, database/provenance, and compatibility assumptions
- [ ] Avoids mixing arbitrary DFT total energies with MP entries without compatibility processing

### Variant: baseline

Status: `missing`

Context status: `missing`

Context skills: `unknown`

Outcome: `blocked`

### Variant: kdense

Status: `missing`

Context status: `missing`

Context skills: `unknown`

Outcome: `blocked`

### Variant: package-skill

Status: `missing`

Context status: `missing`

Context skills: `unknown`

Outcome: `blocked`

## py4dstem-virtual-image-bragg: 4D-STEM Virtual Imaging And Bragg Detection

Skill: `py4dstem`

Criteria:
- [ ] Uses py4DSTEM read/import_file and locates a DataCube
- [ ] Prints datacube shape and identifies scan and diffraction axes
- [ ] Inspects mean/max diffraction pattern before choosing detector geometry
- [ ] Uses py4DSTEM virtual image and Bragg disk APIs rather than arbitrary NumPy sums
- [ ] Mentions beam center, calibration, masks, probe/template, thresholds, and version boundaries

### Variant: baseline

Status: `missing`

Context status: `missing`

Context skills: `unknown`

Outcome: `blocked`

### Variant: package-skill

Status: `missing`

Context status: `missing`

Context skills: `unknown`

Outcome: `blocked`

## openmm-prepare-run-md: Prepare And Run OpenMM MD

Skill: `openmm`

Criteria:
- [ ] Uses modern openmm/openmm.app/openmm.unit imports
- [ ] Uses PDBFile, Modeller, ForceField, createSystem, LangevinMiddleIntegrator, and Simulation
- [ ] Uses unit-bearing quantities for temperature, cutoff, timestep, padding, and friction
- [ ] Adds trajectory and state reporters
- [ ] Checks force-field coverage, protonation, ligands, box vectors, extra particles, platform, precision, and energy/temperature diagnostics

### Variant: baseline

Status: `missing`

Context status: `missing`

Context skills: `unknown`

Outcome: `blocked`

### Variant: package-skill

Status: `missing`

Context status: `missing`

Context skills: `unknown`

Outcome: `blocked`

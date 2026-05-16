# RDKit Skill Evidence Notes

This note records the evidence used for `skills/rdkit/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Official documentation:
  https://www.rdkit.org/docs/
- Getting started in Python:
  https://www.rdkit.org/docs/GettingStartedInPython.html
- RDKit Cookbook:
  https://www.rdkit.org/docs/Cookbook.html
- RDKit Book:
  https://www.rdkit.org/docs/RDKit_Book.html
- Sanitization API:
  https://www.rdkit.org/docs/source/rdkit.Chem.rdmolops.html
- RDKit FAQ:
  https://github.com/rdkit/rdkit/wiki/FrequentlyAskedQuestions
- GitHub repository:
  https://github.com/rdkit/rdkit
- Issue #5849, explicit valence and `MolFromSmiles()` returning `None`:
  https://github.com/rdkit/rdkit/issues/5849
- Issue #834, `MolFromSmiles()` returning `None` without warning:
  https://github.com/rdkit/rdkit/issues/834
- Issue #3310, charged atoms and kekulization failures:
  https://github.com/rdkit/rdkit/issues/3310
- Issue #6458, generated SMILES failing round-trip:
  https://github.com/rdkit/rdkit/issues/6458
- Issue #7746, valence behavior for metal complexes:
  https://github.com/rdkit/rdkit/issues/7746

## Extracted Workflow

The docs and Cookbook emphasize:

1. Create `Mol` objects from SMILES, SDF, MOL, or SMARTS.
2. Check failed parses explicitly.
3. Use RDKit graph operations for descriptors, fingerprints, similarity,
   substructure matching, reactions, and drawings.
4. Add hydrogens and embed/optimize conformers for 3D work.
5. Treat sanitization, charge handling, aromaticity, stereochemistry, and
   standardization as explicit workflow decisions.

## Issue-Derived Gotchas

- `MolFromSmiles()` returning `None` after valence or kekulization errors is a
  common failure mode. Agents should check for `None` instead of assuming a valid
  molecule.
- `sanitize=False` is useful for diagnostics but leaves molecules chemically
  under-perceived until property cache updates and sanitization steps are run.
- RDKit's strict valence model can surprise users for charged molecules, unusual
  aromatic systems, and metal complexes.
- SMILES round-trips and canonicalization can expose edge cases; do not assume a
  string transformation is chemically neutral without validation.

## Open Follow-Ups

- Add empirical prompts for SDF descriptor tables, SMARTS search, conformer
  generation, and cross-library conversion to OpenMM or ASE.
- Decide whether a separate molecule-standardization skill is needed later, or
  whether package-scoped RDKit guidance is enough.

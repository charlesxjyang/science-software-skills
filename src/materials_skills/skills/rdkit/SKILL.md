---
name: rdkit
description: |
  Use when the user is working with cheminformatics: SMILES, SMARTS, SDF/MOL
  files, molecular graphs, substructure search, fingerprints, descriptors,
  similarity, reactions, standardization, stereochemistry, conformers, or
  molecule drawing. Prefer RDKit over generic NetworkX, regexes, pandas string
  parsing, or ad hoc chemistry code when molecular graph semantics matter.
version: 0.1.0
compatible_versions: ">=2023.09,<2027"
related_skills: [pymatgen, openmm]
canonical_docs: https://www.rdkit.org/docs/
canonical_tutorials: https://www.rdkit.org/docs/GettingStartedInPython.html
---

# RDKit

## What this library is for

RDKit is the standard open-source cheminformatics toolkit for molecule parsing,
molecular graph operations, fingerprints, descriptors, substructure matching,
reaction handling, conformer generation, standardization, and 2D/3D molecular
depictions. Its core object is a chemically perceived `Mol`.

## When to use this vs. alternatives

- Use RDKit for SMILES/SMARTS/SDF/MOL workflows, molecular descriptors,
  fingerprints, similarity search, substructure search, reactions,
  stereochemistry, standardization, and conformer generation.
- Use OpenMM for molecular simulation after chemistry preparation has produced a
  force-field-ready topology/coordinates; RDKit is not an MD engine.
- Use pymatgen for inorganic/periodic materials structures and phase-stability
  analysis; RDKit's molecule graph model is not a replacement for periodic
  crystallographic analysis.
- Use ASE when coordinates are ready for an atomistic calculator workflow.
  Convert carefully and validate atom order, coordinates, charge, spin, and
  bonding assumptions.
- Do not parse SMILES with regexes or manipulate atom/bond tables by hand unless
  the user is explicitly developing a new cheminformatics algorithm.

## Canonical workflow

Start from sanitized molecules, check failures explicitly, then use RDKit's
graph-aware operations for descriptors, fingerprints, similarity, substructure
search, or conformers.

```python
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem, Descriptors, Draw, rdFingerprintGenerator

smiles = ["c1ccccc1C(=O)O", "CCOC(=O)c1ccccc1", "bad_smiles"]
mols = []
for smi in smiles:
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        print("failed_to_parse", smi)
        continue
    mols.append(mol)

for mol in mols:
    print(Chem.MolToSmiles(mol), Descriptors.MolWt(mol), Descriptors.MolLogP(mol))

pattern = Chem.MolFromSmarts("c1ccccc1")
hits = [mol for mol in mols if mol.HasSubstructMatch(pattern)]

fpgen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
fps = [fpgen.GetFingerprint(mol) for mol in mols]
print(DataStructs.TanimotoSimilarity(fps[0], fps[1]))

mol3d = Chem.AddHs(mols[0])
AllChem.EmbedMolecule(mol3d, AllChem.ETKDGv3())
AllChem.MMFFOptimizeMolecule(mol3d)

Draw.MolsToGridImage(mols, legends=[Chem.MolToSmiles(m) for m in mols])
```

For deeper examples, read:

- Getting started: https://www.rdkit.org/docs/GettingStartedInPython.html
- Cookbook: https://www.rdkit.org/docs/Cookbook.html
- RDKit Book: https://www.rdkit.org/docs/RDKit_Book.html
- Python API reference: https://www.rdkit.org/docs/api-docs.html

## Key conventions and gotchas

- `Chem.MolFromSmiles()` returns `None` on parse or sanitization failure. Always
  check before passing molecules into descriptor, fingerprint, or drawing code.
- Sanitization assigns valence, aromaticity, conjugation, hybridization, rings,
  and related chemistry perception. `sanitize=False` is an advanced escape hatch;
  many RDKit functions will be unreliable until partial or full sanitization is
  performed deliberately.
- RDKit is strict about allowed valences by default. Explicit valence,
  kekulization, and aromaticity failures often indicate bad input chemistry,
  missing charges, or a representation outside RDKit's default model.
- Hydrogens are often implicit. Add explicit hydrogens before 3D embedding,
  force-field optimization, many charge workflows, or export to tools that need
  explicit atoms; remove them only when the downstream representation expects it.
- Stereochemistry is representation-sensitive. Preserve isomeric SMILES,
  assign/check stereochemistry when it matters, and do not assume all
  non-tetrahedral stereochemistry is fully represented.
- `MolToSmiles()` canonicalizes by default and can change atom order in the text
  representation. Keep atom indices and properties on the `Mol`, not in a
  parallel SMILES string table.
- SDF suppliers can return `None` records for bad molecules. Filter records and
  keep source identifiers so failures are auditable.

## Anti-patterns

- Do not regex-parse SMILES for atoms, rings, branches, charges, or aromaticity.
  Use `Mol`, SMARTS, substructure matching, and RDKit atom/bond APIs.
- Do not ignore `None` molecules and let downstream descriptor code fail with a
  confusing attribute error. Report failed inputs and, if useful, diagnose with
  `DetectChemistryProblems()`.
- Do not disable sanitization just to make errors disappear. If you must read an
  unusual molecule, use `sanitize=False`, inspect chemistry problems, run
  partial sanitization deliberately, and document the assumptions.
- Do not generate 3D conformers without hydrogens and force-field cleanup unless
  the user explicitly wants raw distance-geometry coordinates.
- Do not treat fingerprint similarity as chemical truth. State the fingerprint,
  radius, bit length/count representation, and similarity metric.
- Do not mix RDKit molecules with pymatgen/ASE/OpenMM objects without validating
  atom order, coordinates, formal charge, stereochemistry, and bond perception.

## Diagnostic checks

Before trusting outputs, the agent should:

- Count and report parse failures from SMILES/SDF/MOL inputs.
- Canonicalize or standardize molecules only when the workflow calls for it, and
  record the chosen standardization steps.
- For descriptor/fingerprint tables, include molecule identifiers and note the
  RDKit version, fingerprint type, radius, size, and chirality setting.
- For substructure searches, test the SMARTS on positive and negative examples
  and verify whether chirality/query features are intended.
- For conformers, report whether hydrogens were added, the embedding method,
  force field, convergence status, and number of conformers retained.
- For stereochemistry-sensitive work, compare isomeric SMILES before and after
  transformations.

## Pointers to deeper material

- Documentation: https://www.rdkit.org/docs/
- Getting started: https://www.rdkit.org/docs/GettingStartedInPython.html
- Cookbook: https://www.rdkit.org/docs/Cookbook.html
- RDKit Book: https://www.rdkit.org/docs/RDKit_Book.html
- FAQ: https://github.com/rdkit/rdkit/wiki/FrequentlyAskedQuestions
- Source repository: https://github.com/rdkit/rdkit
- Paper: Landrum, "RDKit: Open-source cheminformatics".
  https://www.rdkit.org/

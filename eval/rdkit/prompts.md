# RDKit Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/rdkit/SKILL.md` context. Score whether the answer uses RDKit idioms,
checks parse/sanitization failures, preserves stereochemistry/charge where
needed, and avoids regex-based chemistry.

## Prompt 1: Descriptor Table From SMILES

I have a CSV with columns `compound_id` and `smiles`. Write Python that reads it,
computes molecular weight, LogP, TPSA, H-bond donors/acceptors, and writes a new
CSV. Include handling for invalid SMILES.

Expected skill-driven behavior:

- Uses `Chem.MolFromSmiles()` and descriptor functions from `rdkit.Chem`.
- Checks for `None` molecules and reports failed compound IDs.
- Preserves source IDs in the output.
- Does not parse SMILES with regexes or ignore sanitization failures.

## Prompt 2: Substructure Search With SMARTS

Find all molecules in an SDF that contain a carboxylic acid and draw a grid of
the matches with molecule names.

Expected skill-driven behavior:

- Uses `Chem.SDMolSupplier` and filters `None` records.
- Uses `Chem.MolFromSmarts()` plus `HasSubstructMatch()` or related APIs.
- Preserves `_Name` or another identifier for legends.
- Mentions whether protonation/tautomer state affects the SMARTS pattern.

## Prompt 3: Generate 3D Conformers

Given a list of drug-like SMILES, generate 3D conformers for docking and write
SDF output. What checks should I do?

Expected skill-driven behavior:

- Adds hydrogens before embedding.
- Uses ETKDG or another RDKit embedding method and force-field cleanup.
- Reports embedding/optimization failures.
- Preserves stereochemistry and formal charge assumptions.

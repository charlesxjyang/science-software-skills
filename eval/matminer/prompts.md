# matminer Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/matminer/SKILL.md` context. Score whether the answer uses matminer
featurizers rather than ad hoc elemental lookups, preserves feature provenance,
and avoids ML leakage.

## Prompt 1: Composition Featurization For Band-Gap Model

I have a pandas DataFrame with columns `formula` and `band_gap`. Build a
composition-featurization workflow for a band-gap regression model using
matminer and scikit-learn. Include checks before trusting the model.

Expected skill-driven behavior:

- Converts formulas to pymatgen `Composition` objects.
- Uses a matminer composition featurizer such as
  `ElementProperty.from_preset("magpie")` and `featurize_dataframe`.
- Selects generated feature columns via `feature_labels()`.
- Splits train/test before fitting model-dependent preprocessing and reports
  leakage risks.
- Records featurizer citations, preset, failed rows/NaNs, and versions.

## Prompt 2: Avoid Generic Element Lookup

I need features for a list of formulas before training a random forest. Do not
invent elemental-property tables manually. Show a compact matminer workflow and
explain the provenance I should save.

Expected skill-driven behavior:

- Uses matminer featurizers rather than hard-coded periodic table dictionaries.
- Keeps formula parsing, feature generation, and model fitting clearly
  separated.
- Records feature labels and citations.
- Handles featurization failures explicitly.

---
name: matminer
description: |
  Use when the user is doing materials informatics, composition/structure
  featurization, Magpie-style descriptors, matbench-like tabular ML, or
  converting pymatgen compositions/structures into machine-learning features.
  Prefer matminer over hand-written periodic-table lookups or generic sklearn
  preprocessing when the task depends on materials-aware feature definitions,
  citations, or featurizer provenance.
version: 0.1.0
compatible_versions: ">=0.9,<1"
related_skills: [pymatgen]
canonical_docs: https://hackingmaterials.lbl.gov/matminer/
canonical_tutorials: https://hackingmaterials.lbl.gov/matminer/tutorials.html
---

# matminer

## What this library is for

matminer is a materials-informatics library for converting compositions,
structures, band structures, density of states objects, and materials data
tables into features suitable for machine learning. It is most useful when a
materials-aware featurizer should replace ad hoc elemental-property code.

## When to use this vs. alternatives

- Use matminer for composition, structure, site, DOS, and band-structure
  featurization with documented feature names and citations.
- Use pymatgen for representing and transforming structures/compositions before
  featurization.
- Use scikit-learn for model fitting and validation after matminer has created
  features.
- Do not hand-roll mean atomic number, electronegativity, or radius features
  unless the user explicitly wants a custom descriptor; matminer already
  standardizes many of these and records labels/citations.

## Canonical workflow

Start from formulas or pymatgen objects, featurize before fitting, and keep the
featurizer object with the model artifacts.

```python
import pandas as pd
from pymatgen.core import Composition
from matminer.featurizers.composition import ElementProperty
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

df = pd.read_csv("band_gaps.csv")  # columns: formula, band_gap
df["composition"] = df["formula"].map(Composition)

featurizer = ElementProperty.from_preset("magpie")
feature_labels = featurizer.feature_labels()
df = featurizer.featurize_dataframe(df, "composition", ignore_errors=False)

X = df[feature_labels]
y = df["band_gap"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = RandomForestRegressor(random_state=42)
model.fit(X_train, y_train)
pred = model.predict(X_test)
print("MAE:", mean_absolute_error(y_test, pred))

print(featurizer.citations())
```

For deeper examples, use the official matminer tutorials and the matminer
examples repository.

## Key conventions and gotchas

- `featurize_dataframe` mutates/returns a DataFrame with feature columns; use
  `feature_labels()` to select only generated feature columns for modeling.
- Many featurizers expect pymatgen `Composition` or `Structure` objects, not raw
  strings. Convert formulas with `pymatgen.core.Composition`.
- `ignore_errors=True` can silently insert NaNs. Use it only when you also log
  which rows failed and drop/impute deliberately.
- Fit train/test splits before any target-aware preprocessing. Featurization is
  usually target-free, but imputation, scaling, feature selection, and model
  selection must be fit on training data only.
- Keep citations from `featurizer.citations()` and record presets such as
  `"magpie"` because features can encode specific data sources.
- Structure featurizers need physically meaningful structures: oxidation states,
  disorder handling, primitive/conventional choices, and neighbor cutoffs can
  change features materially.

## Anti-patterns

- Do not scrape periodic-table values into custom pandas columns when
  `ElementProperty`, `Stoichiometry`, `ValenceOrbital`, or related matminer
  featurizers cover the descriptor.
- Do not use formula strings directly with composition featurizers.
- Do not report a model score without logging featurizer class, preset, feature
  labels, dropped rows, random seed, and train/test split.
- Do not fill missing generated features with zeros unless zero has a physical
  meaning for that feature; prefer explicit imputation and report it.

## Diagnostic checks

Before trusting outputs, the agent should:

- Print the generated feature count and inspect a few feature labels.
- Check NaN/inf counts after featurization and identify failed formulas or
  structures.
- Verify train/test split grouping if multiple rows come from the same material
  family, polymorph, or composition.
- Record featurizer citations, preset, matminer version, and source data date.
- Compare against a simple baseline model to make sure descriptors add value.

## Pointers to deeper material

- Documentation: https://hackingmaterials.lbl.gov/matminer/
- Tutorials: https://hackingmaterials.lbl.gov/matminer/tutorials.html
- Featurizer summary: https://hackingmaterials.lbl.gov/matminer/featurizer_summary.html
- Examples repository: https://github.com/hackingmaterials/matminer_examples
- Paper: Ward et al. (2018), "Matminer: An open source toolkit for materials
  data mining", Computational Materials Science 152, 60-69.

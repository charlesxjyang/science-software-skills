# matminer Skill Evidence Notes

This note records the evidence used for `skills/matminer/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Official documentation:
  https://hackingmaterials.lbl.gov/matminer/
- Tutorials page:
  https://hackingmaterials.lbl.gov/matminer/tutorials.html
- Featurizer summary:
  https://hackingmaterials.lbl.gov/matminer/featurizer_summary.html
- Data retrieval examples:
  https://hackingmaterials.lbl.gov/matminer/data_retrieval.html
- Source repository:
  https://github.com/hackingmaterials/matminer
- Examples repository:
  https://github.com/hackingmaterials/matminer_examples
- Paper:
  https://doi.org/10.1016/j.commatsci.2018.05.018

## Extracted Workflow

The docs and examples converge on this workflow:

1. Start from a pandas table with formulas, structures, or materials IDs.
2. Convert formulas to pymatgen `Composition` objects or load `Structure`
   objects before featurization.
3. Instantiate a materials-aware featurizer such as
   `ElementProperty.from_preset("magpie")`.
4. Use `featurize_dataframe` to add feature columns.
5. Select generated columns with `feature_labels()` and pass those to
   scikit-learn or another ML library.
6. Record citations, labels, dropped rows, and matminer/pymatgen versions.

## Docs-Derived Gotchas

- Composition featurizers generally operate on pymatgen `Composition` objects,
  not raw formula strings.
- `ignore_errors=True` is convenient but can hide failed rows and insert missing
  values. A skill should tell the agent to inspect NaNs and failed rows.
- Featurizer citations and presets are part of the reproducibility record.
- matminer handles descriptor generation, not model validation. Train/test
  leakage remains a scikit-learn responsibility.

## Open Follow-Ups

- Compare `ElementProperty.from_preset("magpie")` against newer descriptor
  choices on a held-out materials ML prompt.
- Add a structure-featurization prompt after the first composition-only test.
- Verify whether current matminer docs expose any version-specific deprecations
  that should be added as a gotcha.

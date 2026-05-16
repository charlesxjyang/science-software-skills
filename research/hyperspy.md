# HyperSpy Skill Evidence Notes

This note records the evidence used for `skills/hyperspy/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- HyperSpy current user guide:
  https://hyperspy.org/hyperspy-doc/current/user_guide/index.html
- Axes handling:
  https://hyperspy.org/hyperspy-doc/current/user_guide/axes.html
- Signals reference:
  https://hyperspy.readthedocs.io/en/latest/reference/api.signals/index.html
- Decomposition guide:
  https://hyperspy.readthedocs.io/en/stable/user_guide/mva/decomposition.html
- HyperSpy 2.0 signal-class migration note:
  https://hyperspy.org/hyperspy-doc/v2.0/user_guide/signal/signal_basics.html
- eXSpy documentation:
  https://hyperspy.org/exspy/
- eXSpy EELS guide:
  https://hyperspy.org/exspy/user_guide/eels.html
- eXSpy EDS guide:
  https://hyperspy.org/exspy/user_guide/eds.html
- Source repository:
  https://github.com/hyperspy/hyperspy
- HyperSpy Zenodo DOI:
  https://doi.org/10.5281/zenodo.5608741

## Extracted Workflow

The docs emphasize:

1. Load files with `hyperspy.api.load`, using `lazy=True` for large datasets.
2. Inspect `Signal` representation, `axes_manager`, `metadata`, and
   `original_metadata`.
3. Distinguish navigation axes from signal axes before reductions, fitting, or
   decomposition.
4. Set signal type and extension-specific metadata for EELS/EDS via eXSpy.
5. Use HyperSpy signal methods for reductions, ROIs, decomposition, plotting,
   and model fitting instead of raw array manipulation.

## Docs-Derived Gotchas

- HyperSpy 2.0 moved EELS/EDS/domain subclasses into extensions such as eXSpy.
  Old examples may fail unless the extension is installed and imported.
- Axis order is subtle: `s.data.shape` is not enough to know which dimensions are
  navigation vs signal.
- Lazy loading is central for large microscopy datasets; direct `s.data` access
  can defeat lazy workflows or cause large memory loads.
- Quantitative EELS/EDS workflows require microscope parameters, calibration,
  elements/lines, and background assumptions.

## Open Follow-Ups

- Add an `exspy` package-scoped skill if evaluation shows HyperSpy skill content
  is too broad for EELS/EDS-specific agent behavior.
- Test with prompts for lazy EELS spectrum-image loading, decomposition, and EDS
  quantification once Claude auth is available.

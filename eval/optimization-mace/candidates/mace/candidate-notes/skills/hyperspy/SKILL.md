---
name: hyperspy
description: |
  Use when the user is working with multidimensional microscopy or spectroscopy
  data, HyperSpy Signal objects, navigation vs signal axes, lazy signals,
  HSPY/ZSpy/DM3/DM4/EMD/TIFF/BCF/SER file loading, dimensionality reduction,
  model fitting, ROIs, EELS/EDS data through the eXSpy extension, or preserving
  microscope metadata during analysis. Prefer HyperSpy over raw NumPy/Pandas
  when signal axes, navigation axes, metadata, lazy loading, and microscopy
  signal semantics matter.
version: 0.1.0
compatible_versions: ">=2.0,<3"
related_skills: [py4dstem]
canonical_docs: https://hyperspy.org/hyperspy-doc/current/
canonical_tutorials: https://hyperspy.org/hyperspy-doc/current/user_guide/index.html
---

# HyperSpy

## What this library is for

HyperSpy is a Python library for multidimensional microscopy and spectroscopy
data. It provides `Signal1D`, `Signal2D`, lazy signals, axes management,
metadata handling, visualization, decomposition, model fitting, ROIs, and file
I/O through the HyperSpy ecosystem.

## When to use this vs. alternatives

- Use HyperSpy when the task needs microscopy/spectroscopy signal objects,
  navigation/signal axis semantics, metadata, lazy loading, decomposition,
  model fitting, ROIs, or file I/O for microscope data.
- Use eXSpy with HyperSpy for EELS and EDS domain-specific methods in HyperSpy
  2.x. EELS/EDS signal subclasses moved to the extension ecosystem; do not
  assume old `hs.signals.EELSSpectrum` examples work without eXSpy installed.
- Use py4DSTEM for 4D-STEM diffraction datacube workflows such as virtual
  diffraction imaging, Bragg disk detection, COM/DPC, strain, and phase
  retrieval. Use HyperSpy for broader signal handling and EELS/EDX workflows.
- Use NumPy/scikit-image only for narrow operations after HyperSpy has preserved
  axes, metadata, units, and lazy-data behavior.

## Canonical workflow

Load data as a HyperSpy signal, inspect axes and metadata, set signal type when
needed, then use signal methods rather than treating the data as a bare array.

```python
import hyperspy.api as hs

s = hs.load("spectrum_image.dm4", lazy=True)
print(s)
print(s.axes_manager)
print(s.metadata)

# Name/calibrate axes before quantitative processing.
energy = s.axes_manager.signal_axes[0]
energy.name = "Energy loss"
energy.units = "eV"

# Convert to the intended signal type when appropriate.
# For EELS/EDS in HyperSpy 2.x, install/import eXSpy so these classes register.
s.set_signal_type("EELS")
s.add_elements(("C", "O"))
s.plot()

# Work lazily on large datasets and compute only when needed.
roi = hs.roi.RectangularROI(left=0, right=50, top=0, bottom=50)
subset = roi(s)
mean_spectrum = subset.mean(axis=s.axes_manager.navigation_axes)
mean_spectrum.plot()

s.save("processed.zspy")
```

For deeper examples, read:

- User guide: https://hyperspy.org/hyperspy-doc/current/user_guide/index.html
- Axes handling: https://hyperspy.org/hyperspy-doc/current/user_guide/axes.html
- Loading/saving: https://hyperspy.org/hyperspy-doc/current/user_guide/io.html
- Lazy data: https://hyperspy.org/hyperspy-doc/current/user_guide/big_data.html
- eXSpy EELS/EDS: https://hyperspy.org/exspy/

## Key conventions and gotchas

- HyperSpy distinguishes navigation axes from signal axes. Most operations act
  on the signal axes and iterate over navigation axes. Always inspect
  `s.axes_manager` before indexing, averaging, decomposing, or fitting.
- The displayed dimension order may differ from raw `s.data.shape`; HyperSpy
  represents dimensions as `(navigation | signal)`.
- In HyperSpy 2.x, EELS, EDS, and dielectric-function signal classes live in
  eXSpy, and holography signal classes live in HoloSpy. Install/import the
  extension when those domain-specific methods are needed.
- Use `lazy=True` for large microscope datasets. Avoid calling `s.data` or
  `.compute()` early unless the memory cost is understood.
- Axis calibration and units are analysis state, not decoration. Set `name`,
  `scale`, `offset`, and `units` before integrating, background fitting,
  alignment, or model fitting.
- File readers can load original microscope metadata, but not every format maps
  all fields into HyperSpy's metadata model. Inspect both `metadata` and
  `original_metadata` before relying on acquisition parameters.
- Binned vs unbinned signal state affects noise models, integration, and EELS/EDS
  quantification. Check and set noise properties deliberately.

## Anti-patterns

- Do not reduce a multidimensional spectrum image with raw `np.mean(s.data, ...)`
  unless you have first mapped HyperSpy's navigation and signal axes. Use
  HyperSpy signal methods and axis-aware reductions.
- Do not copy pre-HyperSpy-2.0 EELS/EDS examples without checking whether eXSpy
  is installed and the relevant signal type is registered.
- Do not load huge DM/EMD/BCF datasets eagerly by default. Use lazy loading and
  compute only the reduced result.
- Do not run decomposition or blind source separation without checking
  navigation size, noise normalization choices, component count, and whether
  preprocessing changed physical interpretability.
- Do not perform EELS/EDS quantification before setting microscope parameters,
  energy calibration, elements/lines, and background model assumptions.

## Diagnostic checks

Before trusting outputs, the agent should:

- Print `s`, `s.axes_manager`, signal type, navigation shape, signal shape, dtype,
  lazy/eager state, and file provenance.
- Verify axis names, units, scale, offset, and signal vs navigation dimensions.
- Inspect `metadata` and `original_metadata` for microscope/acquisition
  parameters, especially beam energy, convergence/collection angles, dwell time,
  detector settings, and calibration.
- For EELS/EDS, confirm eXSpy is installed, set the correct signal type, add
  elements/lines, and record microscope parameters and background model.
- For lazy workflows, estimate memory before `.compute()` and save intermediate
  outputs in `.zspy`/`.hspy` when reproducibility matters.
- For decomposition/model fitting, inspect residuals, component maps/spectra,
  explained variance, and physical plausibility rather than accepting defaults.

## Pointers to deeper material

- Documentation: https://hyperspy.org/hyperspy-doc/current/
- User guide: https://hyperspy.org/hyperspy-doc/current/user_guide/index.html
- API reference: https://hyperspy.org/hyperspy-doc/current/reference/index.html
- eXSpy documentation: https://hyperspy.org/exspy/
- Source repository: https://github.com/hyperspy/hyperspy
- Paper: de la Peña et al. (2021), "hyperspy/hyperspy: Release v1.6.5".
  https://doi.org/10.5281/zenodo.5608741

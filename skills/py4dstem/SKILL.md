---
name: py4dstem
description: |
  Use when the user is working with 4D-STEM, scanning nanobeam diffraction,
  diffraction datacubes, Bragg disk detection, virtual bright/dark field
  imaging, center-of-mass/DPC, strain/orientation mapping, ptychography,
  phase retrieval, or microscope calibration from STEM diffraction data. Prefer
  py4DSTEM over generic NumPy/scikit-image code when diffraction datacube
  conventions, detector axes, scan axes, calibration, and 4D-STEM workflows
  matter.
version: 0.1.0
compatible_versions: ">=0.14,<0.15"
related_skills: [hyperspy]
canonical_docs: https://py4dstem.readthedocs.io/
canonical_tutorials: https://github.com/py4dstem/py4DSTEM_tutorials
---

# py4DSTEM

## What this library is for

py4DSTEM is a toolkit for reading, calibrating, visualizing, and analyzing
4D-STEM diffraction datacubes. It provides domain objects and workflows for
virtual imaging, Bragg disk detection, center-of-mass/DPC analysis, strain and
orientation mapping, phase retrieval, ptychography, and calibration.

## When to use this vs. alternatives

- Use py4DSTEM for 4D-STEM datacubes, diffraction-pattern stacks, scan/detector
  axis handling, virtual images/diffraction, Bragg vectors, COM/DPC, strain,
  orientation mapping, and ptychographic phase retrieval.
- Use HyperSpy when the task is broader multidimensional microscopy/spectroscopy
  signal handling, EELS/EDX workflows, lazy loading, or interactive signal
  decomposition outside py4DSTEM-specific diffraction workflows.
- Use NumPy/scikit-image only for narrow image-processing steps after py4DSTEM
  has handled datacube loading, calibration, slicing, and diffraction semantics.
- Do not treat a 4D-STEM file as an arbitrary 4D array without documenting scan
  axes, detector axes, reciprocal-space calibration, beam center, and masks.

## Canonical workflow

Start by loading a datacube, inspecting dimensions, setting or checking
calibration, building virtual detectors/images, then moving to Bragg/COM/strain
workflows only after the raw data and masks make sense.

```python
import py4DSTEM

py4DSTEM.print_h5_tree("scan_4dstem.h5")
datacube = py4DSTEM.read("scan_4dstem.h5", datapath="root/datacube")
# For non-native microscope formats, use py4DSTEM.import_file(...) instead.

print(datacube.data.shape)  # typically (scan_y, scan_x, q_y, q_x)
datacube.calibration

# Average diffraction pattern and virtual bright-field image.
dp_mean = datacube.get_dp_mean()
bf = datacube.get_virtual_image(
    mode="circle",
    geometry=((0, 0), 20),
    centered=True,
)

# Inspect before quantitative analysis.
py4DSTEM.show(dp_mean)
py4DSTEM.show(bf)

# Bragg disk workflows need a probe/kernel and detection parameters chosen from
# the actual diffraction pattern, not copied blindly from an example.
probe = datacube.get_vacuum_probe()
bragg_peaks = datacube.find_Bragg_disks(template=probe, corrPower=1.0, sigma=2)
```

For deeper examples, read:

- Tutorial notebooks: https://github.com/py4dstem/py4DSTEM_tutorials
- First steps: https://py4dstem.readthedocs.io/en/latest/examples/first_steps.html
- Virtual imaging: https://py4dstem.readthedocs.io/en/latest/examples/virtual_imaging.html
- Bragg disk detection: https://py4dstem.readthedocs.io/en/latest/examples/bragg_disk_detection.html

## Key conventions and gotchas

- py4DSTEM v0.14 is a major workflow/API boundary. Older pre-0.14 examples can
  be structurally misleading; check the docs version before copying code.
- Phase-retrieval APIs were reorganized in v0.14.9 with shortened class names.
  If ptychography examples fail at import time, verify the installed py4DSTEM
  version and current phase-retrieval class names.
- Datacube axes are domain-significant. Confirm scan axes and diffraction axes
  before indexing, reshaping, summing, or exporting arrays.
- Virtual detector geometry is in detector/reciprocal-space pixel coordinates
  unless calibration-specific code says otherwise. Do not use a copied radius or
  center without checking the beam center and diffraction pattern scale.
- Quantitative Bragg/strain/orientation workflows depend on probe/kernel choice,
  thresholds, masks, calibration, elliptical distortion correction, and scan
  distortions. Do not report quantitative strain from raw peaks without these
  checks.
- py4DSTEM data can be large. Prefer the package's readers, tree objects, and
  tutorial patterns over loading entire HDF5 datasets into ad hoc arrays.

## Anti-patterns

- Do not write generic NumPy code that assumes shape order without printing and
  naming `(R_y, R_x, Q_y, Q_x)` or the corresponding py4DSTEM dimensions.
- Do not run Bragg disk detection with tutorial thresholds on a new dataset.
  Inspect the mean/max diffraction pattern, mask saturated/hot pixels, choose a
  probe/template, and validate peaks visually.
- Do not average or crop diffraction patterns before recording calibration and
  beam-center assumptions.
- Do not mix py4DSTEM v0.13 notebooks with v0.14+ code unless deliberately
  porting the workflow.
- Do not use phase-retrieval examples without checking whether the class names
  match the installed version.

## Diagnostic checks

Before trusting outputs, the agent should:

- Log py4DSTEM version, file path, tree keys, datacube shape, dtype, and whether
  data are loaded eagerly or lazily.
- Show the mean or max diffraction pattern and at least one scan-position
  diffraction pattern before quantitative processing.
- Verify scan/detector axis order, beam center, calibration units, detector
  mask, and virtual detector geometry.
- For Bragg workflows, overlay detected peaks on representative diffraction
  patterns and record probe/template, thresholds, and masks.
- For strain/orientation outputs, record calibration, reference lattice/peaks,
  distortion corrections, and uncertainty or residual checks.
- Save intermediate py4DSTEM objects or output files with enough metadata to
  reproduce detector geometry and calibration choices.

## Pointers to deeper material

- Documentation: https://py4dstem.readthedocs.io/
- Tutorial repository: https://github.com/py4dstem/py4DSTEM_tutorials
- Source repository: https://github.com/py4dstem/py4DSTEM
- Paper: Savitzky et al. (2021), "py4DSTEM: A Software Package for Four-
  Dimensional Scanning Transmission Electron Microscopy Data Analysis",
  Microscopy and Microanalysis 27, 712-743. https://doi.org/10.1017/S1431927621000477

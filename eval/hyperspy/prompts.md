# HyperSpy Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/hyperspy/SKILL.md` context. Score whether the answer preserves
navigation/signal axes, metadata, lazy loading, and the HyperSpy/eXSpy split.

## Prompt 1: Lazy Load An EELS Spectrum Image

I have a large DigitalMicrograph `.dm4` EELS spectrum image. Write Python that
loads it lazily, checks the axes and metadata, sets it up for EELS analysis, and
computes a mean spectrum over a rectangular ROI.

Expected skill-driven behavior:

- Uses `hyperspy.api.load(..., lazy=True)`.
- Prints/inspects `s`, `s.axes_manager`, `metadata`, and `original_metadata`.
- Recognizes that EELS-specific methods require eXSpy in HyperSpy 2.x.
- Uses HyperSpy ROI and mean methods rather than raw NumPy axes.
- Avoids eager `.data` access or `.compute()` before reduction.

## Prompt 2: EDS Quantification Setup

I loaded an EDS spectrum in HyperSpy. What metadata and signal setup should I
check before quantifying elemental intensities?

Expected skill-driven behavior:

- Sets or verifies `signal_type="EDS_TEM"` or `EDS_SEM`.
- Mentions eXSpy for EDS-specific methods.
- Checks detector, microscope/acquisition parameters, elements/lines, energy
  calibration, background assumptions, and metadata provenance.

## Prompt 3: Decompose A Spectrum Image

Show a safe workflow for denoising a spectrum image with HyperSpy decomposition.
What should I inspect before trusting the components?

Expected skill-driven behavior:

- Uses `s.decomposition()` and `get_decomposition_model()` patterns.
- Checks navigation size and axis semantics.
- Discusses Poisson noise normalization/component count.
- Inspects scree/explained variance, component spectra/maps, residuals, and
  physical plausibility.

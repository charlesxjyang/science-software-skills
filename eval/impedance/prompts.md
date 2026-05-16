# impedance.py Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/impedance/SKILL.md` context. Score whether the answer reaches for
impedance.py, preserves EIS conventions, performs validation, and avoids
generic SciPy-only fitting unless explicitly justified.

## Prompt 1: Fit A Battery EIS Spectrum

I have a CSV exported from a potentiostat with columns frequency, Zreal, Zimag.
Fit it to `R_0-p(R_1,CPE_1)-Wo_1`, plot the Nyquist data and fit, and give me a
small table of fitted parameter values with uncertainties. Write Python code I
can adapt.

Expected skill-driven behavior:

- Uses `impedance.preprocessing.readCSV` or clearly creates the equivalent
  complex `Z` array.
- Uses `CustomCircuit`, not a hand-rolled `scipy.optimize.curve_fit` model.
- Mentions ordered `initial_guess`, `get_param_names()`, `parameters_`, and
  `conf_`.
- Plots the raw data and predicted fit with `plot_nyquist`.
- Flags initial-guess sensitivity and residual inspection.

## Prompt 2: Validate Before Fitting

Before fitting my EIS spectrum, I want to check whether the data are physically
consistent. I have arrays `f` and `Z`. What should I run in Python, and what
should I inspect before trusting equivalent-circuit parameters?

Expected skill-driven behavior:

- Uses `impedance.validation.linKK`.
- Explains causality, linearity, and stability as EIS assumptions.
- Plots or inspects real/imag residuals rather than relying only on one scalar.
- Notes `c`, `max_M`, and possible under/over-fitting behavior.
- Avoids claiming Lin-KK proves the model circuit is correct.

## Prompt 3: Batch Fit Many ZPlot Files

I have a folder of Scribner ZPlot `.z` files from replicate circuit measurements.
Write Python that loops over the files, fits each to `R0-p(R1,C1)`, saves the
parameters to a DataFrame, and makes per-circuit Nyquist overlays.

Expected skill-driven behavior:

- Uses `glob` plus `impedance.preprocessing.readZPlot`.
- Creates one `CustomCircuit` per file with the same circuit string and initial
  guess.
- Extracts labeled parameters via `get_param_names()` and `parameters_`.
- Uses `predict()` and `plot_nyquist`; optionally groups plots by circuit name.
- Does not parse `.z` files manually unless impedance.py cannot read them.

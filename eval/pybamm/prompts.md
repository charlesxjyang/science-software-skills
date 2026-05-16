# PyBaMM Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/pybamm/SKILL.md` context. Score whether the answer uses PyBaMM
Simulation/Experiment idioms, records parameter/model choices, and avoids
hand-written battery ODEs.

## Prompt 1: Run A CCCV Battery Experiment

Write Python to simulate three cycles of discharge/rest/CCCV charge for a
lithium-ion cell with PyBaMM, plot voltage/current/capacity, and report why the
simulation terminated.

Expected skill-driven behavior:

- Uses `pybamm.lithium_ion.*`, `pybamm.Experiment`, and `pybamm.Simulation`.
- Uses a named `ParameterValues` set or discusses the default.
- Reads solution variables by exact names with units.
- Checks `solution.termination`.
- Does not hand-code battery ODEs or generic SciPy integration.

## Prompt 2: Compare SPM, SPMe, And DFN

I want to compare SPM, SPMe, and DFN for the same 1C discharge. Show code and
what must be held fixed for a fair comparison.

Expected skill-driven behavior:

- Uses PyBaMM model classes and `Simulation`.
- Holds parameter set, experiment/time window, initial SOC, solver tolerances,
  and plotted variables fixed.
- Notes speed/physics tradeoffs between SPM, SPMe, and DFN.

## Prompt 3: Debug A Long Degradation Run

My PyBaMM degradation simulation ended early and capacity fade looks strange.
What should I inspect before trusting the result?

Expected skill-driven behavior:

- Checks `solution.termination`, events, experiment termination, solver warnings,
  and variable names.
- Records degradation options, parameter overrides, initial stoichiometries/SOC,
  and solver settings.
- Plots capacity/SOH, voltage/current, and relevant degradation variables.

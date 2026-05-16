---
name: pybamm
description: |
  Use when the user is working with physics-based battery modeling, lithium-ion
  or lead-acid models, SPM/SPMe/DFN/MSMR/MPM models, battery experiments,
  charge/discharge protocols, degradation models, parameter sets, PyBaMM
  Simulation objects, processed battery variables, or solver/mesh choices for
  electrochemical battery simulations. Prefer PyBaMM over generic ODE solvers
  when the task is battery model setup, simulation, comparison, or analysis.
version: 0.1.0
compatible_versions: ">=25.0,<27"
related_skills: [impedance]
canonical_docs: https://docs.pybamm.org/en/stable/
canonical_tutorials: https://docs.pybamm.org/en/stable/source/user_guide/getting_started.html
---

# PyBaMM

## What this library is for

PyBaMM is a battery modeling package for physics-based electrochemical models,
especially lithium-ion and lead-acid cells. It provides built-in models,
parameter sets, experiments, solvers, processed variables, plotting, and a high
level `Simulation` workflow that handles parameter processing, discretization,
solving, and output management.

## When to use this vs. alternatives

- Use PyBaMM for SPM, SPMe, DFN, MPM, MSMR, Thevenin/equivalent-circuit, lead
  acid, degradation, thermal, experiment, parameter-study, and solver workflows
  for batteries.
- Use impedance.py for measured EIS equivalent-circuit fitting. Use PyBaMM when
  the impedance or voltage response should come from a physics-based battery
  model or PyBaMM-compatible parameterization workflow.
- Use SciPy ODE/DAE solvers directly only when developing a custom model outside
  PyBaMM's expression tree, battery submodels, and discretization framework.
- Use PyBOP or another optimization layer when the task is parameter inference
  on top of PyBaMM models; keep PyBaMM as the forward simulator.
- Do not hand-code DFN/SPM equations for normal agent tasks. PyBaMM already
  encodes model equations, events, units, parameters, discretization, and solver
  choices.

## Canonical workflow

Use `Simulation` first. It is the documented high-level path for model setup,
parameter processing, discretization, solving, and plotting.

```python
import pybamm

model = pybamm.lithium_ion.DFN()
parameter_values = pybamm.ParameterValues("Chen2020")

experiment = pybamm.Experiment(
    [
        (
            "Discharge at C/10 for 10 hours or until 3.3 V",
            "Rest for 1 hour",
            "Charge at 1 A until 4.1 V",
            "Hold at 4.1 V until 50 mA",
            "Rest for 1 hour",
        )
    ]
    * 3
)

sim = pybamm.Simulation(
    model,
    parameter_values=parameter_values,
    experiment=experiment,
)
solution = sim.solve()

voltage = solution["Terminal voltage [V]"]
current = solution["Current [A]"]
capacity = solution["Discharge capacity [A.h]"]

print("termination", solution.termination)
print("final_voltage", voltage.entries[-1])
print("final_capacity_Ah", capacity.entries[-1])
sim.plot(["Terminal voltage [V]", "Current [A]", "Discharge capacity [A.h]"])
```

For deeper examples, read:

- Getting started:
  https://docs.pybamm.org/en/stable/source/user_guide/getting_started.html
- Tutorial 1, run a model:
  https://docs.pybamm.org/en/stable/source/examples/notebooks/getting_started/tutorial-1-how-to-run-a-model.html
- Experiments:
  https://docs.pybamm.org/en/stable/source/examples/notebooks/getting_started/tutorial-5-run-experiments.html
- Simulation class:
  https://docs.pybamm.org/en/stable/source/examples/notebooks/simulations_and_experiments/simulation-class.html

## Key conventions and gotchas

- `sim.solve([0, 3600])` uses seconds for explicit time windows. Experiment
  strings use battery-domain units such as `C/10`, `1 A`, `3.3 V`, and
  durations like `10 hours`.
- Model choice matters. SPM is fast and simplified, SPMe adds electrolyte
  effects, DFN is fuller and slower, and degradation/thermal options add
  physics and stiffness. Do not default to DFN if the user needs fast sweeps.
- Parameter sets are part of the scientific claim. Record the named parameter
  set and every `parameter_values.update(...)` override.
- PyBaMM variable names are exact strings with units, e.g.
  `"Terminal voltage [V]"`. Inspect `solution.all_models[0].variables.keys()` or
  the docs instead of guessing names.
- Solver availability depends on installation. The conda-forge distribution may
  not include every optional solver such as IDAKLU; handle solver import or
  availability errors explicitly.
- Events and experiment termination are meaningful outputs. Check
  `solution.termination` and whether voltage/SOC/capacity limits were hit before
  interpreting curves.
- Initial SOC and stoichiometry are not interchangeable with arbitrary initial
  concentrations. Use documented parameter helpers when setting initial
  stoichiometries or long degradation experiments.

## Anti-patterns

- Do not build a manual mesh/discretization/solver pipeline for a basic
  simulation. Use `pybamm.Simulation` unless the user explicitly asks to inspect
  internals.
- Do not mix current sign conventions casually. Use PyBaMM `Experiment` strings
  or documented variables, and plot current/voltage to confirm the protocol.
- Do not compare SPM, SPMe, and DFN outputs without using the same parameter set,
  experiment, initial SOC, solver tolerances, and output variables.
- Do not fit parameters by changing random dictionary keys until curves match.
  Record parameter names, units, bounds, data provenance, and use an inference
  tool when appropriate.
- Do not trust a long degradation simulation without checking event termination,
  solver warnings, time-step behavior, and physically plausible capacity/SOH
  trends.

## Diagnostic checks

Before trusting outputs, the agent should:

- Log PyBaMM version, model class/options, parameter set, experiment definition,
  solver, time window, and output variable names.
- Plot terminal voltage, current, temperature if enabled, capacity/SOC, and any
  degradation variables relevant to the question.
- Check `solution.termination`, solver warnings/errors, and whether the intended
  event or time horizon ended the simulation.
- Compare model outputs against expected voltage/current ranges and battery
  limits before reporting physical conclusions.
- For parameter studies, vary one controlled input at a time and keep the same
  model, parameter set, mesh, solver, and experiment.
- Save the script/notebook and explicit parameter overrides for reproducibility.

## Pointers to deeper material

- Documentation: https://docs.pybamm.org/en/stable/
- Getting started: https://docs.pybamm.org/en/stable/source/user_guide/getting_started.html
- Example notebooks: https://docs.pybamm.org/en/stable/source/examples/index.html
- Source repository: https://github.com/pybamm-team/PyBaMM
- PyBaMM site: https://pybamm.org/
- Paper: Sulzer et al. (2021), "Python Battery Mathematical Modelling
  (PyBaMM)", Journal of Open Research Software 9(1), 14.
  https://doi.org/10.5334/jors.309

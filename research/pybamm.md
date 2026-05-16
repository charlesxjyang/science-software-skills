# PyBaMM Skill Evidence Notes

This note records the evidence used for `skills/pybamm/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Stable documentation:
  https://docs.pybamm.org/en/stable/
- Current getting started guide:
  https://docs.pybamm.org/en/v26.4.0/source/user_guide/getting_started.html
- Stable Tutorial 1, run a model:
  https://docs.pybamm.org/en/stable/source/examples/notebooks/getting_started/tutorial-1-how-to-run-a-model.html
- Simulation class notebook:
  https://docs.pybamm.org/en/v25.4.0/source/examples/notebooks/simulations_and_experiments/simulation-class.html
- Long experiments/degradation example:
  https://docs.pybamm.org/en/latest/source/examples/notebooks/simulations_and_experiments/simulating-long-experiments.html
- PyBaMM learning page:
  https://pybamm.org/learn/
- Source repository:
  https://github.com/pybamm-team/PyBaMM
- PyBaMM paper:
  https://doi.org/10.5334/jors.309

## Extracted Workflow

The docs emphasize:

1. Choose a built-in battery model such as SPM, SPMe, DFN, MPM, MSMR, or
   equivalent-circuit models.
2. Use `pybamm.Simulation` for ordinary setup, parameter processing,
   discretization, solving, plotting, and output management.
3. Use `pybamm.ParameterValues` for named parameter sets and explicit overrides.
4. Use `pybamm.Experiment` strings for realistic charge/discharge/rest/CCCV
   protocols.
5. Access results through named solution variables with units and check
   termination/events.

## Docs-Derived Gotchas

- Time windows passed to `solve` are seconds, while experiment strings use
  battery-domain units.
- Solver availability differs by installation method; PyBaMM's learning page
  notes conda-forge's `pybamm-base` does not include IDAKLUSolver.
- Model/parameter/experiment choices are part of the scientific result and must
  be recorded.
- Long degradation experiments should be checked for event termination,
  physically plausible capacity fade, and solver behavior.

## Open Follow-Ups

- Add empirical prompts for SPM/SPMe/DFN comparison, parameter override mistakes,
  degradation experiments, and impedance-model integration once Claude auth is
  available.

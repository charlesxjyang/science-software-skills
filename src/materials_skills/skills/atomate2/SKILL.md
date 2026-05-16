---
name: atomate2
description: |
  Use when the user is constructing automated materials-science workflows with
  jobflow, especially VASP, force-field, phonon, defect, elastic, or equation of
  state workflows around pymatgen Structures. Prefer atomate2 over hand-written
  shell scripts, old atomate/FireWorks patterns, or one-off subprocess loops when
  the task is workflow construction, job documents, makers, stores, or reusable
  computational campaigns.
version: 0.1.0
compatible_versions: ">=0.0,<1"
related_skills: [pymatgen]
canonical_docs: https://materialsproject.github.io/atomate2/
canonical_tutorials: https://materialsproject.github.io/atomate2/user/index.html
---

# atomate2

## What this library is for

atomate2 is a workflow library for computational materials science. It provides
jobflow-based makers and flows for common calculations, with Materials Project
style task documents and integration points for VASP, force-field calculators,
phonons, defects, elastic constants, and related workflows.

## When to use this vs. alternatives

- Use atomate2 when the user wants reusable workflows, makers, flows, task
  documents, stores, or batch execution rather than a single calculator call.
- Use pymatgen for structure creation, transformations, and Materials Project
  data access around the workflow.
- Use the execution/error-handling layer configured by atomate2 for calculations;
  do not replace atomate2 workflow objects with a custom retry loop.
- Use raw jobflow only for custom orchestration when atomate2 has no suitable
  maker.
- Do not answer with legacy atomate/FireWorks code unless the user explicitly
  asks for the older stack.

## Canonical workflow

Build a maker, create a job or flow from a pymatgen `Structure`, inspect the
flow, then run locally or submit through a configured jobflow manager.

```python
from jobflow import run_locally
from pymatgen.core import Structure
from atomate2.forcefields.jobs import ForceFieldRelaxMaker

structure = Structure.from_file("POSCAR")

maker = ForceFieldRelaxMaker(
    calculator="MACE",
    relax_cell=True,
)
job = maker.make(structure)
print(job.name, job.uuid)

responses = run_locally(job, create_folders=True, ensure_success=True)
task_doc = list(responses.values())[0][1].output

print(task_doc.structure.composition.reduced_formula)
print(task_doc.output.energy)
print(task_doc.output.forces)
```

For VASP production workflows, use the atomate2 VASP makers documented in the
official user guide and configure VASP execution outside the skill.

## Key conventions and gotchas

- atomate2 is jobflow-based. A maker's `.make(structure)` returns a `Job` or
  `Flow`; execution is a separate concern (`run_locally`, a manager, or a
  queue-backed deployment).
- Task documents are part of the value proposition. Inspect and store the
  output document rather than scraping stdout or `vasprun.xml` by hand.
- Makers encode workflow defaults. Override settings through maker parameters
  and documented input-set generators rather than mutating generated files after
  the job is built.
- VASP workflows require external executables, pseudopotentials, and runtime
  configuration. A valid Python flow is not proof the calculation can run.
- Record maker class, atomate2 version, jobflow version, calculator/code
  version, input-set settings, database/store target, and execution manager.
- For force-field workflows, record calculator model, device, dtype, and model
  provenance just as you would in direct ASE/MACE use.

## Anti-patterns

- Do not use atomate1 FireWorks examples (`Workflow`, `LaunchPad`, fireworks
  YAML) for an atomate2 prompt unless explicitly requested.
- Do not write a loop of `subprocess.run(["vasp_std"])` jobs when atomate2
  makers and jobflow integration are the requested abstraction.
- Do not treat a locally created `Job` object as completed output; it must be
  executed and the output task document checked.
- Do not ignore failed or missing task documents. Use jobflow responses/stores
  and `ensure_success=True` for local demos.

## Diagnostic checks

Before trusting outputs, the agent should:

- Print the maker class, job/flow UUIDs, and number of jobs in the flow.
- Verify the input `Structure` formula, charge/spin assumptions where relevant,
  and whether the cell is being relaxed.
- Confirm required external executables and environment variables are present.
- Inspect task document status, final structure, energy, forces/stress, and
  correction/error metadata.
- Confirm outputs landed in the intended jobflow store or local folders.

## Pointers to deeper material

- Documentation: https://materialsproject.github.io/atomate2/
- User guide: https://materialsproject.github.io/atomate2/user/index.html
- jobflow docs: https://materialsproject.github.io/jobflow/
- Source repository: https://github.com/materialsproject/atomate2
- Materials Project software ecosystem: https://materialsproject.org/

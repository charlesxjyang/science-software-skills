# atomate2 Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/atomate2/SKILL.md` context. Score whether the answer uses atomate2
makers and jobflow concepts rather than legacy atomate/FireWorks or ad hoc
workflow scripts.

## Prompt 1: Force-Field Relaxation Workflow

I have a pymatgen `Structure` and want an atomate2 workflow that relaxes it
with a force-field calculator, runs locally for a demo, and inspects the task
document. Write Python and list the provenance checks.

Expected skill-driven behavior:

- Uses an atomate2 maker and `.make(structure)` to create a job or flow.
- Uses jobflow local execution or clearly separates workflow construction from
  execution.
- Inspects the output task document rather than scraping stdout.
- Records maker class, atomate2/jobflow versions, calculator/model settings,
  and store/execution context.
- Avoids legacy atomate1 FireWorks patterns unless explicitly requested.

## Prompt 2: VASP Workflow Planning

Sketch how I should construct an atomate2 VASP relaxation workflow from a
pymatgen `Structure`. I do not need to run VASP in the answer, but I do need
the objects, execution assumptions, and checks before trusting outputs.

Expected skill-driven behavior:

- Uses atomate2 VASP maker/input-set concepts.
- Notes external VASP executable, POTCAR, queue, and store requirements.
- Explains task documents and workflow provenance.
- Mentions configured execution/error handling as infrastructure, not a custom
  shell retry loop.

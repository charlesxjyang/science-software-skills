# atomate2 Skill Evidence Notes

This note records the evidence used for `skills/atomate2/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Official documentation:
  https://materialsproject.github.io/atomate2/
- User guide:
  https://materialsproject.github.io/atomate2/user/index.html
- atomate2 repository:
  https://github.com/materialsproject/atomate2
- jobflow documentation:
  https://materialsproject.github.io/jobflow/
- atomate2 force-field workflows:
  https://materialsproject.github.io/atomate2/user/codes/forcefields.html
- atomate2 VASP workflows:
  https://materialsproject.github.io/atomate2/user/codes/vasp.html

## Extracted Workflow

The maintained atomate2 docs frame the canonical workflow around makers:

1. Create or load a pymatgen `Structure`.
2. Choose a maker for the code/workflow family, for example force-field or VASP
   makers.
3. Call `.make(structure)` to create a job or flow.
4. Execute the jobflow object locally or with a configured manager/store.
5. Inspect task documents rather than scraping raw stdout.
6. Record maker, code, input-set, store, and execution provenance.

## Docs-Derived Gotchas

- atomate2 is not atomate1. The current stack uses jobflow makers and flows,
  not FireWorks `LaunchPad` examples.
- Creating a job/flow does not run it. The output task document only exists
  after execution.
- External code workflows still require executables, pseudopotentials, and
  runtime configuration outside Python.
- For force-field workflows, calculator model provenance remains critical.

## Open Follow-Ups

- Add an evaluation task specifically for VASP makers once a safe non-executing
  prompt is chosen.
- Decide whether atomate2 needs bridge guidance with custodian or whether
  `related_skills` plus task-specific composition is enough.
- Re-check current maker import paths before a release, because atomate2 is
  under active development.

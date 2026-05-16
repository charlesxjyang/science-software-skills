# custodian Skill Evidence Notes

This note records the evidence used for `skills/custodian/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Official documentation:
  https://materialsproject.github.io/custodian/
- VASP API docs:
  https://materialsproject.github.io/custodian/custodian.vasp.html
- Custodian repository:
  https://github.com/materialsproject/custodian
- pymatgen VASP input documentation:
  https://pymatgen.org/pymatgen.io.vasp.html
- atomate2 documentation:
  https://materialsproject.github.io/atomate2/
- Materials Project software ecosystem:
  https://materialsproject.org/

## Extracted Workflow

The docs emphasize a monitored execution pattern:

1. Generate or verify code input files.
2. Construct one or more `Job` objects such as `VaspJob`.
3. Select domain-specific handlers for known failures.
4. Select validators for outputs that must be present and parseable.
5. Run jobs through `Custodian` with a bounded `max_errors` policy.
6. Audit the correction log, backups, validators, and final scientific
   convergence before trusting outputs.

## Docs-Derived Gotchas

- custodian handlers inspect files and make domain-specific corrections. They
  are not generic Python exception handlers.
- A zero exit code does not imply a scientifically valid calculation; validators
  and convergence checks still matter.
- Handler choice should match the calculation type. Inappropriate automatic
  fixes can change the scientific calculation.
- Backup/correction logs are provenance and should not be discarded.

## Open Follow-Ups

- Add issue-derived gotchas for the highest-frequency VASP corrections after
  reviewing current open issues.
- Test whether a custodian skill improves agents that otherwise write generic
  shell retry loops.
- Decide whether atomate2 VASP workflows should load both `atomate2` and
  `custodian` skills by default.

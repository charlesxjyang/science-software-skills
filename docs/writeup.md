# Environment-Aware Skills for Materials and Chemistry Python

## Thesis

Installed Python packages are user context. A materials researcher with ASE,
pymatgen, MACE, py4DSTEM, HyperSpy, PyBaMM, RDKit, and impedance.py installed
has already revealed a domain, a vocabulary, file formats, and preferred
abstractions. An agent that sees this environment should load package-scoped
skills before reaching for generic SciPy, sklearn, NumPy, or ad hoc parsers.

## Design

This repo uses package-shaped skills rather than workflow-shaped skills. Each
skill is scoped to one library and contains:

- trigger language for when the package should be used,
- guidance on when to use alternatives,
- one compact canonical workflow,
- conventions and failure modes that agents commonly miss,
- diagnostic checks before trusting outputs,
- links to maintained tutorials and docs.

The CLI is intentionally thin:

```bash
materials-skills install --env environment.yml --agent claude
pip list | materials-skills install --env - --agent all
materials-skills install --env pip-list.txt --target .cursor/skills
materials-skills install --dry-run --json
materials-skills registry --json
materials-skills validate --source-root skills
materials-skills --version
```

It parses a Python environment, matches installed distributions against a small
registry, and copies the corresponding `SKILL.md` folders into agent-specific
skill directories. The current v0 shape is hybrid: skills ship with the Python
package for offline installation, while the package-to-skill map is available
both as `materials-skills registry --json` and as a checked `registry.json`
snapshot for registry-style inspection or downstream tooling.

## Current v0 Evidence

Implemented package skills:

- ASE
- pymatgen
- RDKit
- MACE
- impedance.py
- py4DSTEM
- HyperSpy
- PyBaMM
- PySCF
- OpenMM
- matminer
- atomate2

Verified locally:

- `pip list` table parsing
- `pip list --format=json` parsing
- `pip freeze`-style parsing
- editable, VCS, direct-reference, spaced-version, and bare wheel URL pip
  requirement parsing
- `conda env export` parsing, including nested `pip:` dependencies
- `conda env export --json`, `conda list --json`, `conda list`,
  `conda list --export`, and explicit conda URL lockfile parsing
- current Python environment detection when `--env` is omitted
- stdin environment input with `--env -`
- install into `.claude/skills`, `.cursor/skills`, and `.codex/skills` targets,
  including `--agent all`
- idempotent installs, overwrite protection, `--force`, dry-run conflict
  previews, and structured JSON errors
- match provenance showing which installed distributions and parsed versions
  triggered each skill
- requested-agent provenance in install JSON, including multi-target
  `--agent all` installs
- advisory compatibility status against each skill's declared
  `compatible_versions`
- JSON registry export, checked `registry.json` sync, and a registry JSON writer
- skill/frontmatter validation including malformed inline lists and normalized
  duplicate canonical URL checks, package-data sync checks, wheel payload checks
  that compare the built wheel against source skills, source Python modules,
  README metadata, the expected console-script entry point, and package/wheel
  versions, source-distribution payload checks, plus an installed-wheel smoke
  check

The current synthetic environment installs ten package-scoped skills from one
mixed conda+pip environment file, demonstrating the composability mechanism.
The local non-empirical gate currently passes with 320 tests, validates all
skills, verifies package-data sync and canonical registry JSON sync, checks
that the built wheel carries the current source skill and Python module content
plus the CLI entry point, and smoke-tests the installed console script in a
temporary venv. It also checks that the source distribution carries the current
source/package skill files, Python modules, release scripts, docs, evaluation
harness/artifacts, research notes, tests/fixtures, `registry.json`, README, and
`pyproject.toml`.

## Empirical Results

The empirical harness now has real Claude outputs and manually scored reports.
The first-package impedance.py matrix contains six records: three prompts run
once without package-skill context and once with `skills/impedance/SKILL.md`.
The package skill won two prompts and tied one:

- Equivalent-circuit fitting: package-skill win. The baseline reached for
  impedance.py but treated `get_param_names()` as a flat list; the package-skill
  answer used the current `(names, units)` convention before pairing
  `parameters_` and `conf_`.
- Lin-KK validation before fitting: tie. Both variants used `linKK`, inspected
  real and imaginary residuals, explained causality/linearity/stability, and
  preserved the caveat that Lin-KK does not validate the circuit topology.
- Batch ZPlot fitting: package-skill win. The baseline used the right high-level
  library flow but reversed the `plot_nyquist` positional arguments; the
  package-skill answer used `plot_nyquist(Z, ax=...)` correctly.

The full v0 matrix contains 11 records: five baseline, five package-skill, and
one public K-Dense pymatgen comparison. Results were mixed:

- impedance: package-skill win.
- ASE+pymatgen+MACE composition: baseline win. The package-skill answer loaded
  all three package skills but was weaker on species-order, cell, PBC, and unit
  verification after `AseAtomsAdaptor`.
- pymatgen phase diagram: baseline win, local package skill tie, K-Dense loss.
  The K-Dense answer included a brittle assertion that can reject valid
  compatible entries with zero correction.
- py4DSTEM: tie. Both variants used py4DSTEM APIs and covered axes, diffraction
  inspection, calibration, detector geometry, probe/template, threshold, and
  Bragg-detection checks.
- OpenMM: baseline win. The package-skill answer truncated before final
  diagnostics and added extra particles after `createSystem`, the wrong order
  when templates require extra particles.

The empirical read is narrower than the original bet: package-scoped skills can
prevent concrete API mistakes in sparse-training-data cases, especially
impedance.py, but composition is not automatically solved by loading multiple
package skills. Cross-library handoff details may need their own small bridge
artifact when correctness depends on the boundary between libraries.

The gates behind these claims are strict. The completeness gate requires every
expected baseline/package-skill/K-Dense record to have `status: "ok"`, prompt
provenance, non-empty model output, matching skill metadata, context-free
baseline records, and provided context where required. The scoring gate rejects
unchecked criteria, `Outcome: not-scored`, summary/variant outcome mismatches,
invalid winners, missing prompt blocks, and empty output blocks. Both the
first-package impedance gate and the full v0 artifact gate pass. The status
command still emits `automation_steps` for machine-readable final gates when
artifacts are incomplete, and reports no blockers after the scored artifacts
pass.

The extension benchmark now has five environment-discovery tasks per active
package skill. These prompts intentionally avoid naming the desired workflow
library in the user request, expose only generic distractors (`numpy`,
`pandas`, `scipy`, `scikit-learn`, `matplotlib`), and hide the scoring criteria
from the model. Each task records documentation sources and a fixed hidden
rubric. The expanded Claude and Codex runs cover the current five-task-per-skill
suite. For Claude, package skills win all 12 package suites; baseline scores
159/300 rubric terms and package-skill context scores 268/300. One Claude
baseline call for the pymatgen Pourbaix task repeatedly timed out and is counted
as zero. For Codex, package skills win 11 of 12 package suites and tie RDKit;
baseline scores 143/300 and package-skill context scores 257/300. MACE still
shows a positive margin in the expanded Codex run: baseline 13/25,
package-skill 18/25. The first black-box optimizer run on the earlier
three-task MACE suite improved the candidate-notes heldout score from 10/15 to
11/15; those generic notes were folded into the canonical MACE skill, while the
optimizer still refuses automatic promotion without a train/dev selection split.

## Open Design Questions

- Registry placement: the current implementation tests a local hybrid of
  package-shipped skills plus checked JSON registry export. A hosted central
  registry still needs testing.
- Cross-library guidance: the ASE+pymatgen+MACE result shows that multiple
  package skills load correctly but do not guarantee correct handoff behavior.
  A narrow bridge artifact is likely the next thing to test.
- Minimum useful skill size: current skills are intentionally under 300 lines;
  impedance.py shows that compact API-convention guidance can change behavior,
  but other package skills may need tighter triggers or more focused gotchas.
- Mixed conda+pip environments: the parser handles common exports, but real user
  environments should be tested.

See `docs/design-decisions.md` for the current evidence-backed answer to each
open question and the remaining post-v0 risks.

# K-Dense pymatgen Comparison

## Source

- K-Dense repository: https://github.com/K-Dense-AI/claude-scientific-skills
- Public raw skill fixture:
  https://raw.githubusercontent.com/K-Dense-AI/claude-scientific-skills/main/scientific-skills/pymatgen/SKILL.md
- Local fixture: `eval/kdense-public/pymatgen/SKILL.md`
- Local package skill: `skills/pymatgen/SKILL.md`

## Snapshot

| Skill | Lines | Shape |
| --- | ---: | --- |
| K-Dense pymatgen | 689 | Broad workflow/reference skill with install commands, scripts, references, and many examples |
| Local pymatgen | 149 | Compact package-scoped trigger/judgment skill with canonical workflow, gotchas, anti-patterns, diagnostics |

## Where K-Dense Is Stronger

- Much broader surface area: structures, conversions, symmetry, phase diagrams,
  electronic structure, surfaces/interfaces, VASP workflows, Materials Project
  usage, scripts, and references.
- Includes concrete helper-script workflows such as structure conversion,
  analysis, and phase diagram generation.
- Uses the `mp_api.client.MPRester` path prominently for Materials Project
  examples; the local skill keeps `pymatgen.ext.matproj.MPRester` because the
  current pymatgen docs describe it as an MP API v2 interface with pymatgen
  object/workflow fit.
- Better as a standalone deep reference when pymatgen is the whole task and
  context budget is not constrained.

## Where Local Package Skill Is Different

- Smaller by design: 149 lines instead of 689, making it more suitable for
  automatic environment-triggered loading and composition with ASE, MACE, RDKit,
  PyBaMM, etc.
- Emphasizes when to use pymatgen vs. ASE/RDKit/MACE rather than treating
  pymatgen as the whole workflow.
- Includes issue-derived agent gotchas: CIF duplicate/disordered sites,
  `Structure.from_spacegroup()` atom-count surprises, periodic neighbor edge
  cases, and current `MPRester` field-name/API drift.
- Contains explicit anti-patterns and diagnostic checks tailored to agent
  behavior, including compatibility/provenance warnings for phase diagrams.

## Implication For v0

Keep both in the empirical matrix where applicable:

- Compare K-Dense vs. local package skill on the pymatgen phase-diagram task.
- Expect K-Dense to do well on broad pymatgen-only workflows.
- Expect the local skill to be more composable when the environment contains
  multiple packages and the task crosses package boundaries.

The local skill is not a drop-in replacement for K-Dense's broad reference
skill. It is a smaller package-shaped skill intended to be loaded automatically
from environment detection.

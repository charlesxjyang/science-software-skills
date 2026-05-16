# v0 Demo Transcript

This demo uses the mixed conda+pip fixture in
`tests/fixtures/conda-env.yml`. It includes conda packages such as `ase`,
`pymatgen`, and `rdkit`, plus a nested `pip:` block with `mace-torch`,
`impedance`, `py4DSTEM`, `hyperspy`, `pybamm`, `pyscf`, `openmm`, `matminer`,
and `atomate2`.

The transcript below uses `PYTHONPATH=src python -m materials_skills.cli` so it
can be reproduced directly from a source checkout. After installing the wheel,
the equivalent user-facing command starts with `materials-skills`:

```bash
materials-skills install --env tests/fixtures/conda-env.yml --agent all --dry-run --json
```

## Dry-Run Skill Discovery

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/conda-env.yml \
  --agent all \
  --skills-root skills \
  --dry-run \
  --json
```

Observed result, abbreviated to the stable fields relevant to the demo:

```json
{
  "environment": {
    "source": "tests/fixtures/conda-env.yml",
    "requested_format": "auto",
    "format": "conda",
    "package_count": 16,
    "package_versions": {
      "ase": "3.26",
      "atomate2": "0.0.21",
      "impedance": "1.7.1",
      "mace-torch": "0.3.13",
      "matminer": "0.9.3",
      "py4DSTEM": "0.14.14"
    }
  },
  "skills": [
    "ase",
    "pymatgen",
    "rdkit",
    "mace",
    "impedance",
    "py4dstem",
    "hyperspy",
    "pybamm",
    "pyscf",
    "openmm",
    "matminer",
    "atomate2"
  ],
  "agent": "all",
  "targets": [
    ".claude/skills",
    ".cursor/skills",
    ".codex/skills"
  ],
  "dry_run": true
}
```

The `matches` field records why each skill was selected. Examples from the
same run:

```json
[
  {
    "skill": "mace",
    "matched_distributions": ["mace-torch"],
    "matched_versions": {"mace-torch": "0.3.13"},
    "compatible_versions": ">=0.3.10,<0.4",
    "compatibility": "compatible",
    "registered_distributions": ["mace-torch"]
  },
  {
    "skill": "impedance",
    "matched_distributions": ["impedance"],
    "matched_versions": {"impedance": "1.7.1"},
    "compatible_versions": ">=1.7,<2",
    "compatibility": "compatible",
    "registered_distributions": ["impedance"]
  },
  {
    "skill": "py4dstem",
    "matched_distributions": ["py4DSTEM"],
    "matched_versions": {"py4DSTEM": "0.14.14"},
    "compatible_versions": ">=0.14,<0.15",
    "compatibility": "compatible",
    "registered_distributions": ["py4DSTEM", "py4dstem"]
  }
]
```

## Install Command

The same command without `--dry-run` writes each matched skill to every built-in
agent target:

```bash
PYTHONPATH=src python -m materials_skills.cli install \
  --env tests/fixtures/conda-env.yml \
  --agent all \
  --skills-root skills \
  --json
```

The integration test `InstallCommandTests.test_agent_all_installs_to_every_builtin_target`
verifies that this creates `SKILL.md` files under all three target roots:

```text
.claude/skills/impedance/SKILL.md
.cursor/skills/impedance/SKILL.md
.codex/skills/impedance/SKILL.md
```

The same test asserts that 36 install actions are emitted: 12 package skills
times 3 built-in agent targets.

## Registry Snapshot

```bash
PYTHONPATH=src python -m materials_skills.cli registry --json
```

The registry currently maps these package distributions to the v0 skills:

| Skill | Triggering distributions |
| --- | --- |
| `ase` | `ase` |
| `pymatgen` | `pymatgen` |
| `rdkit` | `rdkit`, `rdkit-pypi` |
| `mace` | `mace-torch` |
| `impedance` | `impedance` |
| `py4dstem` | `py4DSTEM`, `py4dstem` |
| `hyperspy` | `hyperspy` |
| `pybamm` | `pybamm`, `pybamm-base` |
| `pyscf` | `pyscf` |
| `openmm` | `openmm` |
| `matminer` | `matminer` |
| `atomate2` | `atomate2` |

## Verification

```bash
PYTHONPATH=src:. python -m unittest discover -s tests
PYTHONPATH=src python -m materials_skills.cli validate --source-root skills --json
```

Current result: 320 tests pass, and skill validation returns
`{"ok": true, "errors": []}`.

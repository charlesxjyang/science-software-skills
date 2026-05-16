# v0 Design Decisions and Open Questions

This note records what the current implementation and v0 empirical run have
actually resolved versus what still needs more evidence.

## Registry Placement

Status: locally resolved for v0; hosted registry unresolved.

The v0 implementation uses a hybrid shape:

- package-scoped `SKILL.md` files live in the source tree under `skills/`
- the same skills are shipped as package data under `src/materials_skills/skills/`
- `materials-skills registry --json` exposes the package-to-skill mapping for
  inspection and downstream tooling
- checked `registry.json` mirrors that runtime payload for non-Python tooling
- `scripts/check_registry_json.py --write` regenerates the checked registry
  snapshot from the runtime registry
- release checks verify that source skills, packaged skills, the wheel, and the
  source distribution stay synchronized

This is enough for an offline demo and installed CLI usage. A hosted central
registry is deferred because v0 has not yet shown that remote discovery adds
value beyond package-shipped skills plus a checked JSON registry snapshot.

## Conda and Pip Mixed Environments

Status: implemented against representative exports; real user environments
still need sampling.

The parser handles `pip list`, `pip freeze`-style lines, pip JSON, conda env
YAML/JSON exports, conda list table/JSON/export outputs, explicit conda package
URLs, nested `pip:` dependency blocks, stdin input, and current environment
detection. The demo fixture intentionally mixes conda packages with nested pip
packages and resolves all ten v0 skills.

The remaining risk is long-tail environment syntax from real projects. The v0
answer is to keep parser behavior conservative, emit parse errors clearly, and
add formats only when observed in real exports.

## Minimum Useful Skill Content

Status: structure chosen; minimum can probably shrink, but not uniformly.

The v0 skill format is intentionally small: trigger metadata, when-to-use
guidance, one canonical workflow, conventions/gotchas, anti-patterns,
diagnostic checks, and links to maintained tutorials. Validation enforces a
300-line cap so the skill remains a routing and judgment layer rather than a
documentation mirror.

The impedance.py results show that compact API-convention guidance can change
model behavior: the package-skill answer avoided current-API mistakes around
`get_param_names()` and `plot_nyquist`. Other package-skill results were weaker
or tied, so v0 does not justify making every skill longer. The next iteration
should tighten the highest-impact gotchas instead of expanding skills into
workflow manuals.

## Cross-Library Composition

Status: evaluator and manifests support composition; agent behavior is mixed.

The runner can load multiple package skills for one task. The full v0 manifest
uses this for the ASE+pymatgen+MACE relaxation prompt, where the package-skill
variant records `context_skills: ["mace", "ase", "pymatgen"]`. Completeness
checks reject missing, duplicate, unregistered, or manifest-mismatched composed
skills.

This proves the plumbing can compose package-shaped skills. The empirical
result also shows that loading the package skills is not sufficient by itself:
the package-skill answer lost to baseline because it was weaker on the
pymatgen-to-ASE conversion audit. The next test should add a small bridge
artifact for that boundary rather than bloating each package skill with
cross-library workflow documentation.

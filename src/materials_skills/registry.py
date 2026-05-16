"""Registry of Python distributions that imply package-scoped skills."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillRecord:
    """A package-to-skill mapping."""

    skill_name: str
    distributions: tuple[str, ...]
    skill_dir: str


REGISTRY: tuple[SkillRecord, ...] = (
    SkillRecord(
        skill_name="ase",
        distributions=("ase",),
        skill_dir="ase",
    ),
    SkillRecord(
        skill_name="pymatgen",
        distributions=("pymatgen",),
        skill_dir="pymatgen",
    ),
    SkillRecord(
        skill_name="rdkit",
        distributions=("rdkit", "rdkit-pypi"),
        skill_dir="rdkit",
    ),
    SkillRecord(
        skill_name="mace",
        distributions=("mace-torch",),
        skill_dir="mace",
    ),
    SkillRecord(
        skill_name="impedance",
        distributions=("impedance",),
        skill_dir="impedance",
    ),
    SkillRecord(
        skill_name="py4dstem",
        distributions=("py4DSTEM", "py4dstem"),
        skill_dir="py4dstem",
    ),
    SkillRecord(
        skill_name="hyperspy",
        distributions=("hyperspy",),
        skill_dir="hyperspy",
    ),
    SkillRecord(
        skill_name="pybamm",
        distributions=("pybamm", "pybamm-base"),
        skill_dir="pybamm",
    ),
    SkillRecord(
        skill_name="pyscf",
        distributions=("pyscf",),
        skill_dir="pyscf",
    ),
    SkillRecord(
        skill_name="openmm",
        distributions=("openmm",),
        skill_dir="openmm",
    ),
    SkillRecord(
        skill_name="matminer",
        distributions=("matminer",),
        skill_dir="matminer",
    ),
    SkillRecord(
        skill_name="atomate2",
        distributions=("atomate2",),
        skill_dir="atomate2",
    ),
)


def normalize_distribution_name(name: str) -> str:
    """Normalize package names following the PyPA name-comparison convention."""

    return name.strip().lower().replace("_", "-").replace(".", "-")


def default_skills_root() -> Path:
    """Return the packaged skills directory, with source-checkout fallback."""

    packaged = Path(__file__).resolve().parent / "skills"
    if packaged.is_dir():
        return packaged
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "skills"


def match_skills(package_names: set[str]) -> list[SkillRecord]:
    """Return registry records whose distribution aliases are installed."""

    normalized = {normalize_distribution_name(name) for name in package_names}
    matches: list[SkillRecord] = []
    for record in REGISTRY:
        aliases = {normalize_distribution_name(name) for name in record.distributions}
        if normalized.intersection(aliases):
            matches.append(record)
    return matches


def registry_payload() -> list[dict[str, object]]:
    return [
        {
            "skill_name": record.skill_name,
            "distributions": list(record.distributions),
            "skill_dir": record.skill_dir,
        }
        for record in REGISTRY
    ]

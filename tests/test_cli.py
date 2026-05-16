from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import call, patch

import scripts.check_local_v0 as local_v0_script
import scripts.check_v0_status as v0_status_script
import scripts.check_wheel_install as wheel_install_script
from scripts.check_wheel_install import smoke_wheel_install, wheel_filename_version
from scripts.check_wheel_skills import check_wheel_skills, main as check_wheel_skills_main
from scripts.check_sdist_payload import check_sdist_payload, main as check_sdist_payload_main
from scripts.check_registry_json import (
    check_registry_json,
    main as check_registry_json_main,
    registry_json_text,
    write_registry_json,
)
from scripts.check_local_v0 import CHECKS as LOCAL_V0_CHECKS
from scripts.sync_packaged_skills import check_sync, main as sync_skills_main

from materials_skills import __version__
from materials_skills.cli import (
    compatibility_status,
    detect_current_environment,
    detect_current_environment_details,
    describe_skill_matches,
    install_skills,
    load_environment,
    main,
    parse_conda_export,
    parse_conda_json,
    parse_conda_list,
    parse_environment_file,
    parse_pip_json,
    parse_pip_list,
    parse_frontmatter_list,
    ParsedEnvironment,
    registry_payload,
    select_install_targets,
    validate_skills,
)
from materials_skills.registry import REGISTRY, default_skills_root, match_skills, normalize_distribution_name


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SKILLS_ROOT = ROOT / "skills"


def capture_stdout():
    import contextlib
    import io

    return contextlib.redirect_stdout(io.StringIO())


class ParserTests(unittest.TestCase):
    def test_parse_pip_list_table(self) -> None:
        text = (FIXTURES / "pip-list.txt").read_text(encoding="utf-8")
        self.assertEqual(
            parse_pip_list(text),
            {
                "numpy",
                "ase",
                "impedance",
                "mace-torch",
                "py4DSTEM",
                "hyperspy",
                "openmm",
                "pybamm",
                "pyscf",
                "pymatgen",
                "rdkit",
                "matminer",
                "atomate2",
                "scipy",
            },
        )

    def test_parse_pip_json(self) -> None:
        text = (FIXTURES / "pip-list.json").read_text(encoding="utf-8")
        self.assertEqual(
            parse_pip_json(text),
            {
                "numpy",
                "ase",
                "impedance",
                "mace-torch",
                "py4DSTEM",
                "hyperspy",
                "openmm",
                "pybamm",
                "pyscf",
                "pymatgen",
                "rdkit",
                "matminer",
                "atomate2",
                "scipy",
            },
        )

    def test_parse_pip_requirement_forms(self) -> None:
        packages = parse_pip_list(
            """
            impedance==1.7.1
            mace-torch @ git+https://github.com/ACEsuit/mace
            -e git+https://github.com/py4dstem/py4DSTEM.git#egg=py4DSTEM
            --editable git+https://github.com/hyperspy/hyperspy.git#egg=hyperspy
            pybamm[plot]==26.4.0 ; python_version >= "3.10"
            https://example.invalid/wheels/openmm-8.4.0-py3-none-any.whl
            git+https://github.com/example/no-egg.git
            --find-links https://example.invalid/wheels
            """
        )
        self.assertIn("impedance", packages)
        self.assertIn("mace-torch", packages)
        self.assertIn("py4DSTEM", packages)
        self.assertIn("hyperspy", packages)
        self.assertIn("pybamm", packages)
        self.assertIn("openmm", packages)
        self.assertNotIn("-e", packages)
        self.assertNotIn("--editable", packages)
        self.assertNotIn("git+https://github.com/example/no-egg.git", packages)

    def test_parse_pip_requirements_with_spaced_version_operators(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reqs = Path(tmp) / "requirements.txt"
            reqs.write_text(
                "\n".join(
                    [
                        "impedance == 1.7.1 --hash=sha256:abc",
                        "pybamm[plot] == 26.4.0 ; python_version >= '3.10'",
                        "ase >= 3.26",
                    ]
                ),
                encoding="utf-8",
            )
            environment = load_environment(reqs, "pip")

        self.assertIn("impedance", environment.package_names)
        self.assertIn("pybamm", environment.package_names)
        self.assertIn("ase", environment.package_names)
        self.assertEqual(environment.package_versions["impedance"], "1.7.1")
        self.assertEqual(environment.package_versions["pybamm"], "26.4.0")
        self.assertNotIn("ase", environment.package_versions)

    def test_parse_conda_export_with_pip_block(self) -> None:
        text = (FIXTURES / "conda-env.yml").read_text(encoding="utf-8")
        packages = parse_conda_export(text)
        self.assertIn("python", packages)
        self.assertIn("numpy", packages)
        self.assertIn("ase", packages)
        self.assertIn("pymatgen", packages)
        self.assertIn("rdkit", packages)
        self.assertIn("mace-torch", packages)
        self.assertIn("py4DSTEM", packages)
        self.assertIn("hyperspy", packages)
        self.assertIn("openmm", packages)
        self.assertIn("pybamm", packages)
        self.assertIn("pyscf", packages)
        self.assertIn("pip", packages)
        self.assertIn("impedance", packages)
        self.assertIn("scipy", packages)

    def test_parse_conda_export_pip_block_with_editable_requirement(self) -> None:
        packages = parse_conda_export(
            """
            name: editable-demo
            dependencies:
              - python=3.12
              - pip:
                  - -e git+https://github.com/ECSHackWeek/impedance.py.git#egg=impedance
                  - mace-torch @ git+https://github.com/ACEsuit/mace
            """
        )
        self.assertIn("python", packages)
        self.assertIn("impedance", packages)
        self.assertIn("mace-torch", packages)
        self.assertNotIn("-e", packages)

    def test_parse_conda_json_export_with_pip_block(self) -> None:
        text = (FIXTURES / "conda-env.json").read_text(encoding="utf-8")
        packages = parse_conda_json(text)
        self.assertIn("python", packages)
        self.assertIn("numpy", packages)
        self.assertIn("ase", packages)
        self.assertIn("pymatgen", packages)
        self.assertIn("rdkit", packages)
        self.assertIn("mace-torch", packages)
        self.assertIn("py4DSTEM", packages)
        self.assertIn("hyperspy", packages)
        self.assertIn("openmm", packages)
        self.assertIn("pybamm", packages)
        self.assertIn("pyscf", packages)
        self.assertIn("impedance", packages)

    def test_parse_conda_json_pip_block_with_editable_requirement(self) -> None:
        packages = parse_conda_json(
            json.dumps(
                {
                    "dependencies": [
                        "python=3.12",
                        {
                            "pip": [
                                "--editable git+https://github.com/ECSHackWeek/impedance.py.git#egg=impedance",
                                "py4DSTEM @ git+https://github.com/py4dstem/py4DSTEM",
                            ]
                        },
                    ]
                }
            )
        )
        self.assertIn("python", packages)
        self.assertIn("impedance", packages)
        self.assertIn("py4DSTEM", packages)
        self.assertNotIn("--editable", packages)

    def test_parse_conda_json_list(self) -> None:
        text = (FIXTURES / "conda-list.json").read_text(encoding="utf-8")
        packages = parse_conda_json(text)
        self.assertIn("ase", packages)
        self.assertIn("mace-torch", packages)
        self.assertIn("py4DSTEM", packages)
        self.assertIn("openmm", packages)

    def test_parse_conda_list_table(self) -> None:
        text = (FIXTURES / "conda-list.txt").read_text(encoding="utf-8")
        packages = parse_conda_list(text)
        self.assertIn("ase", packages)
        self.assertIn("pymatgen", packages)
        self.assertIn("rdkit", packages)
        self.assertIn("mace-torch", packages)
        self.assertIn("impedance", packages)
        self.assertIn("py4DSTEM", packages)
        self.assertIn("hyperspy", packages)
        self.assertIn("openmm", packages)

    def test_parse_conda_list_export(self) -> None:
        text = (FIXTURES / "conda-list-export.txt").read_text(encoding="utf-8")
        packages = parse_conda_list(text)
        self.assertIn("ase", packages)
        self.assertIn("impedance", packages)
        self.assertIn("mace-torch", packages)
        self.assertNotIn("ase=3.26.0=pyhd8ed1ab_0", packages)

    def test_parse_conda_explicit_urls(self) -> None:
        text = (FIXTURES / "conda-explicit.txt").read_text(encoding="utf-8")
        packages = parse_conda_list(text)
        self.assertIn("ase", packages)
        self.assertIn("pymatgen", packages)
        self.assertIn("rdkit", packages)
        self.assertIn("mace-torch", packages)
        self.assertIn("impedance", packages)
        self.assertIn("py4DSTEM", packages)
        self.assertIn("hyperspy", packages)
        self.assertIn("openmm", packages)
        self.assertNotIn("@EXPLICIT", packages)

    def test_auto_format_inference(self) -> None:
        packages = parse_environment_file(FIXTURES / "conda-env.yml", "auto")
        self.assertIn("impedance", packages)

    def test_auto_format_inference_for_pip_json(self) -> None:
        packages = parse_environment_file(FIXTURES / "pip-list.json", "auto")
        self.assertIn("impedance", packages)
        self.assertIn("py4DSTEM", packages)

    def test_auto_format_inference_for_conda_json_export(self) -> None:
        packages = parse_environment_file(FIXTURES / "conda-env.json", "auto")
        self.assertIn("impedance", packages)
        self.assertIn("mace-torch", packages)

    def test_auto_format_inference_for_conda_json_list(self) -> None:
        packages = parse_environment_file(FIXTURES / "conda-list.json", "auto")
        self.assertIn("impedance", packages)
        self.assertIn("openmm", packages)

    def test_load_environment_reports_source_and_detected_format(self) -> None:
        environment = load_environment(FIXTURES / "conda-list.json", "auto")
        self.assertEqual(environment.source, str(FIXTURES / "conda-list.json"))
        self.assertEqual(environment.requested_format, "auto")
        self.assertEqual(environment.detected_format, "conda-json")
        self.assertIn("impedance", environment.package_names)
        self.assertEqual(environment.package_versions["impedance"], "1.7.1")
        self.assertEqual(environment.package_versions["openmm"], "8.4.0")

    def test_load_environment_reports_stdin_source(self) -> None:
        text = (FIXTURES / "pip-list.txt").read_text(encoding="utf-8")
        with patch("sys.stdin", io.StringIO(text)):
            environment = load_environment(Path("-"), "auto")
        self.assertEqual(environment.source, "stdin")
        self.assertEqual(environment.detected_format, "pip")
        self.assertIn("py4DSTEM", environment.package_names)
        self.assertEqual(environment.package_versions["impedance"], "1.7.1")

    def test_auto_format_inference_for_conda_list_table(self) -> None:
        packages = parse_environment_file(FIXTURES / "conda-list.txt", "auto")
        self.assertIn("py4DSTEM", packages)

    def test_auto_format_inference_for_conda_list_export(self) -> None:
        packages = parse_environment_file(FIXTURES / "conda-list-export.txt", "auto")
        self.assertIn("pybamm", packages)

    def test_auto_format_inference_for_conda_explicit(self) -> None:
        packages = parse_environment_file(FIXTURES / "conda-explicit.txt", "auto")
        self.assertIn("openmm", packages)

    def test_auto_format_inference_keeps_pip_direct_refs_as_pip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reqs = Path(tmp) / "requirements.txt"
            reqs.write_text(
                "\n".join(
                    [
                        "impedance==1.7.1",
                        "mace-torch @ git+https://github.com/ACEsuit/mace",
                        "-e git+https://github.com/py4dstem/py4DSTEM.git#egg=py4DSTEM",
                    ]
                ),
                encoding="utf-8",
            )
            environment = load_environment(reqs, "auto")
        self.assertEqual(environment.detected_format, "pip")
        self.assertIn("impedance", environment.package_names)
        self.assertIn("mace-torch", environment.package_names)
        self.assertIn("py4DSTEM", environment.package_names)

    def test_auto_format_inference_keeps_http_pip_wheel_as_pip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reqs = Path(tmp) / "requirements.txt"
            reqs.write_text(
                "\n".join(
                    [
                        "https://example.invalid/wheels/impedance-1.7.1-py3-none-any.whl",
                        "rdkit @ https://example.invalid/wheels/rdkit-2026.03.2-py3-none-any.whl",
                    ]
                ),
                encoding="utf-8",
            )
            environment = load_environment(reqs, "auto")
        self.assertEqual(environment.detected_format, "pip")
        self.assertIn("impedance", environment.package_names)
        self.assertIn("rdkit", environment.package_names)
        self.assertNotIn("impedance-1.7.1-py3-none-any.whl", environment.package_names)
        self.assertEqual(environment.package_versions["impedance"], "1.7.1")
        self.assertEqual(environment.package_versions["rdkit"], "2026.03.2")

    def test_parse_environment_file_reads_stdin_for_dash_path(self) -> None:
        text = (FIXTURES / "pip-list.txt").read_text(encoding="utf-8")
        with patch("sys.stdin", io.StringIO(text)):
            packages = parse_environment_file(Path("-"), "auto")
        self.assertIn("impedance", packages)
        self.assertIn("py4DSTEM", packages)

    def test_detect_current_environment_uses_distribution_metadata(self) -> None:
        class FakeDistribution:
            def __init__(self, name: str | None, version: str = "") -> None:
                self.metadata = {} if name is None else {"Name": name}
                self.version = version

        with patch(
            "materials_skills.cli.metadata.distributions",
            return_value=[
                FakeDistribution("impedance", "1.7.1"),
                FakeDistribution("mace-torch", "0.3.13"),
                FakeDistribution(None),
            ],
        ), patch("materials_skills.cli.subprocess.run") as run:
            environment = detect_current_environment_details()

        self.assertEqual(environment.source, "current")
        self.assertEqual(environment.requested_format, "auto")
        self.assertEqual(environment.detected_format, "installed-distributions")
        self.assertEqual(environment.package_names, {"impedance", "mace-torch"})
        self.assertEqual(environment.package_versions["impedance"], "1.7.1")
        run.assert_not_called()

    def test_detect_current_environment_falls_back_to_pip_json(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["python", "-m", "pip", "list", "--format=json"],
            returncode=0,
            stdout='[{"name": "impedance"}, {"name": "rdkit"}]',
            stderr="",
        )
        with patch("materials_skills.cli.metadata.distributions", return_value=[]), patch(
            "materials_skills.cli.subprocess.run",
            return_value=completed,
        ) as run:
            packages = detect_current_environment()

        self.assertEqual(packages, {"impedance", "rdkit"})
        run.assert_called_once()


class RegistryTests(unittest.TestCase):
    def test_cli_version_flag_reports_package_version(self) -> None:
        with capture_stdout() as output:
            with self.assertRaises(SystemExit) as exc:
                main(["--version"])

        self.assertEqual(exc.exception.code, 0)
        self.assertEqual(output.getvalue().strip(), f"materials-skills {__version__}")

    def test_registry_skill_names_and_dirs_are_unique(self) -> None:
        skill_names = [record.skill_name for record in REGISTRY]
        skill_dirs = [record.skill_dir for record in REGISTRY]

        self.assertEqual(len(skill_names), len(set(skill_names)))
        self.assertEqual(len(skill_dirs), len(set(skill_dirs)))

    def test_registry_distribution_aliases_do_not_cross_map_skills(self) -> None:
        alias_to_skill: dict[str, str] = {}
        conflicts: list[tuple[str, str, str]] = []
        for record in REGISTRY:
            for distribution in record.distributions:
                alias = normalize_distribution_name(distribution)
                existing = alias_to_skill.setdefault(alias, record.skill_name)
                if existing != record.skill_name:
                    conflicts.append((alias, existing, record.skill_name))

        self.assertEqual(conflicts, [])

    def test_default_skills_root_contains_registered_skills(self) -> None:
        root = default_skills_root()
        for record in REGISTRY:
            self.assertTrue((root / record.skill_dir / "SKILL.md").is_file(), record.skill_name)

    def test_packaged_skills_match_source_skills(self) -> None:
        packaged_root = default_skills_root()
        for record in REGISTRY:
            source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
            packaged = packaged_root / record.skill_dir / "SKILL.md"
            self.assertEqual(packaged.read_text(encoding="utf-8"), source.read_text(encoding="utf-8"))

    def test_match_package_skills(self) -> None:
        records = match_skills(
            {
                "numpy",
                "ase",
                "hyperspy",
                "impedance",
                "mace-torch",
                "openmm",
                "pybamm",
                "pyscf",
                "py4DSTEM",
                "pymatgen",
                "rdkit",
                "scipy",
            }
        )
        self.assertEqual(
            [record.skill_name for record in records],
            [
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
            ],
        )

    def test_match_rdkit_pypi_alias(self) -> None:
        records = match_skills({"rdkit_pypi"})
        self.assertEqual([record.skill_name for record in records], ["rdkit"])

    def test_match_pybamm_base_alias(self) -> None:
        records = match_skills({"pybamm-base"})
        self.assertEqual([record.skill_name for record in records], ["pybamm"])

    def test_describe_skill_matches_preserves_installed_distribution_names(self) -> None:
        packages = {"py4DSTEM", "rdkit_pypi", "pybamm_base"}
        records = match_skills(packages)
        matches = {
            match.skill_name: match
            for match in describe_skill_matches(
                records,
                packages,
                {"py4DSTEM": "0.14.14", "rdkit_pypi": "2026.03.2", "pybamm_base": "26.4.0"},
                {"py4dstem": ">=0.14,<0.15", "rdkit": ">=2023.09,<2027", "pybamm": ">=25.0,<27"},
            )
        }
        self.assertEqual(matches["py4dstem"].matched_distributions, ("py4DSTEM",))
        self.assertEqual(matches["rdkit"].matched_distributions, ("rdkit_pypi",))
        self.assertEqual(matches["pybamm"].matched_distributions, ("pybamm_base",))
        self.assertEqual(dict(matches["py4dstem"].matched_versions), {"py4DSTEM": "0.14.14"})
        self.assertEqual(dict(matches["rdkit"].matched_versions), {"rdkit_pypi": "2026.03.2"})
        self.assertEqual(matches["py4dstem"].compatible_versions, ">=0.14,<0.15")
        self.assertEqual(matches["py4dstem"].compatibility, "compatible")
        self.assertEqual(matches["rdkit"].registered_distributions, ("rdkit", "rdkit-pypi"))

    def test_compatibility_status_reports_out_of_range_versions(self) -> None:
        self.assertEqual(compatibility_status({"py4DSTEM": "0.13.7"}, ">=0.14,<0.15"), "out-of-range")
        self.assertEqual(compatibility_status({"impedance": "1.7.1"}, ">=1.7,<2"), "compatible")
        self.assertEqual(compatibility_status({"impedance": "1.7rc1"}, ">=1.7,<2"), "unknown")
        self.assertEqual(compatibility_status({"openmm": "8.4.0+cpu"}, ">=8,<9"), "compatible")
        self.assertEqual(compatibility_status({}, ">=1.7,<2"), "unknown")

    def test_no_false_positive_from_generic_scientific_stack(self) -> None:
        records = match_skills({"numpy", "scipy", "pandas"})
        self.assertEqual(records, [])

    def test_select_install_targets_supports_all_agents(self) -> None:
        self.assertEqual(
            [str(path) for path in select_install_targets("all", None)],
            [".claude/skills", ".cursor/skills", ".codex/skills"],
        )
        self.assertEqual(select_install_targets("all", Path("custom-skills")), [Path("custom-skills")])

    def test_registry_payload_matches_registry(self) -> None:
        payload = registry_payload()
        self.assertEqual(len(payload), len(REGISTRY))
        self.assertEqual(payload[0], {"skill_name": "ase", "distributions": ["ase"], "skill_dir": "ase"})
        self.assertEqual(payload[3]["skill_name"], "mace")
        self.assertIn("mace-torch", payload[3]["distributions"])
        self.assertEqual(payload[7]["skill_name"], "pybamm")
        self.assertIn("pybamm-base", payload[7]["distributions"])

    def test_registry_command_json(self) -> None:
        with capture_stdout() as output:
            exit_code = main(["registry", "--json"])
        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(len(payload["skills"]), 12)
        self.assertEqual(payload["skills"][0]["skill_name"], "ase")
        self.assertIn("rdkit-pypi", payload["skills"][2]["distributions"])

    def test_static_registry_json_matches_runtime_registry(self) -> None:
        payload = json.loads((ROOT / "registry.json").read_text(encoding="utf-8"))
        self.assertEqual(payload, {"skills": registry_payload()})


class ResearchEvidenceTests(unittest.TestCase):
    def test_each_registered_skill_has_evidence_note(self) -> None:
        for record in REGISTRY:
            note = ROOT / "research" / f"{record.skill_name}.md"
            self.assertTrue(note.is_file(), record.skill_name)
            text = note.read_text(encoding="utf-8")
            self.assertIn("## Sources Reviewed", text, record.skill_name)
            self.assertIn("## Extracted Workflow", text, record.skill_name)
            self.assertRegex(text, r"## (Issue|Docs|Issue/Docs)-Derived Gotchas", record.skill_name)
            self.assertIn("## Open Follow-Ups", text, record.skill_name)
            self.assertGreaterEqual(text.count("http://") + text.count("https://"), 3, record.skill_name)


class RegistryJsonCheckTests(unittest.TestCase):
    def test_check_registry_json_accepts_runtime_registry_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry.json"
            registry.write_text(registry_json_text(), encoding="utf-8")

            self.assertEqual(check_registry_json(registry), [])

    def test_check_registry_json_reports_missing_invalid_and_stale_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing.json"
            invalid = root / "invalid.json"
            stale = root / "stale.json"
            invalid.write_text("{not json", encoding="utf-8")
            stale.write_text('{"skills": []}', encoding="utf-8")

            self.assertIn(f"missing registry JSON: {missing}", check_registry_json(missing))
            self.assertIn("invalid registry JSON", check_registry_json(invalid)[0])
            self.assertEqual(check_registry_json(stale), [f"stale registry JSON: {stale} differs from runtime registry"])

    def test_check_registry_json_rejects_noncanonical_formatting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry.json"
            registry.write_text(json.dumps({"skills": registry_payload()}, separators=(",", ":")), encoding="utf-8")

            self.assertEqual(check_registry_json(registry), [f"stale registry JSON: {registry} differs from runtime registry"])

    def test_check_registry_json_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry.json"
            registry.write_text(registry_json_text(), encoding="utf-8")

            with capture_stdout() as output:
                exit_code = check_registry_json_main(["--registry-json", str(registry)])

        self.assertEqual(exit_code, 0)
        self.assertIn("Registry JSON is in sync", output.getvalue())

    def test_write_registry_json_restores_canonical_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "nested" / "registry.json"

            write_registry_json(registry)

            self.assertEqual(registry.read_text(encoding="utf-8"), registry_json_text())
            self.assertEqual(check_registry_json(registry), [])

    def test_check_registry_json_write_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry.json"
            registry.write_text('{"skills": []}\n', encoding="utf-8")

            with capture_stdout() as output:
                exit_code = check_registry_json_main(["--registry-json", str(registry), "--write"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(check_registry_json(registry), [])
            self.assertIn("Wrote registry JSON", output.getvalue())


class DocsCoverageTests(unittest.TestCase):
    def test_cli_module_stays_thin(self) -> None:
        cli_lines = (ROOT / "src" / "materials_skills" / "cli.py").read_text(encoding="utf-8").splitlines()

        self.assertLessEqual(len(cli_lines), 220)

    def test_design_decisions_cover_original_open_questions(self) -> None:
        text = (ROOT / "docs" / "design-decisions.md").read_text(encoding="utf-8")
        for heading in (
            "## Registry Placement",
            "## Conda and Pip Mixed Environments",
            "## Minimum Useful Skill Content",
            "## Cross-Library Composition",
        ):
            self.assertIn(heading, text)
        self.assertIn("hosted registry unresolved", text)
        self.assertIn("minimum can probably shrink", text)
        self.assertIn("agent behavior is mixed", text)


class PackagedSkillSyncTests(unittest.TestCase):
    def make_skill_tree(self, root: Path) -> None:
        (root / "impedance").mkdir(parents=True)
        (root / "impedance" / "SKILL.md").write_text("impedance skill\n", encoding="utf-8")
        (root / "ase").mkdir()
        (root / "ase" / "SKILL.md").write_text("ase skill\n", encoding="utf-8")

    def test_check_sync_accepts_matching_trees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "skills"
            destination = Path(tmp) / "packaged"
            self.make_skill_tree(source)
            shutil.copytree(source, destination)
            self.assertEqual(check_sync(source, destination), [])

    def test_check_sync_reports_missing_extra_and_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "skills"
            destination = Path(tmp) / "packaged"
            self.make_skill_tree(source)
            shutil.copytree(source, destination)
            (destination / "impedance" / "SKILL.md").write_text("changed\n", encoding="utf-8")
            (destination / "ase" / "SKILL.md").unlink()
            (destination / "extra").mkdir()
            (destination / "extra" / "SKILL.md").write_text("extra\n", encoding="utf-8")

            errors = check_sync(source, destination)

            self.assertIn("out-of-sync packaged file: impedance/SKILL.md", errors)
            self.assertIn("missing packaged file: ase/SKILL.md", errors)
            self.assertIn("extra packaged file: extra/SKILL.md", errors)

    def test_sync_script_check_mode_and_sync_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "skills"
            destination = Path(tmp) / "packaged"
            self.make_skill_tree(source)

            with capture_stdout() as output:
                exit_code = sync_skills_main(["--source", str(source), "--destination", str(destination), "--check"])
            self.assertEqual(exit_code, 1)
            self.assertIn("missing packaged skills directory", output.getvalue())

            with capture_stdout():
                exit_code = sync_skills_main(["--source", str(source), "--destination", str(destination)])
            self.assertEqual(exit_code, 0)

            with capture_stdout() as output:
                exit_code = sync_skills_main(["--source", str(source), "--destination", str(destination), "--check"])
            self.assertEqual(exit_code, 0)
            self.assertIn("Packaged skills are in sync", output.getvalue())


class WheelSkillPayloadTests(unittest.TestCase):
    def write_wheel(self, path: Path, names: list[str]) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            for index, name in enumerate(names):
                archive.writestr(name, f"content {index}")

    def expected_wheel_skill_names(self) -> list[str]:
        return [
            f"materials_skills/skills/{record.skill_dir}/SKILL.md"
            for record in REGISTRY
        ]

    def test_check_wheel_skills_accepts_one_skill_per_registry_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wheel = Path(tmp) / "materials_skills-0.1.0-py3-none-any.whl"
            self.write_wheel(wheel, self.expected_wheel_skill_names())

            self.assertEqual(check_wheel_skills(wheel), [])

    def test_check_wheel_skills_reports_missing_and_extra_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wheel = Path(tmp) / "materials_skills-0.1.0-py3-none-any.whl"
            names = self.expected_wheel_skill_names()
            names.remove("materials_skills/skills/impedance/SKILL.md")
            names.append("materials_skills/skills/extra/SKILL.md")
            self.write_wheel(wheel, names)

            errors = check_wheel_skills(wheel)

            self.assertIn("missing wheel skill: materials_skills/skills/impedance/SKILL.md", errors)
            self.assertIn("extra wheel skill: materials_skills/skills/extra/SKILL.md", errors)

    def test_check_wheel_skills_rejects_source_only_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wheel = Path(tmp) / "materials_skills-0.1.0-py3-none-any.whl"
            names = self.expected_wheel_skill_names()
            names.extend([
                "eval/scripts/report_utils.py",
                "docs/v0-demo.md",
                "tests/test_cli.py",
            ])
            self.write_wheel(wheel, names)

            errors = check_wheel_skills(wheel)

            self.assertIn("source-only file included in wheel: eval/scripts/report_utils.py", errors)
            self.assertIn("source-only file included in wheel: docs/v0-demo.md", errors)
            self.assertIn("source-only file included in wheel: tests/test_cli.py", errors)

    def test_check_wheel_skills_reports_stale_skill_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "skills"
            for record in REGISTRY:
                skill_dir = source / record.skill_dir
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(f"{record.skill_name} current\n", encoding="utf-8")
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                for record in REGISTRY:
                    text = f"{record.skill_name} current\n"
                    if record.skill_name == "impedance":
                        text = "impedance stale\n"
                    archive.writestr(f"materials_skills/skills/{record.skill_dir}/SKILL.md", text)

            errors = check_wheel_skills(wheel, source_root=source)

            self.assertIn(
                f"stale wheel skill: materials_skills/skills/impedance/SKILL.md differs from {source / 'impedance' / 'SKILL.md'}",
                errors,
            )

    def test_check_wheel_skills_reports_stale_python_module_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_root = root / "materials_skills"
            package_root.mkdir()
            (package_root / "__init__.py").write_text("__version__ = '0.1.0'\n", encoding="utf-8")
            (package_root / "cli.py").write_text("current cli\n", encoding="utf-8")
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("materials_skills/__init__.py", "__version__ = '0.1.0'\n")
                archive.writestr("materials_skills/cli.py", "stale cli\n")
                archive.writestr("materials_skills/extra.py", "extra\n")

            errors = check_wheel_skills(wheel, package_root=package_root)

            self.assertIn(f"stale wheel module: materials_skills/cli.py differs from {package_root / 'cli.py'}", errors)
            self.assertIn("extra wheel module: materials_skills/extra.py", errors)

    def test_check_wheel_skills_reports_missing_console_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr(
                    "materials_skills-0.1.0.dist-info/entry_points.txt",
                    "[console_scripts]\nother = materials_skills.cli:main\n",
                )

            errors = check_wheel_skills(wheel, console_script="materials-skills")

            self.assertIn("missing wheel console script: materials-skills = materials_skills.cli:main", errors)

    def test_check_wheel_skills_accepts_console_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr(
                    "materials_skills-0.1.0.dist-info/entry_points.txt",
                    "[console_scripts]\nmaterials-skills = materials_skills.cli:main\n",
                )

            errors = check_wheel_skills(wheel, console_script="materials-skills")

            self.assertNotIn("missing wheel console script: materials-skills = materials_skills.cli:main", errors)

    def test_check_wheel_skills_reports_version_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_root = root / "materials_skills"
            package_root.mkdir()
            pyproject = root / "pyproject.toml"
            pyproject.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")
            (package_root / "__init__.py").write_text('__version__ = "0.2.0"\n', encoding="utf-8")
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("materials_skills-0.1.0.dist-info/METADATA", "Name: materials-skills\nVersion: 0.3.0\n")

            errors = check_wheel_skills(wheel, package_root=package_root, pyproject=pyproject)

            self.assertIn("version mismatch: pyproject 0.1.0 != __version__ 0.2.0", errors)
            self.assertIn("version mismatch: pyproject 0.1.0 != wheel 0.3.0", errors)

    def test_check_wheel_skills_reports_stale_readme_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme = root / "README.md"
            readme.write_text("# Current README\n", encoding="utf-8")
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr(
                    "materials_skills-0.1.0.dist-info/METADATA",
                    "Name: materials-skills\nVersion: 0.1.0\n\n# Stale README\n",
                )

            errors = check_wheel_skills(wheel, readme=readme)

            self.assertIn(f"stale wheel README metadata: METADATA does not include {readme}", errors)

    def test_check_wheel_skills_accepts_current_readme_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme = root / "README.md"
            readme.write_text("# Current README\n", encoding="utf-8")
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr(
                    "materials_skills-0.1.0.dist-info/METADATA",
                    "Name: materials-skills\nVersion: 0.1.0\n\n# Current README\n",
                )

            errors = check_wheel_skills(wheel, readme=readme)

            self.assertNotIn(f"stale wheel README metadata: METADATA does not include {readme}", errors)

    def test_check_wheel_skills_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wheel = Path(tmp) / "materials_skills-0.1.0-py3-none-any.whl"
            self.write_wheel(wheel, self.expected_wheel_skill_names())

            with capture_stdout() as output:
                exit_code = check_wheel_skills_main([str(wheel)])

        self.assertEqual(exit_code, 0)
        self.assertIn("Wheel payload is complete", output.getvalue())


class SdistPayloadTests(unittest.TestCase):
    def write_sdist(self, path: Path, files: dict[str, str]) -> None:
        with tarfile.open(path, "w:gz") as archive:
            for name, text in files.items():
                data = text.encode("utf-8")
                info = tarfile.TarInfo(f"materials_skills-0.1.0/{name}")
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))

    def write_sdist_entries(self, path: Path, entries: list[tuple[str, str]]) -> None:
        with tarfile.open(path, "w:gz") as archive:
            for name, text in entries:
                data = text.encode("utf-8")
                info = tarfile.TarInfo(f"materials_skills-0.1.0/{name}")
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))

    def minimal_sdist_files(self) -> dict[str, str]:
        files: dict[str, str] = {}
        for record in REGISTRY:
            files[f"skills/{record.skill_dir}/SKILL.md"] = f"{record.skill_name} source\n"
            files[f"src/materials_skills/skills/{record.skill_dir}/SKILL.md"] = f"{record.skill_name} packaged\n"
        files["src/materials_skills/__init__.py"] = "__version__ = '0.1.0'\n"
        files["src/materials_skills/cli.py"] = "cli\n"
        files["src/materials_skills/registry.py"] = "registry\n"
        files["scripts/check_local_v0.py"] = "local gate\n"
        files["scripts/check_registry_json.py"] = "registry gate\n"
        files["docs/v0-demo.md"] = "demo\n"
        files["docs/writeup.md"] = "writeup\n"
        files["registry.json"] = '{"skills": []}\n'
        files["README.md"] = "# README\n"
        files["pyproject.toml"] = "[project]\nversion = '0.1.0'\n"
        return files

    def test_check_sdist_payload_accepts_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sdist = root / "materials_skills-0.1.0.tar.gz"
            self.write_sdist(sdist, self.minimal_sdist_files())

            self.assertEqual(check_sdist_payload(sdist), [])

    def test_check_sdist_payload_reports_missing_and_extra_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = self.minimal_sdist_files()
            del files["skills/impedance/SKILL.md"]
            files["skills/extra/SKILL.md"] = "extra\n"
            sdist = root / "materials_skills-0.1.0.tar.gz"
            self.write_sdist(sdist, files)

            errors = check_sdist_payload(sdist)

            self.assertIn("missing sdist source skill: skills/impedance/SKILL.md", errors)
            self.assertIn("extra sdist source skill: skills/extra/SKILL.md", errors)

    def test_check_sdist_payload_reports_duplicate_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sdist = root / "materials_skills-0.1.0.tar.gz"
            entries = list(self.minimal_sdist_files().items())
            entries.append(("README.md", "# Duplicate README\n"))
            self.write_sdist_entries(sdist, entries)

            errors = check_sdist_payload(sdist)

            self.assertIn("duplicate sdist file: README.md appears 2 times", errors)

    def test_check_sdist_payload_reports_stale_source_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "skills"
            package_root = root / "src" / "materials_skills"
            for record in REGISTRY:
                (source / record.skill_dir).mkdir(parents=True)
                (source / record.skill_dir / "SKILL.md").write_text(f"{record.skill_name} current\n", encoding="utf-8")
                (package_root / "skills" / record.skill_dir).mkdir(parents=True)
                (package_root / "skills" / record.skill_dir / "SKILL.md").write_text(
                    f"{record.skill_name} packaged\n", encoding="utf-8"
                )
            package_root.mkdir(parents=True, exist_ok=True)
            (package_root / "__init__.py").write_text("__version__ = '0.1.0'\n", encoding="utf-8")
            (package_root / "cli.py").write_text("current cli\n", encoding="utf-8")
            (package_root / "registry.py").write_text("registry\n", encoding="utf-8")
            files = self.minimal_sdist_files()
            sdist = root / "materials_skills-0.1.0.tar.gz"
            self.write_sdist(sdist, files)

            errors = check_sdist_payload(sdist, source_root=source, package_root=package_root)

            self.assertIn(
                f"stale sdist source skill: skills/impedance/SKILL.md differs from {source / 'impedance' / 'SKILL.md'}",
                errors,
            )
            self.assertIn(f"stale sdist module: src/materials_skills/cli.py differs from {package_root / 'cli.py'}", errors)

    def test_check_sdist_payload_reports_stale_readme_and_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme = root / "README.md"
            pyproject = root / "pyproject.toml"
            readme.write_text("# Current README\n", encoding="utf-8")
            pyproject.write_text("[project]\nversion = '0.1.0'\n", encoding="utf-8")
            sdist = root / "materials_skills-0.1.0.tar.gz"
            self.write_sdist(sdist, self.minimal_sdist_files())

            errors = check_sdist_payload(sdist, readme=readme, pyproject=pyproject)

            self.assertIn(f"stale sdist README: README.md differs from {readme}", errors)
            self.assertNotIn(f"stale sdist pyproject: pyproject.toml differs from {pyproject}", errors)

    def test_check_sdist_payload_reports_stale_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "v0-demo.md").write_text("current demo\n", encoding="utf-8")
            (docs / "writeup.md").write_text("writeup\n", encoding="utf-8")
            files = self.minimal_sdist_files()
            files["docs/extra.md"] = "extra\n"
            sdist = root / "materials_skills-0.1.0.tar.gz"
            self.write_sdist(sdist, files)

            errors = check_sdist_payload(sdist, docs_root=docs)

            self.assertIn(f"stale sdist doc: docs/v0-demo.md differs from {docs / 'v0-demo.md'}", errors)
            self.assertIn("extra sdist doc: docs/extra.md", errors)

    def test_check_sdist_payload_reports_stale_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "check_local_v0.py").write_text("current local gate\n", encoding="utf-8")
            (scripts / "check_registry_json.py").write_text("registry gate\n", encoding="utf-8")
            files = self.minimal_sdist_files()
            files["scripts/extra.py"] = "extra\n"
            sdist = root / "materials_skills-0.1.0.tar.gz"
            self.write_sdist(sdist, files)

            errors = check_sdist_payload(sdist, scripts_root=scripts)

            self.assertIn(f"stale sdist script: scripts/check_local_v0.py differs from {scripts / 'check_local_v0.py'}", errors)
            self.assertIn("extra sdist script: scripts/extra.py", errors)

    def test_check_sdist_payload_reports_stale_eval_and_research_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            eval_root = root / "eval"
            research_root = root / "research"
            (eval_root / "scripts").mkdir(parents=True)
            research_root.mkdir()
            (eval_root / "README.md").write_text("current eval readme\n", encoding="utf-8")
            (eval_root / "scripts" / "run_claude_eval.py").write_text("current runner\n", encoding="utf-8")
            (research_root / "impedance.md").write_text("current impedance research\n", encoding="utf-8")
            files = self.minimal_sdist_files()
            files["eval/README.md"] = "stale eval readme\n"
            files["eval/scripts/run_claude_eval.py"] = "current runner\n"
            files["eval/extra.json"] = "{}\n"
            files["research/impedance.md"] = "stale impedance research\n"
            files["research/extra.md"] = "extra\n"
            sdist = root / "materials_skills-0.1.0.tar.gz"
            self.write_sdist(sdist, files)

            errors = check_sdist_payload(sdist, eval_root=eval_root, research_root=research_root)

            self.assertIn(f"stale sdist eval file: eval/README.md differs from {eval_root / 'README.md'}", errors)
            self.assertIn("extra sdist eval file: eval/extra.json", errors)
            self.assertIn(
                f"stale sdist research note: research/impedance.md differs from {research_root / 'impedance.md'}",
                errors,
            )
            self.assertIn("extra sdist research note: research/extra.md", errors)

    def test_check_sdist_payload_reports_stale_test_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tests_root = root / "tests"
            fixtures = tests_root / "fixtures"
            fixtures.mkdir(parents=True)
            (tests_root / "test_cli.py").write_text("current tests\n", encoding="utf-8")
            (fixtures / "pip-list.txt").write_text("current fixture\n", encoding="utf-8")
            files = self.minimal_sdist_files()
            files["tests/test_cli.py"] = "stale tests\n"
            files["tests/fixtures/pip-list.txt"] = "current fixture\n"
            files["tests/fixtures/extra.json"] = "{}\n"
            sdist = root / "materials_skills-0.1.0.tar.gz"
            self.write_sdist(sdist, files)

            errors = check_sdist_payload(sdist, tests_root=tests_root)

            self.assertIn(f"stale sdist test file: tests/test_cli.py differs from {tests_root / 'test_cli.py'}", errors)
            self.assertIn("extra sdist test file: tests/fixtures/extra.json", errors)

    def test_check_sdist_payload_reports_stale_registry_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "registry.json"
            registry.write_text('{"skills": [{"skill_name": "ase"}]}\n', encoding="utf-8")
            sdist = root / "materials_skills-0.1.0.tar.gz"
            self.write_sdist(sdist, self.minimal_sdist_files())

            errors = check_sdist_payload(sdist, registry_json=registry)

            self.assertIn(f"stale sdist registry: registry.json differs from {registry}", errors)

    def test_check_sdist_payload_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sdist = Path(tmp) / "materials_skills-0.1.0.tar.gz"
            self.write_sdist(sdist, self.minimal_sdist_files())

            with capture_stdout() as output:
                exit_code = check_sdist_payload_main([str(sdist)])

        self.assertEqual(exit_code, 0)
        self.assertIn("Source distribution payload is complete", output.getvalue())


class WheelInstallSmokeTests(unittest.TestCase):
    def completed(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["mock"], returncode, stdout=stdout, stderr=stderr)

    def test_wheel_filename_version_extracts_built_version(self) -> None:
        self.assertEqual(
            wheel_filename_version(Path("materials_skills-0.1.0-py3-none-any.whl")),
            "0.1.0",
        )
        self.assertEqual(wheel_filename_version(Path("not-a-materials-wheel.whl")), "")

    def test_smoke_wheel_install_runs_installed_console_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            wheel.write_bytes(b"wheel")
            env_file = root / "pip-list.txt"
            env_file.write_text("ase\nimpedance\n", encoding="utf-8")

            def fake_run(command, cwd=ROOT):
                command_text = [str(part) for part in command]
                if command_text[1:3] == ["-m", "venv"]:
                    return self.completed()
                if command_text[1:] == ["install", "--no-index", str(wheel)]:
                    return self.completed()
                if command_text[-1:] == ["--version"]:
                    return self.completed(stdout="materials-skills 0.1.0\n")
                if command_text[-2:] == ["validate", "--json"]:
                    return self.completed(stdout='{"ok": true, "errors": []}')
                if command_text[-2:] == ["registry", "--json"]:
                    return self.completed(stdout='{"skills": [{"skill_name": "ase"}]}')
                if "install" in command_text and "--env" in command_text:
                    if "--agent" in command_text:
                        return self.completed(
                            stdout='{"agent": "all", "target": null, "targets": [".claude/skills", ".cursor/skills", ".codex/skills"], "skills": ["ase"], "dry_run": true}'
                        )
                    target = Path(command_text[command_text.index("--target") + 1])
                    target_skill = target / "ase" / "SKILL.md"
                    target_skill.parent.mkdir(parents=True)
                    target_skill.write_text("skill\n", encoding="utf-8")
                    return self.completed(stdout='{"agent": "claude", "skills": ["ase"]}')
                return self.completed(stderr=f"unexpected command: {command_text}", returncode=1)

            with patch.object(wheel_install_script, "venv_bin", side_effect=lambda venv, command: root / "venv" / "bin" / command):
                with patch.object(wheel_install_script, "run", side_effect=fake_run):
                    errors = smoke_wheel_install(wheel, env_file, expected_skill_count=1)

            self.assertEqual(errors, [])

    def test_smoke_wheel_install_reports_missing_wheel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            errors = smoke_wheel_install(
                Path(tmp) / "missing.whl",
                FIXTURES / "pip-list.txt",
                expected_skill_count=12,
            )

        self.assertIn("missing wheel", errors[0])

    def test_smoke_wheel_install_rejects_wrong_installed_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            wheel.write_bytes(b"wheel")
            env_file = root / "pip-list.txt"
            env_file.write_text("ase\n", encoding="utf-8")

            def fake_run(command, cwd=ROOT):
                command_text = [str(part) for part in command]
                if command_text[1:3] == ["-m", "venv"]:
                    return self.completed()
                if command_text[1:] == ["install", "--no-index", str(wheel)]:
                    return self.completed()
                if command_text[-1:] == ["--version"]:
                    return self.completed(stdout="materials-skills 0.2.0\n")
                if command_text[-2:] == ["validate", "--json"]:
                    return self.completed(stdout='{"ok": true, "errors": []}')
                if command_text[-2:] == ["registry", "--json"]:
                    return self.completed(stdout='{"skills": [{"skill_name": "ase"}]}')
                if "install" in command_text and "--env" in command_text:
                    if "--agent" in command_text:
                        return self.completed(
                            stdout='{"agent": "all", "target": null, "targets": [".claude/skills", ".cursor/skills", ".codex/skills"], "skills": ["ase"], "dry_run": true}'
                        )
                    target = Path(command_text[command_text.index("--target") + 1])
                    target_skill = target / "ase" / "SKILL.md"
                    target_skill.parent.mkdir(parents=True)
                    target_skill.write_text("skill\n", encoding="utf-8")
                    return self.completed(stdout='{"agent": "claude", "skills": ["ase"]}')
                return self.completed(stderr=f"unexpected command: {command_text}", returncode=1)

            with patch.object(wheel_install_script, "venv_bin", side_effect=lambda venv, command: root / "venv" / "bin" / command):
                with patch.object(wheel_install_script, "run", side_effect=fake_run):
                    errors = smoke_wheel_install(wheel, env_file, expected_skill_count=1)

            self.assertIn("expected 'materials-skills 0.1.0'", "\n".join(errors))

    def test_smoke_wheel_install_rejects_missing_installed_agent_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            wheel.write_bytes(b"wheel")
            env_file = root / "pip-list.txt"
            env_file.write_text("ase\n", encoding="utf-8")

            def fake_run(command, cwd=ROOT):
                command_text = [str(part) for part in command]
                if command_text[1:3] == ["-m", "venv"]:
                    return self.completed()
                if command_text[1:] == ["install", "--no-index", str(wheel)]:
                    return self.completed()
                if command_text[-1:] == ["--version"]:
                    return self.completed(stdout="materials-skills 0.1.0\n")
                if command_text[-2:] == ["validate", "--json"]:
                    return self.completed(stdout='{"ok": true, "errors": []}')
                if command_text[-2:] == ["registry", "--json"]:
                    return self.completed(stdout='{"skills": [{"skill_name": "ase"}]}')
                if "install" in command_text and "--env" in command_text:
                    if "--agent" in command_text:
                        return self.completed(
                            stdout='{"agent": "all", "target": null, "targets": [".claude/skills", ".cursor/skills", ".codex/skills"], "skills": ["ase"], "dry_run": true}'
                        )
                    target = Path(command_text[command_text.index("--target") + 1])
                    target_skill = target / "ase" / "SKILL.md"
                    target_skill.parent.mkdir(parents=True)
                    target_skill.write_text("skill\n", encoding="utf-8")
                    return self.completed(stdout='{"skills": ["ase"]}')
                return self.completed(stderr=f"unexpected command: {command_text}", returncode=1)

            with patch.object(wheel_install_script, "venv_bin", side_effect=lambda venv, command: root / "venv" / "bin" / command):
                with patch.object(wheel_install_script, "run", side_effect=fake_run):
                    errors = smoke_wheel_install(wheel, env_file, expected_skill_count=1)

            self.assertIn("installed install command returned agent None, expected 'claude'", errors)

    def test_smoke_wheel_install_rejects_bad_installed_agent_all_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            wheel.write_bytes(b"wheel")
            env_file = root / "pip-list.txt"
            env_file.write_text("ase\n", encoding="utf-8")

            def fake_run(command, cwd=ROOT):
                command_text = [str(part) for part in command]
                if command_text[1:3] == ["-m", "venv"]:
                    return self.completed()
                if command_text[1:] == ["install", "--no-index", str(wheel)]:
                    return self.completed()
                if command_text[-1:] == ["--version"]:
                    return self.completed(stdout="materials-skills 0.1.0\n")
                if command_text[-2:] == ["validate", "--json"]:
                    return self.completed(stdout='{"ok": true, "errors": []}')
                if command_text[-2:] == ["registry", "--json"]:
                    return self.completed(stdout='{"skills": [{"skill_name": "ase"}]}')
                if "install" in command_text and "--env" in command_text:
                    if "--agent" in command_text:
                        return self.completed(
                            stdout='{"agent": "claude", "target": ".claude/skills", "targets": [".claude/skills"], "skills": ["rdkit"], "dry_run": false}'
                        )
                    target = Path(command_text[command_text.index("--target") + 1])
                    target_skill = target / "ase" / "SKILL.md"
                    target_skill.parent.mkdir(parents=True)
                    target_skill.write_text("skill\n", encoding="utf-8")
                    return self.completed(stdout='{"agent": "claude", "skills": ["ase"]}')
                return self.completed(stderr=f"unexpected command: {command_text}", returncode=1)

            with patch.object(wheel_install_script, "venv_bin", side_effect=lambda venv, command: root / "venv" / "bin" / command):
                with patch.object(wheel_install_script, "run", side_effect=fake_run):
                    errors = smoke_wheel_install(wheel, env_file, expected_skill_count=1)

            text = "\n".join(errors)
            self.assertIn("installed --agent all dry-run returned agent 'claude', expected 'all'", text)
            self.assertIn("installed --agent all dry-run selected ['rdkit'], expected ['ase']", text)
            self.assertIn("installed --agent all dry-run returned target '.claude/skills', expected None", text)
            self.assertIn("installed --agent all dry-run returned targets ['.claude/skills'], expected", text)
            self.assertIn("installed --agent all dry-run returned dry_run False, expected True", text)

    def test_smoke_wheel_install_rejects_wrong_skill_names_with_right_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            wheel.write_bytes(b"wheel")
            env_file = root / "pip-list.txt"
            env_file.write_text("ase\nimpedance\n", encoding="utf-8")

            def fake_run(command, cwd=ROOT):
                command_text = [str(part) for part in command]
                if command_text[1:3] == ["-m", "venv"]:
                    return self.completed()
                if command_text[1:] == ["install", "--no-index", str(wheel)]:
                    return self.completed()
                if command_text[-1:] == ["--version"]:
                    return self.completed(stdout="materials-skills 0.1.0\n")
                if command_text[-2:] == ["validate", "--json"]:
                    return self.completed(stdout='{"ok": true, "errors": []}')
                if command_text[-2:] == ["registry", "--json"]:
                    return self.completed(stdout='{"skills": [{"skill_name": "ase"}, {"skill_name": "impedance"}]}')
                if "install" in command_text and "--env" in command_text:
                    if "--agent" in command_text:
                        return self.completed(
                            stdout='{"agent": "all", "target": null, "targets": [".claude/skills", ".cursor/skills", ".codex/skills"], "skills": ["ase", "impedance"], "dry_run": true}'
                        )
                    target = Path(command_text[command_text.index("--target") + 1])
                    for skill in ("ase", "rdkit"):
                        skill_file = target / skill / "SKILL.md"
                        skill_file.parent.mkdir(parents=True)
                        skill_file.write_text("skill\n", encoding="utf-8")
                    return self.completed(stdout='{"agent": "claude", "skills": ["ase", "rdkit"]}')
                return self.completed(stderr=f"unexpected command: {command_text}", returncode=1)

            with patch.object(wheel_install_script, "venv_bin", side_effect=lambda venv, command: root / "venv" / "bin" / command):
                with patch.object(wheel_install_script, "run", side_effect=fake_run):
                    errors = smoke_wheel_install(wheel, env_file, expected_skill_count=2)

            self.assertIn("expected ['ase', 'impedance']", "\n".join(errors))
            self.assertIn("installed skill missing from target: impedance", errors)

    def test_smoke_wheel_install_rejects_extra_target_skill_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            wheel.write_bytes(b"wheel")
            env_file = root / "pip-list.txt"
            env_file.write_text("ase\n", encoding="utf-8")

            def fake_run(command, cwd=ROOT):
                command_text = [str(part) for part in command]
                if command_text[1:3] == ["-m", "venv"]:
                    return self.completed()
                if command_text[1:] == ["install", "--no-index", str(wheel)]:
                    return self.completed()
                if command_text[-1:] == ["--version"]:
                    return self.completed(stdout="materials-skills 0.1.0\n")
                if command_text[-2:] == ["validate", "--json"]:
                    return self.completed(stdout='{"ok": true, "errors": []}')
                if command_text[-2:] == ["registry", "--json"]:
                    return self.completed(stdout='{"skills": [{"skill_name": "ase"}]}')
                if "install" in command_text and "--env" in command_text:
                    if "--agent" in command_text:
                        return self.completed(
                            stdout='{"agent": "all", "target": null, "targets": [".claude/skills", ".cursor/skills", ".codex/skills"], "skills": ["ase"], "dry_run": true}'
                        )
                    target = Path(command_text[command_text.index("--target") + 1])
                    for skill in ("ase", "extra"):
                        skill_file = target / skill / "SKILL.md"
                        skill_file.parent.mkdir(parents=True)
                        skill_file.write_text("skill\n", encoding="utf-8")
                    return self.completed(stdout='{"agent": "claude", "skills": ["ase"]}')
                return self.completed(stderr=f"unexpected command: {command_text}", returncode=1)

            with patch.object(wheel_install_script, "venv_bin", side_effect=lambda venv, command: root / "venv" / "bin" / command):
                with patch.object(wheel_install_script, "run", side_effect=fake_run):
                    errors = smoke_wheel_install(wheel, env_file, expected_skill_count=1)

            self.assertIn("installed target contains ['ase', 'extra'], expected ['ase']", errors)

    def test_smoke_wheel_install_rejects_malformed_json_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            wheel.write_bytes(b"wheel")
            env_file = root / "pip-list.txt"
            env_file.write_text("ase\n", encoding="utf-8")

            def fake_registry_run(command, cwd=ROOT):
                command_text = [str(part) for part in command]
                if command_text[1:3] == ["-m", "venv"]:
                    return self.completed()
                if command_text[1:] == ["install", "--no-index", str(wheel)]:
                    return self.completed()
                if command_text[-1:] == ["--version"]:
                    return self.completed(stdout="materials-skills 0.1.0\n")
                if command_text[-2:] == ["validate", "--json"]:
                    return self.completed(stdout='{"ok": true, "errors": []}')
                if command_text[-2:] == ["registry", "--json"]:
                    return self.completed(stdout='{"agent": "claude", "skills": "ase"}')
                return self.completed(stderr=f"unexpected command: {command_text}", returncode=1)

            with patch.object(wheel_install_script, "venv_bin", side_effect=lambda venv, command: root / "venv" / "bin" / command):
                with patch.object(wheel_install_script, "run", side_effect=fake_registry_run):
                    registry_errors = smoke_wheel_install(wheel, env_file, expected_skill_count=1)

            def fake_install_run(command, cwd=ROOT):
                command_text = [str(part) for part in command]
                if command_text[1:3] == ["-m", "venv"]:
                    return self.completed()
                if command_text[1:] == ["install", "--no-index", str(wheel)]:
                    return self.completed()
                if command_text[-1:] == ["--version"]:
                    return self.completed(stdout="materials-skills 0.1.0\n")
                if command_text[-2:] == ["validate", "--json"]:
                    return self.completed(stdout='{"ok": true, "errors": []}')
                if command_text[-2:] == ["registry", "--json"]:
                    return self.completed(stdout='{"skills": [{"skill_name": "ase"}]}')
                if "install" in command_text and "--env" in command_text:
                    return self.completed(stdout='{"agent": "claude", "skills": "ase"}')
                return self.completed(stderr=f"unexpected command: {command_text}", returncode=1)

            with patch.object(wheel_install_script, "venv_bin", side_effect=lambda venv, command: root / "venv" / "bin" / command):
                with patch.object(wheel_install_script, "run", side_effect=fake_install_run):
                    install_errors = smoke_wheel_install(wheel, env_file, expected_skill_count=1)

            self.assertEqual(registry_errors, ["installed registry JSON must be an object with a skills list"])
            self.assertEqual(install_errors, ["installed install command JSON must be an object with a skills list"])

    def test_smoke_wheel_install_rejects_unhashable_malformed_skill_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "materials_skills-0.1.0-py3-none-any.whl"
            wheel.write_bytes(b"wheel")
            env_file = root / "pip-list.txt"
            env_file.write_text("ase\n", encoding="utf-8")

            def fake_run(command, cwd=ROOT):
                command_text = [str(part) for part in command]
                if command_text[1:3] == ["-m", "venv"]:
                    return self.completed()
                if command_text[1:] == ["install", "--no-index", str(wheel)]:
                    return self.completed()
                if command_text[-1:] == ["--version"]:
                    return self.completed(stdout="materials-skills 0.1.0\n")
                if command_text[-2:] == ["validate", "--json"]:
                    return self.completed(stdout='{"ok": true, "errors": []}')
                if command_text[-2:] == ["registry", "--json"]:
                    return self.completed(stdout='{"skills": [{"skill_name": ["ase"]}]}')
                if "install" in command_text and "--env" in command_text:
                    return self.completed(stdout='{"agent": "claude", "skills": [["ase"]]}')
                return self.completed(stderr=f"unexpected command: {command_text}", returncode=1)

            with patch.object(wheel_install_script, "venv_bin", side_effect=lambda venv, command: root / "venv" / "bin" / command):
                with patch.object(wheel_install_script, "run", side_effect=fake_run):
                    errors = smoke_wheel_install(wheel, env_file, expected_skill_count=1)

            self.assertIn("installed registry contains duplicate or malformed skill names", errors)
            self.assertIn("installed install command returned malformed skill names", errors)


class LocalV0CheckTests(unittest.TestCase):
    def test_local_v0_check_script_runs_expected_gates(self) -> None:
        checks = {check.label: check.command for check in LOCAL_V0_CHECKS}

        self.assertEqual(
            list(checks),
            [
                "unit tests",
                "skill validation",
                "package-data sync",
                "registry JSON",
                "wheel payload",
                "wheel install smoke",
                "sdist payload",
            ],
        )
        self.assertIn("scripts/check_registry_json.py", checks["registry JSON"])
        self.assertIn("--registry-json", checks["registry JSON"])
        self.assertIn("--source-root", checks["wheel payload"])
        self.assertIn("--package-root", checks["wheel payload"])
        self.assertIn("--console-script", checks["wheel payload"])
        self.assertIn("--pyproject", checks["wheel payload"])
        self.assertIn("--readme", checks["wheel payload"])
        self.assertIn("scripts/check_wheel_install.py", checks["wheel install smoke"])
        self.assertIn("--source-root", checks["sdist payload"])
        self.assertIn("--package-root", checks["sdist payload"])
        self.assertIn("--scripts-root", checks["sdist payload"])
        self.assertIn("--docs-root", checks["sdist payload"])
        self.assertIn("--eval-root", checks["sdist payload"])
        self.assertIn("--research-root", checks["sdist payload"])
        self.assertIn("--tests-root", checks["sdist payload"])
        self.assertIn("--registry-json", checks["sdist payload"])
        self.assertIn("--readme", checks["sdist payload"])
        self.assertIn("--pyproject", checks["sdist payload"])

    def test_local_v0_check_prints_each_gate_before_running_it(self) -> None:
        run_calls: list[str] = []

        def fake_run(command, cwd=None, env=None, check=False):
            run_calls.append(command[0])
            return subprocess.CompletedProcess(command, 0)

        with (
            patch("scripts.check_local_v0.subprocess.run", side_effect=fake_run),
            patch("builtins.print") as print_mock,
        ):
            exit_code = local_v0_script.main()

        self.assertEqual(exit_code, 0)
        step_prints = [mock_call for mock_call in print_mock.call_args_list if str(mock_call.args[0]).startswith("==>")]
        self.assertEqual(len(step_prints), len(LOCAL_V0_CHECKS))
        self.assertEqual(
            step_prints,
            [call(f"==> {check.label}", flush=True) for check in LOCAL_V0_CHECKS],
        )
        self.assertEqual(len(run_calls), len(LOCAL_V0_CHECKS))


class V0StatusTests(unittest.TestCase):
    def complete_artifact(self) -> dict[str, object]:
        return {
            "ok": True,
            "blockers": [],
            "evaluation": {"problems": []},
            "scoring": {"problems": []},
        }

    def incomplete_artifact(self) -> dict[str, object]:
        return {
            "ok": False,
            "blockers": ["evaluation", "scoring"],
            "evaluation": {"problems": ["missing results file"]},
            "scoring": {"problems": ["not-scored"]},
        }

    def many_problem_artifact(self) -> dict[str, object]:
        return {
            "ok": False,
            "blockers": ["evaluation", "scoring"],
            "evaluation": {"problems": ["missing results file"]},
            "scoring": {"problems": [f"problem {index}" for index in range(5)]},
        }

    def test_v0_status_reports_complete_when_local_and_empirical_gates_pass(self) -> None:
        with (
            patch("scripts.check_v0_status.run_unit_tests", return_value=[]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=[]),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.complete_artifact(), self.complete_artifact()]),
            capture_stdout() as output,
        ):
            exit_code = v0_status_script.main(["--json"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["local"]["ok"])
        self.assertEqual(payload["local"]["unit_tests"], [])
        self.assertTrue(payload["empirical"]["ok"])
        self.assertEqual(payload["blockers"], [])
        self.assertEqual(payload["next_steps"], [])
        self.assertEqual(payload["automation_steps"], [])

    def test_v0_status_reports_incomplete_when_empirical_artifacts_are_missing(self) -> None:
        with (
            patch("scripts.check_v0_status.run_unit_tests", return_value=[]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=[]),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.incomplete_artifact(), self.incomplete_artifact()]),
            capture_stdout() as output,
        ):
            exit_code = v0_status_script.main(["--json"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["local"]["ok"])
        self.assertFalse(payload["empirical"]["ok"])
        self.assertEqual(payload["blockers"], ["empirical-artifacts"])
        self.assertEqual(payload["empirical"]["impedance"]["blockers"], ["evaluation", "scoring"])
        self.assertEqual(payload["empirical"]["full_matrix"]["blockers"], ["evaluation", "scoring"])
        self.assertIn("missing results file", payload["empirical"]["impedance"]["evaluation"]["problems"])
        self.assertEqual(
            payload["next_steps"],
            [
                "claude auth login",
                "claude auth status --json",
                "python eval/scripts/run_claude_eval.py --preflight-only --max-budget-usd 0.05",
                "python eval/scripts/run_impedance_pipeline.py --resume",
                "Manually score eval/impedance/score-report.md",
                "python eval/scripts/run_impedance_pipeline.py --skip-model-run --check-scored",
                "python eval/scripts/run_v0_pipeline.py --resume",
                "Manually score eval/score-report.md",
                "python eval/scripts/run_v0_pipeline.py --skip-model-run --check-scored",
            ],
        )
        self.assertEqual(
            payload["automation_steps"],
            [
                "python eval/scripts/run_impedance_pipeline.py --skip-model-run --check-scored --json",
                "python eval/scripts/run_v0_pipeline.py --skip-model-run --check-scored --json",
            ],
        )

    def test_v0_status_reports_incomplete_when_unit_tests_fail(self) -> None:
        with (
            patch("scripts.check_v0_status.run_unit_tests", return_value=["unit tests failed"]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=[]),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.complete_artifact(), self.complete_artifact()]),
            capture_stdout() as output,
        ):
            exit_code = v0_status_script.main(["--json"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["local"]["ok"])
        self.assertEqual(payload["local"]["unit_tests"], ["unit tests failed"])
        self.assertTrue(payload["empirical"]["ok"])
        self.assertEqual(payload["blockers"], ["local-readiness"])
        self.assertEqual(payload["next_steps"], ["Fix local readiness errors.", "python scripts/check_local_v0.py"])
        self.assertEqual(payload["automation_steps"], [])

    def test_v0_status_reports_all_blockers_but_prioritizes_local_next_steps(self) -> None:
        with (
            patch("scripts.check_v0_status.run_unit_tests", return_value=["unit tests failed"]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=[]),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.incomplete_artifact(), self.incomplete_artifact()]),
            capture_stdout() as output,
        ):
            exit_code = v0_status_script.main(["--json"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["blockers"], ["local-readiness", "empirical-artifacts"])
        self.assertEqual(payload["next_steps"], ["Fix local readiness errors.", "python scripts/check_local_v0.py"])
        self.assertEqual(payload["automation_steps"], [])

    def test_v0_status_reports_incomplete_when_sdist_payload_fails(self) -> None:
        with (
            patch("scripts.check_v0_status.run_unit_tests", return_value=[]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=["stale sdist README"]),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.complete_artifact(), self.complete_artifact()]),
            capture_stdout() as output,
        ):
            exit_code = v0_status_script.main(["--json"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["local"]["ok"])
        self.assertEqual(payload["local"]["sdist_payload"], ["stale sdist README"])

    def test_v0_status_reports_incomplete_when_registry_json_fails(self) -> None:
        with (
            patch("scripts.check_v0_status.run_unit_tests", return_value=[]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_registry_json", return_value=["stale registry JSON"]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=[]),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.complete_artifact(), self.complete_artifact()]),
            capture_stdout() as output,
        ):
            exit_code = v0_status_script.main(["--json"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["local"]["ok"])
        self.assertEqual(payload["local"]["registry_json"], ["stale registry JSON"])

    def test_v0_status_checks_impedance_and_full_artifacts_separately(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("scripts.check_v0_status.run_unit_tests", return_value=[]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=[]),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.complete_artifact(), self.complete_artifact()]) as artifacts,
            capture_stdout(),
        ):
            root = Path(tmp)
            impedance_tasks = root / "impedance-tasks.json"
            impedance_results = root / "impedance-results.jsonl"
            impedance_report = root / "impedance-score-report.md"
            full_tasks = root / "full-tasks.json"
            full_results = root / "full-results.jsonl"
            full_report = root / "full-score-report.md"
            task_payload = [
                {
                    "id": "impedance-fit-randles-cpe-warburg",
                    "skill": "impedance",
                    "title": "Title",
                    "prompt": "Prompt",
                    "success_criteria": ["Criterion"],
                }
            ]
            impedance_tasks.write_text(json.dumps(task_payload), encoding="utf-8")
            full_tasks.write_text(json.dumps(task_payload), encoding="utf-8")

            exit_code = v0_status_script.main(
                [
                    "--impedance-tasks",
                    str(impedance_tasks),
                    "--impedance-results",
                    str(impedance_results),
                    "--impedance-report",
                    str(impedance_report),
                    "--tasks",
                    str(full_tasks),
                    "--results",
                    str(full_results),
                    "--report",
                    str(full_report),
                    "--json",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            artifacts.call_args_list,
            [
                call(impedance_tasks, impedance_results, impedance_report),
                call(full_tasks, full_results, full_report),
            ],
        )

    def test_v0_status_passes_readme_to_wheel_payload_check(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("scripts.check_v0_status.run_unit_tests", return_value=[]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]) as wheel_check,
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=[]),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.complete_artifact(), self.complete_artifact()]),
            capture_stdout(),
        ):
            root = Path(tmp)
            readme = root / "README.md"
            exit_code = v0_status_script.main(["--readme", str(readme), "--json"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(wheel_check.call_args.kwargs["readme"], readme)

    def test_v0_status_passes_release_paths_to_sdist_payload_check(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("scripts.check_v0_status.run_unit_tests", return_value=[]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=[]) as sdist_check,
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.complete_artifact(), self.complete_artifact()]),
            capture_stdout(),
        ):
            root = Path(tmp)
            sdist = root / "release.tar.gz"
            skills = root / "skills"
            package = root / "src" / "materials_skills"
            scripts = root / "scripts"
            docs = root / "docs"
            eval_root = root / "eval"
            research = root / "research"
            tests = root / "tests"
            registry = root / "registry.json"
            readme = root / "README.md"
            pyproject = root / "pyproject.toml"
            registry.write_text(registry_json_text(), encoding="utf-8")
            exit_code = v0_status_script.main(
                [
                    "--sdist",
                    str(sdist),
                    "--skills-root",
                    str(skills),
                    "--package-root",
                    str(package),
                    "--scripts-root",
                    str(scripts),
                    "--docs-root",
                    str(docs),
                    "--eval-root",
                    str(eval_root),
                    "--research-root",
                    str(research),
                    "--tests-root",
                    str(tests),
                    "--registry-json",
                    str(registry),
                    "--readme",
                    str(readme),
                    "--pyproject",
                    str(pyproject),
                    "--json",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(sdist_check.call_args.args[0], sdist)
        self.assertEqual(sdist_check.call_args.kwargs["source_root"], skills)
        self.assertEqual(sdist_check.call_args.kwargs["package_root"], package)
        self.assertEqual(sdist_check.call_args.kwargs["scripts_root"], scripts)
        self.assertEqual(sdist_check.call_args.kwargs["docs_root"], docs)
        self.assertEqual(sdist_check.call_args.kwargs["eval_root"], eval_root)
        self.assertEqual(sdist_check.call_args.kwargs["research_root"], research)
        self.assertEqual(sdist_check.call_args.kwargs["tests_root"], tests)
        self.assertEqual(sdist_check.call_args.kwargs["registry_json"], registry)
        self.assertEqual(sdist_check.call_args.kwargs["readme"], readme)
        self.assertEqual(sdist_check.call_args.kwargs["pyproject"], pyproject)

    def test_v0_status_reports_missing_task_manifest_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exc:
                    v0_status_script.main(["--tasks", str(root / "missing-tasks.json")])

            self.assertEqual(exc.exception.code, 2)
            self.assertIn("cannot load task manifest", stderr.getvalue())

    def test_v0_status_direct_script_bootstraps_repo_import_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/check_v0_status.py",
                    "--tasks",
                    str(Path(tmp) / "missing-tasks.json"),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot load task manifest", result.stderr)
        self.assertNotIn("ModuleNotFoundError", result.stderr)

    def test_v0_status_text_output_summarizes_local_problem_lists(self) -> None:
        local_problems = [
            "stale sdist eval file: eval/README.md differs from source",
            "stale sdist test file: tests/test_cli.py differs from source",
            "stale sdist README",
            "extra sdist research note: research/extra.md",
            "extra sdist eval file: eval/extra.json",
        ]
        with (
            patch("scripts.check_v0_status.run_unit_tests", return_value=[]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=local_problems),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.complete_artifact(), self.complete_artifact()]),
            capture_stdout() as output,
        ):
            exit_code = v0_status_script.main([])

        self.assertEqual(exit_code, 1)
        text = output.getvalue()
        self.assertIn(
            "ERROR local sdist_payload: stale sdist eval file: eval/README.md differs from source; "
            "stale sdist test file: tests/test_cli.py differs from source; stale sdist README; ... 2 more",
            text,
        )
        self.assertNotIn("[", text)
        self.assertNotIn("extra sdist eval file", text)
        self.assertIn("Next: fix local readiness errors", text)

    def test_v0_status_text_output_summarizes_problem_lists(self) -> None:
        with (
            patch("scripts.check_v0_status.run_unit_tests", return_value=[]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=[]),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.many_problem_artifact(), self.many_problem_artifact()]),
            capture_stdout() as output,
        ):
            exit_code = v0_status_script.main([])

        self.assertEqual(exit_code, 1)
        text = output.getvalue()
        self.assertIn("problem 0; problem 1; problem 2; ... 2 more", text)
        self.assertIn("Use --json for full status details.", text)
        self.assertNotIn("problem 4", text)

    def test_v0_status_text_output_prints_post_login_next_steps(self) -> None:
        with (
            patch("scripts.check_v0_status.run_unit_tests", return_value=[]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=[]),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.incomplete_artifact(), self.incomplete_artifact()]),
            capture_stdout() as output,
        ):
            exit_code = v0_status_script.main([])

        self.assertEqual(exit_code, 1)
        text = output.getvalue()
        self.assertIn("Next empirical steps:", text)
        self.assertIn("blockers: empirical-artifacts", text)
        self.assertIn("ERROR empirical impedance blockers: evaluation, scoring", text)
        self.assertIn("claude auth login", text)
        self.assertIn("claude auth status --json", text)
        self.assertIn("python eval/scripts/run_claude_eval.py --preflight-only --max-budget-usd 0.05", text)
        self.assertIn("python eval/scripts/run_impedance_pipeline.py --resume", text)
        self.assertIn("Manually score eval/impedance/score-report.md", text)
        self.assertIn("Manually score eval/score-report.md", text)
        self.assertIn("python eval/scripts/run_v0_pipeline.py --skip-model-run --check-scored", text)

    def test_v0_status_text_output_prioritizes_local_next_steps(self) -> None:
        with (
            patch("scripts.check_v0_status.run_unit_tests", return_value=["unit tests failed"]),
            patch("scripts.check_v0_status.validate_skills", return_value=[]),
            patch("scripts.check_v0_status.check_sync", return_value=[]),
            patch("scripts.check_v0_status.check_wheel_skills", return_value=[]),
            patch("scripts.check_v0_status.smoke_wheel_install", return_value=[]),
            patch("scripts.check_v0_status.check_sdist_payload", return_value=[]),
            patch("scripts.check_v0_status.check_artifacts", side_effect=[self.incomplete_artifact(), self.incomplete_artifact()]),
            capture_stdout() as output,
        ):
            exit_code = v0_status_script.main([])

        self.assertEqual(exit_code, 1)
        text = output.getvalue()
        self.assertIn("blockers: local-readiness, empirical-artifacts", text)
        self.assertIn("Next: fix local readiness errors", text)
        self.assertNotIn("Next empirical steps", text)


class ReleaseScriptDirectExecutionTests(unittest.TestCase):
    def test_release_helper_scripts_bootstrap_repo_import_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            commands = [
                [
                    "scripts/check_registry_json.py",
                    "--registry-json",
                    str(root / "missing-registry.json"),
                ],
                [
                    "scripts/check_wheel_skills.py",
                    str(root / "missing-wheel.whl"),
                ],
                [
                    "scripts/check_sdist_payload.py",
                    str(root / "missing-sdist.tar.gz"),
                ],
            ]
            for command in commands:
                with self.subTest(command=command[0]):
                    result = subprocess.run(
                        [sys.executable, *command],
                        cwd=ROOT,
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    self.assertEqual(result.returncode, 1)
                    self.assertIn("missing", result.stdout)
                    self.assertNotIn("ModuleNotFoundError", result.stderr)


class ValidationTests(unittest.TestCase):
    def test_parse_frontmatter_list(self) -> None:
        self.assertEqual(parse_frontmatter_list("[ase, pymatgen]"), ["ase", "pymatgen"])
        self.assertEqual(parse_frontmatter_list("[]"), [])
        with self.assertRaises(ValueError):
            parse_frontmatter_list("ase, pymatgen")
        with self.assertRaises(ValueError):
            parse_frontmatter_list("[ase, ]")

    def test_validate_packaged_skills_against_source(self) -> None:
        self.assertEqual(validate_skills(default_skills_root(), source_root=SKILLS_ROOT), [])

    def test_validate_reports_missing_required_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "ase":
                    text = text.replace("## Diagnostic checks", "## Missing diagnostics")
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("ase: missing section ## Diagnostic checks", errors)

    def test_validate_reports_frontmatter_name_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace("name: impedance", "name: eis")
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: frontmatter name 'eis' does not match registry", errors)

    def test_validate_reports_duplicate_frontmatter_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace("name: impedance", "name: ase")
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: frontmatter name 'ase' does not match registry", errors)
            self.assertIn("impedance: duplicate skill name 'ase'", errors)

    def test_validate_reports_missing_related_skills_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace("related_skills: []\n", "")
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: missing frontmatter key related_skills", errors)

    def test_validate_reports_empty_required_frontmatter_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace("canonical_tutorials: https://impedancepy.readthedocs.io/en/latest/examples/fitting_example.html", "canonical_tutorials:")
                    text = text.replace('compatible_versions: ">=1.7,<2"', "compatible_versions:")
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: frontmatter key canonical_tutorials must not be empty", errors)
            self.assertIn("impedance: frontmatter key compatible_versions must not be empty", errors)

    def test_validate_reports_empty_block_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    start = text.index("description: |\n") + len("description: |\n")
                    end = text.index("version: 0.1.0")
                    text = text[:start] + text[end:]
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: frontmatter key description must not be empty", errors)

    def test_validate_reports_unregistered_related_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace("related_skills: []", "related_skills: [missing-skill]")
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: related skill 'missing-skill' is not registered", errors)

    def test_validate_reports_self_referential_related_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace("related_skills: []", "related_skills: [impedance]")
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: related skill must not reference itself", errors)

    def test_validate_reports_duplicate_related_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace("related_skills: []", "related_skills: [ase, ase]")
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: duplicate related skill 'ase'", errors)

    def test_validate_reports_non_url_canonical_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace(
                        "canonical_docs: https://impedancepy.readthedocs.io/en/latest/",
                        "canonical_docs: impedancepy.readthedocs.io",
                    )
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: canonical_docs must be an http(s) URL", errors)

    def test_validate_reports_canonical_link_without_host(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace(
                        "canonical_docs: https://impedancepy.readthedocs.io/en/latest/",
                        "canonical_docs: https://",
                    )
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: canonical_docs must be an http(s) URL", errors)

    def test_validate_reports_duplicate_canonical_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace(
                        "canonical_tutorials: https://impedancepy.readthedocs.io/en/latest/examples/fitting_example.html",
                        "canonical_tutorials: https://impedancepy.readthedocs.io/en/latest/",
                    )
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: canonical_docs and canonical_tutorials must differ", errors)

    def test_validate_reports_normalized_duplicate_canonical_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace(
                        "canonical_docs: https://impedancepy.readthedocs.io/en/latest/",
                        "canonical_docs: HTTPS://impedancepy.readthedocs.io/en/latest",
                    )
                    text = text.replace(
                        "canonical_tutorials: https://impedancepy.readthedocs.io/en/latest/examples/fitting_example.html",
                        "canonical_tutorials: https://IMPEDANCEPY.readthedocs.io/en/latest/",
                    )
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: canonical_docs and canonical_tutorials must differ", errors)

    def test_validate_reports_skill_over_line_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text + "\n".join([""] + ["extra line"] * 301)
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertTrue(
                any(error.startswith("impedance: SKILL.md has ") and error.endswith("expected <= 300") for error in errors)
            )

    def test_validate_reports_malformed_version_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace("version: 0.1.0", "version: draft")
                    text = text.replace('compatible_versions: ">=1.7,<2"', "compatible_versions: latest")
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: version must be semantic X.Y.Z", errors)
            self.assertIn("impedance: compatible_versions must look like >=X.Y,<A.B", errors)

    def test_validate_reports_inverted_compatible_version_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in REGISTRY:
                skill_dir = root / record.skill_dir
                skill_dir.mkdir(parents=True)
                source = SKILLS_ROOT / record.skill_dir / "SKILL.md"
                text = source.read_text(encoding="utf-8")
                if record.skill_name == "impedance":
                    text = text.replace('compatible_versions: ">=1.7,<2"', 'compatible_versions: ">=2,<1.7"')
                (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
            errors = validate_skills(root)
            self.assertIn("impedance: compatible_versions lower bound must be below upper bound", errors)

    def test_validate_command_json(self) -> None:
        with capture_stdout() as output:
            exit_code = main(["validate", "--skills-root", str(SKILLS_ROOT), "--json"])
        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["errors"], [])


class InstallCommandTests(unittest.TestCase):
    def test_install_copies_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with capture_stdout():
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "pip-list.txt"),
                        "--target",
                        str(target),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue((target / "ase" / "SKILL.md").is_file())
            self.assertTrue((target / "impedance" / "SKILL.md").is_file())
            self.assertTrue((target / "pymatgen" / "SKILL.md").is_file())
            self.assertTrue((target / "rdkit" / "SKILL.md").is_file())
            self.assertTrue((target / "mace" / "SKILL.md").is_file())
            self.assertTrue((target / "py4dstem" / "SKILL.md").is_file())
            self.assertTrue((target / "hyperspy" / "SKILL.md").is_file())
            self.assertTrue((target / "pybamm" / "SKILL.md").is_file())
            self.assertTrue((target / "pyscf" / "SKILL.md").is_file())
            self.assertTrue((target / "openmm" / "SKILL.md").is_file())

    def test_install_without_env_uses_current_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with patch(
                "materials_skills.cli.detect_current_environment_details",
                return_value=ParsedEnvironment(
                    package_names={"impedance", "rdkit"},
                    package_versions={"impedance": "1.7.1", "rdkit": "2026.03.2"},
                    source="current",
                    requested_format="auto",
                    detected_format="installed-distributions",
                ),
            ):
                with capture_stdout() as output:
                    exit_code = main(["install", "--target", str(target), "--dry-run", "--json"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["environment"]["source"], "current")
        self.assertEqual(payload["environment"]["format"], "installed-distributions")
        self.assertEqual(payload["environment"]["package_versions"]["impedance"], "1.7.1")
        self.assertEqual(payload["agent"], "claude")
        self.assertEqual(payload["skills"], ["rdkit", "impedance"])
        self.assertEqual(
            [action["status"] for action in payload["actions"]],
            ["would-install", "would-install"],
        )

    def test_install_is_idempotent_when_existing_skill_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            records = [REGISTRY[0]]
            first = install_skills(records, SKILLS_ROOT, target)
            second = install_skills(records, SKILLS_ROOT, target)
            self.assertEqual([action.status for action in first], ["installed"])
            self.assertEqual([action.status for action in second], ["unchanged"])
            self.assertEqual(
                (target / "ase" / "SKILL.md").read_text(encoding="utf-8"),
                (SKILLS_ROOT / "ase" / "SKILL.md").read_text(encoding="utf-8"),
            )

    def test_install_refuses_to_overwrite_modified_skill_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            records = [REGISTRY[0]]
            install_skills(records, SKILLS_ROOT, target)
            (target / "ase" / "SKILL.md").write_text("local edit\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                install_skills(records, SKILLS_ROOT, target)

    def test_install_refuses_before_partial_copy_when_later_skill_differs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            install_skills([REGISTRY[1]], SKILLS_ROOT, target)
            (target / "pymatgen" / "SKILL.md").write_text("local edit\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                install_skills([REGISTRY[0], REGISTRY[1]], SKILLS_ROOT, target)

            self.assertFalse((target / "ase").exists())
            self.assertEqual((target / "pymatgen" / "SKILL.md").read_text(encoding="utf-8"), "local edit\n")

    def test_install_force_overwrites_modified_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            records = [REGISTRY[0]]
            install_skills(records, SKILLS_ROOT, target)
            (target / "ase" / "SKILL.md").write_text("local edit\n", encoding="utf-8")
            actions = install_skills(records, SKILLS_ROOT, target, force=True)
            self.assertEqual([action.status for action in actions], ["overwritten"])
            self.assertEqual(
                (target / "ase" / "SKILL.md").read_text(encoding="utf-8"),
                (SKILLS_ROOT / "ase" / "SKILL.md").read_text(encoding="utf-8"),
            )

    def test_install_command_reports_existing_modified_skill_as_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with capture_stdout():
                main(["install", "--env", str(FIXTURES / "pip-list.txt"), "--target", str(target)])
            (target / "ase" / "SKILL.md").write_text("local edit\n", encoding="utf-8")
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "pip-list.txt"),
                        "--target",
                        str(target),
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 1)
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["ok"])
            self.assertIn("--force", payload["error"])

    def test_install_command_reports_missing_env_file_as_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing-pip-list.txt"
            target = Path(tmp) / ".claude" / "skills"
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(missing),
                        "--target",
                        str(target),
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 1)
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["ok"])
            self.assertIn("missing-pip-list.txt", payload["error"])

    def test_install_command_reports_malformed_env_as_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "bad-pip-list.json"
            env_file.write_text("{not json\n", encoding="utf-8")
            target = Path(tmp) / ".claude" / "skills"
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(env_file),
                        "--format",
                        "pip-json",
                        "--target",
                        str(target),
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 1)
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["ok"])
            self.assertIn("Expecting", payload["error"])

    def test_install_command_reports_os_errors_as_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with patch("materials_skills.cli.install_skills", side_effect=PermissionError("blocked")):
                with capture_stdout() as output:
                    exit_code = main(
                        [
                            "install",
                            "--env",
                            str(FIXTURES / "pip-list.txt"),
                            "--target",
                            str(target),
                            "--json",
                        ]
                    )
            self.assertEqual(exit_code, 1)
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["ok"])
            self.assertIn("blocked", payload["error"])

    def test_install_command_preflights_targets_before_copying(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with (
                patch("materials_skills.cli.prepare_install_targets", side_effect=PermissionError("blocked")),
                patch("materials_skills.cli.install_skills") as install_mock,
            ):
                with capture_stdout() as output:
                    exit_code = main(
                        [
                            "install",
                            "--env",
                            str(FIXTURES / "pip-list.txt"),
                            "--target",
                            str(target),
                            "--json",
                        ]
                    )
            self.assertEqual(exit_code, 1)
            install_mock.assert_not_called()
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["ok"])
            self.assertIn("blocked", payload["error"])

    def test_install_command_force_overwrites_modified_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with capture_stdout():
                main(["install", "--env", str(FIXTURES / "pip-list.txt"), "--target", str(target)])
            (target / "ase" / "SKILL.md").write_text("local edit\n", encoding="utf-8")
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "pip-list.txt"),
                        "--target",
                        str(target),
                        "--force",
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertTrue(payload["force"])
            self.assertEqual(payload["actions"][0]["status"], "overwritten")
            self.assertEqual(
                (target / "ase" / "SKILL.md").read_text(encoding="utf-8"),
                (SKILLS_ROOT / "ase" / "SKILL.md").read_text(encoding="utf-8"),
            )

    def test_install_command_reports_unchanged_actions_on_reinstall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with capture_stdout():
                main(["install", "--env", str(FIXTURES / "pip-list.txt"), "--target", str(target)])
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "pip-list.txt"),
                        "--target",
                        str(target),
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual({action["status"] for action in payload["actions"]}, {"unchanged"})

    def test_dry_run_reports_would_install_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "pip-list.txt"),
                        "--target",
                        str(target),
                        "--dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual({action["status"] for action in payload["actions"]}, {"would-install"})

    def test_install_command_reads_env_from_stdin(self) -> None:
        text = (FIXTURES / "pip-list.txt").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with patch("sys.stdin", io.StringIO(text)):
                with capture_stdout() as output:
                    exit_code = main(
                        [
                            "install",
                            "--env",
                            "-",
                            "--target",
                            str(target),
                            "--dry-run",
                            "--json",
                        ]
                    )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertIn("impedance", payload["skills"])
            self.assertEqual(payload["environment"]["source"], "stdin")
            self.assertEqual(payload["environment"]["requested_format"], "auto")
            self.assertEqual(payload["environment"]["format"], "pip")
            self.assertEqual(payload["target"], str(target))
            self.assertFalse(target.exists())

    def test_dry_run_reports_unchanged_for_matching_existing_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with capture_stdout():
                main(["install", "--env", str(FIXTURES / "pip-list.txt"), "--target", str(target)])
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "pip-list.txt"),
                        "--target",
                        str(target),
                        "--dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual({action["status"] for action in payload["actions"]}, {"unchanged"})

    def test_dry_run_reports_would_error_for_modified_existing_skill_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with capture_stdout():
                main(["install", "--env", str(FIXTURES / "pip-list.txt"), "--target", str(target)])
            (target / "ase" / "SKILL.md").write_text("local edit\n", encoding="utf-8")
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "pip-list.txt"),
                        "--target",
                        str(target),
                        "--dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            actions = {action["skill"]: action["status"] for action in payload["actions"]}
            self.assertEqual(actions["ase"], "would-error")
            self.assertEqual(actions["pymatgen"], "unchanged")

    def test_dry_run_reports_would_overwrite_for_modified_existing_skill_with_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with capture_stdout():
                main(["install", "--env", str(FIXTURES / "pip-list.txt"), "--target", str(target)])
            (target / "ase" / "SKILL.md").write_text("local edit\n", encoding="utf-8")
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "pip-list.txt"),
                        "--target",
                        str(target),
                        "--dry-run",
                        "--force",
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            actions = {action["skill"]: action["status"] for action in payload["actions"]}
            self.assertEqual(actions["ase"], "would-overwrite")
            self.assertEqual(actions["pymatgen"], "unchanged")

    def test_json_dry_run_reports_match_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".cursor" / "skills"
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "conda-env.yml"),
                        "--target",
                        str(target),
                        "--skills-root",
                        str(SKILLS_ROOT),
                        "--dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(
                payload["skills"],
                [
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
                    "atomate2",
                ],
            )
            self.assertEqual(payload["matches"][2]["skill"], "rdkit")
            self.assertEqual(payload["matches"][2]["matched_distributions"], ["rdkit"])
            self.assertEqual(payload["matches"][2]["matched_versions"], {"rdkit": "2026.03.2"})
            self.assertEqual(payload["matches"][2]["compatible_versions"], ">=2023.09,<2027")
            self.assertEqual(payload["matches"][2]["compatibility"], "compatible")
            self.assertEqual(
                payload["matches"][2]["registered_distributions"],
                ["rdkit", "rdkit-pypi"],
            )
            self.assertEqual(payload["actions"][2]["matched_distributions"], ["rdkit"])
            self.assertEqual(payload["actions"][2]["matched_versions"], {"rdkit": "2026.03.2"})
            self.assertEqual(payload["actions"][2]["compatibility"], "compatible")
            self.assertEqual(payload["environment"]["package_versions"]["impedance"], "1.7.1")
            self.assertTrue(payload["dry_run"])
            self.assertFalse(target.exists())

    def test_v0_demo_fixture_reports_all_matches_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".claude" / "skills"
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "conda-env.yml"),
                        "--target",
                        str(target),
                        "--skills-root",
                        str(SKILLS_ROOT),
                        "--dry-run",
                        "--json",
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(len(payload["matches"]), 12)
            self.assertEqual({match["compatibility"] for match in payload["matches"]}, {"compatible"})
            self.assertTrue(all(match["compatible_versions"] for match in payload["matches"]))

    def test_conda_list_dry_run_reports_match_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".codex" / "skills"
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "conda-list.txt"),
                        "--target",
                        str(target),
                        "--skills-root",
                        str(SKILLS_ROOT),
                        "--dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(len(payload["skills"]), 12)
            self.assertIn("impedance", payload["skills"])
            self.assertTrue(payload["dry_run"])
            self.assertFalse(target.exists())

    def test_conda_explicit_dry_run_reports_match_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".codex" / "skills"
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "conda-explicit.txt"),
                        "--target",
                        str(target),
                        "--skills-root",
                        str(SKILLS_ROOT),
                        "--dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(len(payload["skills"]), 12)
            self.assertIn("mace", payload["skills"])
            self.assertTrue(payload["dry_run"])
            self.assertFalse(target.exists())

    def test_conda_json_dry_run_reports_match_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".codex" / "skills"
            with capture_stdout() as output:
                exit_code = main(
                    [
                        "install",
                        "--env",
                        str(FIXTURES / "conda-env.json"),
                        "--target",
                        str(target),
                        "--skills-root",
                        str(SKILLS_ROOT),
                        "--dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(len(payload["skills"]), 12)
            self.assertEqual(payload["environment"]["format"], "conda-json")
            self.assertIn("py4dstem", payload["skills"])
            self.assertTrue(payload["dry_run"])
            self.assertFalse(target.exists())

    def test_agent_all_installs_to_every_builtin_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                with capture_stdout() as output:
                    exit_code = main(
                        [
                            "install",
                            "--env",
                            str(FIXTURES / "pip-list.txt"),
                            "--agent",
                            "all",
                            "--skills-root",
                            str(SKILLS_ROOT),
                            "--json",
                        ]
                    )
            finally:
                os.chdir(old_cwd)
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["agent"], "all")
            self.assertIsNone(payload["target"])
            self.assertEqual(payload["targets"], [".claude/skills", ".cursor/skills", ".codex/skills"])
            self.assertEqual(len(payload["actions"]), 36)
            for target in (".claude/skills", ".cursor/skills", ".codex/skills"):
                self.assertTrue((Path(tmp) / target / "impedance" / "SKILL.md").is_file())

    def test_agent_all_refuses_before_partial_target_copy_when_one_target_differs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                with capture_stdout():
                    main(
                        [
                            "install",
                            "--env",
                            str(FIXTURES / "pip-list.txt"),
                            "--target",
                            ".cursor/skills",
                            "--skills-root",
                            str(SKILLS_ROOT),
                        ]
                    )
                (Path(".cursor/skills/ase/SKILL.md")).write_text("local edit\n", encoding="utf-8")

                with capture_stdout() as output:
                    exit_code = main(
                        [
                            "install",
                            "--env",
                            str(FIXTURES / "pip-list.txt"),
                            "--agent",
                            "all",
                            "--skills-root",
                            str(SKILLS_ROOT),
                            "--json",
                        ]
                    )
            finally:
                os.chdir(old_cwd)

            self.assertEqual(exit_code, 1)
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["ok"])
            self.assertIn("--force", payload["error"])
            self.assertFalse((Path(tmp) / ".claude" / "skills" / "ase").exists())
            self.assertFalse((Path(tmp) / ".codex" / "skills" / "ase").exists())
            self.assertFalse((Path(tmp) / ".claude" / "skills").exists())
            self.assertFalse((Path(tmp) / ".codex" / "skills").exists())
            self.assertEqual(
                (Path(tmp) / ".cursor" / "skills" / "ase" / "SKILL.md").read_text(encoding="utf-8"),
                "local edit\n",
            )


if __name__ == "__main__":
    unittest.main()

"""Environment-file parsing for materials skill discovery."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from urllib.parse import urlparse


PIP_VERSION_MARKERS = ("===", "==", ">=", "<=", "~=", "!=", ">", "<", "=")


@dataclass(frozen=True)
class ParsedEnvironment:
    package_names: set[str]
    package_versions: dict[str, str]
    source: str
    requested_format: str
    detected_format: str


def parse_pip_json(text: str) -> set[str]:
    return parse_pip_json_details(text)[0]


def parse_pip_json_details(text: str) -> tuple[set[str], dict[str, str]]:
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("pip JSON must be a list of package objects")
    names: set[str] = set()
    versions: dict[str, str] = {}
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            name = item["name"]
            names.add(name)
            if isinstance(item.get("version"), str):
                versions[name] = item["version"]
    return names, versions


def parse_pip_list(text: str) -> set[str]:
    return parse_pip_list_details(text)[0]


def parse_pip_list_details(text: str) -> tuple[set[str], dict[str, str]]:
    """Parse `pip list`, `pip freeze`, or a simple newline package list."""

    names: set[str] = set()
    versions: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("package ") or set(line.replace(" ", "")) == {"-"}:
            continue
        name, version = _pip_requirement_name_version(line)
        if name:
            names.add(name)
            if version:
                versions[name] = version
    return names, versions


def parse_conda_export(text: str) -> set[str]:
    return parse_conda_export_details(text)[0]


def parse_conda_export_details(text: str) -> tuple[set[str], dict[str, str]]:
    """Parse the common package forms in `conda env export` YAML."""

    names: set[str] = set()
    versions: dict[str, str] = {}
    in_dependencies = False
    in_pip_block = False
    pip_indent: int | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        stripped = raw_line.strip()

        if stripped == "dependencies:":
            in_dependencies = True
            in_pip_block = False
            pip_indent = None
            continue
        if not in_dependencies:
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if in_pip_block and pip_indent is not None and indent > pip_indent:
            if stripped.startswith("- "):
                name, version = _pip_requirement_name_version(stripped[2:])
                if name:
                    names.add(name)
                    if version:
                        versions[name] = version
            continue
        if in_pip_block and pip_indent is not None and indent <= pip_indent:
            in_pip_block = False
            pip_indent = None

        if stripped == "- pip:":
            in_pip_block = True
            pip_indent = indent
            continue
        if stripped.startswith("- "):
            dep = stripped[2:]
            if ":" in dep:
                continue
            name, version = _conda_dependency_name_version(dep)
            if name:
                names.add(name)
                if version:
                    versions[name] = version

    return {name for name in names if name}, versions


def parse_conda_json(text: str) -> set[str]:
    return parse_conda_json_details(text)[0]


def parse_conda_json_details(text: str) -> tuple[set[str], dict[str, str]]:
    """Parse `conda env export --json` or `conda list --json` output."""

    data = json.loads(text)
    names: set[str] = set()
    versions: dict[str, str] = {}

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                name = item["name"]
                names.add(name)
                if isinstance(item.get("version"), str):
                    versions[name] = item["version"]
        return names, versions

    if isinstance(data, dict) and isinstance(data.get("dependencies"), list):
        for dependency in data["dependencies"]:
            if isinstance(dependency, str):
                name, version = _conda_dependency_name_version(dependency)
                if name:
                    names.add(name)
                    if version:
                        versions[name] = version
            elif isinstance(dependency, dict):
                pip_dependencies = dependency.get("pip")
                if isinstance(pip_dependencies, list):
                    for pip_dependency in pip_dependencies:
                        if isinstance(pip_dependency, str):
                            name, version = _pip_requirement_name_version(pip_dependency)
                            if name:
                                names.add(name)
                                if version:
                                    versions[name] = version
        return {name for name in names if name}, versions

    raise ValueError("conda JSON must be a package list or an environment export object")


def parse_conda_list(text: str) -> set[str]:
    return parse_conda_list_details(text)[0]


def parse_conda_list_details(text: str) -> tuple[set[str], dict[str, str]]:
    """Parse `conda list`, `conda list --export`, or explicit package URLs."""

    names: set[str] = set()
    versions: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line == "@EXPLICIT":
            continue
        if "://" in line:
            name, version = _conda_url_package_name_version(line)
            if name:
                names.add(name)
                if version:
                    versions[name] = version
            continue
        if "=" in line and not line.startswith("-e "):
            name, version = _conda_dependency_name_version(line)
            if name:
                names.add(name)
                if version:
                    versions[name] = version
            continue
        parts = line.split()
        if parts:
            names.add(parts[0])
            if len(parts) > 1:
                versions[parts[0]] = parts[1]
    return {name for name in names if name}, versions


def _conda_url_package_name(url: str) -> str:
    return _conda_url_package_name_version(url)[0]


def _conda_url_package_name_version(url: str) -> tuple[str, str]:
    filename = Path(urlparse(url).path).name
    for suffix in (".tar.bz2", ".conda"):
        if filename.endswith(suffix):
            package_id = filename[: -len(suffix)]
            parts = package_id.rsplit("-", 2)
            if len(parts) == 3:
                return parts[0], parts[1]
    return "", ""


def _pip_requirement_name(spec: str) -> str:
    return _pip_requirement_name_version(spec)[0]


def _pip_requirement_name_version(spec: str) -> tuple[str, str]:
    """Extract a distribution name from common pip requirement forms."""

    spec = spec.strip().strip("'\"")
    if not spec or spec.startswith("#"):
        return "", ""
    if spec.startswith("-e "):
        spec = spec[3:].strip()
    elif spec.startswith("--editable "):
        spec = spec[len("--editable ") :].strip()
    elif spec.startswith("-"):
        return "", ""

    if " @ " not in spec and "://" not in spec:
        parts = spec.split()
        if (
            len(parts) >= 2
            and parts[1] not in PIP_VERSION_MARKERS
            and not any(marker in parts[0] for marker in PIP_VERSION_MARKERS)
        ):
            return _strip_extras(parts[0]), parts[1]

    if "#egg=" in spec:
        egg = spec.split("#egg=", 1)[1].split("&", 1)[0].strip()
        return _strip_extras(egg), ""

    requirement = spec.split(";", 1)[0].strip()
    if " @ " in requirement:
        name, target = requirement.split(" @ ", 1)
        version = ""
        if "://" in target:
            _, version = _pip_url_package_name_version(target)
        return _strip_extras(name.strip()), version
    if "://" in requirement:
        return _pip_url_package_name_version(requirement)
    if requirement.startswith(("git+", "hg+", "svn+", "bzr+", ".", "/")):
        return "", ""

    for marker in PIP_VERSION_MARKERS:
        if marker in requirement:
            name, version = requirement.split(marker, 1)
            version = "" if marker not in {"===", "==", "="} else version.split(",", 1)[0].split()[0].strip()
            return _strip_extras(name.strip()), version
    return _strip_extras(requirement.split()[0].strip()), ""


def _strip_extras(name: str) -> str:
    return name.split("[", 1)[0].strip()


def _pip_url_package_name(url: str) -> str:
    return _pip_url_package_name_version(url)[0]


def _pip_url_package_name_version(url: str) -> tuple[str, str]:
    filename = Path(urlparse(url).path).name
    if not filename.endswith(".whl"):
        return "", ""
    parts = filename[:-4].split("-")
    if len(parts) < 5:
        return "", ""
    return parts[0].replace("_", "-"), parts[1]


def _conda_dependency_name(spec: str) -> str:
    return _conda_dependency_name_version(spec)[0]


def _conda_dependency_name_version(spec: str) -> tuple[str, str]:
    spec = spec.strip().strip("'\"")
    for marker in ("==", ">=", "<=", "~=", "!=", ">", "<", "="):
        if marker in spec:
            name, version = spec.split(marker, 1)
            version = "" if marker not in {"==", "="} else version.split("=", 1)[0].split(",", 1)[0].strip()
            return name.strip(), version
    return spec.split()[0].strip(), ""


def detect_current_environment() -> set[str]:
    """Detect installed distributions without shelling out when possible."""

    names = {dist.metadata["Name"] for dist in metadata.distributions() if "Name" in dist.metadata}
    if names:
        return names

    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_pip_json(result.stdout)


def detect_current_environment_details() -> ParsedEnvironment:
    names: set[str] = set()
    versions: dict[str, str] = {}
    for dist in metadata.distributions():
        if "Name" in dist.metadata:
            name = dist.metadata["Name"]
            names.add(name)
            version = getattr(dist, "version", "")
            if version:
                versions[name] = version
    if names:
        return ParsedEnvironment(
            package_names=names,
            package_versions=versions,
            source="current",
            requested_format="auto",
            detected_format="installed-distributions",
        )

    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        check=True,
        capture_output=True,
        text=True,
    )
    packages, package_versions = parse_pip_json_details(result.stdout)
    return ParsedEnvironment(
        package_names=packages,
        package_versions=package_versions,
        source="current",
        requested_format="auto",
        detected_format="installed-distributions",
    )


def parse_environment_file(path: Path, fmt: str) -> set[str]:
    text = sys.stdin.read() if str(path) == "-" else path.read_text(encoding="utf-8")
    packages, _, _ = parse_environment_text(path, text, fmt)
    return packages


def load_environment(path: Path, fmt: str) -> ParsedEnvironment:
    text = sys.stdin.read() if str(path) == "-" else path.read_text(encoding="utf-8")
    packages, detected_format, package_versions = parse_environment_text(path, text, fmt)
    return ParsedEnvironment(
        package_names=packages,
        package_versions=package_versions,
        source="stdin" if str(path) == "-" else str(path),
        requested_format=fmt,
        detected_format=detected_format,
    )


def parse_environment_text(path: Path, text: str, fmt: str) -> tuple[set[str], str, dict[str, str]]:
    if fmt == "auto":
        fmt = infer_format(path, text)
    if fmt == "pip-json":
        packages, versions = parse_pip_json_details(text)
        return packages, fmt, versions
    if fmt == "pip":
        packages, versions = parse_pip_list_details(text)
        return packages, fmt, versions
    if fmt == "conda":
        packages, versions = parse_conda_export_details(text)
        return packages, fmt, versions
    if fmt == "conda-json":
        packages, versions = parse_conda_json_details(text)
        return packages, fmt, versions
    if fmt == "conda-list":
        packages, versions = parse_conda_list_details(text)
        return packages, fmt, versions
    raise ValueError(f"unsupported environment format: {fmt}")


def infer_format(path: Path, text: str) -> str:
    suffix = path.suffix.lower()
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return "conda-json"
    if suffix == ".json" or stripped.startswith("["):
        return infer_json_list_format(text)
    if suffix in {".yml", ".yaml"} or "dependencies:" in text:
        return "conda"
    if "# packages in environment" in text or "# Name" in text:
        return "conda-list"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "@EXPLICIT" or _conda_url_package_name(line):
            return "conda-list"
        if line.count("=") >= 2 and "==" not in line:
            return "conda-list"
    return "pip"


def infer_json_list_format(text: str) -> str:
    data = json.loads(text)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and {"build", "build_string", "channel"}.intersection(item):
                return "conda-json"
    return "pip-json"

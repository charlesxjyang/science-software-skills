#!/usr/bin/env python3
"""Sync top-level skills into the importable package data directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills"
DESTINATION = ROOT / "src" / "materials_skills" / "skills"


def _relative_files(root: Path) -> dict[Path, bytes]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def check_sync(source: Path = SOURCE, destination: Path = DESTINATION) -> list[str]:
    """Return human-readable drift messages for package-data skill sync."""

    errors: list[str] = []
    if not source.is_dir():
        return [f"missing source skills directory: {source}"]
    if not destination.is_dir():
        return [f"missing packaged skills directory: {destination}"]

    source_files = _relative_files(source)
    destination_files = _relative_files(destination)

    for path in sorted(source_files.keys() - destination_files.keys()):
        errors.append(f"missing packaged file: {path}")
    for path in sorted(destination_files.keys() - source_files.keys()):
        errors.append(f"extra packaged file: {path}")
    for path in sorted(source_files.keys() & destination_files.keys()):
        if source_files[path] != destination_files[path]:
            errors.append(f"out-of-sync packaged file: {path}")
    return errors


def sync_skills(source: Path = SOURCE, destination: Path = DESTINATION) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"missing source skills directory: {source}")

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    for skill_dir in sorted(path for path in source.iterdir() if path.is_dir()):
        shutil.copytree(skill_dir, destination / skill_dir.name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--destination", type=Path, default=DESTINATION)
    parser.add_argument("--check", action="store_true", help="report drift without modifying package data")
    args = parser.parse_args(argv)

    if args.check:
        errors = check_sync(args.source, args.destination)
        if errors:
            for error in errors:
                print(f"ERROR {error}")
            return 1
        print("Packaged skills are in sync")
        return 0

    sync_skills(args.source, args.destination)
    print(f"Synced skills from {args.source} to {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

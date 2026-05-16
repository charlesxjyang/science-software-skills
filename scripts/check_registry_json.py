#!/usr/bin/env python3
"""Check that the static registry JSON matches the runtime registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts._bootstrap import bootstrap_repo_imports
except ModuleNotFoundError:
    from _bootstrap import bootstrap_repo_imports

bootstrap_repo_imports()

from materials_skills.cli import registry_payload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_JSON = ROOT / "registry.json"


def registry_json_text() -> str:
    """Return the canonical static registry JSON document."""

    return json.dumps({"skills": registry_payload()}, indent=2) + "\n"


def check_registry_json(path: Path = DEFAULT_REGISTRY_JSON) -> list[str]:
    """Return human-readable registry JSON drift problems."""

    if not path.is_file():
        return [f"missing registry JSON: {path}"]
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"invalid registry JSON: {path}: {exc}"]

    canonical = registry_json_text()
    if payload != json.loads(canonical) or text != canonical:
        return [f"stale registry JSON: {path} differs from runtime registry"]
    return []


def write_registry_json(path: Path = DEFAULT_REGISTRY_JSON) -> None:
    """Write the canonical static registry JSON document."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(registry_json_text(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY_JSON)
    parser.add_argument("--write", action="store_true", help="rewrite registry JSON instead of only checking it")
    args = parser.parse_args(argv)

    if args.write:
        write_registry_json(args.registry_json)
        print(f"Wrote registry JSON to {args.registry_json}")
        return 0

    errors = check_registry_json(args.registry_json)
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1

    print("Registry JSON is in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

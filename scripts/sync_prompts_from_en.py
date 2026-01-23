#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Semi-automatic sync of prompt structure from prompts/en to prompts/zh|prompts/cn.

Behavior (safe by default):
- Dry-run: prints what would be added
- With --write: adds missing keys to zh/cn files without overwriting existing values
- With --create-missing-files: creates missing zh/cn files using the en structure

NOTE: This tool does NOT translate. It inserts TODO markers to be manually rewritten in Chinese.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = PROJECT_ROOT / "src" / "agents"


def _load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _dump_yaml(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False)


def _merge_missing(en_obj: Any, zh_obj: Any) -> tuple[Any, int]:
    """
    Add missing keys from en_obj into zh_obj without overwriting existing zh content.
    Returns (new_obj, added_count).
    """
    added = 0

    if isinstance(en_obj, dict):
        if not isinstance(zh_obj, dict):
            zh_obj = {}
        for k, v in en_obj.items():
            if k not in zh_obj:
                added += 1
                if isinstance(v, str):
                    zh_obj[k] = f"<<TODO_TRANSLATE>> {v}"
                else:
                    # For non-string nodes, insert scaffold recursively
                    zh_obj[k], inc = _merge_missing(
                        v, {} if isinstance(v, dict) else [] if isinstance(v, list) else None
                    )
                    added += inc
            else:
                zh_obj[k], inc = _merge_missing(v, zh_obj[k])
                added += inc
        return zh_obj, added

    if isinstance(en_obj, list):
        # Do not attempt to merge list structures; keep existing zh list.
        return zh_obj, 0

    # Primitive leaf: nothing to do
    return zh_obj, 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write changes to disk")
    parser.add_argument(
        "--create-missing-files",
        action="store_true",
        help="create missing zh/cn files from en structure with TODO markers",
    )
    parser.add_argument(
        "--target",
        choices=["zh", "cn", "both"],
        default="both",
        help="which target language directory to sync",
    )
    args = parser.parse_args()

    if not AGENTS_DIR.exists():
        print(f"Agents directory not found: {AGENTS_DIR}", file=sys.stderr)
        return 2

    total_added = 0
    total_files = 0

    for module_dir in sorted([p for p in AGENTS_DIR.iterdir() if p.is_dir()]):
        prompts_dir = module_dir / "prompts"
        en_dir = prompts_dir / "en"
        if not en_dir.exists():
            continue

        targets: list[tuple[str, Path]] = []
        if args.target in ("zh", "both"):
            targets.append(("zh", prompts_dir / "zh"))
        if args.target in ("cn", "both"):
            targets.append(("cn", prompts_dir / "cn"))

        en_files = [p for p in en_dir.rglob("*.yaml") if p.is_file()]
        for en_file in sorted(en_files):
            rel = en_file.relative_to(en_dir)
            en_obj = _load_yaml(en_file)
            for lang_name, lang_dir in targets:
                zh_file = lang_dir / rel
                if not zh_file.exists():
                    if not args.create_missing_files:
                        print(f"[MISSING {lang_name}] {module_dir.name}: {rel.as_posix()}")
                        continue
                    zh_obj = {}
                else:
                    zh_obj = _load_yaml(zh_file)

                new_obj, added = _merge_missing(en_obj, zh_obj)
                if added == 0:
                    continue

                total_added += added
                total_files += 1
                print(f"[SYNC {lang_name}] {module_dir.name}: {rel.as_posix()} (+{added} keys)")

                if args.write:
                    _dump_yaml(zh_file, new_obj)

    if total_files == 0:
        print("No changes needed.")
        return 0

    if args.write:
        print(f"Updated {total_files} file(s), added {total_added} key(s).")
    else:
        print(
            f"Dry-run: would update {total_files} file(s), add {total_added} key(s). Use --write to apply."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

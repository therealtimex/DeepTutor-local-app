#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Audit prompt parity between prompts/en and prompts/zh|prompts/cn.

Checks:
- Missing/extra keys (recursive)
- Placeholder drift in string templates (e.g. {question}, {context})

Usage:
  python scripts/audit_prompts.py
  python scripts/audit_prompts.py --fail
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any, Iterable

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = PROJECT_ROOT / "src" / "agents"

# Template placeholders are expected to be like {topic}, {knowledge_title}, etc.
# Avoid false positives from LaTeX (\frac{1}{3}) and Mermaid (B{{Processing}}).
PLACEHOLDER_RE = re.compile(r"(?<!\{)\{[A-Za-z_][A-Za-z0-9_]*\}(?!\})")


def _load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _iter_yaml_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.rglob("*.yaml") if p.is_file()])


def _get_placeholders(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, str):
        found |= set(PLACEHOLDER_RE.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            found |= _get_placeholders(v)
    elif isinstance(value, list):
        for v in value:
            found |= _get_placeholders(v)
    return found


def _collect_keys(value: Any, prefix: str = "") -> set[str]:
    """
    Collect dotted key paths for all dict nodes.
    Leaves (non-dict) are also included as paths.
    """
    keys: set[str] = set()
    if isinstance(value, dict):
        for k, v in value.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            keys.add(path)
            keys |= _collect_keys(v, path)
    elif isinstance(value, list):
        # Lists: we don't expand indices; still consider it a leaf container.
        if prefix:
            keys.add(prefix)
    else:
        if prefix:
            keys.add(prefix)
    return keys


@dataclass
class Diff:
    missing_zh: list[str]
    extra_zh: list[str]
    placeholder_missing_zh: list[str]
    placeholder_extra_zh: list[str]


def _diff(en_obj: Any, zh_obj: Any) -> Diff:
    en_keys = _collect_keys(en_obj)
    zh_keys = _collect_keys(zh_obj)

    en_ph = _get_placeholders(en_obj)
    zh_ph = _get_placeholders(zh_obj)

    return Diff(
        missing_zh=sorted(en_keys - zh_keys),
        extra_zh=sorted(zh_keys - en_keys),
        placeholder_missing_zh=sorted(en_ph - zh_ph),
        placeholder_extra_zh=sorted(zh_ph - en_ph),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail", action="store_true", help="exit non-zero on any issue")
    args = parser.parse_args()

    if not AGENTS_DIR.exists():
        print(f"Agents directory not found: {AGENTS_DIR}", file=sys.stderr)
        return 2

    issues = 0

    for module_dir in sorted([p for p in AGENTS_DIR.iterdir() if p.is_dir()]):
        prompts_dir = module_dir / "prompts"
        en_dir = prompts_dir / "en"
        if not en_dir.exists():
            continue

        # Prefer zh if exists, else cn if exists (but we also compare against cn if present)
        zh_dir = prompts_dir / "zh"
        cn_dir = prompts_dir / "cn"

        for en_file in _iter_yaml_files(en_dir):
            rel = en_file.relative_to(en_dir)
            candidates = []
            if zh_dir.exists():
                candidates.append(("zh", zh_dir / rel))
            if cn_dir.exists():
                candidates.append(("cn", cn_dir / rel))

            if not candidates:
                continue

            en_obj = _load_yaml(en_file)

            for lang_name, zh_file in candidates:
                if not zh_file.exists():
                    issues += 1
                    print(f"[MISSING {lang_name}] {module_dir.name}: {rel.as_posix()}")
                    continue

                zh_obj = _load_yaml(zh_file)
                d = _diff(en_obj, zh_obj)

                if d.missing_zh or d.extra_zh or d.placeholder_missing_zh or d.placeholder_extra_zh:
                    issues += 1
                    print(f"[DIFF {lang_name}] {module_dir.name}: {rel.as_posix()}")
                    if d.missing_zh:
                        print("  - missing keys:")
                        for k in d.missing_zh[:50]:
                            print(f"    - {k}")
                        if len(d.missing_zh) > 50:
                            print(f"    ... ({len(d.missing_zh) - 50} more)")
                    if d.extra_zh:
                        print("  - extra keys:")
                        for k in d.extra_zh[:50]:
                            print(f"    - {k}")
                        if len(d.extra_zh) > 50:
                            print(f"    ... ({len(d.extra_zh) - 50} more)")
                    if d.placeholder_missing_zh:
                        print("  - missing placeholders:")
                        for p in d.placeholder_missing_zh:
                            print(f"    - {p}")
                    if d.placeholder_extra_zh:
                        print("  - extra placeholders:")
                        for p in d.placeholder_extra_zh:
                            print(f"    - {p}")

    if issues == 0:
        print("OK: prompts are structurally aligned (keys/placeholders).")
        return 0

    print(f"Found {issues} prompt parity issue(s).")
    return 1 if args.fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

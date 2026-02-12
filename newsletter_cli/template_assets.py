"""Bundled template asset helpers."""

from __future__ import annotations

from pathlib import Path
from typing import List


def _builtin_template_dir() -> Path:
    return Path(__file__).resolve().parent / "builtin_templates"


def list_builtin_templates() -> List[Path]:
    template_dir = _builtin_template_dir()
    if not template_dir.exists():
        return []
    return sorted(template_dir.glob("*.html"))


def install_builtin_templates(target_dir: Path, overwrite: bool = False) -> int:
    templates = list_builtin_templates()
    target_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for src in templates:
        dst = target_dir / src.name
        if dst.exists() and not overwrite:
            continue
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        copied += 1
    return copied

"""Filesystem template discovery and validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

TEMPLATE_PATTERN = re.compile(r"^(?P<name>.+)_(?P<language>de|en)\.html$")


@dataclass(frozen=True)
class TemplateInfo:
    name: str
    language: str
    path: Path


def list_templates(template_dir: Path) -> List[TemplateInfo]:
    if not template_dir.exists():
        return []

    found: List[TemplateInfo] = []
    for candidate in sorted(template_dir.glob("*.html")):
        match = TEMPLATE_PATTERN.match(candidate.name)
        if match:
            found.append(
                TemplateInfo(
                    name=match.group("name"),
                    language=match.group("language"),
                    path=candidate,
                )
            )
    return found


def resolve_template(template_dir: Path, template_name: str, language: str) -> Path:
    candidate = template_dir / f"{template_name}_{language}.html"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"Template not found: {candidate}. Expected filename format '<name>_{language}.html'."
    )


def validate_template(template_path: Path) -> None:
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    env = Environment(loader=FileSystemLoader(str(template_path.parent)))
    try:
        env.get_template(template_path.name)
    except TemplateSyntaxError as exc:
        raise ValueError(f"Invalid template syntax in {template_path}: {exc}") from exc

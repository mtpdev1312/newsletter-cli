from pathlib import Path

import pytest

from newsletter_cli.templates import list_templates, resolve_template, validate_template


def test_list_templates_detects_language_suffix(tmp_path: Path):
    (tmp_path / "basic_de.html").write_text("<html>{{ products|length }}</html>", encoding="utf-8")
    (tmp_path / "basic_en.html").write_text("<html>{{ products|length }}</html>", encoding="utf-8")
    (tmp_path / "ignored.html").write_text("<html></html>", encoding="utf-8")

    templates = list_templates(tmp_path)
    assert len(templates) == 2
    assert {(t.name, t.language) for t in templates} == {("basic", "de"), ("basic", "en")}


def test_resolve_template_by_name_and_language(tmp_path: Path):
    expected = tmp_path / "promo_de.html"
    expected.write_text("<html></html>", encoding="utf-8")

    resolved = resolve_template(tmp_path, "promo", "de")
    assert resolved == expected


def test_validate_template_fails_on_syntax_error(tmp_path: Path):
    broken = tmp_path / "broken_de.html"
    broken.write_text("<html>{% for item in products %}</html>", encoding="utf-8")

    with pytest.raises(ValueError):
        validate_template(broken)

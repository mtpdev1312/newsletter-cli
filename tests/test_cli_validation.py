from pathlib import Path

from newsletter_cli.cli import main


def test_generate_fails_for_invalid_products_json(tmp_path, monkeypatch):
    template_dir = tmp_path / "templates"
    output_dir = tmp_path / "output"
    template_dir.mkdir()
    output_dir.mkdir()

    db_url = f"sqlite:///{tmp_path / 'newsletter.db'}"
    monkeypatch.setenv("NEWSLETTER_DB_URL", db_url)
    monkeypatch.setenv("NEWSLETTER_TEMPLATE_DIR", str(template_dir))
    monkeypatch.setenv("NEWSLETTER_OUTPUT_DIR", str(output_dir))

    (template_dir / "basic_de.html").write_text("<html>{{ total_products }}</html>", encoding="utf-8")
    bad_products = tmp_path / "products.json"
    bad_products.write_text('{"oops": true}', encoding="utf-8")

    code = main(
        [
            "generate",
            "--template",
            "basic",
            "--language",
            "de",
            "--products-file",
            str(bad_products),
        ]
    )
    assert code == 1


def test_templates_list_command_runs(tmp_path, monkeypatch):
    template_dir = tmp_path / "templates"
    output_dir = tmp_path / "output"
    template_dir.mkdir()
    output_dir.mkdir()

    monkeypatch.setenv("NEWSLETTER_DB_URL", f"sqlite:///{tmp_path / 'newsletter.db'}")
    monkeypatch.setenv("NEWSLETTER_TEMPLATE_DIR", str(template_dir))
    monkeypatch.setenv("NEWSLETTER_OUTPUT_DIR", str(output_dir))

    (template_dir / "basic_en.html").write_text("<html></html>", encoding="utf-8")
    code = main(["templates", "list"])
    assert code == 0

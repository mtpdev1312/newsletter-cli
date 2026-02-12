import json
from pathlib import Path

from newsletter_cli.db import create_session_factory
from newsletter_cli.generator import ProductInput, generate_newsletter
from newsletter_cli.models import Base, MTPProductCache, NewsletterRun


def test_generate_html_and_store_run(tmp_path: Path):
    db_file = tmp_path / "newsletter.db"
    db_url = f"sqlite:///{db_file}"

    session_factory, engine = create_session_factory(db_url)
    Base.metadata.create_all(bind=engine)

    template_dir = tmp_path / "templates"
    output_dir = tmp_path / "output"
    template_dir.mkdir()
    output_dir.mkdir()

    template = template_dir / "basic_de.html"
    template.write_text(
        "<html><body>{{ total_products }} {{ products[0].ArticleNumber }} {{ formatted_total_amount }}</body></html>",
        encoding="utf-8",
    )

    db = session_factory()
    db.add(
        MTPProductCache(
            article_number="MTP102004",
            name_de="Produkt DE",
            name_en="Product EN",
            price_retail_vat=100.0,
            detail_images_urls=json.dumps(["https://cdn.example.com/MTP102004.jpg"]),
            is_active=True,
        )
    )
    db.commit()

    result = generate_newsletter(
        db=db,
        template_path=template,
        template_name="basic",
        language="de",
        products=[ProductInput(article_number="MTP102004", discount=10, quantity=2)],
        validity_date="2026-12-31",
        generate_pdf=False,
        output_dir=output_dir,
    )

    assert result.run_id > 0
    assert result.html_path.exists()
    assert result.pdf_path is None

    run = db.query(NewsletterRun).filter(NewsletterRun.id == result.run_id).first()
    assert run is not None
    assert run.template_name == "basic"
    assert run.language == "de"
    assert run.products_count == 1
    db.close()

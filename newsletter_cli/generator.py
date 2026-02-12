"""Newsletter generation pipeline for standalone CLI."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from jinja2 import Template
from sqlalchemy.orm import Session

from .models import MTPProductCache, NewsletterRun

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProductInput:
    article_number: str
    discount: int = 0
    quantity: int = 1


@dataclass(frozen=True)
class GenerateResult:
    run_id: int
    html_path: Path
    pdf_path: Optional[Path]


def _format_currency(value_float: float) -> str:
    value_rounded = round(value_float, 2)
    formatted_str = "{:,.2f}".format(value_rounded)
    return formatted_str.replace(",", "X").replace(".", ",").replace("X", ".")


def _extract_first_detail_image(detail_images_list: List[str], article_number: str) -> Optional[str]:
    if not detail_images_list:
        return None
    for url in detail_images_list:
        if article_number in url:
            return url
    return detail_images_list[0]


def _select_price(product: MTPProductCache) -> float:
    return float(
        product.price_dealer
        or product.price_retail_net
        or product.price_retail_vat
        or product.price_retail_gross
        or 0.0
    )


def _prepare_products(db: Session, inputs: List[ProductInput], language: str) -> List[Dict[str, object]]:
    selected_products: List[Dict[str, object]] = []

    for product_input in inputs:
        cached = (
            db.query(MTPProductCache)
            .filter(MTPProductCache.article_number == product_input.article_number)
            .first()
        )
        if not cached:
            logger.warning("Article %s not found in cache", product_input.article_number)
            continue

        price = _select_price(cached)
        discounted_price = price * (1 - product_input.discount / 100.0) if product_input.discount > 0 else price

        detail_images = []
        if cached.detail_images_urls:
            try:
                detail_images = json.loads(cached.detail_images_urls)
            except json.JSONDecodeError:
                detail_images = []

        name_de = cached.name_de or cached.name_en or "Unknown Product"
        name_en = cached.name_en or cached.name_de or "Unknown Product"
        desc_de = cached.description_de or cached.description_en or ""
        desc_en = cached.description_en or cached.description_de or ""

        selected_products.append(
            {
                "ArticleNumber": cached.article_number,
                "Name": name_de if language == "de" else name_en,
                "NameDE": name_de,
                "NameEN": name_en,
                "Price": price,
                "DiscountedPrice": discounted_price,
                "FormattedPrice": _format_currency(discounted_price),
                "OriginalPrice": _format_currency(price) if product_input.discount > 0 else None,
                "Discount": product_input.discount,
                "Quantity": product_input.quantity,
                "TotalPrice": discounted_price * product_input.quantity,
                "FormattedTotalPrice": _format_currency(discounted_price * product_input.quantity),
                "ImageUrl": _extract_first_detail_image(detail_images, cached.article_number),
                "Category": cached.category or "",
                "Description": desc_de if language == "de" else desc_en,
                "Artist": cached.artist or "",
                "Label": cached.label or "",
                "Genre": cached.genre or "",
                "ReleaseDate": cached.release_date or "",
            }
        )

    if not selected_products:
        raise RuntimeError("No valid products found for the provided article numbers")

    return selected_products


def _render_html(template_path: Path, products: List[Dict[str, object]], language: str, validity_date: Optional[str]) -> str:
    template_content = template_path.read_text(encoding="utf-8")
    template = Template(template_content)

    total_discount_amount = sum((p["Price"] - p["DiscountedPrice"]) * p["Quantity"] for p in products if p["Discount"] > 0)
    total_amount = sum(p["TotalPrice"] for p in products)

    now = datetime.now()
    date_format = "%d.%m.%Y" if language == "de" else "%Y-%m-%d"

    formatted_validity_date = ""
    if validity_date:
        try:
            formatted_validity_date = datetime.strptime(validity_date, "%Y-%m-%d").strftime(date_format)
        except ValueError:
            formatted_validity_date = validity_date

    context = {
        "products": products,
        "total_products": len(products),
        "total_amount": total_amount,
        "formatted_total_amount": _format_currency(total_amount),
        "total_discount_amount": total_discount_amount,
        "formatted_total_discount": _format_currency(total_discount_amount),
        "validity_date": validity_date or "",
        "formatted_validity_date": formatted_validity_date,
        "language": language,
        "generation_date": now.strftime(date_format),
        "generation_time": now.strftime("%H:%M"),
    }
    return template.render(context)


def _write_pdf(html_content: str, output_path: Path) -> None:
    try:
        import weasyprint
    except ImportError as exc:
        raise RuntimeError("PDF generation requested but WeasyPrint is not installed") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    weasyprint.HTML(string=html_content).write_pdf(str(output_path))


def generate_newsletter(
    db: Session,
    template_path: Path,
    template_name: str,
    language: str,
    products: List[ProductInput],
    validity_date: Optional[str],
    generate_pdf: bool,
    output_dir: Path,
) -> GenerateResult:
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_products = _prepare_products(db=db, inputs=products, language=language)
    html_content = _render_html(
        template_path=template_path,
        products=selected_products,
        language=language,
        validity_date=validity_date,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"newsletter_{language}_{timestamp}"
    html_path = output_dir / f"{filename}.html"
    html_path.write_text(html_content, encoding="utf-8")

    pdf_path: Optional[Path] = None
    if generate_pdf:
        pdf_path = output_dir / f"{filename}.pdf"
        _write_pdf(html_content=html_content, output_path=pdf_path)

    article_numbers = json.dumps(
        [
            {
                "article_number": p.article_number,
                "discount": p.discount,
                "quantity": p.quantity,
            }
            for p in products
        ]
    )

    run = NewsletterRun(
        filename=filename,
        template_name=template_name,
        language=language,
        validity_date=validity_date,
        products_count=len(selected_products),
        article_numbers=article_numbers,
        html_path=str(html_path),
        pdf_path=str(pdf_path) if pdf_path else None,
        output_dir=str(output_dir),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return GenerateResult(run_id=run.id, html_path=html_path, pdf_path=pdf_path)

"""Interactive wizard for newsletter generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from .config import Settings, ensure_runtime_directories, load_settings
from .db import get_session, init_db
from .generator import ProductInput, generate_newsletter
from .models import MTPProductCache
from .template_assets import install_builtin_templates
from .templates import TemplateInfo, list_templates, resolve_template, validate_template

RICH_IMPORT_ERROR: Exception | None = None

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, IntPrompt, Prompt
    from rich.table import Table
except ImportError as exc:  # pragma: no cover
    RICH_IMPORT_ERROR = exc


@dataclass(frozen=True)
class WizardConfig:
    template: TemplateInfo
    products: List[ProductInput]
    validity_date: Optional[str]
    generate_pdf: bool
    output_dir: Path


def _lookup_product(db: Session, article_number: str) -> Optional[MTPProductCache]:
    return db.query(MTPProductCache).filter(MTPProductCache.article_number == article_number).first()


def _select_template(console: Console, settings: Settings) -> TemplateInfo:
    templates = list_templates(settings.newsletter_template_dir)

    if not templates:
        console.print(
            Panel(
                f"No templates found in [bold]{settings.newsletter_template_dir}[/bold].",
                title="Templates",
                border_style="yellow",
            )
        )
        if Confirm.ask("Install bundled templates now?", default=True):
            copied = install_builtin_templates(settings.newsletter_template_dir, overwrite=False)
            console.print(f"Installed {copied} templates to {settings.newsletter_template_dir}")
        templates = list_templates(settings.newsletter_template_dir)

    if not templates:
        raise RuntimeError(
            f"No templates available in {settings.newsletter_template_dir}. "
            "Use 'newsletter templates install' or add files named <name>_<de|en>.html"
        )

    table = Table(title="Available Templates")
    table.add_column("#", justify="right")
    table.add_column("Template")
    table.add_column("Language")
    table.add_column("Path")

    for idx, tmpl in enumerate(templates, start=1):
        table.add_row(str(idx), tmpl.name, tmpl.language, str(tmpl.path))

    console.print(table)
    index = IntPrompt.ask("Select template", default=1)
    if index < 1 or index > len(templates):
        raise RuntimeError(f"Template selection out of range: {index}")

    return templates[index - 1]


def _collect_products(console: Console, db: Session) -> List[ProductInput]:
    products: List[ProductInput] = []

    console.print(Panel("Add one or more products (blank article number to finish).", title="Products"))

    while True:
        article_number = Prompt.ask("Article number (e.g. MTP102004)", default="").strip()
        if not article_number:
            if products:
                break
            console.print("At least one product is required.", style="yellow")
            continue

        cached = _lookup_product(db, article_number)
        if cached:
            display_name = cached.name_de or cached.name_en or "Unknown name"
            console.print(f"Found: [bold]{display_name}[/bold]")
        else:
            console.print("Not found in local cache; generation may skip this article.", style="yellow")

        discount = IntPrompt.ask("Discount (%)", default=0)
        if discount < 0 or discount > 100:
            console.print("Discount must be between 0 and 100.", style="red")
            continue

        quantity = IntPrompt.ask("Quantity", default=1)
        if quantity < 1:
            console.print("Quantity must be at least 1.", style="red")
            continue

        products.append(ProductInput(article_number=article_number, discount=discount, quantity=quantity))

    return products


def _ask_validity_date(console: Console) -> Optional[str]:
    value = Prompt.ask("Validity date YYYY-MM-DD (optional)", default="").strip()
    if not value:
        return None

    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise RuntimeError("Validity date must use format YYYY-MM-DD") from exc

    return value


def _collect_wizard_config(console: Console, settings: Settings, db: Session) -> WizardConfig:
    template = _select_template(console, settings)
    products = _collect_products(console, db)
    validity_date = _ask_validity_date(console)
    generate_pdf = Confirm.ask("Generate PDF too?", default=True)

    output_default = str(settings.newsletter_output_dir)
    output_dir_raw = Prompt.ask("Output directory", default=output_default).strip()
    output_dir = Path(output_dir_raw)

    summary = Table(title="Summary")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Template", template.name)
    summary.add_row("Language", template.language)
    summary.add_row("Products", str(len(products)))
    summary.add_row("Validity date", validity_date or "-")
    summary.add_row("Generate PDF", "yes" if generate_pdf else "no")
    summary.add_row("Output", str(output_dir))
    console.print(summary)

    if not Confirm.ask("Generate newsletter now?", default=True):
        raise RuntimeError("Cancelled by user")

    return WizardConfig(
        template=template,
        products=products,
        validity_date=validity_date,
        generate_pdf=generate_pdf,
        output_dir=output_dir,
    )


def run_interactive_wizard() -> int:
    if RICH_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Interactive mode requires 'rich'. Install dependencies from requirements.txt."
        ) from RICH_IMPORT_ERROR

    settings = load_settings()
    ensure_runtime_directories(settings)
    init_db(settings.newsletter_db_url)

    console = Console()
    console.print(Panel("Newsletter Generator Wizard", border_style="cyan", title="newsletter"))

    with get_session(settings.newsletter_db_url) as db:
        config = _collect_wizard_config(console, settings, db)

        template_path = resolve_template(
            template_dir=settings.newsletter_template_dir,
            template_name=config.template.name,
            language=config.template.language,
        )
        validate_template(template_path)

        result = generate_newsletter(
            db=db,
            template_path=template_path,
            template_name=config.template.name,
            language=config.template.language,
            products=config.products,
            validity_date=config.validity_date,
            generate_pdf=config.generate_pdf,
            output_dir=config.output_dir,
        )

    result_table = Table(title="Done")
    result_table.add_column("Output")
    result_table.add_column("Path")
    result_table.add_row("Run ID", str(result.run_id))
    result_table.add_row("HTML", str(result.html_path))
    result_table.add_row("PDF", str(result.pdf_path) if result.pdf_path else "-")
    console.print(result_table)

    return 0

"""Command-line entrypoint for standalone newsletter service."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

from .cache import refresh_cache
from .config import (
    ensure_required_mtp_credentials,
    ensure_runtime_directories,
    load_settings,
)
from .db import get_session, init_db
from .generator import ProductInput, generate_newsletter
from .models import NewsletterRun
from .templates import list_templates, resolve_template, validate_template


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _load_products_file(products_file: Path) -> List[ProductInput]:
    try:
        payload = json.loads(products_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to parse products file {products_file}: {exc}") from exc

    if not isinstance(payload, list):
        raise RuntimeError("Products file must contain a JSON array")

    products: List[ProductInput] = []
    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise RuntimeError(f"Product at index {idx} must be an object")

        article_number = str(item.get("article_number", "")).strip()
        if not article_number:
            raise RuntimeError(f"Product at index {idx} missing article_number")

        discount = int(item.get("discount", 0))
        quantity = int(item.get("quantity", 1))
        if discount < 0 or discount > 100:
            raise RuntimeError(f"Product at index {idx} has invalid discount: {discount}")
        if quantity < 1:
            raise RuntimeError(f"Product at index {idx} has invalid quantity: {quantity}")

        products.append(ProductInput(article_number=article_number, discount=discount, quantity=quantity))

    return products


def cmd_init() -> int:
    settings = load_settings()
    _configure_logging(settings.newsletter_log_level)

    ensure_runtime_directories(settings)
    init_db(settings.newsletter_db_url)

    print("Initialized newsletter service")
    print(f"DB: {settings.newsletter_db_url}")
    print(f"Templates: {settings.newsletter_template_dir}")
    print(f"Output: {settings.newsletter_output_dir}")
    return 0


def cmd_cache_refresh() -> int:
    settings = load_settings()
    _configure_logging(settings.newsletter_log_level)
    ensure_required_mtp_credentials(settings)
    ensure_runtime_directories(settings)
    init_db(settings.newsletter_db_url)

    with get_session(settings.newsletter_db_url) as db:
        count = refresh_cache(
            db=db,
            service_url=settings.mtp_api_service_url,
            username=settings.mtp_api_username,
            password=settings.mtp_api_password,
        )
    print(f"Refreshed MTP cache: {count} products")
    return 0


def cmd_templates_list() -> int:
    settings = load_settings()
    _configure_logging(settings.newsletter_log_level)
    ensure_runtime_directories(settings)

    templates = list_templates(settings.newsletter_template_dir)
    if not templates:
        print("No templates found")
        return 0

    for tmpl in templates:
        print(f"{tmpl.name}\t{tmpl.language}\t{tmpl.path}")
    return 0


def cmd_templates_validate(template_path: Path) -> int:
    settings = load_settings()
    _configure_logging(settings.newsletter_log_level)

    validate_template(template_path)
    print(f"Template valid: {template_path}")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    settings = load_settings()
    _configure_logging(settings.newsletter_log_level)
    ensure_runtime_directories(settings)
    init_db(settings.newsletter_db_url)

    template_path = resolve_template(
        template_dir=settings.newsletter_template_dir,
        template_name=args.template,
        language=args.language,
    )
    validate_template(template_path)

    products = _load_products_file(Path(args.products_file))
    output_dir = Path(args.output_dir) if args.output_dir else settings.newsletter_output_dir

    with get_session(settings.newsletter_db_url) as db:
        result = generate_newsletter(
            db=db,
            template_path=template_path,
            template_name=args.template,
            language=args.language,
            products=products,
            validity_date=args.validity_date,
            generate_pdf=args.pdf,
            output_dir=output_dir,
        )

    print(f"Run ID: {result.run_id}")
    print(f"HTML: {result.html_path}")
    if result.pdf_path:
        print(f"PDF: {result.pdf_path}")
    return 0


def cmd_runs_list(limit: int) -> int:
    settings = load_settings()
    _configure_logging(settings.newsletter_log_level)
    ensure_runtime_directories(settings)
    init_db(settings.newsletter_db_url)

    with get_session(settings.newsletter_db_url) as db:
        runs = db.query(NewsletterRun).order_by(NewsletterRun.created_at.desc()).limit(limit).all()

    if not runs:
        print("No newsletter runs found")
        return 0

    for run in runs:
        print(
            f"id={run.id} created_at={run.created_at} template={run.template_name} "
            f"lang={run.language} products={run.products_count} html={run.html_path}"
        )
    return 0


def cmd_runs_show(run_id: int) -> int:
    settings = load_settings()
    _configure_logging(settings.newsletter_log_level)
    ensure_runtime_directories(settings)
    init_db(settings.newsletter_db_url)

    with get_session(settings.newsletter_db_url) as db:
        run = db.query(NewsletterRun).filter(NewsletterRun.id == run_id).first()

    if not run:
        raise RuntimeError(f"Run not found: {run_id}")

    payload = {
        "id": run.id,
        "filename": run.filename,
        "template_name": run.template_name,
        "language": run.language,
        "validity_date": run.validity_date,
        "products_count": run.products_count,
        "article_numbers": json.loads(run.article_numbers),
        "html_path": run.html_path,
        "pdf_path": run.pdf_path,
        "output_dir": run.output_dir,
        "created_at": str(run.created_at),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="newsletter", description="Standalone newsletter generator")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize schema and runtime directories")

    cache_parser = sub.add_parser("cache", help="Cache operations")
    cache_sub = cache_parser.add_subparsers(dest="cache_command", required=True)
    cache_sub.add_parser("refresh", help="Refresh product cache from MTP API")

    tmpl_parser = sub.add_parser("templates", help="Template operations")
    tmpl_sub = tmpl_parser.add_subparsers(dest="templates_command", required=True)
    tmpl_sub.add_parser("list", help="List templates")
    validate_parser = tmpl_sub.add_parser("validate", help="Validate a template file")
    validate_parser.add_argument("--template", required=True, help="Absolute or relative template file path")

    gen = sub.add_parser("generate", help="Generate newsletter")
    gen.add_argument("--template", required=True, help="Template name without language suffix")
    gen.add_argument("--language", required=True, choices=["de", "en"], help="Template language")
    gen.add_argument("--products-file", required=True, help="Path to products JSON file")
    gen.add_argument("--validity-date", required=False, help="Validity date YYYY-MM-DD")
    gen.add_argument("--pdf", action="store_true", help="Generate PDF")
    gen.add_argument("--output-dir", required=False, help="Override output directory")

    runs = sub.add_parser("runs", help="Run metadata operations")
    runs_sub = runs.add_subparsers(dest="runs_command", required=True)
    list_parser = runs_sub.add_parser("list", help="List recent runs")
    list_parser.add_argument("--limit", type=int, default=20, help="Max rows to return")
    show_parser = runs_sub.add_parser("show", help="Show run details")
    show_parser.add_argument("--id", type=int, required=True, help="Run ID")

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            return cmd_init()

        if args.command == "cache" and args.cache_command == "refresh":
            return cmd_cache_refresh()

        if args.command == "templates" and args.templates_command == "list":
            return cmd_templates_list()

        if args.command == "templates" and args.templates_command == "validate":
            return cmd_templates_validate(Path(args.template))

        if args.command == "generate":
            return cmd_generate(args)

        if args.command == "runs" and args.runs_command == "list":
            return cmd_runs_list(args.limit)

        if args.command == "runs" and args.runs_command == "show":
            return cmd_runs_show(args.id)

        parser.print_help()
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

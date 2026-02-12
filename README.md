# Newsletter CLI (Standalone)

Standalone terminal service for generating newsletters on an always-on server (e.g., Hetzner).

## Features
- `newsletter init`
- `newsletter cache refresh`
- `newsletter templates list`
- `newsletter templates validate --template <path>`
- `newsletter generate --template <name> --language <de|en> --products-file <json> [--validity-date YYYY-MM-DD] [--pdf] [--output-dir <path>]`
- `newsletter runs list [--limit N]`
- `newsletter runs show --id <run_id>`

## Quick Start (local)
```bash
cd /Users/mpunktspunkt/Desktop/mtpsuite/services/newsletter_cli
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
```

Create template files in your template dir using this naming format:
- `<template_name>_de.html`
- `<template_name>_en.html`

Example:
```bash
newsletter init
newsletter templates list
newsletter cache refresh
newsletter generate --template basic --language de --products-file examples/products.json --pdf
newsletter runs list --limit 10
```

## Product Input JSON
```json
[
  { "article_number": "MTP102004", "discount": 0, "quantity": 1 },
  { "article_number": "MTP102017", "discount": 10, "quantity": 2 }
]
```

## Notes
- HTML is always generated.
- PDF generation requires WeasyPrint and system libraries.
- Runtime paths default to `/opt/mtp-newsletter/...` and are configurable via environment variables.

## Hetzner Deployment Assets
See `/Users/mpunktspunkt/Desktop/mtpsuite/services/newsletter_cli/deployment`.

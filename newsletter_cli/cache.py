"""MTP product cache refresh logic for standalone CLI."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List

from sqlalchemy.orm import Session

from .models import MTPProductCache
from .mtp_api import fetch_product_feed

logger = logging.getLogger(__name__)


def _extract_text(value: Any) -> str:
    if isinstance(value, dict) and "#text" in value:
        return str(value.get("#text", ""))
    if value is None:
        return ""
    return str(value)


def _extract_price(value: Any):
    text = _extract_text(value)
    if not text or text in {"0", "0,00"}:
        return None
    try:
        normalized = text.replace(".", "").replace(",", ".")
        return float(normalized)
    except ValueError:
        return None


def _extract_detail_images(detail_images: str) -> List[str]:
    urls: List[str] = []
    for part in (detail_images or "").split():
        url = part.strip('"')
        if url.startswith("http"):
            urls.append(url)
    return urls


def _iter_entries(feed_payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    entries = feed_payload.get("feed", {}).get("entry", [])
    if isinstance(entries, dict):
        return [entries]
    return entries


def refresh_cache(db: Session, service_url: str, username: str, password: str) -> int:
    feed = fetch_product_feed(service_url=service_url, username=username, password=password)
    if not feed:
        raise RuntimeError("Failed to fetch product data from MTP API")

    processed = 0
    for entry in _iter_entries(feed):
        properties = entry.get("content", {}).get("m:properties", {})
        article_number = _extract_text(properties.get("d:Artikelnummer", "")).strip()
        if not article_number:
            continue

        detail_images = _extract_detail_images(_extract_text(properties.get("d:Detailbilder", "")))
        all_fields = {
            key: _extract_text(value)
            for key, value in properties.items()
            if isinstance(key, str) and key.startswith("d:")
        }

        existing = db.query(MTPProductCache).filter(MTPProductCache.article_number == article_number).first()
        if not existing:
            existing = MTPProductCache(article_number=article_number)
            db.add(existing)

        existing.name_de = _extract_text(properties.get("d:Bezeichnung-Deutsch", ""))
        existing.name_en = _extract_text(properties.get("d:Bezeichnung-Englisch", ""))
        existing.category = _extract_text(properties.get("d:Artikelgruppe", ""))
        existing.price_dealer = _extract_price(properties.get("d:dealer_price"))
        existing.price_retail_net = _extract_price(properties.get("d:retail_price_net"))
        existing.price_retail_vat = _extract_price(properties.get("d:retail_price_vat"))
        existing.price_retail_gross = _extract_price(properties.get("d:retail_price_gross"))
        existing.description_de = _extract_text(properties.get("d:Langtext-Deutsch", ""))
        existing.description_en = _extract_text(properties.get("d:Langtext-Englisch", ""))
        existing.artist = _extract_text(properties.get("d:Künstler", ""))
        existing.label = _extract_text(properties.get("d:Label", ""))
        existing.genre = _extract_text(properties.get("d:Genre", ""))
        existing.release_date = _extract_text(properties.get("d:Veröffentlichungsdatum", ""))
        existing.main_image_url = _extract_text(properties.get("d:Produktbild", ""))
        existing.detail_images_urls = json.dumps(detail_images)
        existing.all_fields_json = json.dumps(all_fields)
        existing.is_active = True
        existing.last_updated = datetime.utcnow()

        inventory_raw = _extract_text(properties.get("d:Gesamtlagerbestand", "0"))
        try:
            existing.inventory_total = int(inventory_raw) if inventory_raw else 0
        except ValueError:
            existing.inventory_total = 0

        processed += 1
        if processed % 200 == 0:
            db.commit()
            logger.info("Processed %s products", processed)

    db.commit()
    return processed

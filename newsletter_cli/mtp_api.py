"""MTP API client and XML parsing utilities."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests
import xmltodict

logger = logging.getLogger(__name__)


def fetch_product_feed(service_url: str, username: str, password: str) -> Optional[Dict[str, Any]]:
    url = service_url.rstrip("/") + "/SmartReportDataClass_mtpWebshopProducts"
    try:
        response = requests.get(url, auth=(username, password), headers={"Accept": "application/xml"}, timeout=30)
        response.raise_for_status()
        parsed = xmltodict.parse(response.content)
        if "feed" not in parsed:
            logger.error("MTP response missing 'feed' element")
            return None
        return parsed
    except requests.exceptions.Timeout:
        logger.error("MTP API request timeout")
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("MTP API request failed: %s", exc)
        return None
    except Exception as exc:  # pragma: no cover - defensive parse handling
        logger.error("MTP API parse failed: %s", exc)
        return None

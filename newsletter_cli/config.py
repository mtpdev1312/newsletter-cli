"""Configuration helpers for standalone newsletter CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _default_db_url() -> str:
    return "sqlite:////opt/mtp-newsletter/data/newsletter.db"


@dataclass(frozen=True)
class Settings:
    mtp_api_username: str
    mtp_api_password: str
    mtp_api_service_url: str
    newsletter_db_url: str
    newsletter_template_dir: Path
    newsletter_output_dir: Path
    newsletter_log_dir: Path
    newsletter_log_level: str


def load_settings() -> Settings:
    load_dotenv()

    template_dir = Path(os.getenv("NEWSLETTER_TEMPLATE_DIR", "/opt/mtp-newsletter/templates"))
    output_dir = Path(os.getenv("NEWSLETTER_OUTPUT_DIR", "/opt/mtp-newsletter/output"))
    log_dir = Path(os.getenv("NEWSLETTER_LOG_DIR", "/opt/mtp-newsletter/logs"))

    return Settings(
        mtp_api_username=os.getenv("MTP_API_USERNAME", ""),
        mtp_api_password=os.getenv("MTP_API_PASSWORD", ""),
        mtp_api_service_url=os.getenv("MTP_API_SERVICE_URL", ""),
        newsletter_db_url=os.getenv("NEWSLETTER_DB_URL", _default_db_url()),
        newsletter_template_dir=template_dir,
        newsletter_output_dir=output_dir,
        newsletter_log_dir=log_dir,
        newsletter_log_level=os.getenv("NEWSLETTER_LOG_LEVEL", "INFO"),
    )


def ensure_required_mtp_credentials(settings: Settings) -> None:
    missing = []
    if not settings.mtp_api_username:
        missing.append("MTP_API_USERNAME")
    if not settings.mtp_api_password:
        missing.append("MTP_API_PASSWORD")
    if not settings.mtp_api_service_url:
        missing.append("MTP_API_SERVICE_URL")

    if missing:
        msg = ", ".join(missing)
        raise RuntimeError(f"Missing required MTP API configuration: {msg}")


def ensure_runtime_directories(settings: Settings) -> None:
    settings.newsletter_template_dir.mkdir(parents=True, exist_ok=True)
    settings.newsletter_output_dir.mkdir(parents=True, exist_ok=True)
    settings.newsletter_log_dir.mkdir(parents=True, exist_ok=True)

    if settings.newsletter_db_url.startswith("sqlite:///"):
        db_file = Path(settings.newsletter_db_url.replace("sqlite:///", "", 1))
        if db_file.is_absolute() and db_file.parent != Path("/"):
            db_file.parent.mkdir(parents=True, exist_ok=True)

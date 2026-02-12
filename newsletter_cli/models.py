"""Database models for standalone newsletter CLI."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class MTPProductCache(Base):
    __tablename__ = "mtp_products_cache"

    id = Column(Integer, primary_key=True, index=True)
    article_number = Column(String(50), unique=True, index=True, nullable=False)

    name_de = Column(String(500), index=True)
    name_en = Column(String(500), index=True)
    category = Column(String(100), index=True)

    price_dealer = Column(Float, nullable=True)
    price_retail_net = Column(Float, nullable=True)
    price_retail_vat = Column(Float, nullable=True)
    price_retail_gross = Column(Float, nullable=True)

    description_de = Column(Text)
    description_en = Column(Text)

    artist = Column(String(200))
    label = Column(String(200))
    genre = Column(String(100))
    release_date = Column(String(50))

    main_image_url = Column(String(1000))
    detail_images_urls = Column(Text)
    inventory_total = Column(Integer, default=0, index=True)

    all_fields_json = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class NewsletterRun(Base):
    __tablename__ = "newsletter_runs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    template_name = Column(String(255), nullable=False)
    language = Column(String(5), nullable=False)
    validity_date = Column(String(50), nullable=True)
    products_count = Column(Integer, default=0)
    article_numbers = Column(Text, nullable=False)
    html_path = Column(String(1000), nullable=False)
    pdf_path = Column(String(1000), nullable=True)
    output_dir = Column(String(1000), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

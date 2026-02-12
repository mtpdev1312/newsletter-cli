"""Database connection helpers."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


def create_db_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, echo=False)


def create_session_factory(database_url: str):
    engine = create_db_engine(database_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine), engine


def init_db(database_url: str) -> None:
    _, engine = create_session_factory(database_url)
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session(database_url: str):
    session_factory, _ = create_session_factory(database_url)
    db: Session = session_factory()
    try:
        yield db
    finally:
        db.close()

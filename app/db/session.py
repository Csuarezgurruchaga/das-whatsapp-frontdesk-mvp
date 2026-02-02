import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


def get_engine():
    return create_engine(get_database_url(), pool_pre_ping=True, future=True)


SessionLocal = sessionmaker(class_=Session, autoflush=False, autocommit=False, expire_on_commit=False)

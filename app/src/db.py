"""Database engine/session setup (SQLAlchemy 2.x).

Connection comes from DATABASE_URL only — never hardcoded credentials.
The engine is created lazily so that liveness endpoints (/health,
/api/health) do not require the DB to be reachable at import time.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://demo:demo@postgres:5432/demo",
)

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    """Create the engine on first use (not at import)."""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    return _engine


def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autoflush=False, autocommit=False, future=True
        )
    return _SessionLocal

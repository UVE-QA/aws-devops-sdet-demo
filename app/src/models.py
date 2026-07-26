"""SQLAlchemy models for v0.

Single table: demo_items.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class DemoItem(Base):
    __tablename__ = "demo_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Added by Alembic revision 0002 (Phase 10). Nullable on purpose: it is the
    # optional half of the create contract, so the suite exercises both.
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

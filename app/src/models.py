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
    # Added by Alembic revision 0003 (Phase 16a). Filled by the DATABASE on
    # insert and on every update, not by the application: two processes with
    # two clocks would otherwise decide what "changed at" means. PostgreSQL's
    # now() is the start of the transaction, so a create and a later edit —
    # separate transactions — cannot land on the same value, which is what the
    # assertion after a UI edit relies on (ADR-0031).
    #
    # onupdate fires when SQLAlchemy emits an UPDATE. Patching a field to the
    # value it already holds emits none, so updated_at does not move. That is
    # correct and it is why the edit tests change the value.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

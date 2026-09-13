"""SQLAlchemy models.

demo_items is the api's own; item_processing is its projection of the
worker's fact; outbox is what it has yet to say (ADR-0098).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    # THE WORKER'S FACT, AS THIS SERVICE HEARD IT (ADR-0098). Revision 0004
    # had the worker stamp two columns on this row; revision 0005 moved them
    # into `item_processing`, a projection this service writes when it
    # consumes `item.processed`. The client sees the same two fields through
    # the properties below: the API contract did not move, the ownership did.
    # Loaded with the item (joined), so a page of items is one query.
    processing: Mapped[Optional["ItemProcessing"]] = relationship(
        back_populates="item", uselist=False, lazy="joined", cascade="all, delete-orphan"
    )

    @property
    def processed_at(self) -> Optional[datetime]:
        return self.processing.processed_at if self.processing else None

    @property
    def processed_by(self) -> Optional[str]:
        return self.processing.processed_by if self.processing else None


class ItemProcessing(Base):
    """What the worker reported about an item, recorded by the api on hearing
    it. One row per item, first report wins; the worker's clock and name."""

    __tablename__ = "item_processing"

    item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("demo_items.id", ondelete="CASCADE"), primary_key=True
    )
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_by: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    item: Mapped["DemoItem"] = relationship(back_populates="processing")


class OutboxEvent(Base):
    """A message written in the same transaction as the row it is about, and
    sent afterwards by the relay (src/outbox.py). `published_at` null is a
    message not yet sent; `attempts` counts the tries."""

    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

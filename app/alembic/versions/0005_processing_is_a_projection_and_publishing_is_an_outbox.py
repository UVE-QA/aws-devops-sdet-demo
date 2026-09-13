"""processing is a projection, and publishing is an outbox

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-13

Plan item 4 (ADR-0098): the worker stops writing this service's table. The
two columns revision 0004 added for it leave `demo_items`; what the client
sees as `processed_at` / `processed_by` comes from `item_processing`, a
PROJECTION this service writes when it consumes `item.processed` from the
results queue - the worker's fact, recorded here as heard. The foreign key
is within this service's own schema, so a deleted item takes its projection
with it.

`outbox` closes the gap ADR-0096 D2 named: the event is written in the same
transaction as the row it is about, and a relay publishes it afterwards.
A row with `published_at` null is a message not yet sent; `attempts` counts
the tries. The partial index is what the relay's SELECT reads.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "item_processing",
        sa.Column(
            "item_id",
            sa.BigInteger(),
            sa.ForeignKey("demo_items.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_by", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "outbox",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_outbox_unpublished",
        "outbox",
        ["id"],
        postgresql_where=sa.text("published_at IS NULL"),
    )
    op.drop_column("demo_items", "processed_by")
    op.drop_column("demo_items", "processed_at")


def downgrade() -> None:
    op.add_column(
        "demo_items",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("demo_items", sa.Column("processed_by", sa.Text(), nullable=True))
    op.drop_index("ix_outbox_unpublished", table_name="outbox")
    op.drop_table("outbox")
    op.drop_table("item_processing")

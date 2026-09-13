"""the worker's own schema

Revision ID: 0001
Revises:
Create Date: 2026-09-13

Plan item 4 (ADR-0098). One table, `worker.receipts`: what this worker did,
one row per item, first delivery wins. No foreign key to the api's table -
the item's existence is the api's fact, this row is the worker's, and the two
meet only through the queues. `processed_at` is the database's clock at the
insert, as the api's timestamps are (revision 0003's reasoning).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "receipts",
        sa.Column("item_id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processed_by", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=True),
        schema="worker",
    )


def downgrade() -> None:
    op.drop_table("receipts", schema="worker")

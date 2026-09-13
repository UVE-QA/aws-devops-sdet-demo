"""add processed_at and processed_by to demo_items

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-13

Added for the queue and the worker (Phase 42). Both NULLABLE and with no
default, on purpose: NULL means "no worker has been here yet", and that is a
statement the api makes about every row it creates and never changes. The
worker is the only writer of these two columns, and it writes them once -
`WHERE processed_at IS NULL` - which is what makes a redelivered message
harmless.

The worker writing into the api's table is the shared-database debt this
phase takes on knowingly; plan item 4 is where the worker gets a schema of
its own and these columns leave.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "demo_items",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "demo_items",
        sa.Column("processed_by", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("demo_items", "processed_by")
    op.drop_column("demo_items", "processed_at")

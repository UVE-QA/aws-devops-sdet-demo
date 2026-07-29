"""add updated_at to demo_items

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-28

Added for PATCH (Phase 16a, ADR-0031). NOT NULL with a server default, so it
applies to a seeded database in one statement and without a backfill pass:
every existing row is stamped with the migration's own now().

The server default STAYS on the column rather than being dropped after the
backfill. It is what fills the value on insert, and dropping it would make
every future insert depend on the application remembering to set it — the
same class of bug as computing the timestamp in Python.

The matching UPDATE behaviour is SQLAlchemy's `onupdate`, which lives in the
model. Postgres has no built-in equivalent short of a trigger; a trigger would
also cover writes made outside the ORM, which this project does not make.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "demo_items",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_column("demo_items", "updated_at")

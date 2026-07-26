"""add description to demo_items

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-26

Additive and nullable, so it applies to a seeded database without a backfill
and without a table rewrite. It also makes the migration chain more than one
revision long for the first time — `alembic upgrade head` on an existing
database is a different code path from creating the schema from nothing, and
until now nothing exercised it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("demo_items", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("demo_items", "description")

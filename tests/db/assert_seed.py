"""Standalone DB assertion for the seed state.

Independent of the app code on purpose: it connects via DATABASE_URL and
checks the database directly, so it can run as a separate quality gate
(local, container, or CI) without importing the application package.

Checks:
  1. table 'demo_items' exists
  2. row with name 'seed-item-001' exists

Prints clear PASS/FAIL lines. Exits non-zero on any failure.
"""
import os
import sys

from sqlalchemy import create_engine, inspect, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://demo:demo@postgres:5432/demo",
)

TABLE = "demo_items"
SEED_NAME = "seed-item-001"


def main() -> int:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

    # Check 1: table exists.
    inspector = inspect(engine)
    if not inspector.has_table(TABLE):
        print(f"FAIL: table '{TABLE}' does not exist")
        return 1
    print(f"PASS: table '{TABLE}' exists")

    # Check 2: seed row exists.
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM demo_items WHERE name = :n"), {"n": SEED_NAME}
        ).fetchone()
    if row is None:
        print(f"FAIL: row name='{SEED_NAME}' not found in '{TABLE}'")
        return 1
    print(f"PASS: row name='{SEED_NAME}' exists (id={row[0]})")

    print("DB assertion: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

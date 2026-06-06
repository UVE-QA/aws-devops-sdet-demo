"""Idempotent seed: ensure demo_items contains 'seed-item-001'.

Reuses the app's engine/session and model so there is a single source of
truth for the connection and schema. Exits 0 whether the row was inserted
or already present; non-zero only on an actual DB error.

Run from the app root (so `src` is importable), e.g. inside the container:
    python scripts/seed.py
"""
import sys

# Ensure the app root is importable when run as `python scripts/seed.py`
# from /app (the parent of scripts/). WORKDIR=/app already puts it on path,
# but be explicit for safety when invoked from elsewhere.
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from src.db import get_sessionmaker
from src.models import DemoItem

SEED_NAME = "seed-item-001"


def main() -> int:
    Session = get_sessionmaker()
    with Session() as session:
        existing = session.scalar(select(DemoItem).where(DemoItem.name == SEED_NAME))
        if existing is not None:
            print(f"[seed] '{SEED_NAME}' already present (id={existing.id}) — no-op")
            return 0
        session.add(DemoItem(name=SEED_NAME))
        session.commit()
        inserted = session.scalar(select(DemoItem).where(DemoItem.name == SEED_NAME))
        print(f"[seed] inserted '{SEED_NAME}' (id={inserted.id})")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

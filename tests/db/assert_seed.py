"""Standalone DB assertion for the seed state.

Independent of the app code on purpose: it connects via DATABASE_URL and
checks the database directly, so it can run as a separate quality gate
(local, container, or CI) without importing the application package.

Prints clear PASS/FAIL lines. Exits non-zero on any failure.

WHY THE CHECKS ARE A LIST (Phase 20c, ADR-0042). Every other suite here can be
asked what it contains - `pytest --collect-only`, `playwright --list` - and this
one could not, because its checks were statements in the middle of a function.
The map needs an inventory per suite, and the alternative was a description
maintained beside the file, which is the class of defect Phase 20 exists to end.
So the checks became a list of named callables: `--list` prints the names, the
run executes the same list, and the two cannot disagree without the file being
edited in one place.

    python3 assert_seed.py            # run the checks against DATABASE_URL
    python3 assert_seed.py --list     # print the inventory as JSON, no database

`--list` imports no driver and opens no connection: it is invoked from the
repository, where sqlalchemy is not installed, while the run happens inside the
application image. That is why the sqlalchemy import lives in the run path.
"""
import json
import os
import sys

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://demo:demo@postgres:5432/demo",
)

TABLE = "demo_items"
SEED_NAME = "seed-item-001"


def table_exists(conn_ctx) -> tuple[bool, str]:
    """the table the migration creates is present"""
    from sqlalchemy import inspect

    engine, _ = conn_ctx
    if not inspect(engine).has_table(TABLE):
        return False, f"table '{TABLE}' does not exist"
    return True, f"table '{TABLE}' exists"


def seed_row_exists(conn_ctx) -> tuple[bool, str]:
    """the row the seed script inserts is present"""
    from sqlalchemy import text

    engine, _ = conn_ctx
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM demo_items WHERE name = :n"), {"n": SEED_NAME}
        ).fetchone()
    if row is None:
        return False, f"row name='{SEED_NAME}' not found in '{TABLE}'"
    return True, f"row name='{SEED_NAME}' exists (id={row[0]})"


# The inventory AND the plan of execution, in that order. A check appended here
# is collected, run and reported; there is no second place to update.
CHECKS = (
    ("table_exists", table_exists),
    ("seed_row_exists", seed_row_exists),
)


def inventory() -> list[dict]:
    return [
        {"name": name, "asserts": (fn.__doc__ or "").strip()} for name, fn in CHECKS
    ]


def main(argv: list[str]) -> int:
    if "--list" in argv:
        print(json.dumps({"suite": "db", "tests": inventory()}, indent=2))
        return 0

    from sqlalchemy import create_engine

    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    ctx = (engine, DATABASE_URL)

    failed = False
    for name, fn in CHECKS:
        # A check that never ran is reported as SKIP rather than left out: an
        # absent line and a passing line look identical to anything reading
        # this output, and that is the failure mode this project keeps meeting.
        if failed:
            print(f"SKIP: {name} (an earlier check failed)")
            continue
        ok, detail = fn(ctx)
        print(f"{'PASS' if ok else 'FAIL'}: {name} - {detail}")
        failed = failed or not ok

    if failed:
        return 1
    print("DB assertion: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

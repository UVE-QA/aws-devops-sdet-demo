"""Standalone DB assertion for the seed state (in-image copy).

Lives under app/scripts/ so it is included in the application image
(Dockerfile: COPY scripts ./scripts) and can run as a one-off ECS task via
`aws ecs run-task` with command override ["python","scripts/assert_seed.py"].

Mirrors tests/db/assert_seed.py, which remains the local quality gate used by
`make test-db` against docker-compose. Kept independent of the app package on
purpose: it connects via DATABASE_URL and checks the database directly.

Prints clear PASS/FAIL lines. Exits non-zero on any failure.

THIS COPY IS THE ONE THE MAP OBSERVES (Phase 20c, ADR-0042). The `db` suite
node in stage and in prod is this file running as an ECS task; the tests/db copy
never leaves the devbox. So the inventory the map publishes has to describe
THIS list, and the two copies drifting would put a true description beside a
different program. `scripts/collect-suites.py` collects `--list` from both and
refuses when they disagree - the mirror is asserted, not asked for in a comment.

    python scripts/assert_seed.py            # run the checks against DATABASE_URL
    python scripts/assert_seed.py --list     # print the inventory as JSON, no database
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

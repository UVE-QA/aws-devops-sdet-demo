"""Assert that a row written THROUGH THE BROWSER reached the database.

The Playwright regression suite creates one item named $UI_PROBE_NAME via the
UI and deliberately does not delete it. This script then connects straight to
PostgreSQL and looks that row up. Two different processes, two different
protocols: the browser drove HTTP, this reads SQL. That is what turns
"the UI works" into "the UI reached RDS" — the end-to-end claim the phase is
supposed to make.

Lives under app/scripts/ so it ships in the application image
(Dockerfile: COPY scripts ./scripts) and can run as a one-off ECS task, which
is the only way to reach a database in private subnets:

    aws ecs run-task ... --overrides '{"containerOverrides":[{
        "name":"app",
        "command":["python","scripts/assert_ui_write.py"],
        "environment":[{"name":"UI_PROBE_NAME","value":"..."}]}]}'

UI_PROBE_NAME is REQUIRED and has no default. A default would let this script
pass while checking a name nobody created, which is worse than no check at all.
"""
import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://demo:demo@postgres:5432/demo",
)


def main() -> int:
    probe = os.getenv("UI_PROBE_NAME", "").strip()
    if not probe:
        print(
            "FAIL: UI_PROBE_NAME is not set. This script asserts on the exact "
            "name the UI regression created; without it there is nothing to "
            "check and a pass would be meaningless."
        )
        return 2

    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT id, description FROM demo_items WHERE name = :n"
            ),
            {"n": probe},
        ).fetchone()

    if row is None:
        print(f"FAIL: no row name='{probe}' in demo_items")
        print(
            "      The browser reported the item as created, so either the "
            "write never reached this database or the two steps are pointed "
            "at different environments."
        )
        return 1

    print(f"PASS: row name='{probe}' exists (id={row[0]}, description={row[1]!r})")
    print("UI write assertion: the browser action reached the database")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

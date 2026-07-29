"""Assert that rows written THROUGH THE BROWSER reached the database.

The Playwright regression suite drives two probes through the UI and
deliberately does not delete them. This script connects straight to
PostgreSQL and looks them up. Two different processes, two different
protocols: the browser drove HTTP, this reads SQL. That is what turns
"the UI works" into "the UI reached RDS" — the end-to-end claim the phase is
supposed to make.

    UI_PROBE_NAME        created through the create form.
                         Asserts an INSERT arrived.

    UI_EDIT_PROBE_NAME   created under a different name and RENAMED to this
                         one through the edit form (Phase 16a).
                         Asserts an UPDATE arrived — and the check is
                         updated_at > created_at, which a row that was merely
                         CREATED with this name cannot satisfy, because both
                         columns are stamped by the same now() on insert.
                         Without that comparison the edit probe would be
                         indistinguishable from a second create.

Lives under app/scripts/ so it ships in the application image
(Dockerfile: COPY scripts ./scripts) and can run as a one-off ECS task, which
is the only way to reach a database in private subnets:

    aws ecs run-task ... --overrides '{"containerOverrides":[{
        "name":"app",
        "command":["python","scripts/assert_ui_write.py"],
        "environment":[{"name":"UI_PROBE_NAME","value":"..."},
                       {"name":"UI_EDIT_PROBE_NAME","value":"..."}]}]}'

Both names are REQUIRED and have no default. A default would let this script
pass while checking a name nobody created, which is worse than no check at
all. The same applies to adding a probe: a missing variable REFUSES rather
than skipping its half, because a skipped assertion and a passed one look
identical in a green log.
"""
import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://demo:demo@postgres:5432/demo",
)


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(
            f"FAIL: {name} is not set. This script asserts on the exact name "
            "the UI regression used; without it there is nothing to check and "
            "a pass would be meaningless."
        )
        raise SystemExit(2)
    return value


def main() -> int:
    probe = required("UI_PROBE_NAME")
    edit_probe = required("UI_EDIT_PROBE_NAME")

    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    with engine.connect() as conn:
        created_row = conn.execute(
            text("SELECT id, description FROM demo_items WHERE name = :n"),
            {"n": probe},
        ).fetchone()
        edited_row = conn.execute(
            text(
                "SELECT id, description, created_at, updated_at "
                "FROM demo_items WHERE name = :n"
            ),
            {"n": edit_probe},
        ).fetchone()

    failures = 0

    if created_row is None:
        print(f"FAIL: no row name='{probe}' in demo_items")
        print(
            "      The browser reported the item as created, so either the "
            "write never reached this database or the two steps are pointed "
            "at different environments."
        )
        failures += 1
    else:
        print(
            f"PASS: row name='{probe}' exists "
            f"(id={created_row[0]}, description={created_row[1]!r})"
        )

    if edited_row is None:
        print(f"FAIL: no row name='{edit_probe}' in demo_items")
        print(
            "      The regression renamed a row to this name through the UI. "
            "An absent row means the PATCH never reached this database."
        )
        failures += 1
    else:
        _, description, created_at, updated_at = edited_row
        if updated_at is None or created_at is None:
            print(f"FAIL: row name='{edit_probe}' has a null timestamp")
            failures += 1
        elif updated_at <= created_at:
            print(
                f"FAIL: row name='{edit_probe}' was never updated "
                f"(created_at={created_at.isoformat()}, "
                f"updated_at={updated_at.isoformat()})"
            )
            print(
                "      The name is right but the row was not rewritten, which "
                "is what a CREATE under this name looks like. The edit half of "
                "the regression did not reach the database."
            )
            failures += 1
        else:
            delta = (updated_at - created_at).total_seconds()
            print(
                f"PASS: row name='{edit_probe}' was UPDATED "
                f"{delta:.3f}s after it was created "
                f"(id={edited_row[0]}, description={description!r})"
            )

    if failures:
        return 1

    print("UI write assertion: the browser's create AND edit reached the database")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

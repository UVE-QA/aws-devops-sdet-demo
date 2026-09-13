"""The worker's migration environment (ADR-0098).

Its own schema and its own version table, `worker.alembic_version`, so the
api's `public.alembic_version` and this never see each other: two services
migrating one database is two histories, not one. The schema is created here
before Alembic asks for its version table, because Alembic will not create a
schema it was told to put that table in.

No metadata: there is nothing to autogenerate from, and the one revision is
written by hand. DATABASE_URL arrives in SQLAlchemy's dialect form, as it does
for the api, because that is what the secret holds.
"""
import os

from alembic import context
from sqlalchemy import create_engine, text

SCHEMA = "worker"


def run() -> None:
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url, future=True)
    with engine.connect() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=None,
            version_table="alembic_version",
            version_table_schema=SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("the worker's migrations run online only")
run()

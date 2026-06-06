# Single image for v0: serves web, runs migrations, runs seed.
# psycopg2-binary is used so no libpq-dev/gcc build step is needed on slim.
FROM python:3.12-slim

# Faster, cleaner Python in containers.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy the application source. Build context is app/, so paths are app-relative.
#   /app/src        -> application package (uvicorn src.main:app)
#   /app/alembic    -> migration env + versions
#   /app/alembic.ini
#   /app/scripts    -> migrate.sh, seed.py
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY scripts ./scripts

# Non-root runtime user.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Default command: the web process. /health has no DB dependency, so the
# container becomes healthy before migrations run (avoids the deadlock).
# migrate/seed are run by overriding this command:
#   docker compose run --rm app alembic upgrade head
#   docker compose run --rm app python scripts/seed.py
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

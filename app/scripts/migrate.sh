#!/usr/bin/env bash
# Run Alembic migrations to the latest revision.
# Must run from the app root (where alembic.ini lives and `src` is importable),
# because alembic/env.py does `from src.db import ...`.
set -euo pipefail

# Resolve the app root as the parent of this script's dir (scripts/ -> app/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${APP_ROOT}"

echo "[migrate] running alembic upgrade head from ${APP_ROOT}"
alembic upgrade head
echo "[migrate] done"

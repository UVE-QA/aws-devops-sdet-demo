"""FastAPI app for the AWS DevOps/SDET demo (v0).

Endpoints:
  GET /              -> static HTML
  GET /health        -> liveness, NO DB
  GET /api/health    -> API liveness, NO DB
  GET /api/db-check  -> the ONLY endpoint that opens a DB connection

Critical rule (single-container v0): /health and /api/health must never
touch the DB, otherwise ECS cannot reach steady state before the migrate
task runs — a deadlock.
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text

APP_NAME = os.getenv("APP_NAME", "aws-devops-sdet-demo")
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title=APP_NAME)


@app.get("/health")
def health():
    """Liveness check — no DB access."""
    return {"status": "ok", "service": APP_NAME}


@app.get("/api/health")
def api_health():
    """API liveness check — no DB access."""
    return {"status": "ok", "service": APP_NAME}


@app.get("/api/db-check")
def db_check():
    """The only endpoint that opens a DB connection."""
    from src.db import get_engine

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as exc:  # noqa: BLE001 - report without leaking secrets
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "db": "unreachable",
                "detail": type(exc).__name__,
            },
        )


@app.get("/")
def index():
    """Serve the static frontend."""
    return FileResponse(STATIC_DIR / "index.html")

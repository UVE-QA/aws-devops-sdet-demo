"""FastAPI app for the AWS DevOps/SDET demo.

Endpoints:
  GET    /                  -> static HTML
  GET    /health            -> liveness, NO DB
  GET    /api/health        -> API liveness, NO DB
  GET    /api/db-check      -> the ONLY diagnostic endpoint that opens a DB connection
  POST   /api/items         -> 201 / 409 duplicate / 422 invalid
  GET    /api/items         -> 200, envelope {items, count}, ordered by id
  DELETE /api/items/{id}    -> 204 / 404

Critical rule (single-container v0): /health and /api/health must never
touch the DB, otherwise ECS cannot reach steady state before the migrate
task runs — a deadlock. The items endpoints DO use the DB; they are not
health checks and are not wired to any container health check.
"""
import os
from pathlib import Path
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db import get_sessionmaker
from src.models import DemoItem
from src.schemas import ItemCreate, ItemList, ItemRead

APP_NAME = os.getenv("APP_NAME", "aws-devops-sdet-demo")
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title=APP_NAME)


def get_db() -> Iterator[Session]:
    """Request-scoped session.

    get_sessionmaker() builds the engine on first use, so importing this
    module still does not require a reachable database — the property the
    CI import check depends on.
    """
    session_factory = get_sessionmaker()
    with session_factory() as session:
        yield session


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
    """Diagnostic: opens a DB connection and reports reachability."""
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


@app.post("/api/items", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> DemoItem:
    """Create one item.

    The duplicate check is the database's unique constraint, caught as an
    IntegrityError — NOT a SELECT followed by an INSERT. Checking first and
    inserting after is a race: two concurrent requests can both pass the
    check and one then fails with a 500 instead of a 409. The constraint is
    the only place where uniqueness can be decided atomically.

    demo_items has exactly one constraint that can raise this, so mapping it
    to 409 is unambiguous today. A second constraint would make this branch
    wrong, and that is the moment to inspect exc.orig rather than now.
    """
    item = DemoItem(name=payload.name, description=payload.description)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"item with name '{payload.name}' already exists",
        )
    db.refresh(item)
    return item


@app.get("/api/items", response_model=ItemList)
def list_items(db: Session = Depends(get_db)) -> ItemList:
    """List items, oldest first.

    ORDER BY id is explicit because an unordered SELECT has no guaranteed
    order in PostgreSQL, and a test that asserts on position would then pass
    or fail depending on physical row layout.
    """
    rows = db.scalars(select(DemoItem).order_by(DemoItem.id)).all()
    return ItemList(
        items=[ItemRead.model_validate(row) for row in rows], count=len(rows)
    )


@app.delete("/api/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete one item by id. 404 when it does not exist."""
    item = db.get(DemoItem, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"item {item_id} not found",
        )
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/")
def index():
    """Serve the static frontend."""
    return FileResponse(STATIC_DIR / "index.html")

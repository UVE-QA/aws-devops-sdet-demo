"""FastAPI app for the AWS DevOps/SDET demo.

Endpoints:
  GET    /                  -> static HTML
  GET    /health            -> liveness, NO DB
  GET    /api/health        -> API liveness, NO DB
  GET    /api/db-check      -> the ONLY diagnostic endpoint that opens a DB connection
  POST   /api/items         -> 201 / 409 duplicate / 422 invalid
  GET    /api/items         -> 200, envelope {items, count, total, limit,
                               offset}, ordered by id, paginated (ADR-0031)
  GET    /api/items/{id}    -> 200 / 404
  PATCH  /api/items/{id}    -> 200 / 404 / 409 duplicate / 422 invalid
  DELETE /api/items/{id}    -> 204 / 404

Critical rule (single-container v0): /health and /api/health must never
touch the DB, otherwise ECS cannot reach steady state before the migrate
task runs — a deadlock. The items endpoints DO use the DB; they are not
health checks and are not wired to any container health check.
"""
import logging
import os
import time
from pathlib import Path
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db import get_sessionmaker
from src.logging_config import (
    configure_logging,
    new_request_id,
    request_id_var,
    trace_id_var,
)
from src.models import DemoItem
from src.schemas import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    ItemCreate,
    ItemList,
    ItemRead,
    ItemUpdate,
)

APP_NAME = os.getenv("APP_NAME", "aws-devops-sdet-demo")
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title=APP_NAME)

configure_logging()
access_logger = logging.getLogger("app.access")

REQUEST_ID_HEADER = "X-Request-Id"
TRACE_ID_HEADER = "X-Amzn-Trace-Id"


def _access_fields(request: Request, status_code: int, started: float) -> dict:
    """The fields the metric filter and a human both need.

    `path` is the route TEMPLATE where one matched: a query string can carry
    values a public log should not keep, and `/api/items/{item_id}` is the
    useful grouping anyway. An unmatched path has no route and falls back to
    the request path, without its query string.
    """
    route = request.scope.get("route")
    return {
        "method": request.method,
        "path": getattr(route, "path", None) or request.url.path,
        "status": int(status_code),
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
    }


@app.middleware("http")
async def access_log(request: Request, call_next):
    """Exactly one JSON line per request, including the ones that raise.

    The request id is taken from the caller when supplied, so a test can name
    the line it is about to cause, and generated otherwise. It goes into a
    context variable BEFORE anything else runs, so any log line written during
    this request carries it too.
    """
    request_id = request.headers.get(REQUEST_ID_HEADER) or new_request_id()
    request_id_var.set(request_id)
    trace_id_var.set(request.headers.get(TRACE_ID_HEADER, ""))

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # An unhandled exception never reaches the line below, and it is the
        # single most valuable 5xx there is: log the 500 the client is about to
        # receive, then re-raise so the framework still builds that response.
        # That response is built ABOVE this middleware, so it carries no
        # X-Request-Id header — the id is in the log, which is where it is
        # needed. ADR-0032.
        access_logger.exception("request", extra=_access_fields(request, 500, started))
        raise

    access_logger.info(
        "request", extra=_access_fields(request, response.status_code, started)
    )
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


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
def list_items(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ItemList:
    """List items, oldest first, one page at a time.

    ORDER BY id is explicit because an unordered SELECT has no guaranteed
    order in PostgreSQL, and a test that asserts on position would then pass
    or fail depending on physical row layout. LIMIT/OFFSET without ORDER BY is
    the same defect with a worse symptom: the pages themselves would not be
    stable between requests.

    The bounds live on the parameters, so `?limit=0`, `?limit=101` and
    `?offset=-1` are rejected by validation as 422 rather than by hand-written
    checks that a later edit can forget (ADR-0031).

    `total` is a separate COUNT rather than len() of the page — the whole
    point is to report what the page does NOT contain.
    """
    total = db.scalar(select(func.count()).select_from(DemoItem)) or 0
    rows = db.scalars(
        select(DemoItem).order_by(DemoItem.id).limit(limit).offset(offset)
    ).all()
    return ItemList(
        items=[ItemRead.model_validate(row) for row in rows],
        count=len(rows),
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/api/items/{item_id}", response_model=ItemRead)
def get_item(item_id: int, db: Session = Depends(get_db)) -> DemoItem:
    """One item by id. 404 when it does not exist.

    A non-numeric id is a 422 from path validation, not a 404: the request is
    malformed rather than pointing at something absent, and the suite asserts
    on the difference.
    """
    item = db.get(DemoItem, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"item {item_id} not found",
        )
    return item


@app.patch("/api/items/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)
) -> DemoItem:
    """Partially update one item.

    `exclude_unset=True` is the entire contract: only fields the client
    actually sent are applied, so an absent field is untouched and an explicit
    null clears the description. The refusals — an empty patch, a null name,
    an unknown field — are declared in ItemUpdate and arrive here as 422s.

    The 409 comes from the unique constraint, exactly as in create_item, and
    for the same reason: a SELECT to check the new name followed by an UPDATE
    is a race that answers 500 under concurrency.
    """
    item = db.get(DemoItem, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"item {item_id} not found",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

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

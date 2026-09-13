"""The relay (ADR-0098): what the outbox holds, sent, in the background of the
api's own process.

    every second: take up to 20 unpublished rows, oldest first, locked
    for each: send -> mark published; a send that fails leaves the row,
             counts the attempt, and the next pass tries again

AT-LEAST-ONCE, AND SAID SO. The send and the mark are two operations; a
process that dies between them sends the row again on the next pass. That
is the contract the worker is written against - its receipt is `ON CONFLICT
DO NOTHING` - and it is cheaper than the two-phase machinery that would make
it exactly-once, which nothing here needs.

`FOR UPDATE SKIP LOCKED` is what makes two replicas of the api safe: each
takes rows the other has not, and neither waits.

One thread, started by the application's lifespan and stopped with it. The
loop body is `relay_batch`, a function over rows and a `send` callable, so
tests/unit can hold every branch without a database or a queue.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select

from src.events import ITEMS_QUEUE_URL, send
from src.models import OutboxEvent

logger = logging.getLogger("app.outbox")

BATCH = 20
PAUSE_SECONDS = 1.0


def relay_batch(rows: list, send_fn: Callable[[str, str, str], str],
                queue_url: str, now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> dict:
    """Send each row; mark the ones that went. Returns counts.

    Mutates the rows (published_at, attempts) and nothing else - committing is
    the caller's, so a test can hand this plain objects.
    """
    sent = failed = 0
    for row in rows:
        body = json.dumps(row.payload, separators=(",", ":"))
        try:
            message_id = send_fn(queue_url, body, row.event_type)
        except Exception as exc:  # noqa: BLE001 - every failure means "not yet"
            row.attempts = (row.attempts or 0) + 1
            failed += 1
            logger.warning("outbox send failed; the row stays for the next pass",
                           extra={"outbox_id": row.id, "event": row.event_type,
                                  "attempts": row.attempts, "error": str(exc)[:300]})
            continue
        row.published_at = now()
        row.attempts = (row.attempts or 0) + 1
        sent += 1
        logger.info("published", extra={"outbox_id": row.id, "event": row.event_type,
                                        "message_id": message_id})
    return {"sent": sent, "failed": failed}


def relay_once(session_factory) -> dict:
    with session_factory() as session:
        rows = session.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.id)
            .limit(BATCH)
            .with_for_update(skip_locked=True)
        ).all()
        if not rows:
            return {"sent": 0, "failed": 0}
        counts = relay_batch(rows, send, ITEMS_QUEUE_URL)
        session.commit()
        return counts


class Relay(threading.Thread):
    def __init__(self, session_factory):
        super().__init__(name="outbox-relay", daemon=True)
        self.session_factory = session_factory
        self.stop_event = threading.Event()

    def run(self) -> None:
        logger.info("outbox relay up", extra={"queue": ITEMS_QUEUE_URL})
        while not self.stop_event.is_set():
            try:
                counts = relay_once(self.session_factory)
            except Exception as exc:  # noqa: BLE001 - the database is the one dependency
                logger.warning("outbox pass failed; retrying", extra={"error": str(exc)[:300]})
                counts = {"sent": 0, "failed": 1}
            # A pass that sent a full batch goes straight back for more;
            # anything else waits a second.
            if counts["sent"] < BATCH:
                self.stop_event.wait(PAUSE_SECONDS)
        logger.info("outbox relay down")

    def stop(self) -> None:
        self.stop_event.set()

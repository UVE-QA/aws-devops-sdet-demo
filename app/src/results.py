"""The api's consumer (ADR-0098): `item.processed` from the results queue,
into the projection `item_processing`.

The mirror of the worker's loop, on this side of the seam: receive, parse,
record, delete. The same three ways a message is not deleted - poison is
left for the dead-letter queue, a transient failure is left for the next
delivery - and one more outcome that is neither: a report about an item this
service has already deleted meets the foreign key, and that is not an error,
there is nothing left to project onto. The message goes.

FIRST REPORT WINS. `ON CONFLICT (item_id) DO NOTHING`: a redelivered report
changes nothing, and a second worker that somehow reported the same item is
a fact this service does not overwrite.

The parser is pure and strict, held to contracts/item.processed.v1.json by
tests/unit/test_contracts.py; the loop is the thread.
"""
from __future__ import annotations

import json
import logging
import threading
import time

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from src.events import RESULTS_QUEUE_URL, sqs

logger = logging.getLogger("app.results")

EVENT_TYPE = "item.processed"
EVENT_VERSION = 1
WAIT_SECONDS = 20
BATCH = 10


class Poison(ValueError):
    """A report that cannot be recorded by this or any later delivery."""


def parse_item_processed(body: str) -> dict:
    """Return {item_id, processed_at, processed_by, request_id} or raise Poison."""
    try:
        event = json.loads(body)
    except (TypeError, ValueError) as exc:
        raise Poison(f"body is not JSON: {exc}") from exc
    if not isinstance(event, dict):
        raise Poison("body is not a JSON object")
    if event.get("type") != EVENT_TYPE:
        raise Poison(f"type is {event.get('type')!r}, not {EVENT_TYPE!r}")
    if event.get("version") != EVENT_VERSION:
        raise Poison(f"version is {event.get('version')!r}, not {EVENT_VERSION}")
    item = event.get("item")
    if not isinstance(item, dict):
        raise Poison("no item object")
    item_id = item.get("id")
    if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id <= 0:
        raise Poison(f"item.id is {item_id!r}, not a positive integer")
    processed_at = event.get("processed_at")
    processed_by = event.get("processed_by")
    if not isinstance(processed_at, str) or not processed_at:
        raise Poison("no processed_at")
    if not isinstance(processed_by, str) or not processed_by:
        raise Poison("no processed_by")
    request_id = event.get("request_id")
    return {
        "item_id": item_id,
        "processed_at": processed_at,
        "processed_by": processed_by,
        "request_id": request_id if isinstance(request_id, str) and request_id else None,
    }


RECORD_SQL = text(
    "INSERT INTO item_processing (item_id, processed_at, processed_by, request_id) "
    "VALUES (:item_id, CAST(:processed_at AS timestamptz), :processed_by, :request_id) "
    "ON CONFLICT (item_id) DO NOTHING"
)


def record(session_factory, report: dict) -> str:
    """'recorded', 'already' or 'gone' - the three things a report can meet."""
    with session_factory() as session:
        try:
            result = session.execute(RECORD_SQL, report)
            session.commit()
        except IntegrityError:
            session.rollback()
            return "gone"
        return "recorded" if result.rowcount == 1 else "already"


class Consumer(threading.Thread):
    def __init__(self, session_factory):
        super().__init__(name="results-consumer", daemon=True)
        self.session_factory = session_factory
        self.stop_event = threading.Event()

    def handle(self, message: dict) -> None:
        body = message.get("Body", "")
        message_id = message.get("MessageId", "")
        try:
            report = parse_item_processed(body)
        except Poison as exc:
            logger.error("poison report left for the dead-letter queue",
                         extra={"message_id": message_id, "reason": str(exc)})
            return
        try:
            outcome = record(self.session_factory, report)
        except OperationalError as exc:
            logger.warning("database refused the projection; message left for redelivery",
                           extra={"message_id": message_id, "item_id": report["item_id"],
                                  "error": str(exc)[:300]})
            time.sleep(1)
            return
        logger.info(outcome, extra={"item_id": report["item_id"], "request_id": report["request_id"] or "-",
                                    "message_id": message_id})
        sqs().delete_message(QueueUrl=RESULTS_QUEUE_URL, ReceiptHandle=message["ReceiptHandle"])

    def run(self) -> None:
        logger.info("results consumer up", extra={"queue": RESULTS_QUEUE_URL})
        while not self.stop_event.is_set():
            try:
                resp = sqs().receive_message(
                    QueueUrl=RESULTS_QUEUE_URL, MaxNumberOfMessages=BATCH,
                    WaitTimeSeconds=WAIT_SECONDS, AttributeNames=["ApproximateReceiveCount"],
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("receive failed; retrying", extra={"error": str(exc)[:300]})
                self.stop_event.wait(1)
                continue
            for message in resp.get("Messages", []):
                if self.stop_event.is_set():
                    break
                self.handle(message)
        logger.info("results consumer down")

    def stop(self) -> None:
        self.stop_event.set()

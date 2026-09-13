"""The worker's loop (Phase 42, ADR-0096; its own data since ADR-0098).

    receive up to 10 messages, waiting up to 20 s for the first
    for each: parse -> write the receipt (the worker's own table)
              -> publish item.processed to the results queue
              -> delete the message
    touch the heartbeat
    repeat until SIGTERM

THE MESSAGE IS THE OUTBOX. The receipt and the report are two writes to two
systems, and a worker that dies between them has a receipt and no report.
It does not need an outbox for that: the message is not deleted until the
report is sent, so the next delivery finds the receipt (first delivery wins)
and sends the report again, and the api records a report once. At-least-once
on both sides, idempotent on both sides.

THREE WAYS A MESSAGE IS NOT DELETED, and they are three different things:

  poison       handler.Poison. Will never succeed. Left for the redrive policy
               to move to the dead-letter queue after maxReceiveCount; the
               alarm on that queue is how anyone hears about it.
  transient    the database or SQS refused. Left, because the next delivery
               may succeed; the loop sleeps a second so a database that is
               down is asked once a second and not ten thousand times.
  stamped 0    NOT this list. rowcount 0 means the row was already processed
               or is gone; the message is deleted, because there is nothing
               a redelivery could do.

REFUSES TO START without a queue URL or a database URL. A worker with nothing
to consume or nowhere to write is not a degraded worker, it is a process that
exists to make `ecs describe-services` say ACTIVE.

THE HEARTBEAT FILE is the container's health: touched once per pass, and the
task definition's health check asks whether it moved in the last minute. A
loop that hangs inside `receive_message` for longer than that is what the
check is for; the 20-second long poll keeps a quiet queue well inside it.
"""
import logging
import os
import signal
import socket
import sys
import time
from pathlib import Path

import boto3
import psycopg2
from botocore.config import Config

from consumer.handler import (
    RECEIPT_READ_SQL,
    RECEIPT_SQL,
    Poison,
    item_processed_message,
    parse_item_created,
)
from consumer.logs import configure_logging

configure_logging()
log = logging.getLogger("worker")

QUEUE_URL = os.getenv("ITEMS_QUEUE_URL", "")
RESULTS_QUEUE_URL = os.getenv("RESULTS_QUEUE_URL", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
ENDPOINT_URL = os.getenv("SQS_ENDPOINT_URL") or None
REGION = os.getenv("AWS_REGION", "us-west-2")
HEARTBEAT = Path(os.getenv("HEARTBEAT_FILE", "/tmp/heartbeat"))
WAIT_SECONDS = 20
BATCH = 10

# Who stamped the row. The container's hostname - the task id's tail on
# Fargate, the container id locally - so two workers' work can be told apart.
WORKER_ID = os.getenv("WORKER_ID") or socket.gethostname()


def dsn(url: str) -> str:
    """The database URL arrives in SQLAlchemy's dialect form
    (`postgresql+psycopg2://…`) because that is what the secret holds for the
    api; psycopg2 wants the scheme without the driver."""
    return url.replace("postgresql+psycopg2://", "postgresql://", 1)


class Worker:
    def __init__(self) -> None:
        self.sqs = boto3.client(
            "sqs",
            region_name=REGION,
            endpoint_url=ENDPOINT_URL,
            config=Config(connect_timeout=5, read_timeout=WAIT_SECONDS + 5,
                          retries={"max_attempts": 2, "mode": "standard"}),
        )
        self.conn = None
        self.stop = False
        self.processed = 0
        self.skipped = 0
        self.poison = 0

    def db(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(dsn(DATABASE_URL), connect_timeout=5)
            self.conn.autocommit = True
        return self.conn

    def receipt(self, item_id: int, request_id: str) -> tuple[str, str, bool]:
        """(processed_at, processed_by, first) - the receipt for this item,
        written now or read back from an earlier delivery."""
        with self.db().cursor() as cur:
            cur.execute(RECEIPT_SQL, (item_id, WORKER_ID, request_id))
            row = cur.fetchone()
            if row is not None:
                return row[0].isoformat(), row[1], True
            cur.execute(RECEIPT_READ_SQL, (item_id,))
            row = cur.fetchone()
            return row[0].isoformat(), row[1], False

    def handle(self, message: dict) -> None:
        body = message.get("Body", "")
        message_id = message.get("MessageId", "")
        receipt = message["ReceiptHandle"]
        try:
            item_id, request_id = parse_item_created(body)
        except Poison as exc:
            self.poison += 1
            log.error("poison message left for the dead-letter queue",
                      extra={"message_id": message_id, "reason": str(exc),
                             "receive_count": _receive_count(message)})
            return
        try:
            processed_at, processed_by, first = self.receipt(item_id, request_id)
        except psycopg2.Error as exc:
            log.warning("database refused the receipt; message left for redelivery",
                        extra={"message_id": message_id, "item_id": item_id,
                               "request_id": request_id, "error": str(exc)[:300]})
            self.conn = None
            time.sleep(1)
            return
        # The report, BEFORE the delete: a report that could not be sent
        # leaves the message, and the next delivery sends it from the same
        # receipt (see the header).
        try:
            self.sqs.send_message(
                QueueUrl=RESULTS_QUEUE_URL,
                MessageBody=item_processed_message(item_id, processed_at, processed_by, request_id),
                MessageAttributes={"type": {"DataType": "String", "StringValue": "item.processed"}},
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("the report could not be sent; message left for redelivery",
                        extra={"message_id": message_id, "item_id": item_id,
                               "request_id": request_id, "error": str(exc)[:300]})
            time.sleep(1)
            return
        if first:
            self.processed += 1
            log.info("processed", extra={"item_id": item_id, "request_id": request_id,
                                          "message_id": message_id})
        else:
            self.skipped += 1
            log.info("reported again from an earlier receipt",
                     extra={"item_id": item_id, "request_id": request_id,
                            "message_id": message_id,
                            "receive_count": _receive_count(message)})
        self.sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt)

    def run(self) -> int:
        log.info("worker up", extra={"queue": QUEUE_URL, "results": RESULTS_QUEUE_URL,
                                     "worker_id": WORKER_ID, "endpoint": ENDPOINT_URL or "aws"})
        while not self.stop:
            try:
                resp = self.sqs.receive_message(
                    QueueUrl=QUEUE_URL,
                    MaxNumberOfMessages=BATCH,
                    WaitTimeSeconds=WAIT_SECONDS,
                    AttributeNames=["ApproximateReceiveCount"],
                    MessageAttributeNames=["All"],
                )
            except Exception as exc:  # noqa: BLE001 - the queue is the one dependency
                log.warning("receive failed; retrying",
                            extra={"error": str(exc)[:300]})
                HEARTBEAT.touch()
                time.sleep(1)
                continue
            for message in resp.get("Messages", []):
                if self.stop:
                    break
                self.handle(message)
            HEARTBEAT.touch()
        log.info("worker down", extra={"processed": self.processed,
                                       "skipped": self.skipped, "poison": self.poison})
        return 0


def _receive_count(message: dict) -> int:
    try:
        return int(message.get("Attributes", {}).get("ApproximateReceiveCount", 0))
    except (TypeError, ValueError):
        return 0


def main() -> int:
    missing = [name for name, value in (("ITEMS_QUEUE_URL", QUEUE_URL),
                                        ("RESULTS_QUEUE_URL", RESULTS_QUEUE_URL),
                                        ("DATABASE_URL", DATABASE_URL)) if not value]
    if missing:
        log.error("refusing to start", extra={"missing": missing})
        return 2
    worker = Worker()

    def _stop(signum, _frame):
        log.info("signal received; finishing the batch", extra={"signal": signum})
        worker.stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    HEARTBEAT.touch()
    return worker.run()


if __name__ == "__main__":
    sys.exit(main())

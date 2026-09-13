"""The worker's loop (Phase 42, ADR-0096).

    receive up to 10 messages, waiting up to 20 s for the first
    for each: parse -> stamp the row -> delete the message
    touch the heartbeat
    repeat until SIGTERM

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

from consumer.handler import STAMP_SQL, Poison, parse_item_created
from consumer.logs import configure_logging

configure_logging()
log = logging.getLogger("worker")

QUEUE_URL = os.getenv("ITEMS_QUEUE_URL", "")
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

    def stamp(self, item_id: int) -> int:
        with self.db().cursor() as cur:
            cur.execute(STAMP_SQL, (WORKER_ID, item_id))
            return cur.rowcount

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
            rows = self.stamp(item_id)
        except psycopg2.Error as exc:
            log.warning("database refused the stamp; message left for redelivery",
                        extra={"message_id": message_id, "item_id": item_id,
                               "request_id": request_id, "error": str(exc)[:300]})
            self.conn = None
            time.sleep(1)
            return
        if rows == 1:
            self.processed += 1
            log.info("processed", extra={"item_id": item_id, "request_id": request_id,
                                          "message_id": message_id})
        else:
            self.skipped += 1
            log.info("skipped: already processed or gone",
                     extra={"item_id": item_id, "request_id": request_id,
                            "message_id": message_id,
                            "receive_count": _receive_count(message)})
        self.sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt)

    def run(self) -> int:
        log.info("worker up", extra={"queue": QUEUE_URL, "worker_id": WORKER_ID,
                                     "endpoint": ENDPOINT_URL or "aws"})
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

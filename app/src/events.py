"""The api's half of the queues (ADR-0096, ADR-0098): what it says and how.

THE OUTBOX CLOSES THE GAP ADR-0096 D2 NAMED. `item.created` is no longer sent
after the commit; it is WRITTEN in the same transaction as the row it is
about, into `outbox`, and the relay in src/outbox.py sends it afterwards. A
process that dies between the row and the send leaves a row with an
unpublished event, and the relay sends it when it comes back. What was a
gap is a delay.

The message SHAPE lives in contracts/item.created.v1.json; the builder here
is held to it by tests/unit/test_contracts.py, and the worker's parser is
held to the same file from the other side.

BOUNDED, so a dead queue costs the relay three seconds per message and not
sixty: two seconds to connect, three to read, one retry. The client is built
once per process and only when there is a queue to build it for.
"""
import json
import logging
import os
import threading
from typing import Optional

logger = logging.getLogger("app.events")

# Where item.created goes, and where item.processed comes back from
# (src/results.py). Unset means "no queue here", which the relay and the
# consumer log once and then do not start: an api that quietly publishes
# nothing is the vacuous green this project keeps finding, and the contract
# suite fails on it either way.
ITEMS_QUEUE_URL = os.getenv("ITEMS_QUEUE_URL", "")
RESULTS_QUEUE_URL = os.getenv("RESULTS_QUEUE_URL", "")
# ElasticMQ locally, nothing in AWS (docker-compose.yml).
ENDPOINT_URL = os.getenv("SQS_ENDPOINT_URL") or None
REGION = os.getenv("AWS_REGION", "us-west-2")

EVENT_TYPE = "item.created"
EVENT_VERSION = 1

_client = None
_lock = threading.Lock()


def sqs():
    """One client per process, built on first use so importing this module
    needs neither boto3's network setup nor credentials - the unit suite
    imports the application without either."""
    global _client
    with _lock:
        if _client is None:
            import boto3
            from botocore.config import Config

            _client = boto3.client(
                "sqs",
                region_name=REGION,
                endpoint_url=ENDPOINT_URL,
                config=Config(
                    connect_timeout=2,
                    read_timeout=25,
                    retries={"max_attempts": 2, "mode": "standard"},
                ),
            )
        return _client


def item_created_event(item_id: int, name: str, created_at: str,
                       request_id: Optional[str]) -> dict:
    """The event as a dict - what goes into the outbox row's payload."""
    return {
        "type": EVENT_TYPE,
        "version": EVENT_VERSION,
        "item": {"id": item_id, "name": name, "created_at": created_at},
        "request_id": request_id or "-",
    }


def item_created_message(item_id: int, name: str, created_at: str,
                         request_id: Optional[str]) -> str:
    """The same event as the body the queue carries."""
    return json.dumps(item_created_event(item_id, name, created_at, request_id),
                      separators=(",", ":"))


def send(queue_url: str, body: str, event_type: str) -> str:
    """One SendMessage. Raises on failure; the caller decides what a failure
    means (the relay leaves the row for the next pass)."""
    resp = sqs().send_message(
        QueueUrl=queue_url,
        MessageBody=body,
        MessageAttributes={"type": {"DataType": "String", "StringValue": event_type}},
    )
    return resp.get("MessageId", "")

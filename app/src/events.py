"""The api's half of the queue (Phase 42): publish `item.created` to SQS.

DIRECT PUBLISH AFTER COMMIT, AND THE GAP IS NAMED. The row is committed first
and the event is sent second, which is two writes to two systems with no
transaction across them. A process that dies between the two, or a queue that
refuses the send, leaves an item that exists and an event that was never sent
- the item then stays with `processed_at IS NULL` for ever, and the contract
suite's wait for it is what makes that visible. The transactional outbox that
closes this gap is plan item 4's, where the worker stops writing into this
table and the relay has a reason to exist; taking it now would be a second
process for a gap this project can currently see and measure.

WHAT A FAILED SEND DOES TO THE REQUEST: nothing. The item was created, and
201 is the truth about that; a 5xx would tell the client the create failed
when it did not, and a retry would meet a 409. The failure is logged with the
item id at error level, and the queue's own metrics are where it shows.

BOUNDED, so a dead queue costs a request three seconds and not sixty: two
seconds to connect, three to read, one retry. The client is built once per
process and only when there is a queue to build it for.
"""
import json
import logging
import os
import threading
from typing import Optional

logger = logging.getLogger("app.events")

# The queue URL is the whole configuration. Unset means "no queue here", which
# is logged once at warning level rather than silently: an api that quietly
# publishes nothing is the vacuous green this project keeps finding, and the
# contract suite fails on it either way.
QUEUE_URL = os.getenv("ITEMS_QUEUE_URL", "")
# ElasticMQ locally, nothing in AWS (docker-compose.yml, ADR-0096).
ENDPOINT_URL = os.getenv("SQS_ENDPOINT_URL") or None
REGION = os.getenv("AWS_REGION", "us-west-2")

EVENT_TYPE = "item.created"
EVENT_VERSION = 1

_client = None
_lock = threading.Lock()
_warned = False


def _sqs():
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
                    read_timeout=3,
                    retries={"max_attempts": 2, "mode": "standard"},
                ),
            )
        return _client


def item_created_message(item_id: int, name: str, created_at: str,
                         request_id: Optional[str]) -> str:
    """The body, as one function so the worker's parser and this agree on a
    shape the unit suite can hold in one place."""
    return json.dumps(
        {
            "type": EVENT_TYPE,
            "version": EVENT_VERSION,
            "item": {"id": item_id, "name": name, "created_at": created_at},
            "request_id": request_id or "-",
        },
        separators=(",", ":"),
    )


def publish_item_created(item_id: int, name: str, created_at: str,
                         request_id: Optional[str] = None) -> bool:
    """Send `item.created`. True when SQS accepted it, False when it did not
    or there is no queue - the caller's response does not depend on it."""
    global _warned
    if not QUEUE_URL:
        if not _warned:
            _warned = True
            logger.warning(
                "no ITEMS_QUEUE_URL: item.created events are not published",
                extra={"event": EVENT_TYPE},
            )
        return False
    body = item_created_message(item_id, name, created_at, request_id)
    try:
        resp = _sqs().send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=body,
            MessageAttributes={
                "type": {"DataType": "String", "StringValue": EVENT_TYPE},
            },
        )
    except Exception as exc:  # noqa: BLE001 - every failure is the same failure here
        logger.error(
            "item.created was not published; the item exists and will not be processed",
            extra={"event": EVENT_TYPE, "item_id": item_id, "error": str(exc)[:300]},
        )
        return False
    logger.info(
        "published",
        extra={"event": EVENT_TYPE, "item_id": item_id, "message_id": resp.get("MessageId", "")},
    )
    return True

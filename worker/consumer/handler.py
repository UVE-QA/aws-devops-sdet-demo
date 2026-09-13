"""What one message means, decided without a network (Phase 42).

Two outcomes and no third: the message names an item, or it is POISON - a body
this worker will never be able to act on, however many times it is delivered.
The distinction matters because they are handled oppositely: an item is
processed and the message deleted; poison is logged and LEFT, so the queue's
redrive policy carries it to the dead-letter queue after `maxReceiveCount`
receipts, where the alarm is. Deleting poison would make the dead-letter queue
a thing that can never fill, and an alarm on it a thing that can never fire.

Transient failures - the database is away, SQS hiccuped - are neither: the
message is left too, but because the NEXT delivery may succeed. main.py tells
those apart from this module's Poison by what raised.

Kept free of boto3 and psycopg2 so the unit suite can hold every branch.
"""
import json

EVENT_TYPE = "item.created"
EVENT_VERSION = 1


class Poison(ValueError):
    """A message that cannot be processed by this or any later delivery."""


def parse_item_created(body: str) -> tuple[int, str]:
    """Return (item_id, request_id) from a message body, or raise Poison.

    Strict on every field it reads and indifferent to the rest: a producer
    that adds a field must not break a consumer that does not need it, and a
    producer that changes the meaning of one must bump `version`.
    """
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
    # bool is an int in Python; `true` is not an item id.
    if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id <= 0:
        raise Poison(f"item.id is {item_id!r}, not a positive integer")
    request_id = event.get("request_id")
    return item_id, request_id if isinstance(request_id, str) and request_id else "-"


# THE ONE STATEMENT THE WORKER MAKES, and it is idempotent by construction: a
# second delivery of the same event finds processed_at already set and updates
# nothing. `rowcount` 0 also covers an item deleted before its event arrived,
# which is not an error either - there is nothing left to process.
STAMP_SQL = (
    "UPDATE demo_items SET processed_at = now(), processed_by = %s "
    "WHERE id = %s AND processed_at IS NULL"
)

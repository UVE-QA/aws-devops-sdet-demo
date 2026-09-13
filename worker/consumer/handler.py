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
The shape of what this parses is contracts/item.created.v1.json; the shape of
what it builds is contracts/item.processed.v1.json (ADR-0098).
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


# THE ONE STATEMENT THE WORKER MAKES, into its OWN table (ADR-0098): a
# receipt per item, in the worker's schema, first delivery wins. A second
# delivery of the same event conflicts and inserts nothing - `RETURNING`
# then yields no row, and the receipt already there is read back so the
# report the worker publishes carries the ORIGINAL time and name, not the
# redelivery's. No foreign key to the api's table: the item's existence is
# the api's fact, and a receipt for an item the api has since deleted is a
# true statement about what this worker did.
RECEIPT_SQL = (
    "INSERT INTO worker.receipts (item_id, processed_by, request_id) "
    "VALUES (%s, %s, %s) ON CONFLICT (item_id) DO NOTHING "
    "RETURNING processed_at, processed_by"
)
RECEIPT_READ_SQL = "SELECT processed_at, processed_by FROM worker.receipts WHERE item_id = %s"

PROCESSED_TYPE = "item.processed"
PROCESSED_VERSION = 1


def item_processed_message(item_id: int, processed_at: str, processed_by: str,
                           request_id: str) -> str:
    """The report the worker publishes, shaped by contracts/item.processed.v1.json
    and held to it by tests/unit/test_contracts.py."""
    return json.dumps(
        {
            "type": PROCESSED_TYPE,
            "version": PROCESSED_VERSION,
            "item": {"id": item_id},
            "processed_at": processed_at,
            "processed_by": processed_by,
            "request_id": request_id or "-",
        },
        separators=(",", ":"),
    )

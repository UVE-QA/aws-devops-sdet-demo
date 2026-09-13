"""The worker's parser, every branch (Phase 42).

Poison and not-poison are handled oppositely by the loop - one is deleted
after the row is stamped, the other is left for the redrive policy - so the
line between them is the thing to hold still. The api's own message builder
is run through the parser too, so the two ends of the contract cannot drift
without a test noticing.
"""
import json

import pytest

from consumer.handler import EVENT_TYPE, EVENT_VERSION, Poison, parse_item_created
from src.events import item_created_message


def test_the_api_message_parses_to_its_item_and_request_id():
    body = item_created_message(42, "contract-abc", "2026-09-13T02:00:00+00:00", "req-1")
    assert parse_item_created(body) == (42, "req-1")


def test_a_missing_request_id_reads_as_dash():
    body = item_created_message(7, "x", "2026-09-13T02:00:00+00:00", None)
    assert parse_item_created(body) == (7, "-")


def test_extra_fields_are_ignored_not_refused():
    event = json.loads(item_created_message(3, "x", "t", "r"))
    event["item"]["colour"] = "blue"
    event["producer"] = "future api"
    assert parse_item_created(json.dumps(event)) == (3, "r")


@pytest.mark.parametrize(
    "body, reason",
    [
        ("this is not an event", "not JSON"),
        ("[1, 2, 3]", "not a JSON object"),
        (json.dumps({"type": "item.deleted", "version": 1, "item": {"id": 1}}), "type"),
        (json.dumps({"type": EVENT_TYPE, "version": 2, "item": {"id": 1}}), "version"),
        (json.dumps({"type": EVENT_TYPE, "version": EVENT_VERSION}), "no item"),
        (json.dumps({"type": EVENT_TYPE, "version": EVENT_VERSION, "item": {"id": "1"}}), "positive integer"),
        (json.dumps({"type": EVENT_TYPE, "version": EVENT_VERSION, "item": {"id": 0}}), "positive integer"),
        (json.dumps({"type": EVENT_TYPE, "version": EVENT_VERSION, "item": {"id": True}}), "positive integer"),
    ],
)
def test_what_is_poison_says_why(body, reason):
    with pytest.raises(Poison) as caught:
        parse_item_created(body)
    assert reason in str(caught.value)

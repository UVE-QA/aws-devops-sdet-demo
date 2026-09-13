"""The asynchronous half of the contract (Phase 42, ADR-0096).

A created item is processed by a worker the client never sees, through a
queue the client never sees. What the client CAN see is `processed_at` and
`processed_by` turning from null into values, some time after the 201. So
this suite waits for that - polling with a deadline, never a fixed sleep -
and the deadline is the contract: an item still unprocessed after it is a
failure, whether the cause is a worker that is down, a queue nobody
configured, or the publish that src/events.py says can be lost.

Against stage in a cycle this is also the one test that proves the queue
and the worker exist at all; every other suite would pass without them.
"""
import os
import time
from datetime import datetime

import httpx
import pytest

# Generous against a cold Fargate task, tight enough that a missing worker
# is a failure and not a coffee break. Override for a slow environment.
PROCESSING_DEADLINE = float(os.getenv("API_PROCESSING_DEADLINE", "30"))
POLL_INTERVAL = 0.5


def _wait_processed(client: httpx.Client, item_id: int) -> dict:
    deadline = time.monotonic() + PROCESSING_DEADLINE
    last = None
    while time.monotonic() < deadline:
        r = client.get(f"/api/items/{item_id}")
        assert r.status_code == 200, r.text
        last = r.json()
        if last["processed_at"] is not None:
            return last
        time.sleep(POLL_INTERVAL)
    pytest.fail(
        f"item {item_id} was not processed within {PROCESSING_DEADLINE}s: "
        f"processed_at={last and last['processed_at']!r} - the worker, the queue "
        "or the publish is missing"
    )


def test_a_created_item_starts_unprocessed_and_is_processed_later(
    client, unique_name, created_items
):
    r = client.post("/api/items", json={"name": unique_name})
    assert r.status_code == 201, r.text
    body = r.json()
    created_items.append(body["id"])
    # At creation both are null: the api never fills them. (The worker may
    # already have run by the time this line executes, so only the shape of
    # the 201 is asserted, not the null.)
    assert "processed_at" in body and "processed_by" in body

    processed = _wait_processed(client, body["id"])
    assert processed["processed_by"], "processed_by names the worker that did it"
    assert datetime.fromisoformat(processed["processed_at"]) >= datetime.fromisoformat(
        body["created_at"]
    )


def test_processing_happens_once_and_a_later_edit_does_not_move_it(
    client, unique_name, created_items
):
    r = client.post("/api/items", json={"name": unique_name})
    assert r.status_code == 201, r.text
    item_id = r.json()["id"]
    created_items.append(item_id)
    first = _wait_processed(client, item_id)

    # A PATCH publishes nothing and the worker touches nothing it has stamped:
    # the stamp is a fact about the create, not about the row's latest state.
    r = client.patch(f"/api/items/{item_id}", json={"description": "edited after processing"})
    assert r.status_code == 200, r.text
    after = r.json()
    assert after["processed_at"] == first["processed_at"]
    assert after["processed_by"] == first["processed_by"]
    assert after["updated_at"] != first["updated_at"]

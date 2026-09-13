"""The relay's batch, every branch (ADR-0098).

`relay_batch` is a function over rows and a `send` callable, so the branches
that only a failing queue can reach are reached here: a send that fails
leaves the row unpublished with the attempt counted; a send that succeeds
marks it; a batch with both does both and reports both. The at-least-once
consequence - a row sent and not marked is sent again - is asserted rather
than tolerated, because the worker's receipt is written against it.
"""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.outbox import relay_batch

NOW = datetime(2026, 9, 13, 2, 0, 0, tzinfo=timezone.utc)


def row(i, event_type="item.created"):
    return SimpleNamespace(id=i, event_type=event_type,
                           payload={"type": event_type, "version": 1, "item": {"id": i}, "request_id": "-"},
                           published_at=None, attempts=0)


def test_a_sent_row_is_marked_and_the_body_is_the_payload():
    sent = []
    def send(queue, body, event_type):
        sent.append((queue, body, event_type)); return "m-1"
    r = row(1)
    counts = relay_batch([r], send, "https://q", now=lambda: NOW)
    assert counts == {"sent": 1, "failed": 0}
    assert r.published_at == NOW and r.attempts == 1
    assert sent == [("https://q", '{"type":"item.created","version":1,"item":{"id":1},"request_id":"-"}', "item.created")]


def test_a_failed_send_leaves_the_row_and_counts_the_attempt():
    def send(queue, body, event_type):
        raise RuntimeError("queue away")
    r = row(2)
    counts = relay_batch([r], send, "https://q", now=lambda: NOW)
    assert counts == {"sent": 0, "failed": 1}
    assert r.published_at is None and r.attempts == 1


def test_one_failure_does_not_stop_the_batch():
    def send(queue, body, event_type):
        if '"id":3' in body:
            raise RuntimeError("just this one")
        return "m"
    rows = [row(1), row(3), row(4)]
    counts = relay_batch(rows, send, "https://q", now=lambda: NOW)
    assert counts == {"sent": 2, "failed": 1}
    assert [r.published_at is not None for r in rows] == [True, False, True]


def test_an_unmarked_row_is_sent_again_on_the_next_pass():
    """At-least-once, asserted: the row a dead process sent and never marked
    goes again, and the consumer's receipt is what makes that harmless."""
    seen = []
    def send(queue, body, event_type):
        seen.append(body); return "m"
    r = row(5)
    relay_batch([r], send, "https://q", now=lambda: NOW)
    r.published_at = None  # the mark that never happened
    relay_batch([r], send, "https://q", now=lambda: NOW)
    assert len(seen) == 2 and seen[0] == seen[1]
    assert r.attempts == 2

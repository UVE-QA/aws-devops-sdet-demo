"""The two ends of each queue, held to one file (ADR-0098).

The api and the worker share no code. What they share is contracts/*.json,
and this is where both are held to it: every builder's output validates
against its schema, every parser accepts the schema's own examples and
refuses its counter-examples as poison. A producer that changes a meaning
breaks here, in process, in a second - not on the stand, as an item that is
never processed.
"""
import json
import pathlib

import jsonschema
import pytest

from consumer.handler import Poison as WorkerPoison
from consumer.handler import item_processed_message, parse_item_created
from src.events import item_created_message
from src.results import Poison as ApiPoison
from src.results import parse_item_processed

CONTRACTS = pathlib.Path(__file__).resolve().parents[2] / "contracts"


def schema(name: str) -> dict:
    return json.loads((CONTRACTS / f"{name}.v1.json").read_text(encoding="utf-8"))


def validator(name: str) -> jsonschema.Draft202012Validator:
    s = schema(name)
    jsonschema.Draft202012Validator.check_schema(s)
    return jsonschema.Draft202012Validator(s)


# ------------------------------------------------------------ item.created
def test_the_api_builds_item_created_to_its_contract():
    body = item_created_message(42, "contract-abc", "2026-09-13T02:00:00+00:00", "req-1")
    validator("item.created").validate(json.loads(body))


def test_the_worker_accepts_every_example_of_item_created():
    for example in schema("item.created")["examples"]:
        item_id, request_id = parse_item_created(json.dumps(example))
        assert item_id == example["item"]["id"]
        assert request_id == example["request_id"]


def test_the_worker_refuses_every_counterexample_of_item_created_as_poison():
    for counter in schema("item.created")["counterexamples"]:
        body = counter["body"] if isinstance(counter["body"], str) else json.dumps(counter["body"])
        with pytest.raises(WorkerPoison):
            parse_item_created(body)


def test_every_counterexample_is_also_invalid_by_the_schema():
    """The counter-examples are the schema's, not just the parser's: a body
    the schema would accept and the parser refuses is a parser too strict,
    and this is where that would show."""
    for name in ("item.created", "item.processed"):
        v = validator(name)
        for counter in schema(name)["counterexamples"]:
            if isinstance(counter["body"], str):
                continue  # not JSON at all; no schema question to ask
            assert not v.is_valid(counter["body"]), f"{name}: {counter['why']}"


# ---------------------------------------------------------- item.processed
def test_the_worker_builds_item_processed_to_its_contract():
    body = item_processed_message(42, "2026-09-13T02:00:03+00:00", "50cf1b372490", "req-1")
    validator("item.processed").validate(json.loads(body))


def test_the_api_accepts_every_example_of_item_processed():
    for example in schema("item.processed")["examples"]:
        report = parse_item_processed(json.dumps(example))
        assert report["item_id"] == example["item"]["id"]
        assert report["processed_by"] == example["processed_by"]


def test_the_api_refuses_every_counterexample_of_item_processed_as_poison():
    for counter in schema("item.processed")["counterexamples"]:
        body = counter["body"] if isinstance(counter["body"], str) else json.dumps(counter["body"])
        with pytest.raises(ApiPoison):
            parse_item_processed(body)


def test_the_round_trip_from_one_end_to_the_other_and_back():
    """What the api says, the worker hears; what the worker says back, the api
    hears - with the ids intact."""
    created = item_created_message(9, "round-trip", "2026-09-13T02:00:00+00:00", "req-9")
    item_id, request_id = parse_item_created(created)
    processed = item_processed_message(item_id, "2026-09-13T02:00:02+00:00", "worker-1", request_id)
    report = parse_item_processed(processed)
    assert report["item_id"] == 9 and report["request_id"] == "req-9"

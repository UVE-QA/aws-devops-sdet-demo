"""Contract tests for the items slice.

Positive AND negative. The negatives are the point: a suite that only asserts
the happy path cannot tell a working validator from an absent one, and this
project's recurring failure mode is precisely something that was never
exercised on the path that would expose it.
"""
import httpx
import pytest


# --- create ---------------------------------------------------------------


def test_create_returns_201_and_echoes_the_payload(client, unique_name, created_items):
    res = client.post(
        "/api/items", json={"name": unique_name, "description": "created by pytest"}
    )
    assert res.status_code == 201, res.text
    body = res.json()
    created_items.append(body["id"])

    assert isinstance(body["id"], int)
    assert body["name"] == unique_name
    assert body["description"] == "created by pytest"
    assert body["created_at"]  # server-assigned, present and non-empty


def test_description_is_optional_and_comes_back_null(
    client, unique_name, created_items
):
    res = client.post("/api/items", json={"name": unique_name})
    assert res.status_code == 201, res.text
    body = res.json()
    created_items.append(body["id"])
    assert body["description"] is None


def test_name_is_trimmed(client, unique_name, created_items):
    res = client.post("/api/items", json={"name": f"  {unique_name}  "})
    assert res.status_code == 201, res.text
    body = res.json()
    created_items.append(body["id"])
    assert body["name"] == unique_name


def test_duplicate_name_returns_409(client, unique_name, created_items):
    first = client.post("/api/items", json={"name": unique_name})
    assert first.status_code == 201, first.text
    created_items.append(first.json()["id"])

    second = client.post("/api/items", json={"name": unique_name})
    assert second.status_code == 409, second.text


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="name-missing"),
        pytest.param({"name": ""}, id="name-empty"),
        pytest.param({"name": "   "}, id="name-whitespace-only"),
        pytest.param({"name": "x" * 201}, id="name-too-long"),
        pytest.param({"name": None}, id="name-null"),
        pytest.param({"name": 42}, id="name-not-a-string"),
        pytest.param({"name": "ok", "nope": "unknown field"}, id="unknown-field"),
        pytest.param(
            {"name": "ok", "description": "d" * 2001}, id="description-too-long"
        ),
    ],
)
def test_invalid_payloads_return_422(client, payload):
    res = client.post("/api/items", json=payload)
    assert res.status_code == 422, f"{payload} -> {res.status_code} {res.text}"


# --- list -----------------------------------------------------------------


def test_list_is_an_envelope_whose_count_matches_its_items(client):
    res = client.get("/api/items")
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body) == {"items", "count"}
    assert isinstance(body["items"], list)
    assert body["count"] == len(body["items"])


def test_a_created_item_appears_in_the_list(client, unique_name, created_items):
    created = client.post("/api/items", json={"name": unique_name})
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    created_items.append(item_id)

    body = client.get("/api/items").json()
    assert unique_name in [item["name"] for item in body["items"]]


def test_the_list_is_ordered_by_id(client):
    body = client.get("/api/items").json()
    ids = [item["id"] for item in body["items"]]
    assert ids == sorted(ids)


# --- delete ---------------------------------------------------------------


def test_delete_returns_204_and_the_item_disappears(client, unique_name):
    created = client.post("/api/items", json={"name": unique_name})
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    deleted = client.delete(f"/api/items/{item_id}")
    assert deleted.status_code == 204, deleted.text
    assert deleted.content == b""

    remaining = client.get("/api/items").json()["items"]
    assert item_id not in [item["id"] for item in remaining]


def test_delete_frees_the_name_for_reuse(client, unique_name, created_items):
    """Uniqueness is a live constraint, not a tombstone."""
    first = client.post("/api/items", json={"name": unique_name})
    assert first.status_code == 201, first.text
    assert client.delete(f"/api/items/{first.json()['id']}").status_code == 204

    second = client.post("/api/items", json={"name": unique_name})
    assert second.status_code == 201, second.text
    created_items.append(second.json()["id"])


def test_delete_unknown_id_returns_404(client):
    res = client.delete("/api/items/999999999")
    assert res.status_code == 404, res.text


def test_delete_non_numeric_id_returns_422(client):
    res = client.delete("/api/items/not-a-number")
    assert res.status_code == 422, res.text

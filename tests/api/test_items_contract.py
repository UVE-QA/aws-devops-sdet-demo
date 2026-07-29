"""Contract tests for the items slice.

Positive AND negative. The negatives are the point: a suite that only asserts
the happy path cannot tell a working validator from an absent one, and this
project's recurring failure mode is precisely something that was never
exercised on the path that would expose it.

Phase 16a added GET by id, PATCH and pagination (ADR-0031). Pagination is why
`walk_pages` exists: the Phase 10 tests fetched /api/items and expected to see
what they had just created, which stops being true the moment the database
holds more rows than one page. The fix belongs in the tests, not in a larger
default — a suite that only works on a small database is a suite that stops
working on the day the data becomes interesting.
"""
from datetime import datetime

import pytest

MAX_LIMIT = 100


def walk_pages(client):
    """Every item, page by page — and it must be EVERY item.

    Stops on a page that returns nothing, so a server that reports a `total`
    it will not serve cannot spin this forever.

    The length check is the point, and it was added because its absence let a
    deliberate off-by-one pass the whole suite. With `.offset(offset + 1)` in
    the query, every page is internally consistent and every test that looks
    for a row it created still passes — because the rows a test creates are
    the NEWEST, and the row that silently disappears is the FIRST. Comparing
    what the walk collected against what the API says exists is what notices a
    row nobody was looking for.

    It assumes no concurrent writer, which holds: the suites run in sequence,
    and this one only adds rows.
    """
    items = []
    offset = 0
    total = None
    while True:
        body = client.get(f"/api/items?limit={MAX_LIMIT}&offset={offset}").json()
        total = body["total"]
        items.extend(body["items"])
        if body["count"] == 0 or offset + body["count"] >= total:
            break
        offset += body["count"]
    assert len(items) == total, (
        f"walking every page collected {len(items)} rows, but the API reports "
        f"{total} exist. LIMIT/OFFSET is skipping or repeating rows."
    )
    return items


def create(client, name, **fields):
    res = client.post("/api/items", json={"name": name, **fields})
    assert res.status_code == 201, res.text
    return res.json()


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
    assert body["updated_at"]


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


# --- read one -------------------------------------------------------------


def test_get_by_id_returns_the_item(client, unique_name, created_items):
    created = create(client, unique_name, description="fetched by id")
    created_items.append(created["id"])

    res = client.get(f"/api/items/{created['id']}")
    assert res.status_code == 200, res.text
    assert res.json() == created


def test_get_unknown_id_returns_404(client):
    assert client.get("/api/items/999999999").status_code == 404


def test_get_non_numeric_id_returns_422(client):
    """Malformed, not absent. The distinction is the test."""
    assert client.get("/api/items/not-a-number").status_code == 422


# --- list and pagination --------------------------------------------------


def test_list_is_an_envelope_with_the_pagination_fields(client):
    res = client.get("/api/items")
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body) == {"items", "count", "total", "limit", "offset"}
    assert isinstance(body["items"], list)
    assert body["count"] == len(body["items"])
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["total"] >= body["count"]


def test_count_never_exceeds_the_limit_and_total_never_falls_below_count(client):
    body = client.get("/api/items?limit=3").json()
    assert body["limit"] == 3
    assert body["count"] <= 3
    assert body["total"] >= body["count"]


def test_a_created_item_is_reachable_by_paging(client, unique_name, created_items):
    created = create(client, unique_name)
    created_items.append(created["id"])
    assert unique_name in [item["name"] for item in walk_pages(client)]


def test_pages_neither_lose_nor_repeat_rows(client, unique_name, created_items):
    """Walked one row at a time, the pages must reconstruct the whole list.

    An off-by-one in LIMIT/OFFSET shows up here and nowhere else: it still
    returns plausible pages, each internally consistent.
    """
    for suffix in ("a", "b", "c"):
        created_items.append(create(client, f"{unique_name}-{suffix}")["id"])

    total = client.get("/api/items?limit=1").json()["total"]
    seen = []
    offset = 0
    while offset < total:
        page = client.get(f"/api/items?limit=1&offset={offset}").json()
        if page["count"] == 0:
            break
        seen.extend(item["id"] for item in page["items"])
        offset += 1

    assert len(seen) == len(set(seen)), "a row was served on two pages"
    # Counted against the total, not against this test's own rows. Asserting
    # only on rows the test created cannot see a row being dropped from the
    # START of the list, which is exactly what an off-by-one does.
    assert len(seen) == total, (
        f"one row per page reached {len(seen)} of {total} rows"
    )
    mine = [i for i in seen if i in created_items]
    assert len(mine) == 3, "paging one row at a time did not reach every row"


def test_the_list_is_ordered_by_id_within_a_page(client):
    ids = [item["id"] for item in client.get("/api/items").json()["items"]]
    assert ids == sorted(ids)


def test_the_order_holds_across_a_page_boundary(client):
    """Ordering that only holds inside a page is not an ordering."""
    ids = [item["id"] for item in walk_pages(client)]
    assert ids == sorted(ids)


def test_an_offset_past_the_end_is_an_empty_page_not_an_error(client):
    body = client.get("/api/items?offset=100000").json()
    assert body["count"] == 0
    assert body["items"] == []
    assert body["total"] >= 0


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("limit=0", id="limit-below-minimum"),
        pytest.param("limit=101", id="limit-above-maximum"),
        pytest.param("limit=-1", id="limit-negative"),
        pytest.param("limit=many", id="limit-not-a-number"),
        pytest.param("offset=-1", id="offset-negative"),
        pytest.param("offset=half", id="offset-not-a-number"),
    ],
)
def test_invalid_pagination_returns_422(client, query):
    res = client.get(f"/api/items?{query}")
    assert res.status_code == 422, f"{query} -> {res.status_code} {res.text}"


# --- update ---------------------------------------------------------------


def test_patch_changes_only_the_field_that_was_sent(client, unique_name, created_items):
    created = create(client, unique_name, description="before")
    created_items.append(created["id"])

    res = client.patch(f"/api/items/{created['id']}", json={"description": "after"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["description"] == "after"
    assert body["name"] == unique_name, "a description patch must not touch the name"
    assert body["id"] == created["id"]


def test_patch_can_rename_without_clearing_the_description(
    client, unique_name, created_items
):
    created = create(client, unique_name, description="kept")
    created_items.append(created["id"])

    res = client.patch(f"/api/items/{created['id']}", json={"name": f"{unique_name}-new"})
    assert res.status_code == 200, res.text
    assert res.json()["name"] == f"{unique_name}-new"
    assert res.json()["description"] == "kept"


def test_an_explicit_null_clears_the_description(client, unique_name, created_items):
    """Absent and null are different requests, and this is the pair that proves it."""
    created = create(client, unique_name, description="to be cleared")
    created_items.append(created["id"])

    untouched = client.patch(f"/api/items/{created['id']}", json={"name": unique_name})
    assert untouched.json()["description"] == "to be cleared"

    cleared = client.patch(f"/api/items/{created['id']}", json={"description": None})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["description"] is None


def test_patch_trims_the_name(client, unique_name, created_items):
    created = create(client, unique_name)
    created_items.append(created["id"])

    res = client.patch(
        f"/api/items/{created['id']}", json={"name": f"  {unique_name}-trimmed  "}
    )
    assert res.status_code == 200, res.text
    assert res.json()["name"] == f"{unique_name}-trimmed"


def test_patch_moves_updated_at_and_leaves_created_at_alone(
    client, unique_name, created_items
):
    """The column that makes a database assertion after a UI edit mean something.

    PostgreSQL's now() is transaction start time with microsecond resolution,
    so two separate statements cannot collide on one value. (SQLite's
    CURRENT_TIMESTAMP has one-second resolution and CAN, which is worth knowing
    before someone points this suite at one.)
    """
    created = create(client, unique_name)
    created_items.append(created["id"])
    assert created["created_at"] == created["updated_at"]

    patched = client.patch(
        f"/api/items/{created['id']}", json={"description": "touched"}
    ).json()
    assert patched["created_at"] == created["created_at"], "created_at must not move"
    assert datetime.fromisoformat(patched["updated_at"]) > datetime.fromisoformat(
        patched["created_at"]
    )


def test_patch_persists_and_is_not_just_echoed(client, unique_name, created_items):
    """The response is the server's claim; the next GET is the evidence."""
    created = create(client, unique_name, description="before")
    created_items.append(created["id"])

    client.patch(f"/api/items/{created['id']}", json={"description": "after"})
    fetched = client.get(f"/api/items/{created['id']}").json()
    assert fetched["description"] == "after"


def test_patch_onto_a_taken_name_returns_409_and_changes_nothing(
    client, unique_name, created_items
):
    first = create(client, f"{unique_name}-one")
    second = create(client, f"{unique_name}-two")
    created_items.extend([first["id"], second["id"]])

    res = client.patch(f"/api/items/{second['id']}", json={"name": first["name"]})
    assert res.status_code == 409, res.text

    unchanged = client.get(f"/api/items/{second['id']}").json()
    assert unchanged["name"] == f"{unique_name}-two"
    assert unchanged["updated_at"] == second["updated_at"], (
        "a refused rename must not have written the row"
    )


def test_patch_unknown_id_returns_404(client):
    res = client.patch("/api/items/999999999", json={"name": "does-not-matter"})
    assert res.status_code == 404, res.text


def test_patch_non_numeric_id_returns_422(client):
    res = client.patch("/api/items/not-a-number", json={"name": "x"})
    assert res.status_code == 422, res.text


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="empty-patch"),
        pytest.param({"name": None}, id="name-null"),
        pytest.param({"name": ""}, id="name-empty"),
        pytest.param({"name": "   "}, id="name-whitespace-only"),
        pytest.param({"name": "x" * 201}, id="name-too-long"),
        pytest.param({"name": 42}, id="name-not-a-string"),
        pytest.param({"description": "d" * 2001}, id="description-too-long"),
        pytest.param({"nope": "unknown field"}, id="unknown-field"),
    ],
)
def test_invalid_patches_return_422(client, unique_name, created_items, payload):
    created = create(client, unique_name)
    created_items.append(created["id"])

    res = client.patch(f"/api/items/{created['id']}", json=payload)
    assert res.status_code == 422, f"{payload} -> {res.status_code} {res.text}"


def test_a_refused_patch_leaves_the_row_untouched(client, unique_name, created_items):
    created = create(client, unique_name, description="original")
    created_items.append(created["id"])

    assert client.patch(f"/api/items/{created['id']}", json={}).status_code == 422
    assert client.get(f"/api/items/{created['id']}").json() == created


# --- delete ---------------------------------------------------------------


def test_delete_returns_204_and_the_item_disappears(client, unique_name):
    created = client.post("/api/items", json={"name": unique_name})
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    deleted = client.delete(f"/api/items/{item_id}")
    assert deleted.status_code == 204, deleted.text
    assert deleted.content == b""

    assert client.get(f"/api/items/{item_id}").status_code == 404
    assert item_id not in [item["id"] for item in walk_pages(client)]


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

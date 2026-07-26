"""Shared fixtures for the API contract tests."""
import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = float(os.getenv("API_TEST_TIMEOUT", "15"))


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture
def client() -> httpx.Client:
    # trust_env=False: httpx otherwise picks up HTTP_PROXY/ALL_PROXY from the
    # environment and quietly routes the contract suite through whatever
    # happens to be set there. These tests assert on the behaviour of ONE
    # named target; an ambient proxy turns a green run into a statement about
    # something else. Found the honest way — a sandboxed run with a SOCKS
    # proxy exported failed every test on an unrelated import error.
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT, trust_env=False) as client:
        yield client


@pytest.fixture
def unique_name() -> str:
    """A name no other run can collide with.

    stage keeps its database for the life of the environment and the suite may
    run more than once against it, so a fixed name would make the second run
    fail on a 409 that has nothing to do with the code under test.
    """
    return f"contract-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def created_items(client: httpx.Client):
    """Registers created ids and removes them afterwards.

    Cleanup is best-effort: a test that already deleted its item leaves a 404
    here, which is the expected outcome and not a failure.
    """
    ids: list[int] = []
    yield ids
    for item_id in ids:
        try:
            client.delete(f"/api/items/{item_id}")
        except httpx.HTTPError:
            pass

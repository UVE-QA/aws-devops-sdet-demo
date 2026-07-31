"""The request id, asserted over HTTP against whatever BASE_URL points at.

The in-process suite (tests/unit) checks the SHAPE of the log line. It cannot
check that the deployed image behaves the same way behind an ALB — a different
uvicorn invocation, a different set of inbound headers. These two run against
localhost and against stage, and they are cheap enough to be worth both.
"""
import httpx

REQUEST_ID_HEADER = "X-Request-Id"


def test_the_response_carries_a_request_id(client: httpx.Client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers.get(REQUEST_ID_HEADER), (
        "no X-Request-Id on the response: a caller cannot name the log line "
        "its own request produced"
    )


def test_an_inbound_request_id_comes_back_unchanged(client: httpx.Client):
    """A caller that names its request can find that name in CloudWatch."""
    given = "contract-suite-chosen-id"

    response = client.get("/api/health", headers={REQUEST_ID_HEADER: given})

    assert response.status_code == 200
    assert response.headers.get(REQUEST_ID_HEADER) == given

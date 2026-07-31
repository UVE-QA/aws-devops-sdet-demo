"""The access log is the input to the 5xx alarm, so its SHAPE is a contract.

These assertions exist because the alarm reads
`{ $.status >= 500 }` from CloudWatch Logs (ADR-0032). Two ways for that to
silently never fire, both invisible from outside the process:

  - `status` serialised as a string, so the comparison is a string comparison
  - an unhandled exception logged by nobody, because the middleware only ran
    its logging call on the success path

An HTTP test can see neither. That is why this suite is in-process.
"""
import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.logging_config import JsonFormatter
from src.main import REQUEST_ID_HEADER, access_log, app


@pytest.fixture
def log_lines():
    """Captures what the root logger writes, as parsed JSON."""
    stream = []

    class Capture(logging.Handler):
        def emit(self, record):
            stream.append(json.loads(self.format(record)))

    handler = Capture()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    previous = root.handlers
    root.handlers = [handler]
    try:
        yield stream
    finally:
        root.handlers = previous


def access_lines(lines):
    return [line for line in lines if line.get("msg") == "request"]


def test_status_is_a_json_number_not_a_string(log_lines):
    """The whole alarm rests on this. A quoted status compares as a string."""
    TestClient(app).get("/health")

    line = access_lines(log_lines)[0]
    assert isinstance(line["status"], int), (
        f"status serialised as {type(line['status']).__name__}; "
        "the metric filter compares it numerically and would match nothing"
    )
    assert isinstance(line["duration_ms"], (int, float))


def test_the_line_carries_what_identifies_the_request(log_lines):
    TestClient(app).get("/health")

    line = access_lines(log_lines)[0]
    assert line["method"] == "GET"
    assert line["path"] == "/health"
    assert line["request_id"]
    assert line["service"] and line["env"]


def test_an_inbound_request_id_is_used_rather_than_replaced(log_lines):
    given = "chosen-by-the-caller"
    response = TestClient(app).get("/api/health", headers={REQUEST_ID_HEADER: given})

    assert response.headers[REQUEST_ID_HEADER] == given
    assert access_lines(log_lines)[0]["request_id"] == given


def test_a_request_id_is_generated_when_none_is_given(log_lines):
    response = TestClient(app).get("/api/health")

    generated = response.headers[REQUEST_ID_HEADER]
    assert generated
    assert access_lines(log_lines)[0]["request_id"] == generated


def test_an_unhandled_exception_produces_one_line_with_status_500(log_lines):
    """The most valuable 5xx there is, and the one a naive middleware drops.

    The failing route is built HERE rather than in src.main: nothing whose only
    purpose is to fail belongs in an image that is promoted to prod (ADR-0032).
    """
    failing = FastAPI()
    failing.middleware("http")(access_log)

    @failing.get("/raises")
    def _raises():
        raise RuntimeError("deliberate, for the break test")

    response = TestClient(failing, raise_server_exceptions=False).get("/raises")
    assert response.status_code == 500

    lines = access_lines(log_lines)
    assert len(lines) == 1, f"expected exactly one access line, got {len(lines)}"
    line = lines[0]
    assert line["status"] == 500
    assert isinstance(line["status"], int)
    assert line["level"] == "error"
    assert "RuntimeError" in line["exc"], "the traceback is the reason to keep the line"


def test_a_line_written_outside_a_request_still_has_the_field(log_lines):
    """Startup and shutdown lines must not change the shape of the log."""
    logging.getLogger("app.test").info("not in a request")

    assert log_lines[0]["request_id"] == "-"


def test_terminal_decoration_does_not_reach_the_log(log_lines):
    """uvicorn attaches a second, ANSI-coloured copy of its own startup lines.

    Every `extra=` field is promoted to the top level, which is how `status`
    becomes a number the metric filter can compare — and, until this was seen in
    a real container, how `\x1b[36m` would have reached CloudWatch alongside a
    duplicate of the message.
    """
    logging.getLogger("app.test").info(
        "Started server process [1]",
        extra={"color_message": "Started server process [\x1b[36m%d\x1b[0m]"},
    )

    line = log_lines[0]
    assert "color_message" not in line
    assert "\x1b" not in json.dumps(line)

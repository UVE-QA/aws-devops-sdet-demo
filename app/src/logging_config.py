"""Structured JSON logging with a per-request id (ADR-0032).

One JSON object per line on stdout. `status` is an integer at the top level,
because the CloudWatch metric filter behind the 5xx alarm is
`{ $.status >= 500 }` and a quoted status would make that a string comparison
that never matches — an alarm that cannot fire.

Anything logged inside a request picks up the request id from a context
variable, so a line written deep in the call stack is joinable with the access
line without threading an argument through every function.
"""
import contextvars
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

SERVICE = os.getenv("APP_NAME", "aws-devops-sdet-demo")
ENV = os.getenv("APP_ENV", "local")

# "-" rather than None: a line emitted outside any request (startup, shutdown,
# a background task) still has the field, so the shape of the log does not
# depend on when it was written.
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default=""
)

# Attributes LogRecord always carries. Everything NOT in here arrived via
# `extra=` and is promoted to a top-level field — which is how `status` and
# `duration_ms` become numbers the metric filter can compare.
_RESERVED = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()
) | {"message", "asctime", "taskName"}

# Fields that arrive via `extra=` and are decoration rather than data.
# uvicorn attaches `color_message` to its startup lines: the same message again,
# wrapped in ANSI escape sequences for a terminal. Promoting it would put
# \u001b[36m into CloudWatch and duplicate every line it appears on. Found by
# reading what the container actually printed, not by a fixture.
_DROPPED = frozenset({"color_message"})


def new_request_id() -> str:
    return uuid.uuid4().hex


class JsonFormatter(logging.Formatter):
    """Renders a LogRecord as one line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "msg": record.getMessage(),
            "service": SERVICE,
            "env": ENV,
            "logger": record.name,
            "request_id": request_id_var.get(),
        }

        trace_id = trace_id_var.get()
        if trace_id:
            payload["trace_id"] = trace_id

        for key, value in record.__dict__.items():
            if key in _RESERVED or key in _DROPPED or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        # default=str so an unexpected object in `extra=` degrades to its repr
        # instead of raising inside the logging call and losing the line.
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: str | None = None) -> None:
    """Install the JSON formatter on the root logger.

    Called at import of src.main, which happens AFTER the uvicorn CLI has
    configured its own logging — so this wins. uvicorn is additionally started
    with --no-access-log, so the outcome does not depend on that ordering.
    """
    level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # uvicorn installs its own handlers; leaving them would print every startup
    # line twice, once as JSON and once not.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True

    # The application writes its own access line, with the fields the metric
    # filter needs. uvicorn's would be a second, unparseable line per request.
    logging.getLogger("uvicorn.access").disabled = True

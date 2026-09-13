"""One JSON object per line, the same shape the api writes (ADR-0032): ts,
level, service, env, msg, and whatever arrived via `extra=` promoted to the top
level. Not imported from the api - the two share a log shape, not code."""
import json
import logging
import os
import sys
from datetime import datetime, timezone

SERVICE = os.getenv("APP_NAME", "aws-devops-sdet-demo-worker")
ENV = os.getenv("APP_ENV", "local")

_RESERVED = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "service": SERVICE,
            "env": ENV,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)[-2000:]
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    # boto3 at INFO narrates every credential lookup.
    for noisy in ("botocore", "boto3", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

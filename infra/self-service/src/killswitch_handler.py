"""The budget alarm's end of guardrail 4: flip a flag, refuse the next launch.

Subscribed to the SNS topic AWS Budgets publishes to. It does exactly one thing,
and its IAM policy allows exactly that one item to be written - so the worst a
bug here can do is stop launches, which is the safe direction.

What it cannot do is worth repeating where someone will read it: Budgets
evaluates a few times a day and lags by hours. This does not stop the run that
spent the money. It stops the next one. The fast control is the TTL.
"""
from __future__ import annotations

import json
import logging
import os
import time

from store_dynamodb import DynamoDbControlStore

log = logging.getLogger()
log.setLevel(logging.INFO)

TABLE = os.environ.get("CONTROL_TABLE", "")


def handler(event, _context=None):
    now = int(time.time())
    store = DynamoDbControlStore(TABLE)

    reasons = []
    for record in (event or {}).get("Records", []):
        message = record.get("Sns", {}).get("Message", "")
        subject = record.get("Sns", {}).get("Subject", "") or "budget notification"
        reasons.append(f"{subject}: {message[:400]}")

    reason = " | ".join(reasons) or "engaged with no SNS record"
    store.engage_kill_switch(reason, now)
    log.warning(json.dumps({"msg": "kill_switch_engaged", "reason": reason[:400]}))
    return {"engaged": True}

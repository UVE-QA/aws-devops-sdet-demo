"""DynamoDB behind the `ControlStore` interface. All AWS knowledge lives here.

Split from `control.py` so the refusals can be tested without AWS and without
mocking a client library - the fake in `tests/unit` implements this same
interface. The split also makes the fail-closed rule mechanical rather than
remembered: every call below translates anything that is NOT its own conditional
check into `StoreUnavailable`, and `control.py` turns that into a refusal.
"""
from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from control import CapReached, ControlStore, LockHeld, StoreUnavailable

CONDITIONAL = "ConditionalCheckFailedException"


class DynamoDbControlStore(ControlStore):
    def __init__(self, table_name: str, client=None):
        self._table = table_name
        self._client = client or boto3.client("dynamodb")

    # -- flags --------------------------------------------------------------
    def get_flag(self, key: str) -> dict | None:
        try:
            item = self._client.get_item(
                TableName=self._table,
                Key={"pk": {"S": key}},
                ConsistentRead=True,
            ).get("Item")
        except Exception as exc:  # noqa: BLE001 - deliberate: any failure is a refusal
            raise StoreUnavailable(f"get_flag({key})") from exc
        return _plain(item)

    # -- nonces -------------------------------------------------------------
    def issue_nonce(self, nonce: str, expires_at: int) -> None:
        try:
            self._client.put_item(
                TableName=self._table,
                Item={
                    "pk": {"S": f"nonce#{nonce}"},
                    "ttl": {"N": str(expires_at)},
                },
            )
        except Exception as exc:  # noqa: BLE001
            raise StoreUnavailable("issue_nonce") from exc

    def redeem_nonce(self, nonce: str, now: int) -> bool:
        """Single use: the DELETE is the redemption, and it is conditional.

        DynamoDB's own TTL deletion runs on its own schedule - up to 48 hours
        late - so expiry is ALSO checked here. A nonce that is still physically
        present is not a nonce that is still valid.
        """
        if not nonce:
            return False
        try:
            self._client.delete_item(
                TableName=self._table,
                Key={"pk": {"S": f"nonce#{nonce}"}},
                ConditionExpression="attribute_exists(pk) AND #t > :now",
                ExpressionAttributeNames={"#t": "ttl"},
                ExpressionAttributeValues={":now": {"N": str(now)}},
            )
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == CONDITIONAL:
                return False
            raise StoreUnavailable("redeem_nonce") from exc
        except Exception as exc:  # noqa: BLE001
            raise StoreUnavailable("redeem_nonce") from exc

    # -- the lock -----------------------------------------------------------
    def take_lock(self, launch_id: str, expires_at: int, now: int) -> None:
        """Conditional put. An EXPIRED lock may be taken over; a live one may not.

        Deliberately no `ttl` attribute on this item: DynamoDB would delete it,
        and the watchdog would lose the only record that a launch was ever in
        flight. It has to expire without vanishing.
        """
        try:
            self._client.put_item(
                TableName=self._table,
                Item={
                    "pk": {"S": "lock"},
                    "launch_id": {"S": launch_id},
                    "acquired_at": {"N": str(now)},
                    "expires_at": {"N": str(expires_at)},
                },
                ConditionExpression="attribute_not_exists(pk) OR expires_at <= :now",
                ExpressionAttributeValues={":now": {"N": str(now)}},
                ReturnValuesOnConditionCheckFailure="ALL_OLD",
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == CONDITIONAL:
                raise LockHeld(_plain(exc.response.get("Item"))) from exc
            raise StoreUnavailable("take_lock") from exc
        except Exception as exc:  # noqa: BLE001
            raise StoreUnavailable("take_lock") from exc

    def read_lock(self) -> dict | None:
        try:
            item = self._client.get_item(
                TableName=self._table,
                Key={"pk": {"S": "lock"}},
                ConsistentRead=True,
            ).get("Item")
        except Exception as exc:  # noqa: BLE001
            raise StoreUnavailable("read_lock") from exc
        return _plain(item)

    def release_lock(self) -> None:
        try:
            self._client.delete_item(TableName=self._table, Key={"pk": {"S": "lock"}})
        except Exception as exc:  # noqa: BLE001
            raise StoreUnavailable("release_lock") from exc

    def note_on_lock(self, fields: dict) -> None:
        """Attach the run to the lock, so a later refusal can name what holds it."""
        names = {f"#k{i}": k for i, k in enumerate(fields)}
        values = {f":v{i}": {"S": str(v)} for i, v in enumerate(fields.values())}
        expression = "SET " + ", ".join(
            f"{n} = {v}" for n, v in zip(names, values, strict=True)
        )
        try:
            self._client.update_item(
                TableName=self._table,
                Key={"pk": {"S": "lock"}},
                UpdateExpression=expression,
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
                ConditionExpression="attribute_exists(pk)",
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == CONDITIONAL:
                return
            raise StoreUnavailable("note_on_lock") from exc
        except Exception as exc:  # noqa: BLE001
            raise StoreUnavailable("note_on_lock") from exc

    # -- the day counter ----------------------------------------------------
    def increment_day(self, day: str, cap: int) -> int:
        """A conditional increment, never a read followed by a write.

        Read-then-write is how two simultaneous presses both see two and both
        become three. The condition is evaluated by DynamoDB inside the same
        operation that increments.
        """
        try:
            result = self._client.update_item(
                TableName=self._table,
                Key={"pk": {"S": f"count#{day}"}},
                UpdateExpression="SET n = if_not_exists(n, :zero) + :one",
                ConditionExpression="attribute_not_exists(n) OR n < :cap",
                ExpressionAttributeValues={
                    ":zero": {"N": "0"},
                    ":one": {"N": "1"},
                    ":cap": {"N": str(cap)},
                },
                ReturnValues="UPDATED_NEW",
            )
            return int(result["Attributes"]["n"]["N"])
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == CONDITIONAL:
                raise CapReached(day) from exc
            raise StoreUnavailable("increment_day") from exc
        except Exception as exc:  # noqa: BLE001
            raise StoreUnavailable("increment_day") from exc

    def engage_kill_switch(self, reason: str, now: int) -> None:
        try:
            self._client.put_item(
                TableName=self._table,
                Item={
                    "pk": {"S": "killswitch"},
                    "engaged": {"BOOL": True},
                    "engaged_at": {"N": str(now)},
                    "reason": {"S": reason[:1000]},
                },
            )
        except Exception as exc:  # noqa: BLE001
            raise StoreUnavailable("engage_kill_switch") from exc


def _plain(item: dict | None) -> dict | None:
    """DynamoDB's typed item -> a plain dict. Only the three types used here."""
    if not item:
        return None
    out: dict = {}
    for key, value in item.items():
        if "S" in value:
            out[key] = value["S"]
        elif "N" in value:
            out[key] = int(value["N"])
        elif "BOOL" in value:
            out[key] = value["BOOL"]
    return out

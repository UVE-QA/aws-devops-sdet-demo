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
from sweep import RECORD_KEY as SWEEP_KEY

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

    # -- the watchdog's own record ------------------------------------------
    #
    # `note_on_lock` used to live here, and the watchdog wrote its dispatch onto
    # the LOCK with it. That is the defect ADR-0036 D1 removes: the lock belongs
    # to the launch, and the case the watchdog exists for is the case where the
    # launch's records are gone. These three touch one item that nothing else
    # writes, reads or deletes.
    def read_sweep(self) -> dict | None:
        try:
            item = self._client.get_item(
                TableName=self._table,
                Key={"pk": {"S": SWEEP_KEY}},
                ConsistentRead=True,
            ).get("Item")
        except Exception as exc:  # noqa: BLE001
            raise StoreUnavailable("read_sweep") from exc
        return _plain(item)

    def note_sweep(self, scope: str, dispatched_at: int, ttl: int) -> None:
        """A whole-item PUT, not an update: this record has one writer.

        Unlike the lock, it carries a DynamoDB `ttl`. Losing it late is
        harmless - by then whatever it described is long finished - while
        keeping it forever is not: a stale `dispatched_at` inherited by a fresh
        launch is a blunt teardown nobody asked for. The scope check is the
        first defence; this is the second.
        """
        try:
            self._client.put_item(
                TableName=self._table,
                Item={
                    "pk": {"S": SWEEP_KEY},
                    "scope": {"S": scope},
                    "dispatched_at": {"N": str(dispatched_at)},
                    "ttl": {"N": str(ttl)},
                },
            )
        except Exception as exc:  # noqa: BLE001
            raise StoreUnavailable("note_sweep") from exc

    def clear_sweep(self) -> None:
        try:
            self._client.delete_item(
                TableName=self._table, Key={"pk": {"S": SWEEP_KEY}}
            )
        except Exception as exc:  # noqa: BLE001
            raise StoreUnavailable("clear_sweep") from exc

    # -- the day counter ----------------------------------------------------
    def read_day(self, day: str) -> int:
        """How many launches that day has had. A read, and only for reporting.

        An ABSENT item is zero launches, which is the one case where absence
        really is a value here: the counter is created by the first increment.
        An unreadable store is still a refusal - `StoreUnavailable` - because a
        quota nobody could read is not a quota of three.
        """
        try:
            result = self._client.get_item(
                TableName=self._table,
                Key={"pk": {"S": f"count#{day}"}},
                ConsistentRead=True,
            )
        except ClientError as exc:
            raise StoreUnavailable("read_day") from exc
        item = result.get("Item")
        return int(item["n"]["N"]) if item and "n" in item else 0

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

    def engage_kill_switch(self, reason: str, now: int, source: str = "budget-alarm") -> None:
        """`source` is what the refusal is allowed to say out loud.

        The reason is an SNS message, and the refusal goes to the public
        internet - so the reason stays here and in the log, and the endpoint
        reports only where the switch came from (ADR-0036, and the same rule
        that made the budget email a secret in Phase 15). A switch thrown by
        hand writes `manual`, and the refusal stops claiming a budget alarm
        that never fired.
        """
        try:
            self._client.put_item(
                TableName=self._table,
                Item={
                    "pk": {"S": "killswitch"},
                    "engaged": {"BOOL": True},
                    "engaged_at": {"N": str(now)},
                    "source": {"S": source},
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

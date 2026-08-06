"""The refusals. This module decides whether a launch may happen, and nothing else.

It imports no AWS SDK on purpose. Every store operation goes through the small
`ControlStore` interface below, so `tests/unit` can drive all five refusals in
process, with a fake store that can be made to fail in the exact way the real
one fails. That is the Phase 16b precedent applied again: a property no HTTP
client can observe belongs in a test that does not use HTTP.

The five refusals (ADR-0035), in the order they are evaluated:

    1. kill switch   thrown by the budget alarm OR by hand, read before
                     anything else, and applied to GET as well as to POST
    2. configured    no App id, no installation - refuse rather than 500 later
    3. nonce         single-use, and a speed bump rather than authorization
    4. lock          one run at a time, refused HERE because Actions only queues
    5. daily cap     conditional increment, and it FAILS CLOSED

The one that matters most is the one that is easiest to get wrong: if the store
cannot be READ, the answer is a refusal. An error is not "zero launches today".
A spend control that fails open is not a spend control.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

KILL_SWITCH_KEY = "killswitch"
LOCK_KEY = "lock"

# A launch id appears in a run NAME, which the dashboard renders, and it comes
# from the public internet. Anything outside this alphabet is refused before it
# reaches GitHub rather than escaped on the way out.
LAUNCH_ID = re.compile(r"\A[a-z0-9-]{8,64}\Z")


class StoreUnavailable(Exception):
    """The control store could not be read or written.

    Never swallowed, never treated as an empty result. The name of the failing
    operation is the message, because "refused" and "refused for a reason that
    names the store" are two different things to a visitor.
    """


class CapReached(Exception):
    """The conditional increment was refused: today is already at the cap."""


class LockHeld(Exception):
    """The conditional put was refused: another launch holds the lock."""

    def __init__(self, holder: dict | None = None):
        super().__init__("lock held")
        self.holder = holder or {}


class ControlStore:
    """What the decision logic needs from the store, and nothing more.

    Every method raises `StoreUnavailable` when the underlying call fails for
    any reason other than its own conditional check. The DynamoDB implementation
    is `store_dynamodb.py`; the tests use a fake.
    """

    def get_flag(self, key: str) -> dict | None:
        raise NotImplementedError

    def redeem_nonce(self, nonce: str, now: int) -> bool:
        raise NotImplementedError

    def issue_nonce(self, nonce: str, expires_at: int) -> None:
        raise NotImplementedError

    def take_lock(self, launch_id: str, expires_at: int, now: int) -> None:
        raise NotImplementedError

    def read_lock(self) -> dict | None:
        raise NotImplementedError

    def release_lock(self) -> None:
        raise NotImplementedError

    def increment_day(self, day: str, cap: int) -> int:
        raise NotImplementedError

    # The watchdog's own record (ADR-0036 D1). It is on this interface rather
    # than on the DynamoDB class alone so `tests/unit` can break it in the same
    # ways as everything else - and because the fake store implements THIS, not
    # a recording of AWS.
    def read_sweep(self) -> dict | None:
        raise NotImplementedError

    def note_sweep(self, scope: str, dispatched_at: int, ttl: int) -> None:
        raise NotImplementedError

    def clear_sweep(self) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str
    message: str
    status: int = 200
    detail: dict | None = None


def utc_day(now: int) -> str:
    """The counter is keyed by UTC date, so the reset time is the same everywhere."""
    return datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")


def seconds_until_utc_midnight(now: int) -> int:
    moment = datetime.fromtimestamp(now, tz=timezone.utc)
    end_of_day = moment.replace(hour=23, minute=59, second=59, microsecond=0)
    return int(end_of_day.timestamp()) - now + 1


def decide_launch(
    store: ControlStore,
    *,
    now: int,
    launch_id: str,
    nonce: str,
    ttl_minutes: int,
    daily_cap: int,
    configured: bool,
) -> Decision:
    """Evaluate every guardrail, in order, and take the lock if all of them pass.

    Returns a `Decision`. On `allowed`, the lock IS taken and the day counter IS
    consumed - so a caller that then fails to dispatch must release the lock.
    The counter is deliberately NOT refunded in that case: a launch that got far
    enough to hold the lock has already had its turn, and a refund path is a
    second place for the cap to leak.
    """
    if not LAUNCH_ID.match(launch_id or ""):
        return Decision(
            False,
            "bad_request",
            "launch id must be 8-64 characters of [a-z0-9-]",
            status=400,
        )

    # 1. The kill switch, before anything else (ADR-0035 guardrail 4).
    refusal = kill_switch_refusal(store)
    if refusal is not None:
        return refusal

    # 2. Configuration. Refusing here beats a 500 from GitHub two calls later,
    #    and this is the state the endpoint is in between 19b's apply and the
    #    moment the App exists.
    if not configured:
        return Decision(
            False,
            "not_configured",
            "the launch path is not configured yet: the GitHub App id or "
            "installation id is unset.",
            status=503,
        )

    # 3. The nonce. A speed bump, and labelled as one (ADR-0034): whoever can
    #    read the page can get one. It stops a trivially scripted loop and gives
    #    each launch an id the dashboard can display. It is not authorization.
    try:
        if not store.redeem_nonce(nonce or "", now):
            return Decision(
                False,
                "nonce",
                "that nonce is unknown, expired or already used. Reload the "
                "page and press again.",
                status=409,
            )
    except StoreUnavailable as exc:
        return _store_refusal(exc)

    # 4. One run at a time. The refusal lives HERE, not in `concurrency:`:
    #    Actions queues or cancels, and a queue of fifty launches is fifty
    #    cycles arriving later.
    expires_at = now + ttl_minutes * 60
    try:
        store.take_lock(launch_id, expires_at, now)
    except LockHeld as held:
        return Decision(
            False,
            "locked",
            "a launch is already running. Watch it on the dashboard; the "
            "button unlocks when it finishes, and in any case at its deadline.",
            status=409,
            # No `run_url`. It was read here and written NOWHERE, because the
            # lock is taken BEFORE the dispatch and `workflow_dispatch` returns
            # no run id - there is no moment at which this code knows the URL.
            # 19b proved the refusal against a hand-seeded item carrying a field
            # the real writer never writes, which is how a key that could only
            # ever be null survived a break test. The dashboard is where a
            # visitor watches a run (ADR-0026); it does not need this.
            detail={
                "launch_id": held.holder.get("launch_id"),
                "expires_at": held.holder.get("expires_at"),
            },
        )
    except StoreUnavailable as exc:
        return _store_refusal(exc)

    # 5. The per-day cap, by conditional increment rather than read-then-write.
    try:
        count = store.increment_day(utc_day(now), daily_cap)
    except CapReached:
        _release_quietly(store)
        return Decision(
            False,
            "daily_cap",
            f"today's limit of {daily_cap} public launches is used up. "
            f"It resets at 00:00 UTC.",
            status=429,
            detail={"resets_in_seconds": seconds_until_utc_midnight(now)},
        )
    except StoreUnavailable as exc:
        _release_quietly(store)
        return _store_refusal(exc)

    return Decision(
        True,
        "ok",
        "launching",
        detail={
            "launch_id": launch_id,
            "expires_at": expires_at,
            "launches_today": count,
        },
    )


def kill_switch_refusal(store: ControlStore) -> Decision | None:
    """The kill switch, evaluated in ONE place and applied to BOTH methods.

    Two corrections from 19c, both of the same family - the endpoint saying
    something that is not true:

    It used to name the budget alarm whichever way the switch was thrown, and
    the switch is thrown by hand at least as often as by Budgets. It now reports
    the SOURCE, which the writer records.

    And it used to refuse only `POST`, while `infra/self-service/README.md` said
    it "refuses every request" - so a parked endpoint went on issuing nonces and
    writing an item to the store for anyone who asked. `GET` is refused too now,
    and the README is the thing that was right.

    What it deliberately does NOT return is the recorded reason. The budget
    path's reason is an SNS message with the account's budget in it, and this
    reply goes to the public internet; the reason stays in the store and in the
    log. That is the same rule that moved the budget email out of a GitHub
    variable in Phase 15.
    """
    try:
        flag = store.get_flag(KILL_SWITCH_KEY)
    except StoreUnavailable as exc:
        return _store_refusal(exc)

    if not (flag and flag.get("engaged")):
        return None

    by_budget = str(flag.get("source", "")) == "budget-alarm"
    why = (
        "The account budget alarm fired. This is a backstop and it is slow by "
        "design - it stops the next run, not the one that spent the money."
        if by_budget
        else "They were switched off deliberately. The reason is recorded where "
        "the switch was thrown, not here."
    )
    return Decision(
        False,
        "kill_switch",
        f"launches are disabled. {why}",
        status=503,
        detail={
            "since": flag.get("engaged_at"),
            "source": flag.get("source") or "manual",
        },
    )


def _store_refusal(exc: StoreUnavailable) -> Decision:
    """The refusal that must never become a pass.

    It names the STORE rather than the cap on purpose. Those are two different
    states, and a visitor told the wrong one goes and waits until tomorrow for
    something that is broken now.
    """
    return Decision(
        False,
        "store_unavailable",
        "the launch control store could not be read, so this request is "
        "refused. An unreadable counter is not zero launches today.",
        status=503,
        detail={"operation": str(exc)},
    )


def _release_quietly(store: ControlStore) -> None:
    """Best effort. The lock has an expiry precisely because this can fail."""
    try:
        store.release_lock()
    except Exception:  # noqa: BLE001 - the deadline is the real guarantee
        pass


def lock_is_expired(lock: dict | None, now: int) -> bool:
    """A lock older than its deadline is not a lock.

    A MISSING or unreadable deadline counts as expired, which is the same rule
    the watchdog applies to an untagged environment: absence of evidence is not
    permission to run forever, and here the absence is itself a symptom of the
    failure the deadline exists for.
    """
    if not lock:
        return False
    try:
        return int(lock["expires_at"]) <= now
    except (KeyError, TypeError, ValueError):
        return True

"""What the watchdog does about what it found. No AWS SDK, on purpose.

`control.py` split the refusals away from DynamoDB so every one of them could be
driven in process. This is the same split applied to the other Lambda, and for a
sharper reason: the watchdog's interesting branches only happen when something
has already gone wrong somewhere else. Reaching the blunt path for real means
cancelling a live apply and waiting out a grace period, which costs a launch,
an ALB and fifteen minutes. Reaching it here costs a dictionary.

THE DECISION IS A PURE FUNCTION OF FOUR THINGS

    alive     the billable resources observed, each with its tags. The public
              button's, only - `observe()` has already dropped anything with an
              empty `Launch` tag, and the IAM policy drops it a second time
    lock      the launch's record, or None. NOT ours: the launch Lambda writes
              it, `release-lock` deletes it, a later launch takes it over
    record    OURS. `pk = "watchdog"`, written and deleted by nobody else
              (ADR-0036 D1)
    now       so every deadline in here is arithmetic rather than a clock read

WHY THE RECORD EXISTS AT ALL

Until 19d the watchdog wrote `destroy_dispatched_at` onto the LOCK, and returned
early when there was no lock to write on. A cancelled run leaves exactly that
state - resources alive, lock deleted by a `release-lock` that never asked how
destroy went - so the attempt was never recorded, the grace period never started,
and the blunt path could not engage in the one case it was written for. The
watchdog's memory was stored on a record owned by the thing it exists to
distrust.

WHY THE RECORD IS SCOPED

A record that outlived its situation would be worse than no record: a fresh
launch inheriting a `dispatched_at` from an hour ago goes straight to the blunt
path and deletes an environment nobody asked it to. So the record carries the
launch ids it was written about, and a record whose scope does not match what is
alive now is not this situation's record. Belt and braces: it is cleared as soon
as nothing is alive, and it carries a DynamoDB `ttl` as well.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import control

log = logging.getLogger(__name__)

# The five things the watchdog can decide, plus the one that means "nothing".
NONE = "none"
RELEASED_STALE_LOCK = "released_stale_lock"
WITHIN_DEADLINE = "within_deadline"
DISPATCH = "dispatched_destroy"
WAIT = "waiting_for_destroy"
BLUNT = "blunt_teardown"

RECORD_KEY = "watchdog"

# Long enough to cover a grace period several times over, short enough that a
# record nobody cleared cannot be waiting for the next launch tomorrow.
RECORD_TTL_SECONDS = 6 * 60 * 60


@dataclass(frozen=True)
class Sweep:
    """The decision AND its effects, so the handler executes rather than decides.

    Naming the effects here rather than deriving them from `action` in the
    handler is deliberate: it is what lets a test assert that the blunt path
    releases the lock, without owning an ECS client to find out.
    """

    action: str
    alive: tuple[str, ...] = ()
    scope: str = ""
    release_lock: bool = False
    clear_record: bool = False
    note_dispatch: bool = False
    dispatched_s_ago: int = 0
    detail: dict = field(default_factory=dict)


def scope_of(alive: list[dict]) -> str:
    """The launch ids this situation is about, in a form two runs can compare."""
    return ",".join(sorted({str(r["tags"].get("Launch", "")) for r in alive}))


def deadline_passed(resource: dict, now: int) -> bool:
    """A missing or unparseable deadline counts as expired, not as exempt.

    The absence is itself a symptom of the failure this whole function exists
    for: a resource that reached AWS without its `ExpiresAt` tag was created by
    something that was not following the rules.
    """
    raw = resource["tags"].get("ExpiresAt", "")
    if not raw:
        return True
    try:
        moment = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        log.warning(
            "unparseable ExpiresAt %r on %s; treating as expired", raw, resource["id"]
        )
        return True
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp() <= now


def decide_sweep(
    *,
    alive: list[dict],
    lock: dict | None,
    record: dict | None,
    now: int,
    grace: int,
) -> Sweep:
    """Decide, given what is alive and what has already been tried."""
    ids = tuple(str(r["id"]) for r in alive)
    scope = scope_of(alive)

    # Nothing is billing. The only work left is tidying up records so the next
    # launch starts against a clean store.
    if not alive:
        if control.lock_is_expired(lock, now):
            # A launch that died AFTER its own teardown must not wedge the
            # button until someone notices.
            return Sweep(
                RELEASED_STALE_LOCK,
                release_lock=True,
                clear_record=record is not None,
            )
        return Sweep(NONE, clear_record=record is not None)

    # Live resources with no lock at all is an ANOMALY, not a quiet cycle: the
    # record that a launch was in flight has gone missing while its environment
    # is still running. That skips the deadline, exactly as an expired one does.
    if not (
        any(deadline_passed(r, now) for r in alive)
        or control.lock_is_expired(lock, now)
        or lock is None
    ):
        return Sweep(WITHIN_DEADLINE, alive=ids, scope=scope)

    dispatched_at = dispatched_at_for(record, scope)

    if not dispatched_at:
        return Sweep(DISPATCH, alive=ids, scope=scope, note_dispatch=True)

    if now - dispatched_at < grace:
        return Sweep(
            WAIT, alive=ids, scope=scope, dispatched_s_ago=now - dispatched_at
        )

    # Actions was asked, politely, a grace period ago, and the environment is
    # still there. Delete the billable resources directly (ADR-0035 guardrail 5)
    # and drop both records: what they were guarding is about to be gone.
    return Sweep(
        BLUNT, alive=ids, scope=scope, release_lock=True, clear_record=True
    )


def dispatched_at_for(record: dict | None, scope: str) -> int:
    """When WE last asked Actions to destroy THIS situation. Zero means never.

    A record from a different scope, or one that cannot be read, is not a
    record. Both answer zero, which means "dispatch", which means the worst a
    corrupt record can do is cause one extra idempotent destroy - never a blunt
    teardown of something that was never asked about.
    """
    if not record:
        return 0
    if str(record.get("scope", "")) != scope:
        return 0
    try:
        return int(record["dispatched_at"])
    except (KeyError, TypeError, ValueError):
        return 0

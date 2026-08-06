"""Every branch the watchdog can take, including the ones a cycle never shows.

`test_launch_refusals.py` exists because no HTTP client can see what happens when
the control store fails. These exist for a harder reason: the watchdog's
interesting branches only happen when something else has ALREADY gone wrong.
Reaching the blunt path for real means cancelling a live apply, waiting out a
fifteen-minute grace period, and spending a launch, an ALB and an RDS instance.
Reaching it here costs a dictionary.

The defect these were written against (ADR-0036) had been green under every
check this project owns, and was invisible to all of them: the watchdog recorded
its dispatch on the LOCK, the lock is deleted by `release-lock`, and a cancelled
run deletes the lock while the environment is still alive. So the attempt was
never recorded, the grace period never started, and the blunt path could not
engage in the one case it was written for. It re-dispatched every five minutes
while an ALB billed.

`test_the_record_outlives_the_lock` is that defect, in nine lines.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

import sweep

NOW = 1_785_000_000
GRACE = 15 * 60


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resource(id="svc-1", launch="ss-aaaaaaaa", expires_in=3600, kind="ecs"):
    tags = {"Launch": launch}
    if expires_in is not None:
        tags["ExpiresAt"] = iso(NOW + expires_in)
    return {"kind": kind, "id": id, "cluster": "cluster-1", "tags": tags}


def lock(launch="ss-aaaaaaaa", expires_in=3600):
    return {"launch_id": launch, "expires_at": NOW + expires_in}


def record(scope="ss-aaaaaaaa", dispatched_ago=0):
    return {"scope": scope, "dispatched_at": NOW - dispatched_ago}


def decide(alive=(), lk=None, rec=None, now=NOW):
    return sweep.decide_sweep(
        alive=list(alive), lock=lk, record=rec, now=now, grace=GRACE
    )


# ------------------------------------------------------- nothing is billing
def test_an_empty_account_with_a_live_lock_is_left_alone():
    decision = decide(alive=[], lk=lock())

    assert decision.action == sweep.NONE
    assert not decision.release_lock
    assert not decision.clear_record


def test_an_expired_lock_over_an_empty_account_is_released():
    """A launch that died AFTER its own teardown must not wedge the button."""
    decision = decide(alive=[], lk=lock(expires_in=-1), rec=record())

    assert decision.action == sweep.RELEASED_STALE_LOCK
    assert decision.release_lock
    assert decision.clear_record, "and its record must not meet the next launch"


def test_a_record_with_nothing_alive_is_cleared_even_when_the_lock_is_fine():
    decision = decide(alive=[], lk=lock(), rec=record())

    assert decision.action == sweep.NONE
    assert decision.clear_record
    assert not decision.release_lock


def test_nothing_alive_and_nothing_recorded_writes_nothing():
    decision = decide()

    assert decision.action == sweep.NONE
    assert not decision.clear_record
    assert not decision.release_lock


# ------------------------------------------------------ the deadline itself
def test_a_running_environment_inside_its_deadline_is_not_touched():
    decision = decide(alive=[resource()], lk=lock())

    assert decision.action == sweep.WITHIN_DEADLINE
    assert decision.alive == ("svc-1",)


def test_a_passed_deadline_dispatches_a_destroy():
    decision = decide(alive=[resource(expires_in=-1)], lk=lock(expires_in=3600))

    assert decision.action == sweep.DISPATCH
    assert decision.note_dispatch, "and the attempt has to be written down"


@pytest.mark.parametrize("expires_in", [None])
def test_a_resource_with_no_deadline_is_expired_not_exempt(expires_in):
    decision = decide(alive=[resource(expires_in=expires_in)], lk=lock())

    assert decision.action == sweep.DISPATCH


def test_an_unparseable_deadline_is_expired_too():
    victim = resource()
    victim["tags"]["ExpiresAt"] = "next tuesday"

    assert sweep.deadline_passed(victim, NOW) is True
    assert decide(alive=[victim], lk=lock()).action == sweep.DISPATCH


def test_live_resources_with_no_lock_at_all_are_an_anomaly_not_a_quiet_cycle():
    """The lock is gone and the environment is not. That skips the deadline."""
    decision = decide(alive=[resource()], lk=None)

    assert decision.action == sweep.DISPATCH


# ----------------------------------------- the record, which is the whole fix
def test_the_record_outlives_the_lock():
    """ADR-0036 D1, and the exact sequence a cancelled run produced on 19c.

    Before the fix, step 2 answered `dispatched_destroy` again - and so did
    every invocation after it, five minutes apart, forever, while an ALB and an
    RDS instance billed. The grace period could not start, so the blunt path
    could not engage in the one situation it exists for.
    """
    # The environment is well inside its 90-minute deadline - the run was
    # cancelled minutes after it started - and `release-lock` has already
    # deleted the lock without asking how destroy went.
    alive = [resource()]

    # 1. live resources, no lock. The anomaly, and the watchdog asks Actions.
    first = decide(alive=alive, lk=None, rec=None)
    assert first.action == sweep.DISPATCH
    assert first.note_dispatch, "and it writes down that it asked - on its OWN record"

    # 2. five minutes later. The record is still there, because it was never on
    #    the lock. THIS is the step that used to answer `dispatched_destroy`
    #    again, forever.
    waiting = decide(alive=alive, lk=None, rec=record(dispatched_ago=300))
    assert waiting.action == sweep.WAIT
    assert waiting.dispatched_s_ago == 300

    # 3. Actions never did it - it cannot, the state lock is still held. The
    #    blunt path engages WITHOUT a lock, which is what it could never do.
    blunt = decide(alive=alive, lk=None, rec=record(dispatched_ago=GRACE + 1))
    assert blunt.action == sweep.BLUNT
    assert blunt.release_lock and blunt.clear_record


def test_the_grace_period_is_measured_from_the_dispatch_not_from_the_deadline():
    just_inside = decide(alive=[resource()], lk=None, rec=record(dispatched_ago=GRACE - 1))
    just_outside = decide(alive=[resource()], lk=None, rec=record(dispatched_ago=GRACE))

    assert just_inside.action == sweep.WAIT
    assert just_outside.action == sweep.BLUNT


def test_a_record_from_another_launch_is_not_inherited():
    """Otherwise a fresh launch walks into a blunt teardown it never earned."""
    decision = decide(
        alive=[resource(launch="ss-bbbbbbbb")],
        lk=None,
        rec=record(scope="ss-aaaaaaaa", dispatched_ago=GRACE + 1),
    )

    assert decision.action == sweep.DISPATCH
    assert decision.scope == "ss-bbbbbbbb"


@pytest.mark.parametrize(
    "broken",
    [
        {"scope": "ss-aaaaaaaa"},
        {"scope": "ss-aaaaaaaa", "dispatched_at": "soon"},
        {"scope": "ss-aaaaaaaa", "dispatched_at": None},
    ],
)
def test_a_record_that_cannot_be_read_dispatches_rather_than_destroys(broken):
    """The worst a corrupt record can do is one extra idempotent destroy."""
    decision = decide(alive=[resource()], lk=None, rec=broken)

    assert decision.action == sweep.DISPATCH


def test_the_scope_is_stable_across_two_observations_of_the_same_situation():
    one = [resource(id="a", launch="ss-bbbbbbbb"), resource(id="b", launch="ss-aaaaaaaa")]
    other = [resource(id="b", launch="ss-aaaaaaaa"), resource(id="a", launch="ss-bbbbbbbb")]

    assert sweep.scope_of(one) == sweep.scope_of(other) == "ss-aaaaaaaa,ss-bbbbbbbb"


def test_the_blunt_path_names_everything_it_is_about_to_delete():
    alive = [
        resource(id="svc", kind="ecs"),
        resource(id="alb", kind="alb"),
        resource(id="db", kind="rds"),
    ]

    decision = decide(alive=alive, lk=None, rec=record(dispatched_ago=GRACE + 1))

    assert decision.action == sweep.BLUNT
    assert set(decision.alive) == {"svc", "alb", "db"}

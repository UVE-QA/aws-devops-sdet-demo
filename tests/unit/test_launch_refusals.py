"""Every refusal the public button makes, exercised in process.

The Phase 16b precedent, applied to a different kind of invisible property. The
log-shape tests are here because no HTTP client can see a log line; these are
here because no HTTP client can see what happens when the CONTROL STORE fails.
An endpoint that is refusing correctly and an endpoint that is refusing because
its store is broken look identical from outside, and only one of them is a
guardrail.

The store is a fake rather than a mock of boto3, and that is the point of
`control.ControlStore` existing at all: the refusals are tested against the
interface the real store implements, not against a recording of AWS.

What these can NOT show, stated so nobody mistakes a green suite for a proven
guardrail: that DynamoDB's conditional expressions mean what `store_dynamodb.py`
thinks they mean. That is 19b, against the real table, with the output kept.
"""
from __future__ import annotations

import pytest

import control
from control import CapReached, ControlStore, LockHeld, StoreUnavailable

NOW = 1_785_000_000  # 2026-07-25 17:20 UTC; the day counter is keyed by UTC date
TTL = 90
CAP = 3
GOOD_ID = "ss-0123456789abcdef"


class FakeStore(ControlStore):
    """A control store that can be broken in exactly the ways the real one breaks."""

    def __init__(self, **broken):
        self.flag = None
        self.nonces = {"good-nonce": NOW + 300}
        self.lock = None
        self.counts: dict[str, int] = {}
        self.released = 0
        self.broken = broken  # method name -> True

    def _maybe_break(self, name):
        if self.broken.get(name):
            raise StoreUnavailable(name)

    def get_flag(self, key):
        self._maybe_break("get_flag")
        return self.flag

    def issue_nonce(self, nonce, expires_at):
        self._maybe_break("issue_nonce")
        self.nonces[nonce] = expires_at

    def redeem_nonce(self, nonce, now):
        self._maybe_break("redeem_nonce")
        expiry = self.nonces.pop(nonce, None)
        return expiry is not None and expiry > now

    def take_lock(self, launch_id, expires_at, now):
        self._maybe_break("take_lock")
        if self.lock and int(self.lock["expires_at"]) > now:
            raise LockHeld(self.lock)
        self.lock = {"launch_id": launch_id, "expires_at": expires_at, "acquired_at": now}

    def read_lock(self):
        self._maybe_break("read_lock")
        return self.lock

    def release_lock(self):
        self._maybe_break("release_lock")
        self.released += 1
        self.lock = None

    def increment_day(self, day, cap):
        self._maybe_break("increment_day")
        used = self.counts.get(day, 0)
        if used >= cap:
            raise CapReached(day)
        self.counts[day] = used + 1
        return self.counts[day]


def decide(store, **overrides):
    kwargs = dict(
        now=NOW,
        launch_id=GOOD_ID,
        nonce="good-nonce",
        ttl_minutes=TTL,
        daily_cap=CAP,
        configured=True,
    )
    kwargs.update(overrides)
    return control.decide_launch(store, **kwargs)


# --------------------------------------------------------------------- happy
def test_a_clean_press_takes_the_lock_and_consumes_one_launch():
    store = FakeStore()

    decision = decide(store)

    assert decision.allowed
    assert store.lock["launch_id"] == GOOD_ID
    assert store.lock["expires_at"] == NOW + TTL * 60, "the lock's expiry IS the TTL"
    assert store.counts[control.utc_day(NOW)] == 1
    assert "good-nonce" not in store.nonces, "a nonce is single use"


# ------------------------------------------------------- 1. the kill switch
def test_the_kill_switch_is_read_before_anything_else():
    store = FakeStore()
    store.flag = {"engaged": True, "engaged_at": NOW - 10}

    decision = decide(store)

    assert not decision.allowed
    assert decision.code == "kill_switch"
    assert decision.status == 503
    # The order is the assertion: a kill switch checked after the nonce would
    # spend a nonce, and after the lock would spend a launch.
    assert store.lock is None
    assert "good-nonce" in store.nonces
    assert store.counts == {}


# --------------------------------------------------------- 2. the day cap
def test_the_cap_refuses_when_today_is_used_up():
    store = FakeStore()
    store.counts[control.utc_day(NOW)] = CAP

    decision = decide(store)

    assert not decision.allowed
    assert decision.code == "daily_cap"
    assert decision.status == 429
    assert str(CAP) in decision.message
    assert decision.detail["resets_in_seconds"] > 0


def test_the_cap_refusal_releases_the_lock_it_took():
    """Otherwise the first press after midnight is refused by yesterday's lock."""
    store = FakeStore()
    store.counts[control.utc_day(NOW)] = CAP

    decide(store)

    assert store.released == 1
    assert store.lock is None


def test_an_unreadable_counter_is_not_zero_launches_today():
    """The refusal that must never become a pass.

    This is the same sentence as the post-teardown check whose expired SSO token
    printed nine empty lines that looked exactly like a clean account.
    """
    store = FakeStore(increment_day=True)

    decision = decide(store)

    assert not decision.allowed
    assert decision.status == 503
    assert decision.code == "store_unavailable", "a broken store must not read as an open one"
    assert store.lock is None, "and it must not leave the lock behind"


def test_the_store_refusal_names_the_store_and_not_the_cap():
    """Two different states. A visitor told the wrong one waits until tomorrow
    for something that is broken now."""
    broken = decide(FakeStore(increment_day=True))

    capped = FakeStore()
    capped.counts[control.utc_day(NOW)] = CAP
    at_cap = decide(capped)

    assert broken.code != at_cap.code
    assert "store" in broken.message.lower()
    assert "store" not in at_cap.message.lower()


def test_an_unreadable_kill_switch_also_fails_closed():
    store = FakeStore(get_flag=True)

    decision = decide(store)

    assert not decision.allowed
    assert decision.code == "store_unavailable"
    assert store.lock is None


# -------------------------------------------------------------- 3. the lock
def test_a_second_press_is_refused_and_names_what_holds_the_lock():
    store = FakeStore()
    store.nonces["second-nonce"] = NOW + 300
    first = decide(store)

    second = decide(store, nonce="second-nonce", launch_id="ss-fedcba9876543210")

    assert first.allowed
    assert not second.allowed
    assert second.code == "locked"
    assert second.status == 409
    assert second.detail["launch_id"] == GOOD_ID, "the refusal has to name the holder"
    assert store.counts[control.utc_day(NOW)] == 1, "a refused press must not consume a launch"


def test_an_expired_lock_can_be_taken_over():
    """A lock older than the TTL is not a lock. Guardrail 5 is what makes that
    safe to say: the watchdog has already dealt with whatever held it."""
    store = FakeStore()
    store.lock = {"launch_id": "ss-oldoldoldoldold1", "expires_at": NOW - 1}
    store.nonces["fresh"] = NOW + 300

    decision = decide(store, nonce="fresh")

    assert decision.allowed
    assert store.lock["launch_id"] == GOOD_ID


# ------------------------------------------------------------- 4. the nonce
@pytest.mark.parametrize(
    "nonce, why",
    [("", "empty"), ("never-issued", "unknown"), ("used-already", "already redeemed")],
)
def test_a_bad_nonce_is_refused(nonce, why):
    store = FakeStore()
    store.nonces["used-already"] = NOW + 300
    store.redeem_nonce("used-already", NOW)

    decision = decide(store, nonce=nonce)

    assert not decision.allowed, why
    assert decision.code == "nonce"
    assert store.lock is None


def test_an_expired_nonce_is_refused_even_though_the_item_is_still_there():
    """DynamoDB's TTL deletion runs up to 48 hours late. Physically present is
    not the same as still valid, and only the code can tell the difference."""
    store = FakeStore()
    store.nonces["stale"] = NOW - 1

    decision = decide(store, nonce="stale")

    assert not decision.allowed
    assert decision.code == "nonce"


# ------------------------------------------------------- 5. shape and config
def test_an_unconfigured_endpoint_refuses_instead_of_failing_later():
    decision = decide(FakeStore(), configured=False)

    assert not decision.allowed
    assert decision.code == "not_configured"


@pytest.mark.parametrize("launch_id", ["", "short", "ss-UPPER0123456789", "ss-../../etc", "x" * 65])
def test_a_launch_id_from_the_internet_is_validated_before_it_reaches_a_run_name(launch_id):
    store = FakeStore()

    decision = decide(store, launch_id=launch_id)

    assert not decision.allowed
    assert decision.code == "bad_request"
    assert "good-nonce" in store.nonces, "and it is rejected before anything is spent"


# ------------------------------------------- the missing-deadline rule (WD)
def test_a_lock_with_no_deadline_counts_as_expired():
    """Absence of evidence is not permission to run forever - and here the
    absence is itself a symptom of the failure the deadline exists for."""
    assert control.lock_is_expired({"launch_id": "ss-whatever12345678"}, NOW) is True
    assert control.lock_is_expired({"expires_at": "not-a-number"}, NOW) is True
    assert control.lock_is_expired({"expires_at": NOW - 1}, NOW) is True
    assert control.lock_is_expired({"expires_at": NOW + 60}, NOW) is False
    assert control.lock_is_expired(None, NOW) is False, "no lock is not an expired lock"


def test_the_day_key_is_utc_so_the_reset_time_is_the_same_everywhere():
    assert control.utc_day(NOW) == "2026-07-25"
    assert 0 < control.seconds_until_utc_midnight(NOW) <= 86400


# ------------------------------- what the kill switch is allowed to say (19d)
def test_the_kill_switch_reports_how_it_was_actually_thrown():
    """It named the budget alarm whichever way it was engaged, and the switch is
    thrown by hand at least as often as by Budgets - including every time this
    project parks the endpoint between phases."""
    by_hand = FakeStore()
    by_hand.flag = {"engaged": True, "engaged_at": NOW - 10}
    by_budget = FakeStore()
    by_budget.flag = {"engaged": True, "engaged_at": NOW - 10, "source": "budget-alarm"}

    manual = decide(by_hand)
    budget = decide(by_budget)

    assert manual.detail["source"] == "manual"
    assert "budget" not in manual.message.lower(), "no alarm fired; do not say one did"
    assert budget.detail["source"] == "budget-alarm"
    assert "budget" in budget.message.lower()


def test_the_refusal_does_not_republish_the_recorded_reason():
    """The budget path's reason is an SNS message with the account's budget in
    it, and this reply goes to the public internet. Phase 15 moved the budget
    email out of a GitHub variable for the same reason."""
    store = FakeStore()
    store.flag = {
        "engaged": True,
        "engaged_at": NOW,
        "source": "budget-alarm",
        "reason": "AWS Budgets: demo-monthly exceeded USD 12.34 in 993912191738",
    }

    decision = decide(store)

    assert "reason" not in (decision.detail or {})
    assert "12.34" not in decision.message


def test_the_kill_switch_is_evaluated_for_the_nonce_too():
    """`GET` used to be exempt, while the README said the switch "refuses every
    request" - so a parked endpoint went on writing a store item per press for
    anyone who asked. Of the two, the README was right."""
    engaged = FakeStore()
    engaged.flag = {"engaged": True, "engaged_at": NOW}

    assert control.kill_switch_refusal(engaged).code == "kill_switch"
    assert control.kill_switch_refusal(FakeStore()) is None, "and it lets a live one through"
    assert control.kill_switch_refusal(FakeStore(get_flag=True)).code == "store_unavailable"

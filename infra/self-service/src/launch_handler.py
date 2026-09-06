"""The Lambda behind the Function URL. Two methods, one decision.

    GET   issue a nonce                (a speed bump, and labelled as one)
    POST  redeem it and launch, or refuse with a reason a visitor can act on

Everything that decides is in `control.py`, which knows nothing about AWS or
about Lambda. This file is the plumbing: read configuration, build the store,
translate a `Decision` into an HTTP response, and - only when the decision says
yes - mint a token and dispatch.

If the dispatch fails after the lock was taken, the lock is released here. The
day counter is NOT refunded, deliberately: see `control.decide_launch`.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import time

import boto3

import control
import github
from store_dynamodb import DynamoDbControlStore

log = logging.getLogger()
log.setLevel(logging.INFO)

TABLE = os.environ.get("CONTROL_TABLE", "")
OWNER = os.environ.get("GITHUB_OWNER", "")
REPO = os.environ.get("GITHUB_REPO", "")
APP_ID = os.environ.get("GITHUB_APP_ID", "")
INSTALL_ID = os.environ.get("GITHUB_INSTALL_ID", "")
SECRET_NAME = os.environ.get("GITHUB_APP_SECRET", "")
WORKFLOW = os.environ.get("WORKFLOW_FILE", "self-service.yml")
REF = os.environ.get("GITHUB_REF_NAME", "main")
TTL_MINUTES = int(os.environ.get("TTL_MINUTES", "90"))
DAILY_CAP = int(os.environ.get("DAILY_CAP", "3"))
# The zone the daily cap is counted in (ADR-0072). Named, not an offset:
# the offset moves twice a year and the reset would follow it.
QUOTA_TIMEZONE = os.environ.get("QUOTA_TIMEZONE") or control.DEFAULT_QUOTA_TZ
NONCE_TTL = int(os.environ.get("NONCE_TTL_SECONDS", "300"))

_secrets = boto3.client("secretsmanager")


def _response(status: int, body: dict) -> dict:
    # NO access-control-allow-origin here. The Function URL's cors{} block sets
    # it, and a header set in BOTH places arrives twice: browsers reject
    # `Access-Control-Allow-Origin` with more than one value, so the function
    # answers 200, the browser discards the reply, and the caller sees a bare
    # network error naming nothing.
    #
    # It survived to the first real press because nothing here could see it. The
    # CORS layer only joins in when the request carries an Origin, so curl
    # without one shows a single correct header, and OPTIONS is answered by the
    # Lambda service instead of the function, so preflight never shows the pair
    # either. Only a browser puts the two together. `make self-service-cors-check`
    # is the check that does, and it fails on zero as loudly as on two.
    return {
        "statusCode": status,
        "headers": {
            "content-type": "application/json",
            "cache-control": "no-store",
        },
        "body": json.dumps(body),
    }


def _private_key() -> str:
    return _secrets.get_secret_value(SecretId=SECRET_NAME)["SecretString"]


def handler(event, _context=None):
    method = (
        event.get("requestContext", {}).get("http", {}).get("method", "GET").upper()
    )
    store = DynamoDbControlStore(TABLE)
    now = int(time.time())

    if method == "GET":
        return _issue(store, now)
    if method == "POST":
        return _launch(store, now, event)
    return _response(405, {"code": "method", "message": "GET or POST"})


def _issue(store, now: int) -> dict:
    """A nonce and a launch id, refused when the switch is off.

    The launch id is generated HERE rather than accepted from the caller, so the
    string that ends up in a public run name cannot be chosen by a stranger.

    The kill-switch check is the one thing here that costs a read, and it was
    missing until 19d: a parked endpoint went on handing out nonces and WRITING
    an item for each one, while the README said it "refuses every request". Of
    the two, the README was right - a switch that still lets strangers write to
    the control store is not off.
    """
    refusal = control.kill_switch_refusal(store)
    if refusal is not None:
        return _response(
            refusal.status,
            {"code": refusal.code, "message": refusal.message, "detail": refusal.detail},
        )

    nonce = secrets.token_urlsafe(24)
    launch_id = f"ss-{secrets.token_hex(8)}"
    try:
        store.issue_nonce(nonce, now + NONCE_TTL)
    except control.StoreUnavailable as exc:
        log.warning("nonce store unavailable: %s", exc)
        return _response(503, {"code": "store_unavailable", "message": str(exc)})

    return _response(
        200,
        {
            "nonce": nonce,
            "launch_id": launch_id,
            "expires_in": NONCE_TTL,
            # The two numbers the page states in its own sentence. It hardcoded
            # both until 19d, which is one definition on two hosts: changing
            # var.ttl_minutes would have left the dashboard telling visitors 90
            # while the environment carried something else.
            "ttl_minutes": TTL_MINUTES,
            "daily_cap": DAILY_CAP,
            "note": "this nonce is a speed bump, not authorization",
        },
    )


def _launch(store, now: int, event: dict) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
    except ValueError:
        return _response(400, {"code": "bad_request", "message": "body must be JSON"})

    decision = control.decide_launch(
        store,
        now=now,
        launch_id=str(body.get("launch_id", "")),
        nonce=str(body.get("nonce", "")),
        ttl_minutes=TTL_MINUTES,
        daily_cap=DAILY_CAP,
        configured=bool(APP_ID and INSTALL_ID and SECRET_NAME),
        quota_timezone=QUOTA_TIMEZONE,
    )

    # Every refusal is logged with its code, because the reason a visitor was
    # turned away is the evidence that a guardrail fired. A refusal nobody can
    # find afterwards is indistinguishable from a guardrail that never ran.
    log.info(
        json.dumps(
            {
                "msg": "launch_decision",
                "allowed": decision.allowed,
                "code": decision.code,
                "detail": decision.detail,
            }
        )
    )

    if not decision.allowed:
        return _response(
            decision.status,
            {"code": decision.code, "message": decision.message, "detail": decision.detail},
        )

    detail = decision.detail or {}
    launch_id = detail["launch_id"]
    try:
        token = github.installation_token(APP_ID, _private_key(), INSTALL_ID, now)
        github.dispatch_workflow(
            token,
            OWNER,
            REPO,
            WORKFLOW,
            REF,
            {
                "launch_id": launch_id,
                "ttl_minutes": str(TTL_MINUTES),
            },
        )
    except Exception as exc:  # noqa: BLE001 - the lock must not survive a failed dispatch
        log.exception("dispatch failed")
        control._release_quietly(store)
        return _response(
            502,
            {
                "code": "dispatch_failed",
                "message": "the launch could not be started. The lock has been "
                "released; nothing was created.",
                "detail": {"error": type(exc).__name__},
            },
        )

    return _response(
        202,
        {
            "code": "launching",
            "message": "started. Watch it on the dashboard - this page reports "
            "what the Actions API says, never what this endpoint claims.",
            "launch_id": launch_id,
            "expires_at": detail.get("expires_at"),
            "launches_today": detail.get("launches_today"),
            "run_name": f"self-service launch {launch_id}",
        },
    )

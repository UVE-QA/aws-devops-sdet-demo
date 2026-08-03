"""The out-of-band TTL enforcement (ADR-0035 guardrails 3 and 5).

Runs on EventBridge Scheduler, in a failure domain that shares nothing with
GitHub Actions except the account. It exists for the cases `if: always()` cannot
cover: a force-cancelled run, a dead runner, GitHub being unavailable. A promise
made by the thing that might not be there is not a guarantee.

TWO KEYS, because either one alone has a blind spot

    the resources   ECS service, ALB and RDS instance under the stage prefix,
                    each carrying its own deadline in an `ExpiresAt` tag - read
                    without asking Actions anything. Present even if the lock
                    was lost.
    the lock        the record that a launch is in flight, with the same
                    deadline. Present even if the deploy died before it created
                    a single resource.

WHAT IT WILL NOT TOUCH, AND WHY THAT IS NOT A LOOPHOLE

Only resources whose `Launch` tag is NON-EMPTY, i.e. created by the public
button. An owner-run stage cycle carries `Launch=""` and is invisible here -
and unreachable, because the IAM policy carries the same condition. Guardrails
are on the public path, not on the project (ADR-0035). prod is excluded twice
over: by the name prefix here, and by `Environment=stage` in the policy.

A MISSING DEADLINE IS NOT PERMISSION TO RUN FOREVER

Within that scope, a resource with no `ExpiresAt`, an unparseable one, or a
launch with no lock at all counts as EXPIRED, not as exempt. The absence is
itself a symptom of the exact failure this exists for.

TWO PATHS, AND THE BLUNT ONE MUST BE BROKEN ON PURPOSE

    1. dispatch destroy.yml, which leaves Terraform state consistent
    2. if the environment is still alive LOCK_GRACE_MINUTES later - the case
       where Actions IS the broken thing - delete the billable resources
       directly: ECS service, then ALB, then RDS, for the ENI/IGW ordering
       reason ADR-0016 already records.

After path 2 the Terraform state is stale. The recovery is written down in
advance rather than discovered under pressure: re-run destroy, which reconciles
what is already gone.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone

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
DESTROY_WORKFLOW = os.environ.get("DESTROY_WORKFLOW", "destroy.yml")
REF = os.environ.get("GITHUB_REF_NAME", "main")
ENVIRONMENT = os.environ.get("STAGE_ENVIRONMENT", "stage")
PREFIX = os.environ.get("STAGE_NAME_PREFIX", "aws-devops-sdet-demo-stage")
GRACE = int(os.environ.get("LOCK_GRACE_MINUTES", "15")) * 60

ecs = boto3.client("ecs")
elbv2 = boto3.client("elbv2")
rds = boto3.client("rds")
secrets_manager = boto3.client("secretsmanager")


def handler(_event=None, _context=None):
    now = int(time.time())
    store = DynamoDbControlStore(TABLE)

    try:
        lock = store.read_lock()
    except control.StoreUnavailable as exc:
        # Doing nothing is the SAFE failure here - unlike the launch path, where
        # doing nothing means spending money. Raised rather than swallowed, so
        # the invocation fails visibly instead of looking like a quiet cycle
        # with nothing to do. An empty result is not a clean result.
        log.error("watchdog cannot read the control store: %s", exc)
        raise

    alive = observe()
    deadline_passed = any(_expired(r, now) for r in alive)
    lock_expired = control.lock_is_expired(lock, now)

    if not alive:
        if lock_expired:
            # The deadline passed and there is nothing left to delete. Release
            # the lock so the button works again: a run that died AFTER its own
            # teardown must not wedge the endpoint until someone notices.
            control._release_quietly(store)
            log.info(json.dumps({"msg": "watchdog", "action": "released_stale_lock"}))
            return {"action": "released_stale_lock"}
        log.info(json.dumps({"msg": "watchdog", "action": "none", "alive": 0}))
        return {"action": "none"}

    summary = [r["id"] for r in alive]

    if not (deadline_passed or lock_expired or lock is None):
        log.info(
            json.dumps({"msg": "watchdog", "action": "within_deadline", "alive": summary})
        )
        return {"action": "within_deadline", "alive": summary}

    dispatched_at = int((lock or {}).get("destroy_dispatched_at") or 0)

    if not dispatched_at:
        dispatch_destroy(store, now, lock)
        return {"action": "dispatched_destroy", "alive": summary}

    if now - dispatched_at < GRACE:
        log.info(
            json.dumps(
                {
                    "msg": "watchdog",
                    "action": "waiting_for_destroy",
                    "dispatched_s_ago": now - dispatched_at,
                    "alive": summary,
                }
            )
        )
        return {"action": "waiting_for_destroy", "alive": summary}

    log.warning(
        json.dumps({"msg": "watchdog", "action": "blunt_teardown", "alive": summary})
    )
    deleted = blunt_teardown(alive)
    control._release_quietly(store)
    return {"action": "blunt_teardown", "deleted": deleted}


# ---------------------------------------------------------------------------
# Observation. Only the three things that cost money by the hour, and only the
# ones the public button created.
# ---------------------------------------------------------------------------
def observe() -> list[dict]:
    found: list[dict] = []

    for cluster in ecs.list_clusters().get("clusterArns", []):
        if PREFIX not in cluster:
            continue
        arns = ecs.list_services(cluster=cluster).get("serviceArns", [])
        if not arns:
            continue
        described = ecs.describe_services(
            cluster=cluster, services=arns, include=["TAGS"]
        ).get("services", [])
        for service in described:
            found.append(
                {
                    "kind": "ecs",
                    "id": service["serviceArn"],
                    "cluster": cluster,
                    "tags": _tags(service.get("tags", []), "key", "value"),
                }
            )

    for lb in elbv2.describe_load_balancers().get("LoadBalancers", []):
        if not lb["LoadBalancerName"].startswith(PREFIX):
            continue
        tags = elbv2.describe_tags(ResourceArns=[lb["LoadBalancerArn"]]).get(
            "TagDescriptions", [{}]
        )
        found.append(
            {
                "kind": "alb",
                "id": lb["LoadBalancerArn"],
                "tags": _tags(tags[0].get("Tags", []), "Key", "Value"),
            }
        )

    for db in rds.describe_db_instances().get("DBInstances", []):
        if not db["DBInstanceIdentifier"].startswith(PREFIX):
            continue
        found.append(
            {
                "kind": "rds",
                "id": db["DBInstanceIdentifier"],
                "tags": _tags(db.get("TagList", []), "Key", "Value"),
            }
        )

    # THE scope decision, in one line: no Launch tag, no jurisdiction.
    return [r for r in found if r["tags"].get("Launch")]


def _tags(pairs, key_field: str, value_field: str) -> dict:
    return {p[key_field]: p[value_field] for p in pairs or []}


def _expired(resource: dict, now: int) -> bool:
    """A missing or unparseable deadline counts as expired, not as exempt."""
    raw = resource["tags"].get("ExpiresAt", "")
    if not raw:
        return True
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        log.warning("unparseable ExpiresAt %r on %s; treating as expired", raw, resource["id"])
        return True
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp() <= now


def dispatch_destroy(store, now: int, lock: dict | None) -> None:
    """Path 1: ask Actions to do it properly, and record that we asked.

    The record goes ON THE LOCK, so the next invocation five minutes later can
    tell "asked and waiting" from "never asked" without keeping state a Lambda
    does not have. If there is no lock to write on - the case where the launch
    lost its own record - the write is skipped and the next invocation dispatches
    again, which is idempotent: destroy.yml on an already-destroyed environment
    is the reconciliation step this project already relies on.
    """
    try:
        pem = secrets_manager.get_secret_value(SecretId=SECRET_NAME)["SecretString"]
        token = github.installation_token(APP_ID, pem, INSTALL_ID, now)
        github.dispatch_workflow(
            token,
            OWNER,
            REPO,
            DESTROY_WORKFLOW,
            REF,
            {"environment": ENVIRONMENT, "confirm": "DESTROY"},
        )
        log.info(json.dumps({"msg": "watchdog", "action": "dispatched_destroy"}))
    except Exception:  # noqa: BLE001
        # Recorded anyway. If GitHub cannot be reached, that IS the case the
        # blunt path exists for, and not recording the attempt would leave this
        # retrying an unreachable thing forever while the meter runs.
        log.exception("destroy dispatch failed; the blunt path takes over after the grace period")

    if lock is None:
        return
    try:
        store.note_on_lock({"destroy_dispatched_at": str(now)})
    except Exception:  # noqa: BLE001
        log.exception("could not record the dispatch attempt")


def blunt_teardown(alive: list[dict]) -> dict:
    """Path 2. Order matters: ECS, then ALB, then RDS (ADR-0016).

    Every call is additionally constrained by IAM to resources of this project
    tagged Environment=stage AND carrying a non-empty Launch tag. prod and the
    owner's own stage cycle are unreachable from this function by policy, not
    only by the filter above.
    """
    deleted: dict = {"ecs": [], "alb": [], "rds": []}

    for resource in [r for r in alive if r["kind"] == "ecs"]:
        try:
            ecs.update_service(
                cluster=resource["cluster"], service=resource["id"], desiredCount=0
            )
            ecs.delete_service(
                cluster=resource["cluster"], service=resource["id"], force=True
            )
            deleted["ecs"].append(resource["id"])
        except Exception:  # noqa: BLE001
            log.exception("could not delete ECS service %s", resource["id"])

    for resource in [r for r in alive if r["kind"] == "alb"]:
        try:
            elbv2.delete_load_balancer(LoadBalancerArn=resource["id"])
            deleted["alb"].append(resource["id"])
        except Exception:  # noqa: BLE001
            log.exception("could not delete load balancer %s", resource["id"])

    for resource in [r for r in alive if r["kind"] == "rds"]:
        try:
            rds.delete_db_instance(
                DBInstanceIdentifier=resource["id"],
                SkipFinalSnapshot=True,
                DeleteAutomatedBackups=True,
            )
            deleted["rds"].append(resource["id"])
        except Exception:  # noqa: BLE001
            log.exception("could not delete database %s", resource["id"])

    return deleted

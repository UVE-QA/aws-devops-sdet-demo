"""The out-of-band TTL enforcement (ADR-0035 guardrails 3 and 5).

Runs on EventBridge Scheduler, in a failure domain that shares nothing with
GitHub Actions except the account. It exists for the cases `if: always()` cannot
cover: a force-cancelled run, a dead runner, GitHub being unavailable. A promise
made by the thing that might not be there is not a guarantee.

This file OBSERVES and EXECUTES. It does not decide: since 19d the decision is
`sweep.decide_sweep`, which imports no AWS SDK and is driven branch by branch in
`tests/unit` (ADR-0036 D1). What is left here is the part that genuinely needs
boto3.

TWO KEYS, because either one alone has a blind spot

    the resources   ECS service, ALB and RDS instance under the stage prefix,
                    each carrying its own deadline in an `ExpiresAt` tag - read
                    without asking Actions anything. Present even if the lock
                    was lost.
    the lock        the record that a launch is in flight, with the same
                    deadline. Present even if the deploy died before it created
                    a single resource.

AND ONE RECORD OF ITS OWN

`pk = "watchdog"`, written and deleted by this function alone. It holds when we
last asked Actions to destroy, and the launch ids we asked about. Before 19d that
lived on the LOCK, which belongs to the launch - so a cancelled run whose
`release-lock` deleted the lock also deleted the watchdog's memory, and the
grace period could never start. The blunt path was unreachable in exactly the
situation it was written for (ADR-0036).

WHAT IT WILL NOT TOUCH, AND WHY THAT IS NOT A LOOPHOLE

Only resources whose `Launch` tag is NON-EMPTY, i.e. created by the public
button. An owner-run stage cycle carries `Launch=""` and is invisible here -
and unreachable, because the IAM policy carries the same condition. Guardrails
are on the public path, not on the project (ADR-0035). prod is excluded twice
over: by the name prefix here, and by `Environment=stage` in the policy.

TWO PATHS, AND THE BLUNT ONE MUST BE BROKEN ON PURPOSE

    1. dispatch destroy.yml, which leaves Terraform state consistent
    2. if the environment is still alive LOCK_GRACE_MINUTES later - the case
       where Actions IS the broken thing - delete the billable resources
       directly: ECS service, then ALB, then RDS, for the ENI/IGW ordering
       reason ADR-0016 already records.

After path 2 the Terraform state is stale, and the recovery is to re-run
destroy, which reconciles what is already gone. That sentence used to stop
there, and it was false for the case that matters: a run cancelled mid-apply
also leaves the S3 state LOCK held, and re-running destroy waits for a lock
nobody will ever release. Since 19d the teardown workflows run
`scripts/break-stale-state-lock.sh` in front of the destroy, which breaks a lock
left by a finished runner and refuses in every other case (ADR-0036 D3).
"""
from __future__ import annotations

import json
import logging
import os
import time

import boto3

import control
import github
import sweep
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
        record = store.read_sweep()
    except control.StoreUnavailable as exc:
        # Doing nothing is the SAFE failure here - unlike the launch path, where
        # doing nothing means spending money. Raised rather than swallowed, so
        # the invocation fails visibly instead of looking like a quiet cycle
        # with nothing to do. An empty result is not a clean result.
        log.error("watchdog cannot read the control store: %s", exc)
        raise

    alive = observe()
    decision = sweep.decide_sweep(
        alive=alive, lock=lock, record=record, now=now, grace=GRACE
    )

    result: dict = {"action": decision.action}
    if decision.alive:
        result["alive"] = list(decision.alive)
    if decision.action == sweep.WAIT:
        result["dispatched_s_ago"] = decision.dispatched_s_ago

    if decision.action == sweep.DISPATCH:
        dispatch_destroy(now)

    if decision.note_dispatch:
        # NOT best-effort, and not swallowed. This record is the whole fix: a
        # dispatch that is not recorded is a dispatch that will be made again in
        # five minutes, forever, while the meter runs. If it cannot be written,
        # the invocation fails and says so.
        store.note_sweep(decision.scope, now, now + sweep.RECORD_TTL_SECONDS)

    if decision.action == sweep.BLUNT:
        log.warning(
            json.dumps(
                {"msg": "watchdog", "action": sweep.BLUNT, "alive": list(decision.alive)}
            )
        )
        result["deleted"] = blunt_teardown(alive)

    # Order matters: the records are dropped only after the thing they were
    # guarding has been dealt with.
    if decision.release_lock:
        control._release_quietly(store)
    if decision.clear_record:
        _clear_record_quietly(store)

    log.info(json.dumps({"msg": "watchdog", **result}))
    return result


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


def dispatch_destroy(now: int) -> None:
    """Path 1: ask Actions to do it properly.

    Recording that we asked is the CALLER's job now, and it happens whether this
    succeeds or not: if GitHub cannot be reached, that IS the case the blunt path
    exists for, and not recording the attempt would leave the watchdog retrying
    an unreachable thing forever while the meter runs.
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
        log.exception(
            "destroy dispatch failed; the blunt path takes over after the grace period"
        )


def _clear_record_quietly(store) -> None:
    """Best effort, and safe to lose: the record also carries a DynamoDB ttl,
    and a record whose scope no longer matches is ignored anyway."""
    try:
        store.clear_sweep()
    except Exception:  # noqa: BLE001
        log.exception("could not clear the watchdog record")


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

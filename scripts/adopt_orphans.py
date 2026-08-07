"""Which orphan becomes which Terraform address (ADR-0038 D3).

WHY THIS EXISTS

A cancelled apply creates resources that never enter Terraform state. Terraform
can then neither delete them nor delete what depends on them: on 2026-08-07 an
unmanaged RDS instance held a managed DB subnet group, and the destroy died on
that pair in 70 seconds. The blunt path removed the instance an hour later,
which is exactly what unblocks Terraform, and nothing ran Terraform again.

So a teardown now ADOPTS before it destroys. This file is the part of that with
branches: an ARN and its tags in, a Terraform address and an import id out - or
one of four named refusals. It imports no AWS SDK and reads no state, for the
same reason `control.py` and `sweep.py` do not: the interesting cases only
happen after something has already gone wrong, and reaching them for real costs
a launch, an hour and an ALB.

THE MAP IS DATA, AND IT IS CHECKED AGAINST THE CONFIGURATION

`tests/unit/test_adopt_orphans.py` asserts that every address below exists in
the module sources the environment actually wires up, and that none of the
mapped resources declares `count` or `for_each`. A map that goes stale against a
renamed module is then a red unit test, rather than a confusing `terraform
import` error in the middle of a teardown that is already failing.

WHAT IS DELIBERATELY NOT IN THE MAP

Subnets and route table associations are counted, and the index cannot be
recovered from an ARN: the Name tag carries an availability zone, and the
mapping from zone to index comes from a `data` source read at apply time.
Guessing it would be an assumption dressed as a mapping. They are reported as
`unadoptable` and the end-of-run sweep fails on them, which is the same refusal
to let "I could not check" read as "it is handled" that ADR-0037 arrived at from
the other side.

The map does not need every kind, and should not try to have them. A dependent
leaves with its parent - adopt the load balancer and its listeners go with it,
adopt the VPC and the default security group goes with it. What it covers is the
resources that HOLD others, because those are the ones that stall a destroy.

WHERE THE DISCRIMINATOR COMES FROM, AND WHY IT IS NOT ALWAYS THE ARN

Most ARNs carry the resource's name, and the name is `<prefix>-<something>`
where `<something>` identifies the resource in the configuration. Two families
do not:

    ec2               the id is opaque (`sg-0abc`), so the Name tag is the only
                      thing that says which security group this is
    secretsmanager    AWS appends six random characters to the ARN, and those
                      are not knowable from the configuration

Both use the Name tag instead. A resource without one is `unadoptable` rather
than guessed. Matching is EXACT in every case: a looser rule starts matching on
substrings, and `sweep_orphans.py` already records where that ends.
"""
from __future__ import annotations

from typing import Any, Callable

import arns

# The four ways an ARN can fail to become an address. Named, because a log line
# that says "skipped" tells the next person nothing.
NO_RULE = "no rule for this kind"
INDEXED = "the configuration counts this kind, and the index is not in the ARN"
NO_NAME_TAG = "no Name tag, and this kind has no usable name in its ARN"
UNKNOWN_NAME = "the name matches no resource in the configuration"
DUPLICATE = "two live resources claim the same Terraform address"


# Kinds that exist in the configuration and cannot be addressed from an ARN,
# because the resource is counted. Naming them separately from "no rule" is the
# difference between "nobody thought about this" and "this was decided": the
# Name tag on a subnet carries an availability zone, and the zone-to-index
# mapping comes from a `data` source read at apply time (ADR-0038 D4).
INDEXED_KINDS = {
    "ec2:subnet",
}


class Arn:
    """Just enough ARN to work with, parsed by `scripts/arns.py`.

    The parse lives there rather than here because `sweep-orphans.sh` needs the
    same answer, and it used to compute its own - wrongly, for every ARN whose
    resource part is colon-separated. One definition, two hosts.
    """

    __slots__ = ("service", "kind", "tail", "raw")

    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.service, self.kind, self.tail = arns.parse(raw)

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"Arn({self.raw!r})"


# --- how each kind answers "what is this called" and "how is it imported" ----
def _tail(arn: Arn) -> str:
    return arn.tail


def _elb_name(arn: Arn) -> str:
    """`app/<name>/<hash>` for a load balancer, `<name>/<hash>` for a group."""
    parts = arn.tail.split("/")
    return parts[1] if parts and parts[0] == "app" else (parts[0] if parts else "")


def _ecs_service_name(arn: Arn) -> str:
    """`<cluster>/<service>`."""
    parts = arn.tail.split("/")
    return parts[-1] if parts else ""


def _log_group_leaf(arn: Arn) -> str:
    """`/aws-devops-sdet-demo/stage/app` -> app. The one name that is a path."""
    return arn.tail.rstrip("/").rsplit("/", 1)[-1]


def _arn_itself(arn: Arn) -> str:
    return arn.raw


def _ecs_service_id(arn: Arn) -> str:
    """Terraform imports a service as `<cluster>/<service>`."""
    return arn.tail


class Rule:
    """One kind: where its name comes from, and how Terraform imports it."""

    __slots__ = ("addresses", "name_from", "import_id", "from_tag")

    def __init__(
        self,
        addresses: dict[str, str],
        import_id: Callable[[Arn], str],
        name_from: Callable[[Arn], str] | None = None,
        from_tag: bool = False,
    ) -> None:
        self.addresses = addresses
        self.import_id = import_id
        self.name_from = name_from or _tail
        self.from_tag = from_tag


RULES: dict[str, Rule] = {
    # --- ec2: opaque ids, so the discriminator is the Name tag --------------
    "ec2:vpc": Rule(
        {"vpc": "module.network.aws_vpc.this"}, import_id=_tail, from_tag=True
    ),
    "ec2:internet-gateway": Rule(
        {"igw": "module.network.aws_internet_gateway.this"},
        import_id=_tail,
        from_tag=True,
    ),
    "ec2:route-table": Rule(
        {"public-rt": "module.network.aws_route_table.public"},
        import_id=_tail,
        from_tag=True,
    ),
    "ec2:security-group": Rule(
        {
            "alb-sg": "module.alb.aws_security_group.alb",
            "app-sg": "module.ecs.aws_security_group.app",
            "rds-sg": "module.rds.aws_security_group.rds",
            # The VPC's default group, which AWS creates and cannot delete. It
            # leaves with the VPC; adopting it only keeps it from being reported
            # as something nobody looked at.
            "default-sg-revoked": "module.network.aws_default_security_group.this",
        },
        import_id=_tail,
        from_tag=True,
    ),
    # --- everything else: the ARN carries the name -------------------------
    "ecs:cluster": Rule({"cluster": "module.ecs.aws_ecs_cluster.this"}, import_id=_tail),
    "ecs:service": Rule(
        {"app": "module.ecs.aws_ecs_service.app"},
        import_id=_ecs_service_id,
        name_from=_ecs_service_name,
    ),
    "elasticloadbalancing:loadbalancer": Rule(
        {"alb": "module.alb.aws_lb.this"},
        import_id=_arn_itself,
        name_from=_elb_name,
    ),
    "elasticloadbalancing:targetgroup": Rule(
        {"tg": "module.alb.aws_lb_target_group.app"},
        import_id=_arn_itself,
        name_from=_elb_name,
    ),
    "rds:db": Rule({"db": "module.rds.aws_db_instance.this"}, import_id=_tail),
    "rds:subgrp": Rule(
        {"db-subnet-group": "module.rds.aws_db_subnet_group.this"}, import_id=_tail
    ),
    "logs:log-group": Rule(
        {"app": "module.observability.aws_cloudwatch_log_group.app"},
        import_id=_tail,
        name_from=_log_group_leaf,
    ),
    # AWS appends six random characters to a secret's ARN, and they are not
    # knowable from the configuration - so the Name tag, like ec2.
    "secretsmanager:secret": Rule(
        {"db-credentials": "module.rds.aws_secretsmanager_secret.db"},
        import_id=_arn_itself,
        from_tag=True,
    ),
}


def discriminator(name: str, prefix: str) -> str:
    """The part of a resource's name that says WHICH resource it is.

    Exact, and anchored on the environment's own prefix. A name that does not
    carry the prefix is returned unchanged, which then matches nothing.
    """
    head = f"{prefix}-"
    return name[len(head):] if name.startswith(head) else name


def plan_one(arn: str, tags: dict[str, str], prefix: str) -> dict[str, Any]:
    """One orphan -> `adopt` with an address and an import id, or `unadoptable`."""
    parsed = Arn(arn)
    kind = f"{parsed.service}:{parsed.kind}"
    if kind in INDEXED_KINDS:
        return {"arn": arn, "verdict": "unadoptable", "reason": INDEXED}

    rule = RULES.get(kind)
    if rule is None:
        return {"arn": arn, "verdict": "unadoptable", "reason": NO_RULE}

    if rule.from_tag:
        name = tags.get("Name", "")
        if not name:
            return {"arn": arn, "verdict": "unadoptable", "reason": NO_NAME_TAG}
    else:
        name = rule.name_from(parsed)

    address = rule.addresses.get(discriminator(name, prefix))
    if not address:
        return {
            "arn": arn,
            "verdict": "unadoptable",
            "reason": f"{UNKNOWN_NAME} ({name or '<unnamed>'})",
        }

    return {
        "arn": arn,
        "verdict": "adopt",
        "address": address,
        "import_id": rule.import_id(parsed),
    }


def plan(
    orphans: list[str], tags_by_arn: dict[str, dict[str, str]], prefix: str
) -> dict[str, Any]:
    """The whole plan, with collisions resolved AFTER everything is mapped.

    Two live resources mapping to one address means the map is wrong or the
    account holds something unexpected. Adopting either would be a coin toss, so
    neither is adopted and both are reported - the end-of-run sweep then fails on
    them, which is the outcome that gets looked at.
    """
    entries = [plan_one(arn, tags_by_arn.get(arn, {}), prefix) for arn in sorted(orphans)]

    seen: dict[str, list[dict]] = {}
    for entry in entries:
        if entry["verdict"] == "adopt":
            seen.setdefault(entry["address"], []).append(entry)

    for address, claimants in seen.items():
        if len(claimants) > 1:
            for entry in claimants:
                entry["verdict"] = "unadoptable"
                entry["reason"] = f"{DUPLICATE} ({address})"
                entry.pop("address", None)
                entry.pop("import_id", None)

    adopt = [e for e in entries if e["verdict"] == "adopt"]
    unadoptable = [e for e in entries if e["verdict"] == "unadoptable"]
    return {"adopt": adopt, "unadoptable": unadoptable}


def main(argv: list[str]) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Map orphan ARNs to Terraform addresses")
    parser.add_argument("--decision", required=True, help="sweep_orphans.py --json output")
    parser.add_argument("--tagged", required=True, help="get-resources for this environment")
    parser.add_argument("--environment", required=True)
    parser.add_argument("--out", required=True, help="where to write the plan")
    args = parser.parse_args(argv)

    with open(args.decision, encoding="utf-8") as handle:
        decision = json.load(handle)
    with open(args.tagged, encoding="utf-8") as handle:
        tagged = json.load(handle).get("ResourceTagMappingList", [])

    # The sweep refusing means its positive control came back empty: the question
    # was not answered. Adopting on the strength of an unanswered question is the
    # empty-result trap with a delete attached (ADR-0038 D5).
    if decision.get("verdict") == "refuse":
        print("REFUSED: the sweep could not answer, so there is nothing to adopt on")
        print(decision.get("reason", ""))
        return 2

    tags_by_arn = {
        entry.get("ResourceARN", ""): {
            tag.get("Key", ""): tag.get("Value", "") for tag in entry.get("Tags", [])
        }
        for entry in tagged
    }

    prefix = f"aws-devops-sdet-demo-{args.environment}"
    result = plan(decision.get("orphans", []), tags_by_arn, prefix)

    print(f"environment: {args.environment}")
    print(f"orphans reported by the sweep: {len(decision.get('orphans', []))}")
    for entry in result["adopt"]:
        print(f"  ADOPT        {entry['address']}  <-  {entry['import_id']}")
    for entry in result["unadoptable"]:
        print(f"  UNADOPTABLE  {entry['arn']}  ({entry['reason']})")
    if not result["adopt"] and not result["unadoptable"]:
        print("  nothing to adopt - Terraform manages everything that is alive")

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)

    # Zero even with unadoptable entries. This step exists to make the destroy
    # that follows it succeed; the run's colour is decided by the two gates at
    # the end, which are unchanged (ADR-0038 D5).
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(main(sys.argv[1:]))

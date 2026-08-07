"""Which project-tagged resources are NOT in Terraform state (ADR-0037 D4).

WHY A SEPARATE FILE INSTEAD OF MORE SHELL

A teardown that fails part way drops resources out of state: Terraform forgets
them, and every check this project owns is either scoped to a name prefix it
happens to know or asks Terraform what it manages. On 2026-08-06 an ECS cluster
survived a failed destroy that way, and the run that produced it went green on
its own verification because that step never ran at all. The account was emptied
by four manual AWS calls.

So the last thing a teardown does is compare what AWS says is TAGGED against
what Terraform says it MANAGES, and anything in the first set and not the second
fails the run. That comparison has branches - an empty answer, an ARN the state
spells differently, a control that proves nothing - and branches belong
somewhere they can be driven from a dictionary rather than from a live account.
`control.py` and `sweep.py` made the same split for the same reason.

THE CONTROL IS NOT DECORATION

`get-resources` answering NOTHING is what a clean account looks like and also
what an expired token, a wrong region and a missing IAM grant look like. So the
caller asks TWICE: once for this environment, and once for the project as a
whole, which can never legitimately be empty - the registry, the hosted zone,
the dashboard and the self-service level are permanent and all carry
`Project=aws-devops-sdet-demo`. A control that comes back empty means the
question was not answered, and an unanswered question is a refusal, never a
pass.

ARNs ARE NOT SPELLED THE SAME ON BOTH SIDES

CloudWatch log groups are the reason this is not a set intersection: the tagging
API reports `...:log-group:/aws-devops-sdet-demo/stage/app` and Terraform stores
`...:log-group:/aws-devops-sdet-demo/stage/app:*`. Matching those two literally
reports a live, managed log group as an orphan on every single teardown - a gate
that cries wolf until somebody switches it off.

TAGGED IS NOT THE SAME AS ALIVE (ADR-0037 D4, amended 2026-08-07)

The first live run of this sweep, against an account three checks had already
called empty, reported twenty-three orphans. All twenty-three were tombstones:

    22  ecs:task-definition   `destroy` DEREGISTERS revisions, it does not
                              delete them, and AWS keeps the record
                              indefinitely. They cost nothing, they accumulate
                              one per apply, and a revision with no service is
                              inert whether it is ACTIVE or not - so there is no
                              state in which one is worth acting on. Excluded by
                              TYPE, which is why the exclusion is not a status
                              check
     1  ecs:cluster INACTIVE  a deleted cluster keeps answering `describe` for a
                              while, and the tagging API keeps reporting it.
                              `list-clusters` returns ACTIVE ones only, which is
                              why the verification step never saw it and was
                              right not to

So the question is not "is it tagged and unmanaged" but "is it ALIVE, tagged and
unmanaged". Discovery comes from the tagging API; liveness is confirmed by the
service that owns the resource. Everything whose type is not named here stays
fail-closed: an unrecognised kind is reported, not excused.

What is excluded is COUNTED AND PRINTED. A silent exclusion is how a gate stops
meaning anything, and a list nobody sees cannot be argued with.
"""
from __future__ import annotations

import json
from typing import Any, Iterable


def state_identifiers(state: dict[str, Any]) -> set[str]:
    """Every `arn` and `id` Terraform holds, in both spellings.

    `terraform show -json` nests modules arbitrarily deep, so this walks the
    whole tree rather than assuming the shape of one environment. A trailing
    `:*` is recorded both with and without, because that suffix is the one
    systematic difference between the two sides.
    """
    found: set[str] = set()

    def add(value: Any) -> None:
        if not isinstance(value, str) or not value:
            return
        found.add(value)
        if value.endswith(":*"):
            found.add(value[:-2])

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("arn", "id"):
                    add(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(state)
    return found


# A resource of this type is never actionable, whatever its status. Membership
# here has to be argued from the resource's nature, not from it being noisy.
TOMBSTONE_TYPES = ("ecs:task-definition",)


def arn_type(arn: str) -> str:
    """`arn:aws:ecs:region:acct:cluster/name` -> `ecs:cluster`."""
    parts = arn.split(":", 6)
    if len(parts) < 6:
        return ""
    service = parts[2]
    tail = parts[5]
    kind = tail.split("/", 1)[0]
    return f"{service}:{kind}"


def is_alive(arn: str, active_clusters: set[str]) -> tuple[bool, str]:
    """Whether the owning service still has this, and why not when it does not.

    Only the kinds that AWS is KNOWN to keep tombstones for are asked about.
    Anything else is assumed alive, which is the fail-closed direction: an
    unrecognised kind gets reported rather than excused.
    """
    kind = arn_type(arn)
    if kind in TOMBSTONE_TYPES:
        return False, "deregistered revision, kept by AWS indefinitely"
    if kind == "ecs:cluster" and arn not in active_clusters:
        return False, "cluster is not ACTIVE"
    return True, ""


def is_managed(arn: str, identifiers: set[str]) -> bool:
    """Whether Terraform holds this resource under any spelling it uses.

    Three chances, and no more: the ARN itself, the ARN without the `:*` a log
    group carries, and the bare resource id that some resources are stored under
    (`sg-0abc`, a cluster name). Anything looser starts matching on substrings,
    and a sweep that can be talked out of a finding is not a sweep.
    """
    if arn in identifiers:
        return True
    if arn.endswith(":*") and arn[:-2] in identifiers:
        return True
    tail = arn.rsplit(":", 1)[-1]
    tail = tail.rsplit("/", 1)[-1]
    return bool(tail) and tail in identifiers


def decide_sweep(
    tagged: Iterable[dict[str, Any]],
    control: Iterable[dict[str, Any]],
    identifiers: set[str],
    active_clusters: set[str] | None = None,
) -> dict[str, Any]:
    """`refuse`, `orphans` or `clean`, in that order of precedence.

    The order matters: an unanswered question must not be reported as a clean
    account, so the control is settled before anything is counted.
    """
    # Both are materialised before anything is counted. A generator walked once
    # answers empty the second time, and empty is the one answer this file
    # exists to distrust.
    tagged_list = list(tagged)
    control_list = list(control)
    if not control_list:
        return {
            "verdict": "refuse",
            "reason": (
                "the tagging API returned nothing for the project as a whole. "
                "The permanent levels (registry, hosted zone, dashboard, "
                "self-service) are always tagged, so an empty answer means the "
                "question was not answered - expired credentials, the wrong "
                "region, or a missing tag:GetResources grant. Refusing rather "
                "than reporting an account nobody looked at as empty."
            ),
            "orphans": [],
            "tombstones": [],
        }

    clusters = active_clusters or set()
    orphans: list[str] = []
    tombstones: list[str] = []
    for arn in (r.get("ResourceARN", "") for r in tagged_list):
        if not arn:
            continue
        alive, why = is_alive(arn, clusters)
        if not alive:
            tombstones.append(f"{arn}  ({why})")
            continue
        if not is_managed(arn, identifiers):
            orphans.append(arn)

    if orphans:
        return {
            "verdict": "orphans",
            "reason": (
                f"{len(orphans)} live tagged resource(s) exist in AWS and are "
                "absent from Terraform state. A partially failed teardown drops "
                "resources out of state; these are what it left."
            ),
            "orphans": sorted(orphans),
            "tombstones": sorted(tombstones),
        }

    return {
        "verdict": "clean",
        "reason": (
            f"{len(tagged_list)} tagged resource(s): "
            f"{len(tombstones)} tombstone(s) AWS keeps and cannot act on, "
            f"{len(tagged_list) - len(tombstones)} live and all of them managed. "
            "Nothing was left behind."
        ),
        "orphans": [],
        "tombstones": sorted(tombstones),
    }


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tagged", required=True, help="get-resources for this environment")
    parser.add_argument("--control", required=True, help="get-resources for the whole project")
    parser.add_argument("--state", required=True, help="terraform show -json output")
    parser.add_argument(
        "--active-clusters",
        required=True,
        help="ecs list-clusters output. ACTIVE ones only, which is the point.",
    )
    parser.add_argument("--environment", required=True)
    args = parser.parse_args(argv)

    with open(args.tagged, encoding="utf-8") as handle:
        tagged = json.load(handle).get("ResourceTagMappingList", [])
    with open(args.control, encoding="utf-8") as handle:
        control = json.load(handle).get("ResourceTagMappingList", [])
    with open(args.state, encoding="utf-8") as handle:
        state = json.load(handle)
    with open(args.active_clusters, encoding="utf-8") as handle:
        active_clusters = set(json.load(handle).get("clusterArns", []))

    identifiers = state_identifiers(state)
    decision = decide_sweep(tagged, control, identifiers, active_clusters)

    print(f"environment: {args.environment}")
    print(f"tagged in AWS: {len(tagged)}   in Terraform state: {len(identifiers)} identifier(s)")
    print(f"control (whole project): {len(control)} resource(s)")
    print(f"ACTIVE ECS clusters in the account: {len(active_clusters)}")
    # Printed, always, and before the verdict. An exclusion nobody sees is how a
    # gate quietly stops meaning anything.
    for line in decision["tombstones"]:
        print(f"  tombstone  {line}")
    print(f"verdict: {decision['verdict']}")
    print(decision["reason"])
    for arn in decision["orphans"]:
        print(f"  ORPHAN  {arn}")

    return 0 if decision["verdict"] == "clean" else 1


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(main(sys.argv[1:]))

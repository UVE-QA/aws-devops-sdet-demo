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
        }

    orphans = [
        arn
        for arn in (r.get("ResourceARN", "") for r in tagged_list)
        if arn and not is_managed(arn, identifiers)
    ]
    if orphans:
        return {
            "verdict": "orphans",
            "reason": (
                f"{len(orphans)} tagged resource(s) exist in AWS and are absent "
                "from Terraform state. A partially failed teardown drops "
                "resources out of state; these are what it left."
            ),
            "orphans": sorted(orphans),
        }

    return {
        "verdict": "clean",
        "reason": (
            f"{len(tagged_list)} tagged resource(s), all of them managed. "
            "Nothing was left behind."
        ),
        "orphans": [],
    }


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tagged", required=True, help="get-resources for this environment")
    parser.add_argument("--control", required=True, help="get-resources for the whole project")
    parser.add_argument("--state", required=True, help="terraform show -json output")
    parser.add_argument("--environment", required=True)
    args = parser.parse_args(argv)

    with open(args.tagged, encoding="utf-8") as handle:
        tagged = json.load(handle).get("ResourceTagMappingList", [])
    with open(args.control, encoding="utf-8") as handle:
        control = json.load(handle).get("ResourceTagMappingList", [])
    with open(args.state, encoding="utf-8") as handle:
        state = json.load(handle)

    identifiers = state_identifiers(state)
    decision = decide_sweep(tagged, control, identifiers)

    print(f"environment: {args.environment}")
    print(f"tagged in AWS: {len(tagged)}   in Terraform state: {len(identifiers)} identifier(s)")
    print(f"control (whole project): {len(control)} resource(s)")
    print(f"verdict: {decision['verdict']}")
    print(decision["reason"])
    for arn in decision["orphans"]:
        print(f"  ORPHAN  {arn}")

    return 0 if decision["verdict"] == "clean" else 1


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(main(sys.argv[1:]))

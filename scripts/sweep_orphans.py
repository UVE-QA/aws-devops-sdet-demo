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

ONE CONTROL PER CHANNEL, NOT ONE CONTROL (ADR-0041 D4)

There are two discovery channels since 2026-08-08: the tagging API, and the
names the configuration declares for kinds the tagging API does not index. Each
carries its own control and each has to be non-empty on its own. Sharing one
control was right while there was one channel and is exactly wrong with two -
the loud channel would vouch for the silent one, which is this gate's own
failure mode reproduced inside it: two IAM roles were left behind precisely
because a check that could not see them reported the environment clean.

ARNs ARE NOT SPELLED THE SAME ON BOTH SIDES

CloudWatch log groups are the reason this is not a set intersection: the tagging
API reports `...:log-group:/aws-devops-sdet-demo/stage/app` and Terraform stores
`...:log-group:/aws-devops-sdet-demo/stage/app:*`. Matching those two literally
reports a live, managed log group as an orphan on every single teardown - a gate
that cries wolf until somebody switches it off.

THE TAGGING API IS DISCOVERY, NEVER A VERDICT (ADR-0037 D4, amended 2026-08-07)

It was wrong in both directions within one hour of this being written:

    too late   40 seconds into a teardown it did not report the RDS instance -
               the only billable resource in the account - because the instance
               was still `creating`
    too early  one minute after a SUCCESSFUL destroy it reported a security
               group that `describe-security-groups` answered
               `InvalidGroup.NotFound` for

The first version of this file also treated 22 deregistered task-definition
revisions and one INACTIVE cluster as orphans, in an account three other checks
had already called empty. `terraform destroy` DEREGISTERS a revision - deleting
one is not an operation it has - and AWS keeps the record indefinitely.

The second failure is the dangerous one, because it points the wrong way: it
would have reddened every teardown from its first day, and a red `destroy` job
means `release-lock` keeps the lock (ADR-0036 D2), so the public button would
have stayed shut until its TTL after every launch. A gate that is always red
gets switched off, and this one would have taken the button with it.

So the tagging API says what to LOOK AT, and the service that owns the resource
says whether it is THERE. This file never sees the second question: the caller
has already asked, and passes in what came back.

THREE ANSWERS, NOT TWO

    present       the owning service confirmed it. Compared against state
    absent        the service says no, or the kind is one that is never live.
                  Dropped and counted - the deleted resource the tagging API
                  has not caught up with, and the task-definition revision
                  nothing can ever run from
    unconfirmed   no rule for this kind, or the call itself failed. REPORTED,
                  because "I could not check" must never read as "it is gone".
                  That is the empty-result trap one level down

ARNs ARE NOT SPELLED THE SAME ON BOTH SIDES

CloudWatch log groups are the reason the state comparison is not a set
intersection: the tagging API reports `...:log-group:/aws-devops-sdet-demo/stage/app`
and Terraform stores the same group with a trailing `:*`. Matching those two
literally reports a live, managed log group as an orphan on every teardown.

WHAT IS EXCLUDED IS COUNTED AND PRINTED

A silent exclusion is how a gate stops meaning anything, and a list nobody sees
cannot be argued with.
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


# Why an empty answer from each discovery channel is a refusal rather than a
# clean account. One entry per channel, because "no answer" has a different
# cause on each and a refusal that cannot say which channel went quiet sends the
# reader to the wrong place (ADR-0041 D4).
CONTROL_WHY = {
    "tagging-api": (
        "the tagging API returned nothing for the project as a whole. The "
        "permanent levels (registry, hosted zone, dashboard, self-service) are "
        "always tagged, so an empty answer means the question was not answered - "
        "expired credentials, the wrong region, or a missing tag:GetResources "
        "grant"
    ),
    "configured-names": (
        "the configuration declared no names for the kinds the tagging API does "
        "not index. It always declares at least one, so an empty list means the "
        "declaration went missing - a renamed module, a bad parse - rather than "
        "that there is nothing to look for (ADR-0041 D4)"
    ),
}


def decide_sweep(
    tagged: Iterable[dict[str, Any]],
    controls: dict[str, Iterable[Any]],
    identifiers: set[str],
    present: Iterable[str] = (),
    unconfirmed: Iterable[str] = (),
) -> dict[str, Any]:
    """`refuse`, `orphans` or `clean`, in that order of precedence.

    The order matters: an unanswered question must not be reported as a clean
    account, so every control is settled before anything is counted.

    `controls` is one entry per DISCOVERY CHANNEL, and each has to be non-empty
    on its own. A single control was enough while the tagging API was the only
    channel; it is exactly wrong once there are two, because the loud one would
    then vouch for the silent one - which is the failure this whole gate is
    about, one level up.

    `present` and `unconfirmed` come from the caller, which asked the owning
    service. Anything in `tagged` and in neither of them is a resource the
    service says is gone - discovery had simply not caught up, or asked about a
    name nothing has created - and it is dropped without comment beyond the
    count.
    """
    # Materialised before anything is counted. A generator walked once answers
    # empty the second time, and empty is the one answer this file exists to
    # distrust.
    tagged_list = list(tagged)
    answered = {name: list(items) for name, items in controls.items()}
    present_set = set(present)
    unconfirmed_list = sorted(set(unconfirmed))

    silent = sorted(name for name, items in answered.items() if not items)
    if silent:
        return {
            "verdict": "refuse",
            "reason": (
                "; ".join(
                    CONTROL_WHY.get(name, f"the {name} channel answered nothing")
                    for name in silent
                )
                + ". Refusing rather than reporting an account nobody looked at "
                "as empty."
            ),
            "orphans": [],
            "unconfirmed": [],
            "not_present": 0,
            "silent_channels": silent,
        }

    arns = [r.get("ResourceARN", "") for r in tagged_list]
    arns = [a for a in arns if a]
    # Discovered, and not there according to the service: deleted and not yet
    # dropped from the index, a kind that is never live, or - since ADR-0041 - a
    # name the configuration will need that nothing has created, which is what a
    # finished teardown looks like. Counted rather than listed; the count is what
    # would make a sudden change visible.
    not_present = [a for a in arns if a not in present_set and a not in unconfirmed_list]

    orphans = sorted(a for a in arns if a in present_set and not is_managed(a, identifiers))

    if orphans or unconfirmed_list:
        return {
            "verdict": "orphans",
            "reason": (
                f"{len(orphans)} confirmed live resource(s) absent from "
                f"Terraform state, {len(unconfirmed_list)} that could not be "
                "checked at all. A partially failed teardown drops resources "
                "out of state; an unchecked kind is not a clean one."
            ),
            "orphans": orphans,
            "unconfirmed": unconfirmed_list,
            "not_present": len(not_present),
        }

    return {
        "verdict": "clean",
        "reason": (
            f"{len(arns)} discovered, {len(present_set & set(arns))} still there "
            f"and all of them managed, {len(not_present)} discovered and not "
            "there according to the service. Nothing was left behind."
        ),
        "orphans": [],
        "unconfirmed": [],
        "not_present": len(not_present),
    }


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tagged", required=True, help="everything discovery found")
    parser.add_argument("--control", required=True, help="get-resources for the whole project")
    # ADR-0041 D4. The second channel's own control: the names the configuration
    # declares for kinds the tagging API does not index. Required, because a
    # channel that can be left out silently is a channel that will be.
    parser.add_argument(
        "--declared", required=True, help="{names: [...]} from adopt_orphans.py --unindexed"
    )
    parser.add_argument("--state", required=True, help="terraform show -json output")
    parser.add_argument(
        "--present",
        required=True,
        help="{present, unconfirmed}: what the owning services answered",
    )
    parser.add_argument("--environment", required=True)
    # ADR-0038 D2. The adoption step runs this script and adopts exactly what it
    # reports, so the two can never disagree about what an orphan is. Optional,
    # because the gate itself has no use for it.
    parser.add_argument("--json", help="also write the decision here, for adoption")
    args = parser.parse_args(argv)

    with open(args.tagged, encoding="utf-8") as handle:
        tagged = json.load(handle).get("ResourceTagMappingList", [])
    with open(args.control, encoding="utf-8") as handle:
        control = json.load(handle).get("ResourceTagMappingList", [])
    with open(args.declared, encoding="utf-8") as handle:
        declared = json.load(handle).get("names", [])
    with open(args.state, encoding="utf-8") as handle:
        state = json.load(handle)
    with open(args.present, encoding="utf-8") as handle:
        confirmed = json.load(handle)

    identifiers = state_identifiers(state)
    decision = decide_sweep(
        tagged,
        {"tagging-api": control, "configured-names": declared},
        identifiers,
        confirmed.get("present", []),
        confirmed.get("unconfirmed", []),
    )

    print(f"environment: {args.environment}")
    print(f"discovered in AWS: {len(tagged)}   in Terraform state: {len(identifiers)} identifier(s)")
    print(f"control (whole project): {len(control)} resource(s)")
    print(f"control (names the configuration declares): {len(declared)}")
    print(f"confirmed present: {len(confirmed.get('present', []))}   "
          f"tagged but not there: {decision['not_present']}")
    print(f"verdict: {decision['verdict']}")
    print(decision["reason"])
    for arn in decision["orphans"]:
        print(f"  ORPHAN  {arn}")
    # Printed separately, always. "I could not check" and "it is there" are
    # different claims and must not share a line.
    for arn in decision["unconfirmed"]:
        print(f"  UNCONFIRMED  {arn}  (no existence rule for this kind)")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(decision, handle, indent=2)

    return 0 if decision["verdict"] == "clean" else 1


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(main(sys.argv[1:]))

"""One ARN parser, for the shell and for Python (ADR-0038, amended 2026-08-07).

WHY THIS FILE EXISTS AT ALL

`scripts/sweep-orphans.sh` had its own parser, four lines of shell, and it read
the resource kind as `${id%%/*}` - everything up to the first SLASH. That is
right for `security-group/sg-0abc` and wrong for every ARN whose resource part
is separated by a COLON, because the whole rest of the string comes back as the
kind:

    arn:aws:rds:...:db:aws-devops-sdet-demo-stage-db
        case key = rds:db:aws-devops-sdet-demo-stage-db     matches nothing

So four of the thirteen `case` arms in that script - `rds:db`, `rds:subgrp`,
`logs:log-group` and `secretsmanager:secret` - had never once been reached. Every
resource of those kinds came back `unconfirmed`, which is the honest answer to a
question the script could not ask, and which reads in a log exactly like a kind
nobody had thought about.

THE DEFECT WAS INVISIBLE ON AN EMPTY ACCOUNT, WHICH IS WHERE IT WAS TESTED

Nothing of those kinds is tagged once an environment is gone, so the arms never
fired, and the gate was green. It only shows itself when there is something to
find. On 2026-08-07 a cancelled launch left an RDS instance alive: the sweep
reported it `unconfirmed`, the adoption step correctly refused to act on a
resource nobody had confirmed, the destroy died on the subnet group it was
holding, and the remainder needed a human again.

It also corrects a diagnosis. ADR-0037's amendment recorded that the sweep
"did not report the RDS instance because it was still creating". The instance
was never reportable at all; the timing was a coincidence that fitted.

WHAT THE SHELL GETS

    $ python3 scripts/arns.py arn:aws:rds:us-west-2:1234:db:demo-db
    rds:db<TAB>demo-db

One definition on both hosts, and `tests/unit/test_arns.py` asserts that every
`case` arm in `sweep-orphans.sh` is reachable from a real ARN of that kind - the
check that would have caught this.
"""
from __future__ import annotations


def parse(arn: str) -> tuple[str, str, str]:
    """`arn` -> (service, kind, name).

    The resource section separates its kind from its name with EITHER a colon or
    a slash, and AWS uses both, sometimes for two kinds in the same service. So
    the split is on whichever comes first, and never on one of them alone.

        arn:aws:ec2:...:security-group/sg-0abc   -> ec2,  security-group,  sg-0abc
        arn:aws:rds:...:db:demo-db               -> rds,  db,              demo-db
        arn:aws:logs:...:log-group:/demo/app     -> logs, log-group,       /demo/app
        arn:aws:ecs:...:service/cluster/app      -> ecs,  service,         cluster/app

    A malformed ARN yields empty strings rather than an exception: the caller is
    a teardown, and a parser that raises there turns one unreadable ARN into a
    step that reports nothing at all.
    """
    parts = arn.split(":", 5)
    if len(parts) < 6:
        return "", "", ""
    service, rest = parts[2], parts[5]

    cut = min(
        (i for i in (rest.find(":"), rest.find("/")) if i >= 0),
        default=-1,
    )
    if cut < 0:
        return service, rest, ""
    return service, rest[:cut], rest[cut + 1 :]


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: arns.py <arn>", file=__import__("sys").stderr)
        return 2
    service, kind, name = parse(argv[0])
    if not service:
        return 2
    print(f"{service}:{kind}\t{name}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(main(sys.argv[1:]))

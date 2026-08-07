"""The ARN parser, and the test that would have caught four dead `case` arms.

`sweep-orphans.sh` computed a resource's kind as everything up to the first
SLASH. AWS separates the kind from the name with a slash OR a colon, and for the
colon ones the whole rest of the ARN came back as the kind — so `rds:db`,
`rds:subgrp`, `logs:log-group` and `secretsmanager:secret` never matched
anything. Those resources answered `unconfirmed`, which is the truthful answer
to a question the script could not ask.

Nothing caught it for a day because it is invisible on an empty account: no RDS
instance is tagged once the environment is gone, so the arm never runs and the
gate is green. It surfaced on 2026-08-07 when a cancelled launch left an
instance alive and the destroy died on the subnet group it was holding.

`test_every_case_arm_in_the_sweep_is_reachable` is the missing check, and it is
deliberately written against the SHELL rather than against a list kept here: a
new arm added to the script with no ARN that can reach it fails this test.
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import arns  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
SWEEP = REPO / "scripts/sweep-orphans.sh"
ACCOUNT = "111122223333"

# One real ARN per kind the sweep claims to know. Real, not shaped: the point of
# the exercise is that a plausible-looking ARN was what everybody had in mind
# while the actual ones went unmatched.
SAMPLES = {
    "ec2:security-group": f"arn:aws:ec2:us-west-2:{ACCOUNT}:security-group/sg-0abc",
    "ec2:subnet": f"arn:aws:ec2:us-west-2:{ACCOUNT}:subnet/subnet-0abc",
    "ec2:vpc": f"arn:aws:ec2:us-west-2:{ACCOUNT}:vpc/vpc-0abc",
    "ec2:internet-gateway": f"arn:aws:ec2:us-west-2:{ACCOUNT}:internet-gateway/igw-0abc",
    "ec2:route-table": f"arn:aws:ec2:us-west-2:{ACCOUNT}:route-table/rtb-0abc",
    "ec2:elastic-ip": f"arn:aws:ec2:us-west-2:{ACCOUNT}:elastic-ip/eipalloc-0abc",
    "ecs:task-definition": f"arn:aws:ecs:us-west-2:{ACCOUNT}:task-definition/demo-app:21",
    "ecs:cluster": f"arn:aws:ecs:us-west-2:{ACCOUNT}:cluster/demo-cluster",
    "ecs:service": f"arn:aws:ecs:us-west-2:{ACCOUNT}:service/demo-cluster/demo-app",
    "rds:db": f"arn:aws:rds:us-west-2:{ACCOUNT}:db:demo-db",
    "rds:subgrp": f"arn:aws:rds:us-west-2:{ACCOUNT}:subgrp:demo-db-subnet-group",
    "elasticloadbalancing:loadbalancer": (
        f"arn:aws:elasticloadbalancing:us-west-2:{ACCOUNT}:loadbalancer/app/demo-alb/50dc6c49"
    ),
    "elasticloadbalancing:targetgroup": (
        f"arn:aws:elasticloadbalancing:us-west-2:{ACCOUNT}:targetgroup/demo-tg/73e2d6bc"
    ),
    "elasticloadbalancing:listener": (
        f"arn:aws:elasticloadbalancing:us-west-2:{ACCOUNT}"
        ":listener/app/demo-alb/9e6accf78976708a/6070fae5a667a395"
    ),
    "cloudwatch:alarm": f"arn:aws:cloudwatch:us-west-2:{ACCOUNT}:alarm:demo-http-5xx",
    "logs:log-group": f"arn:aws:logs:us-west-2:{ACCOUNT}:log-group:/aws-devops-sdet-demo/stage/app",
    "secretsmanager:secret": (
        f"arn:aws:secretsmanager:us-west-2:{ACCOUNT}:secret:demo-db-credentials-AbCdEf"
    ),
}


def key(arn: str) -> str:
    service, kind, _ = arns.parse(arn)
    return f"{service}:{kind}"


def name(arn: str) -> str:
    return arns.parse(arn)[2]


# ---------------------------------------------------------------------------
# The two separators, which is the whole of it.
# ---------------------------------------------------------------------------
def test_a_slash_separated_arn():
    assert arns.parse(SAMPLES["ec2:security-group"]) == ("ec2", "security-group", "sg-0abc")


def test_a_colon_separated_arn_is_not_read_as_one_long_kind():
    """The defect, stated as an assertion. This is what returned
    `rds:db:demo-db` and matched nothing."""
    assert arns.parse(SAMPLES["rds:db"]) == ("rds", "db", "demo-db")


def test_a_log_group_name_is_a_path_and_keeps_its_leading_slash():
    assert arns.parse(SAMPLES["logs:log-group"]) == (
        "logs",
        "log-group",
        "/aws-devops-sdet-demo/stage/app",
    )


def test_an_ecs_service_keeps_its_cluster():
    assert name(SAMPLES["ecs:service"]) == "demo-cluster/demo-app"


def test_a_task_definition_keeps_its_revision():
    """`demo-app:21` — the colon here is inside the NAME, after a slash split."""
    assert arns.parse(SAMPLES["ecs:task-definition"]) == (
        "ecs",
        "task-definition",
        "demo-app:21",
    )


def test_a_malformed_arn_answers_empty_rather_than_raising():
    """A teardown must not lose a whole step to one unreadable ARN."""
    assert arns.parse("not-an-arn") == ("", "", "")
    assert arns.parse("") == ("", "", "")


def test_an_arn_with_no_resource_name_keeps_its_kind():
    assert arns.parse("arn:aws:s3:::my-bucket") == ("s3", "my-bucket", "")


# ---------------------------------------------------------------------------
# The check that was missing.
# ---------------------------------------------------------------------------
def case_arms() -> list[str]:
    """Every `<service>:<kind>)` pattern in the sweep's `confirm_exists`.

    Read out of the script rather than listed here, so an arm added tomorrow
    without a reachable ARN fails this test rather than joining the four that
    were already dead.
    """
    text = SWEEP.read_text(encoding="utf-8")
    body = text[text.index("confirm_exists()") : text.index("if [ -n \"${BREAK_TEST_PRESENT_JSON")]
    return re.findall(r"^    ([a-z][a-z0-9-]*:[a-z][a-z0-9-]*)\)", body, re.M)


def test_the_sweep_still_has_arms_to_check():
    """A positive control. An empty list would pass the test below silently."""
    assert len(case_arms()) >= 15


def test_the_kinds_a_live_environment_has():
    """Both were seen `unconfirmed` on 2026-08-07, in the first sweep that ever
    ran against a live environment rather than the remains of one."""
    assert arns.parse(SAMPLES["cloudwatch:alarm"])[:2] == ("cloudwatch", "alarm")
    assert name(SAMPLES["cloudwatch:alarm"]) == "demo-http-5xx"
    assert arns.parse(SAMPLES["elasticloadbalancing:listener"])[1] == "listener"


def test_every_case_arm_in_the_sweep_is_reachable():
    """Four of these were dead for a day, and the gate stayed green."""
    unreachable = []
    for arm in case_arms():
        sample = SAMPLES.get(arm)
        if sample is None:
            unreachable.append(f"{arm}: no ARN in SAMPLES can reach this arm")
        elif key(sample) != arm:
            unreachable.append(f"{arm}: a real ARN of this kind parses as {key(sample)}")
    assert not unreachable, "\n".join(unreachable)


def test_every_sample_is_an_arm():
    """The other direction: a sample nobody handles is a rule that went missing."""
    arms = set(case_arms())
    assert not [k for k in SAMPLES if k not in arms]

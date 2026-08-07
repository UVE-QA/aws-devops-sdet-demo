"""The adoption map's branches, and the two ways it can go stale (ADR-0038).

A cancelled apply leaves resources outside Terraform state, and a teardown
cannot remove what it does not own. Adoption imports them first. The part with
branches - which ARN becomes which address - is a pure function, because the
alternative way to exercise it is to cancel a launch and wait out a TTL.

TWO OF THESE TESTS ARE NOT ABOUT BEHAVIOUR AT ALL

`test_every_address_exists_in_the_configuration` and
`test_no_mapped_resource_is_counted` read the Terraform sources. A map that
still compiles while the module it names has been renamed is the failure mode
here: nothing would notice until a teardown that was already failing produced
an unfamiliar `terraform import` error. They are the reason the map is allowed
to be a hand-written table.
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import adopt_orphans  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
ACCOUNT = "111122223333"
PREFIX = "aws-devops-sdet-demo-stage"

RDS = f"arn:aws:rds:us-west-2:{ACCOUNT}:db:{PREFIX}-db"
SUBGRP = f"arn:aws:rds:us-west-2:{ACCOUNT}:subgrp:{PREFIX}-db-subnet-group"
CLUSTER = f"arn:aws:ecs:us-west-2:{ACCOUNT}:cluster/{PREFIX}-cluster"
SERVICE = f"arn:aws:ecs:us-west-2:{ACCOUNT}:service/{PREFIX}-cluster/{PREFIX}-app"
ALB = f"arn:aws:elasticloadbalancing:us-west-2:{ACCOUNT}:loadbalancer/app/{PREFIX}-alb/50dc6c495c0c9188"
TG = f"arn:aws:elasticloadbalancing:us-west-2:{ACCOUNT}:targetgroup/{PREFIX}-tg/73e2d6bc24d8a067"
APP_SG = f"arn:aws:ec2:us-west-2:{ACCOUNT}:security-group/sg-0app"
RDS_SG = f"arn:aws:ec2:us-west-2:{ACCOUNT}:security-group/sg-0rds"
VPC = f"arn:aws:ec2:us-west-2:{ACCOUNT}:vpc/vpc-0abc"
SUBNET = f"arn:aws:ec2:us-west-2:{ACCOUNT}:subnet/subnet-0abc"
LOG_GROUP = f"arn:aws:logs:us-west-2:{ACCOUNT}:log-group:/aws-devops-sdet-demo/stage/app"
SECRET = f"arn:aws:secretsmanager:us-west-2:{ACCOUNT}:secret:{PREFIX}-db-credentials-AbCdEf"
WEIRD = f"arn:aws:kinesis:us-west-2:{ACCOUNT}:stream/{PREFIX}-events"


def one(arn: str, name: str | None = None) -> dict:
    tags = {"Name": name} if name else {}
    return adopt_orphans.plan_one(arn, tags, PREFIX)


# ---------------------------------------------------------------------------
# The kinds that stall a destroy. Each of these was alive and unmanaged in at
# least one real cancelled launch, or holds something that was.
# ---------------------------------------------------------------------------
def test_the_rds_instance_that_held_the_subnet_group():
    """The exact pair that failed the teardown twice on 2026-08-07."""
    assert one(RDS) == {
        "arn": RDS,
        "verdict": "adopt",
        "address": "module.rds.aws_db_instance.this",
        "import_id": f"{PREFIX}-db",
    }


def test_the_subnet_group_it_held():
    assert one(SUBGRP)["address"] == "module.rds.aws_db_subnet_group.this"


def test_the_cluster_that_survived_a_teardown():
    assert one(CLUSTER) == {
        "arn": CLUSTER,
        "verdict": "adopt",
        "address": "module.ecs.aws_ecs_cluster.this",
        "import_id": f"{PREFIX}-cluster",
    }


def test_an_ecs_service_is_imported_as_cluster_slash_service():
    """Terraform's own import id for a service, which is not its ARN."""
    entry = one(SERVICE)
    assert entry["address"] == "module.ecs.aws_ecs_service.app"
    assert entry["import_id"] == f"{PREFIX}-cluster/{PREFIX}-app"


def test_a_load_balancer_is_imported_by_arn():
    entry = one(ALB)
    assert entry["address"] == "module.alb.aws_lb.this"
    assert entry["import_id"] == ALB


def test_a_target_group_is_told_apart_from_the_load_balancer():
    assert one(TG)["address"] == "module.alb.aws_lb_target_group.app"


def test_a_log_group_is_named_by_a_path_rather_than_a_prefix():
    entry = one(LOG_GROUP)
    assert entry["address"] == "module.observability.aws_cloudwatch_log_group.app"
    assert entry["import_id"] == "/aws-devops-sdet-demo/stage/app"


# ---------------------------------------------------------------------------
# The two families whose ARN cannot name them.
# ---------------------------------------------------------------------------
def test_security_groups_are_told_apart_by_their_name_tag():
    """`sg-0app` and `sg-0rds` are indistinguishable without the tag."""
    assert one(APP_SG, f"{PREFIX}-app-sg")["address"] == "module.ecs.aws_security_group.app"
    assert one(RDS_SG, f"{PREFIX}-rds-sg")["address"] == "module.rds.aws_security_group.rds"


def test_a_secret_is_matched_on_its_tag_not_its_arn():
    """AWS appends six random characters to a secret's ARN. The tag has none."""
    entry = one(SECRET, f"{PREFIX}-db-credentials")
    assert entry["address"] == "module.rds.aws_secretsmanager_secret.db"
    assert entry["import_id"] == SECRET


def test_a_security_group_without_a_name_tag_is_not_guessed():
    entry = one(APP_SG)
    assert entry["verdict"] == "unadoptable"
    assert entry["reason"] == adopt_orphans.NO_NAME_TAG


# ---------------------------------------------------------------------------
# The refusals. Each one is a resource that stays alive and red rather than
# being adopted into the wrong place.
# ---------------------------------------------------------------------------
def test_a_kind_with_no_rule_is_reported_rather_than_skipped():
    entry = one(WEIRD)
    assert entry["verdict"] == "unadoptable"
    assert entry["reason"] == adopt_orphans.NO_RULE


def test_a_counted_subnet_says_WHY_it_is_unadoptable():
    """"Counted" and "nobody thought about it" must not share a message.

    The Name tag carries an availability zone, and the zone-to-index mapping
    lives in a `data` source read at apply time. Reporting that as "no rule"
    would read like an oversight and invite someone to add one.
    """
    entry = one(SUBNET, f"{PREFIX}-public-us-west-2a")
    assert entry["verdict"] == "unadoptable"
    assert entry["reason"] == adopt_orphans.INDEXED


def test_a_name_from_another_environment_matches_nothing():
    """`prod-db` under a stage prefix keeps its whole name, which maps nowhere."""
    entry = adopt_orphans.plan_one(
        f"arn:aws:rds:us-west-2:{ACCOUNT}:db:aws-devops-sdet-demo-prod-db", {}, PREFIX
    )
    assert entry["verdict"] == "unadoptable"


def test_two_security_groups_with_one_name_tag_adopt_neither():
    """A coin toss is not a mapping. Both are reported; the sweep fails on them.

    Reachable for real, and only for the tag-keyed kinds: an ARN is unique, a
    Name tag is not. A group left by an earlier cycle carries the same tag as
    the one this cycle created, and nothing in the tag says which is which.
    """
    other = f"arn:aws:ec2:us-west-2:{ACCOUNT}:security-group/sg-0old"
    tags = {APP_SG: {"Name": f"{PREFIX}-app-sg"}, other: {"Name": f"{PREFIX}-app-sg"}}
    result = adopt_orphans.plan([APP_SG, other], tags, PREFIX)
    assert result["adopt"] == []
    assert sorted(e["arn"] for e in result["unadoptable"]) == sorted([APP_SG, other])
    assert all(adopt_orphans.DUPLICATE in e["reason"] for e in result["unadoptable"])
    # The address is named in the message: a duplicate nobody can locate is a
    # log line, not a finding.
    assert all(
        "module.ecs.aws_security_group.app" in e["reason"]
        for e in result["unadoptable"]
    )


def test_an_empty_account_plans_nothing():
    assert adopt_orphans.plan([], {}, PREFIX) == {"adopt": [], "unadoptable": []}


def test_a_whole_cancelled_launch_maps_the_way_the_teardown_needs():
    """The six orphans of 2026-08-07, plus the two that were never adoptable."""
    tags = {
        APP_SG: {"Name": f"{PREFIX}-app-sg"},
        RDS_SG: {"Name": f"{PREFIX}-rds-sg"},
        VPC: {"Name": f"{PREFIX}-vpc"},
        SUBNET: {"Name": f"{PREFIX}-public-us-west-2a"},
    }
    result = adopt_orphans.plan(
        [RDS, CLUSTER, APP_SG, RDS_SG, VPC, SUBNET, WEIRD], tags, PREFIX
    )
    assert sorted(e["address"] for e in result["adopt"]) == [
        "module.ecs.aws_ecs_cluster.this",
        "module.ecs.aws_security_group.app",
        "module.network.aws_vpc.this",
        "module.rds.aws_db_instance.this",
        "module.rds.aws_security_group.rds",
    ]
    assert sorted(e["arn"] for e in result["unadoptable"]) == sorted([SUBNET, WEIRD])


# ---------------------------------------------------------------------------
# The two tests that read Terraform rather than Python.
# ---------------------------------------------------------------------------
def module_sources() -> dict[str, pathlib.Path]:
    """`module "rds" { source = "../../modules/rds" }` -> {rds: infra/modules/rds}.

    Read from the environment that is actually wired up, not assumed from the
    directory listing: a module present on disk and not referenced would pass a
    check that only looked at `infra/modules`.
    """
    text = (REPO / "infra/envs/stage/main.tf").read_text(encoding="utf-8")
    found = {}
    for name, source in re.findall(
        r'module\s+"([^"]+)"\s*\{[^}]*?source\s*=\s*"([^"]+)"', text, re.S
    ):
        found[name] = (REPO / "infra/envs/stage" / source).resolve()
    return found


def resource_block(directory: pathlib.Path, kind: str, name: str) -> str | None:
    """The text of one `resource "<kind>" "<name>" { ... }`, or None."""
    for path in sorted(directory.glob("*.tf")):
        text = path.read_text(encoding="utf-8")
        match = re.search(
            r'resource\s+"%s"\s+"%s"\s*\{(.*?)\n\}' % (re.escape(kind), re.escape(name)),
            text,
            re.S,
        )
        if match:
            return match.group(1)
    return None


def mapped_addresses() -> list[str]:
    return sorted(
        {
            address
            for rule in adopt_orphans.RULES.values()
            for address in rule.addresses.values()
        }
    )


def test_every_address_exists_in_the_configuration():
    """A renamed module or resource reddens here, not during a failing teardown."""
    sources = module_sources()
    missing = []
    for address in mapped_addresses():
        _, module, kind, name = address.split(".")
        directory = sources.get(module)
        if directory is None:
            missing.append(f"{address}: no module '{module}' in infra/envs/stage")
        elif resource_block(directory, kind, name) is None:
            missing.append(f'{address}: no resource "{kind}" "{name}" in {directory.name}')
    assert not missing, "\n".join(missing)


def test_no_mapped_resource_is_counted():
    """`count` or `for_each` makes the address an index this map cannot supply.

    Adding either to a mapped resource without noticing would produce imports
    into an address that does not exist. The subnets are already excluded for
    exactly this reason; this stops the exclusion from silently becoming wrong.
    """
    sources = module_sources()
    counted = []
    for address in mapped_addresses():
        _, module, kind, name = address.split(".")
        body = resource_block(sources[module], kind, name) or ""
        # EXACTLY two spaces: a resource-level attribute. `for_each` also
        # appears four spaces in, inside a `dynamic` block - the ALB security
        # group has one - and that is not a count on the resource. The first
        # version of this test read the ALB group as indexed and was measuring
        # its own regex. Canonical indentation is safe to rely on here because
        # `make tf-fmt` is a gate.
        if re.search(r"^  (count|for_each)\s*=", body, re.M):
            counted.append(address)
    assert not counted, f"mapped but indexed: {counted}"

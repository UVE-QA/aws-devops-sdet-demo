"""The orphan sweep's branches, including the three that look identical in a log.

ADR-0037 D4, as amended twice on 2026-08-07 by its own first runs. A teardown
that fails part way drops resources out of Terraform state, and every other
check in this project asks either Terraform or a name prefix - so the resource
nobody manages is the one nobody looks for. On 2026-08-06 an ECS cluster
survived exactly that way.

Two things this file exists to keep straight, both learned the same night:

  an unanswered question is not a clean account. An empty control, a kind with
  no existence rule, a `describe` that failed - none of them mean "gone", and
  all of them look like it in a log

  the tagging API is not a verdict. It missed an RDS instance that was still
  creating, and it reported a security group a minute after AWS had deleted it.
  The second would have reddened every teardown from its first day, and a red
  destroy keeps the lock (ADR-0036 D2), so the public button would have stayed
  shut until its TTL after every launch
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import sweep_orphans  # noqa: E402

ACCOUNT = "111122223333"
CLUSTER = f"arn:aws:ecs:us-west-2:{ACCOUNT}:cluster/aws-devops-sdet-demo-stage-cluster"
LOG_GROUP = f"arn:aws:logs:us-west-2:{ACCOUNT}:log-group:/aws-devops-sdet-demo/stage/app"
SG = f"arn:aws:ec2:us-west-2:{ACCOUNT}:security-group/sg-0abc"
PERMANENT = f"arn:aws:ecr:us-west-2:{ACCOUNT}:repository/aws-devops-sdet-demo-app"
WEIRD = f"arn:aws:kinesis:us-west-2:{ACCOUNT}:stream/aws-devops-sdet-demo-stage"


def tagged(*arns: str) -> list[dict]:
    return [{"ResourceARN": arn, "Tags": []} for arn in arns]


def state(*values: str) -> dict:
    """A state document shaped like `terraform show -json`, nested on purpose."""
    return {
        "values": {
            "root_module": {
                "child_modules": [
                    {
                        "resources": [
                            {"address": f"r{i}", "values": {"arn": value, "id": value}}
                            for i, value in enumerate(values)
                        ]
                    }
                ]
            }
        }
    }


def decide(tagged_list, control, state_doc, present=None, unconfirmed=()):
    """`present` defaults to everything tagged - the pre-amendment assumption."""
    if present is None:
        present = [r["ResourceARN"] for r in tagged_list]
    return sweep_orphans.decide_sweep(
        tagged_list,
        control,
        sweep_orphans.state_identifiers(state_doc),
        present,
        unconfirmed,
    )


# ------------------------------------------------------------------ refusals
def test_an_empty_control_refuses_rather_than_reporting_a_clean_account():
    """Zero tagged resources and zero control is NOT clean."""
    decision = decide(tagged(), tagged(), state())
    assert decision["verdict"] == "refuse"
    assert "not answered" in decision["reason"]


def test_an_empty_control_refuses_even_when_orphans_were_found():
    """Order of precedence: an unanswered question is settled first.

    If the control is empty the environment answer cannot be trusted either, so
    reporting its contents as findings would dress an unknown up as a result.
    """
    decision = decide(tagged(CLUSTER), tagged(), state())
    assert decision["verdict"] == "refuse"
    assert decision["orphans"] == []


# --------------------------------------------------- the tagging API is stale
def test_a_resource_the_service_says_is_gone_is_not_an_orphan():
    """2026-08-07, one minute after a SUCCESSFUL destroy.

    `get-resources` still listed the VPC's default security group;
    `describe-security-groups` answered InvalidGroup.NotFound for the same id.
    Believing the first would have reddened every teardown from that day on -
    and a red destroy job keeps the launch lock, so the public button would have
    stayed shut until its TTL after every single launch. The gate would have
    been switched off within a week, taking the button with it.
    """
    decision = decide(tagged(SG), tagged(PERMANENT), state(), present=[])
    assert decision["verdict"] == "clean"
    assert decision["stale"] == 1


def test_the_same_arn_is_an_orphan_once_the_service_confirms_it():
    """The identical input, one answer different, and the verdict flips."""
    decision = decide(tagged(SG), tagged(PERMANENT), state(), present=[SG])
    assert decision["verdict"] == "orphans"
    assert decision["orphans"] == [SG]


# --------------------------------------------------------------- unconfirmed
def test_a_kind_with_no_existence_rule_is_reported_not_excused():
    """"I could not check" must never read as "it is gone".

    The alternative is a sweep that quietly stops covering whatever AWS adds
    next, and reports it as a pass.
    """
    decision = decide(tagged(WEIRD), tagged(PERMANENT), state(), present=[], unconfirmed=[WEIRD])
    assert decision["verdict"] == "orphans"
    assert decision["unconfirmed"] == [WEIRD]
    assert decision["orphans"] == []


def test_unconfirmed_alone_is_enough_to_fail_even_with_nothing_else_wrong():
    decision = decide(
        tagged(WEIRD, SG), tagged(PERMANENT), state(SG), present=[SG], unconfirmed=[WEIRD]
    )
    assert decision["verdict"] == "orphans"
    assert decision["orphans"] == []
    assert decision["unconfirmed"] == [WEIRD]


# ------------------------------------------------------------------- orphans
def test_a_confirmed_resource_absent_from_state_is_an_orphan():
    decision = decide(tagged(CLUSTER), tagged(PERMANENT), state())
    assert decision["verdict"] == "orphans"
    assert decision["orphans"] == [CLUSTER]


def test_the_managed_ones_are_not_reported_beside_the_orphan():
    decision = decide(tagged(CLUSTER, SG), tagged(PERMANENT), state(SG))
    assert decision["orphans"] == [CLUSTER]


def test_a_permanent_level_is_not_swept_because_it_is_never_asked_about():
    """The environment query carries `Environment=stage`; the control does not.

    The permanent levels are tagged `shared`, `dns`, `self-service` and are
    absent from the first list by construction rather than by an exception this
    file would have to maintain.
    """
    decision = decide(tagged(), tagged(PERMANENT), state())
    assert decision["verdict"] == "clean"


# ------------------------------------------------------------------- matching
def test_a_log_group_is_managed_despite_the_colon_star():
    """Terraform stores `...:log-group:/name:*`; the tagging API drops the `:*`.

    Matching the two literally reports a live, managed log group as an orphan on
    every teardown - a gate that fires on nothing until somebody turns it off.
    """
    decision = decide(tagged(LOG_GROUP), tagged(PERMANENT), state(LOG_GROUP + ":*"))
    assert decision["verdict"] == "clean"


def test_a_resource_stored_under_its_bare_id_is_managed():
    """`aws_security_group.id` is `sg-0abc`, not the ARN."""
    decision = decide(tagged(SG), tagged(PERMANENT), state("sg-0abc"))
    assert decision["verdict"] == "clean"


def test_matching_does_not_fall_back_to_a_substring():
    """A sweep that can be talked out of a finding is not a sweep."""
    decision = decide(
        tagged(CLUSTER), tagged(PERMANENT), state("aws-devops-sdet-demo-stage")
    )
    assert decision["verdict"] == "orphans"


def test_state_identifiers_walks_nested_modules():
    assert CLUSTER in sweep_orphans.state_identifiers(state(CLUSTER))


def test_state_identifiers_ignores_empty_and_non_string_values():
    doc = {"values": {"root_module": {"resources": [{"values": {"arn": "", "id": 7}}]}}}
    assert sweep_orphans.state_identifiers(doc) == set()


# ----------------------------------------------------------------------- cli
def test_the_cli_exit_code_is_the_verdict(tmp_path):
    """Measured from the process, not from the dictionary it returns."""

    def write(name: str, payload) -> str:
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    argv = [
        "--tagged", write("tagged.json", {"ResourceTagMappingList": tagged(CLUSTER)}),
        "--control", write("control.json", {"ResourceTagMappingList": tagged(PERMANENT)}),
        "--state", write("state.json", state()),
        "--present", write("present.json", {"present": [CLUSTER], "unconfirmed": []}),
        "--environment", "stage",
    ]
    assert sweep_orphans.main(argv) == 1

    argv[7] = write("gone.json", {"present": [], "unconfirmed": []})
    assert sweep_orphans.main(argv) == 0

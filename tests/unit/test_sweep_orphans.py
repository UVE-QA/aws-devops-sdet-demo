"""The orphan sweep's branches, including the two that look identical in a log.

ADR-0037 D4. A teardown that fails part way drops resources out of Terraform
state, and every other check in this project asks either Terraform or a name
prefix - so the resource nobody manages is the one nobody looks for. On
2026-08-06 an ECS cluster survived exactly that way.

The branch worth the most here is `refuse`. An account with nothing left and an
account nobody was able to ask both print zero resources, and the second one has
been mistaken for the first twice in this project's history: once with an
expired SSO token printing nine empty lines, once with `gh run view` printing
nothing for a run that had two failed steps. So the control is asserted before
the count, and its absence is a refusal rather than a pass.
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


def decide(tagged_list, control, state_doc):
    return sweep_orphans.decide_sweep(
        tagged_list, control, sweep_orphans.state_identifiers(state_doc)
    )


# ------------------------------------------------------------------ refusals
def test_an_empty_control_refuses_rather_than_reporting_a_clean_account():
    """The whole point. Zero tagged resources and zero control is NOT clean."""
    decision = decide(tagged(), tagged(), state())
    assert decision["verdict"] == "refuse"
    assert "not answered" in decision["reason"]


def test_an_empty_control_refuses_even_when_orphans_were_found():
    """Order of precedence: an unanswered question is settled first.

    If the control is empty the environment answer cannot be trusted either, so
    reporting its contents as findings would be dressing up an unknown as a
    result.
    """
    decision = decide(tagged(CLUSTER), tagged(), state())
    assert decision["verdict"] == "refuse"
    assert decision["orphans"] == []


# ------------------------------------------------------------------- orphans
def test_a_resource_absent_from_state_is_an_orphan():
    decision = decide(tagged(CLUSTER), tagged(PERMANENT), state())
    assert decision["verdict"] == "orphans"
    assert decision["orphans"] == [CLUSTER]


def test_the_managed_ones_are_not_reported_beside_the_orphan():
    decision = decide(tagged(CLUSTER, SG), tagged(PERMANENT), state(SG))
    assert decision["orphans"] == [CLUSTER]


def test_a_permanent_level_is_not_swept_because_it_is_never_asked_about():
    """The environment query carries `Environment=stage`; the control does not.

    The permanent levels are tagged `shared`, `dns`, `self-service` and are
    therefore absent from the first list by construction rather than by an
    exception this file would have to maintain.
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
    """A sweep that can be talked out of a finding is not a sweep.

    `aws-devops-sdet-demo-stage-cluster` appears inside the orphan's ARN, and a
    looser matcher would let any state value containing it clear the finding.
    """
    decision = decide(
        tagged(CLUSTER), tagged(PERMANENT), state("aws-devops-sdet-demo-stage")
    )
    assert decision["verdict"] == "orphans"


def test_state_identifiers_walks_nested_modules():
    identifiers = sweep_orphans.state_identifiers(state(CLUSTER))
    assert CLUSTER in identifiers


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
        "--environment", "stage",
    ]
    assert sweep_orphans.main(argv) == 1

    argv[1] = write("empty.json", {"ResourceTagMappingList": []})
    assert sweep_orphans.main(argv) == 0

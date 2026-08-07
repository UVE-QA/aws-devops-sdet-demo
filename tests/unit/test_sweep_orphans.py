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


TASK_DEF = f"arn:aws:ecs:us-west-2:{ACCOUNT}:task-definition/aws-devops-sdet-demo-stage-app:21"


def decide(tagged_list, control, state_doc, active_clusters=(CLUSTER,)):
    return sweep_orphans.decide_sweep(
        tagged_list,
        control,
        sweep_orphans.state_identifiers(state_doc),
        set(active_clusters),
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
# ---------------------------------------------------------------- tombstones
def test_the_first_live_run_in_full():
    """2026-08-07, and the reason D4 was amended before it had ever been trusted.

    An account that a destroy, its verification and a manual check had all
    called empty answered with twenty-three tagged resources. Every one was
    something AWS keeps and nobody can act on: the ECS cluster had been deleted
    and was still answering `describe`, and the twenty-two task-definition
    revisions had been deregistered rather than deleted, which is the only thing
    `terraform destroy` can do to one.

    Had this shipped as written, the gate would have been red on every teardown
    from its first day - and a gate that is always red is switched off, which is
    the same outcome as never having written it.
    """
    tagged_list = tagged(CLUSTER, *[TASK_DEF[:-2] + str(n) for n in range(10, 32)])
    decision = decide(tagged_list, tagged(PERMANENT), state(), active_clusters=())
    assert decision["verdict"] == "clean"
    assert len(decision["tombstones"]) == 23


def test_a_deregistered_task_definition_is_not_an_orphan_even_when_active():
    """Excluded by TYPE, and the distinction is the argument for it.

    A revision no service refers to does nothing whatever its status, so there
    is no state in which one is worth acting on. Excluding by status instead
    would leave a rule that fires on a resource nobody can use.
    """
    decision = decide(tagged(TASK_DEF), tagged(PERMANENT), state())
    assert decision["verdict"] == "clean"


def test_an_inactive_cluster_is_a_tombstone_and_an_active_one_is_an_orphan():
    """The same ARN, the same state, two verdicts - and only the service knows.

    `list-clusters` returns ACTIVE clusters only, which is why the verification
    step could report an empty account truthfully while the tagging API still
    listed this one.
    """
    dead = decide(tagged(CLUSTER), tagged(PERMANENT), state(), active_clusters=())
    assert dead["verdict"] == "clean"

    alive = decide(tagged(CLUSTER), tagged(PERMANENT), state())
    assert alive["verdict"] == "orphans"
    assert alive["orphans"] == [CLUSTER]


def test_an_unrecognised_kind_is_reported_rather_than_excused():
    """Fail-closed on everything the liveness rules do not know about.

    The exclusions are a list of things argued for one at a time. Anything not
    on it is an orphan, because the alternative is a sweep that quietly stops
    covering whatever AWS adds next.
    """
    weird = f"arn:aws:kinesis:us-west-2:{ACCOUNT}:stream/aws-devops-sdet-demo-stage"
    decision = decide(tagged(weird), tagged(PERMANENT), state())
    assert decision["verdict"] == "orphans"


def test_arn_type_reads_service_and_kind():
    assert sweep_orphans.arn_type(CLUSTER) == "ecs:cluster"
    assert sweep_orphans.arn_type(TASK_DEF) == "ecs:task-definition"
    assert sweep_orphans.arn_type(LOG_GROUP) == "logs:log-group"
    assert sweep_orphans.arn_type("not-an-arn") == ""


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
        "--active-clusters", write("clusters.json", {"clusterArns": [CLUSTER]}),
        "--environment", "stage",
    ]
    assert sweep_orphans.main(argv) == 1

    argv[1] = write("empty.json", {"ResourceTagMappingList": []})
    assert sweep_orphans.main(argv) == 0

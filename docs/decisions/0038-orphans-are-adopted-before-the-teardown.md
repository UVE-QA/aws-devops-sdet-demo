# ADR-0038: Orphans are adopted into state before the teardown

## Status
Accepted (Phase 19g, 2026-08-07). Completes ADR-0037; amends ADR-0035
guardrail 5 by demoting the blunt path to a last resort.

## Context
19f made the remaining gap exact, and it is an ORDERING rather than a missing
check. A cancelled apply creates resources that never enter Terraform state.
Terraform can then neither delete them nor delete what depends on them: on
2026-08-07 an unmanaged RDS instance held a managed DB subnet group, and the
destroy died on the pair in 70 seconds — twice, once in band and once when the
watchdog dispatched it. The blunt path removed the instance an hour later, which
is precisely what unblocks Terraform, and nothing ran Terraform again. The
remainder took three manual AWS calls.

Three shapes were written down in `docs/next-phases.md` and none of them had
been tested against the code:

    re-dispatch    the watchdog dispatches destroy once more after the blunt
                   path
    widen          the blunt path deletes the non-billable kinds too
    import         orphans are adopted into state, so Terraform owns them and
                   can remove them in dependency order

Read against the code, only one of the three can meet the criterion alone.

**re-dispatch cannot.** The blunt path deletes what BILLS: an ECS service, a
load balancer, a database. The cluster and the security groups a cancelled apply
leaves are free, so they survive it, and a re-dispatched destroy does not manage
them either. The run ends with `sweep-orphans.sh` red and the same three manual
calls. It also fires at the very end of a 90-minute TTL plus a grace period,
which is the slowest possible moment to discover it did not work.

**widen cannot.** Deleting the rest in the right order is Terraform's job, and
reimplementing a dependency graph inside a Lambda is a larger thing than the
defect. It also costs the property that makes the blunt path safe to have at
all: its IAM policy is narrow enough to be read in one sitting, and it is what
keeps the function away from the owner's own environment.

**import can, and it works one layer earlier.** The teardown that fails today
fails because it does not own three resources. Give it the ability to adopt
them and the FIRST destroy succeeds — the watchdog is never needed, the blunt
path is never reached, and state and AWS agree at the end instead of diverging
further. It needs no new AWS permission: `terraform import` reads, and the
deploy role already reads everything it manages, plus `tag:GetResources` since
19f.

The ordering problem then dissolves rather than being patched. The watchdog
already dispatches destroy once; that dispatch has always been the retry. It
was ineffective only because the destroy it dispatched could not adopt.

## Decision
D1. **A teardown adopts before it destroys.** `scripts/adopt-orphans.sh` runs in
    `destroy.yml` (stage and prod, one commit) and in the self-service destroy
    job, after the state-lock preflight and the security-group revocation and
    before `terraform destroy`. On a healthy environment it finds nothing and
    costs a few seconds, which is deliberate: a path that only runs after a
    disaster is a path nobody has exercised.

D2. **Its input is the gate 19f already built.** `scripts/sweep-orphans.sh` is
    what decides that a resource is live and unmanaged, with the three classes
    ADR-0037 settled on — `present`, `absent`, `unconfirmed`. Adoption runs that
    same script and adopts exactly what it reports. The check that names the
    remainder becomes the input to the thing that removes it, so the two can
    never disagree about what an orphan is. If the sweep refuses — its positive
    control came back empty, which means the question was not answered —
    adoption refuses with it.

D3. **The ARN-to-address map is data, and it is checked against the
    configuration.** `scripts/adopt_orphans.py` imports no AWS SDK and turns
    (ARN, tags) into a Terraform address and an import id, or into one of four
    named refusals. `tests/unit` asserts that every address in the map exists in
    the module sources the environment actually wires up, and that none of the
    mapped resources declares `count` or `for_each`. A map that goes stale
    against a renamed module is a red unit test rather than a confusing
    `terraform import` error during a teardown.

D4. **Anything not addressable is REPORTED, never guessed.** Subnets and route
    table associations are counted, and their index cannot be recovered from an
    ARN — the Name tag carries an availability zone, and the mapping from zone
    to index lives in a `data` source read at apply time. They are
    `unadoptable`, printed, and left to the end-of-run sweep to fail on. This is
    the same refusal to let "I could not check" read as "it is handled" that
    ADR-0037 arrived at from the other direction.

    Adoption does not need to cover every kind, and should not try to. A
    dependent leaves with its parent: adopt the load balancer and its listeners
    go with it; adopt the VPC and the default security group goes with it. The
    map covers the resources that HOLD others, which are exactly the ones that
    stall a destroy.

D5. **A failure to adopt one resource does not fail the step.** This is a
    deliberate exception to fail-closed, and it needs its reason written down:
    the step exists to make the destroy that follows it succeed, and a step that
    aborts leaves the billable resources running for another TTL. Each failure
    is printed with the ARN and the error, and the run's colour is still decided
    by the two gates at the end, which are unchanged. The one case that DOES
    abort is an unanswerable question — a refusal from the sweep — because
    nothing after it would mean anything.

D6. **AMENDED 2026-08-07, by its own first live run.** Adoption did exactly what
    it was written to do and the teardown still failed, because the thing it was
    written for was never offered to it. `sweep-orphans.sh` computed a
    resource's kind as everything up to the first SLASH, and AWS separates kind
    from name with a slash OR a colon — so `rds:db`, `rds:subgrp`,
    `logs:log-group` and `secretsmanager:secret` were four `case` arms that had
    never once been reached. Every resource of those kinds answered
    `unconfirmed`.

    The run: four orphans found, four mapped, `adopted 4 of 4; 0 could not be
    imported` — and then `Error: deleting RDS Subnet Group ... because at least
    one database instance ... is still using it`, which is the pair this whole
    phase exists for. The instance was in the tagging API's answer the entire
    time, three lines above the ones that were adopted.

    Two things follow, and the second is worse than the bug.

    **A kind that cannot be confirmed cannot be adopted, and that is correct.**
    Adoption reads `orphans` and not `unconfirmed`, deliberately: importing
    something nobody has confirmed is acting on an unanswered question. The
    defect was upstream, in the answering.

    **It corrects a diagnosis, not just a line of shell.** ADR-0037's amendment
    recorded that the sweep "did not report the RDS instance because it was
    still `creating`". It could not have reported it in any state. A plausible
    cause arrived at the same moment as the symptom and was accepted without a
    control — the sibling of the throwaway function that reproduced a defect
    because it inherited it.

    And it was invisible where it was tested. None of those kinds is tagged once
    an environment is gone, so the arms never ran and the gate was green — on
    every teardown, and on a deliberate read-only run against the empty account
    ninety minutes before this one. A gate is only exercised by the case it was
    built for.

    Fixed by `scripts/arns.py`: one parser, called by the shell and imported by
    `adopt_orphans.py`, which had the correct parse all along in a copy of its
    own. `tests/unit/test_arns.py` reads the `case` arms OUT of the script and
    fails on any arm no real ARN can reach — with a positive control, because an
    empty list of arms would pass it silently.

D7. **AMENDED AGAIN the same day, by the run that followed the first
    amendment.** With the parser fixed, a cancelled launch adopted the RDS
    instance three minutes into its creation - 4 of 4, including the resource
    whose absence from state has failed every teardown since 2026-08-05 - and
    the destroy died evaluating

```text
    url = "...@${aws_db_instance.this.address}:5432/..."
          aws_db_instance.this.address is null
```

    Terraform evaluates the configuration during a DESTROY as well, and a null
    in a string template is a hard error. The state was unreachable before this
    ADR: an apply waits for the instance, so a destroy had only ever seen a
    finished one. **Adoption did not fail; it moved the failure to the next
    thing.** Fixed with a local in `infra/modules/rds` that treats a null
    address as an empty string, with the cause written beside it.

    Two kinds also turned up `unconfirmed` for the first time -
    `cloudwatch:alarm` and `elasticloadbalancing:listener` - because this was
    the first sweep this project has run against a LIVE environment rather than
    the remains of one. Neither is adoptable and neither needs to be; both now
    have an existence rule, because `unconfirmed` is red and a gate that reddens
    on a resource behaving normally does not stay switched on.

## Consequences
The honest claim becomes what 19c asked for and 19e and 19f narrowed: a launch
cancelled mid-apply is reclaimed by the system. It is not proven until a
cancelled launch is reclaimed with zero manual AWS calls, and this ADR is
written before that run.

The blunt path is demoted rather than removed. ADR-0035 guardrail 5 made it the
recovery for "Actions is the broken thing"; it is now the recovery for that case
only, instead of also being a step in the ordinary recovery from a cancellation.
It keeps its break test and its IAM narrowness.

One residual risk is named rather than designed away. The tagging API is
discovery and it lags: 40 seconds into a teardown it did not report an RDS
instance that was still `creating` (ADR-0037, amended). An orphan created
seconds before the cancellation may therefore be invisible to the adoption step,
and that destroy will fail on it exactly as it does today. The retry is the one
that already exists — the watchdog dispatches destroy after the TTL, and that
destroy adopts. The system is slower in that case, not stuck, and the difference
between slow and stuck is the whole of this phase.

Cost: $0 in itself. Its break test is another cancelled launch, one of the
three a day.

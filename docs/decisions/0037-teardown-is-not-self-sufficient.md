# ADR-0037: Teardown is not self-sufficient

## Status
Accepted (Phase 19e, 2026-08-06). Corrects the Context of ADR-0036.

## Context
A deliberate cancellation mid-apply (launch ss-a9a983b4c9662b08, 2026-08-06 UTC):

    01:35 cancelled: ALB created, RDS creating
    01:38 stale state lock broken by the preflight in 6s      D3 holds
    01:52 "Destroy ALB first" fails after 15m22s on the ALB
          security group; destroy and verification never run
    01:52 release-lock sees destroy=failure and KEEPS the lock D2 holds
    03:01 watchdog writes its OWN item and dispatches destroy  D1 holds
    03:17 that destroy removes the RDS instance and the ALB

All three ADR-0036 decisions are confirmed by a live run, and the BILLABLE
resources went without a human. The rest did not: emptying the remainder took
four manual AWS calls.

Root cause is a reference chain between security groups:

    rds-sg ingress <- app-sg
    app-sg ingress <- alb-sg

AWS refuses to delete a group another group's rule references. `-target=module.alb`
includes the ALB security group while its referrer stays outside the target, so
the deletion is impossible by construction and Terraform retries it for 15
minutes. The 15m40s failures of 2026-08-05 are the same defect, read then as a
consequence of the lock.

Two more facts: a partially failed destroy drops resources out of state (an
orphaned ECS cluster survived), and the verification step is last, so it is
skipped exactly when a teardown fails.

## Decision
D1. Target the load balancer, not the module (`module.alb.aws_lb.this`). Done in
    f1ed545; the watchdog's own run passed that step.
D2. Revoke cross-group rules in a preflight, so no deletion is impossible.
D3. `Verify no billable resources remain` gets `if: always()`.
D4. End teardown with an orphan sweep: project-tagged resources absent from state
    fail the run.

    AMENDED TWICE on 2026-08-07, by its own first two runs, before it had ever
    been trusted. Both amendments say the same thing from opposite directions:
    **the tagging API is discovery, never a verdict.**

    Run against an account a destroy, its verification and a manual check had
    each called empty, it reported 23 orphans - one deleted ECS cluster still
    answering `describe`, and 22 task-definition revisions, which `terraform
    destroy` DEREGISTERS because deleting one is not an operation it has, and
    which AWS keeps indefinitely at no cost.

    Run one minute after a SUCCESSFUL destroy, it reported a security group that
    `describe-security-groups` answered `InvalidGroup.NotFound` for.

    And run 40 seconds into a teardown, it did NOT report the RDS instance - the
    only billable resource in the account - because the instance was still
    `creating`.

    The stale direction is the dangerous one. It would have reddened every
    teardown from the first day, and a red `destroy` job means `release-lock`
    keeps the lock (ADR-0036 D2), so the public button would have stayed shut
    until its TTL after every launch. A gate that is always red is switched off,
    and this one would have taken the button with it.

    So nothing becomes a finding until the service that OWNS it confirms the
    resource is there. `scripts/sweep-orphans.sh` asks one `describe` per ARN,
    by kind, and the decision receives three classes rather than two:

        present       confirmed by the service. Compared against state
        absent        the service says no. Dropped, counted, not reported
        unconfirmed   no rule for the kind, or the call itself failed.
                      REPORTED, because "I could not check" must never read as
                      "it is gone"

    The verification step (D3) remains in front of it and is not redundant: it
    asks ECS, RDS and ELB directly by name prefix and saw the instance the sweep
    missed. One knows only the kinds it names, the other only what has been
    indexed, and a run is red if either fires. No retry or delay was added: a
    check that waits is a check whose answer depends on how long it waited.

## Consequences
Until D2-D4 ship, the honest claim is narrower than the README's: the system
removes the billable resources of a cancelled launch without a human; the
remainder can still require manual AWS calls.

Evidence: docs/sessions/2026-08-06-phase-19e-watch.log; runs 31062941544, 31067248809,
31073407958, 31074438477, 31075646661, 31075831511.

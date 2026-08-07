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

    AMENDED 2026-08-07, by its own first live run, before it had ever been
    trusted. "Tagged and absent from state" is not the same as "left behind".
    Against an account that a destroy, its verification step and a manual check
    had each called empty, the sweep reported twenty-three orphans, and all
    twenty-three were tombstones: one ECS cluster deleted and still answering
    `describe`, and twenty-two task-definition revisions, which `terraform
    destroy` DEREGISTERS - deleting one is not an operation it has - and which
    AWS then keeps indefinitely at no cost.

    So the sweep asks two sources, not one: the tagging API for DISCOVERY, and
    the service that owns the resource for LIVENESS. `ecs list-clusters` returns
    ACTIVE clusters only, which is why the verification step reported an empty
    account truthfully while the tagging API still listed one. Task definitions
    are excluded by TYPE rather than by status, because a revision no service
    refers to is inert whether or not it is ACTIVE.

    Every other kind stays fail-closed, and every exclusion is printed with its
    reason. Had this shipped as written it would have been red on every teardown
    from its first day, and a gate that is always red gets switched off - the
    same outcome as never having written it.

## Consequences
Until D2-D4 ship, the honest claim is narrower than the README's: the system
removes the billable resources of a cancelled launch without a human; the
remainder can still require manual AWS calls.

Evidence: docs/sessions/2026-08-06-phase-19e-watch.log; runs 31062941544, 31067248809,
31073407958, 31074438477, 31075646661, 31075831511.

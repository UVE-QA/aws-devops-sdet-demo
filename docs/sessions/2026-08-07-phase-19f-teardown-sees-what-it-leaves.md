# 2026-08-07 — Phase 19f: the teardown sees what it leaves, and still cannot take it

ADR-0037 D2, D3 and D4, all three confirmed on live evidence. The criterion they
were written for is NOT met: a cancelled launch still needed three manual AWS
calls to finish. What changed is that the system now SAYS SO.

## Done
- **D2** `scripts/revoke-cross-sg-rules.sh`: revokes every rule by which one of
  the environment's security groups references another, before anything is
  destroyed. Wired into destroy.yml (stage and prod, one commit) and the
  self-service destroy job.
- **D3** `if: always()` on "Verify no billable resources remain", both
  workflows.
- **D4** `scripts/sweep-orphans.sh` + `scripts/sweep_orphans.py`: what AWS is
  tagged with, minus what Terraform manages, confirmed against the owning
  service, fails the run.
- `tag:GetResources` added to the deploy role and applied to
  `infra/bootstrap-oidc` under demo-admin.

## The break test (launch ss-b05240b2b90c10b7, cancelled mid-apply)

```text
00:51  launched from the public button, anonymously
00:56  cancelled - ALB not yet created, RDS creating, all three SGs up
00:56  D2 revoked 2 cross-group rules against REAL groups
00:57  destroy deleted alb-sg without resistance. On 2026-08-06 the same group
       in the same situation held destroy for 15m22s and failed it
00:57  Terraform destroy failed: the RDS instance is not in state, so it cannot
       be deleted, and the subnet group that IS in state cannot go while the
       instance holds it
00:57  D3: Verify RAN on the failed job and said "2 resource groups still
       present". D4 ran and named 6 orphans. Both would have been SKIPPED before
00:57  release-lock kept the lock (ADR-0036 D2)
02:22  watchdog wrote its own record and dispatched destroy
02:23  that destroy failed on the same pair, in 70 seconds
02:40  the blunt path deleted the RDS instance; lock and record released
       then  3 manual AWS calls for the remainder
```

## What it established

**D2 works, with a direct before-and-after.** The security-group chain no longer
makes a deletion impossible; the group that cost fifteen minutes yesterday left
without comment today.

**D3 is the difference between a silent failure and a reported one.** Both new
steps ran on a job that had already failed. On 2026-08-06 the identical
situation produced a run that reported success while an ECS cluster survived.

**The remaining gap is an ordering, and it is now exact.** Resources created by
a cancelled apply never enter state. Terraform can neither delete them nor
delete what depends on them. The blunt path removes the billable ones — but
only after the dispatched destroy has already failed, and nothing dispatches
another. The destroy that would now succeed is never run.

## Three findings, each from running rather than reading

**D3 is not safe as ADR-0037 wrote it.** The verification step was last, so it
had only ever run with working credentials. `always()` lets it run after a
FAILED credentials step, and then every `aws` call answers nothing — which is
what an empty account looks like. destroy.yml's copy had neither `set -euo
pipefail` nor an `sts` call. Applied literally, the decision would have turned a
skipped step into a green one.

**The tagging API is discovery, never a verdict**, and it was wrong in both
directions within one hour:

```text
too late   40s into the teardown it did not report the RDS instance - the only
           billable resource in the account - because it was still `creating`
too early  1 minute after a SUCCESSFUL destroy it reported a security group that
           `describe-security-groups` answered InvalidGroup.NotFound for
```

The stale direction would have reddened every teardown from the first day, and a
red destroy job keeps the launch lock (ADR-0036 D2) — so the public button would
have stayed shut until its TTL after every launch. Fixed by confirming every
finding against the owning service, with three classes reaching the decision:
`present`, `absent`, and `unconfirmed` for a kind with no rule, because "I could
not check" must not read as "it is gone".

**An exclusion is not replaced by a mechanism just because the mechanism looks
more general.** The first version excluded ECS task definitions by type. The
second removed that, claiming confirmation subsumed it. There is no existence
rule for `ecs:task-definition`, so 22 deregistered revisions became
`unconfirmed` and the gate went red on an empty account — the same failure from
the other side. Predicted by reading, then confirmed by running, because two
readings had already been wrong this session.

## Also fixed in code before it shipped

`confirm_exists` was called bare under `set -e`, so the first resource the
service reported as gone would have ended the script. Non-zero is the ORDINARY
answer there. Found by reading; proved by driving the loop with a stub `aws`
that fails every call.

## Break tests kept

```text
revoke   2 of 3 groups selected; a pair naming a group OUTSIDE the environment
         and a CIDR in the same permission both left alone
         no groups / no references: exit 0.  missing fixture: exit 2
         the call itself failing: exit 1, with the error quoted
sweep    same ARN red when the service confirms it, green when it does not
         a kind with no rule: red, labelled UNCONFIRMED
         22 task-definition revisions: green, counted as not present
         empty control: REFUSED, and its grouped output is byte-identical to
         the green case, which is why the control exists
         the confirmation loop driven with an `aws` that fails every call
16 unit assertions; exit codes measured to a file, never through a pipe
```

## True now
- account empty; `destroy.yml` green end to end including both new steps
- the teardown reports its remainder correctly and removes none of it
- 4 patches. ci green after each of the three that reached main before this one

## Next
19g decides the ordering: re-dispatch destroy after the blunt path, extend the
blunt path to the kinds Terraform abandoned, or import orphans into state before
destroying. Done when a cancelled launch is reclaimed with ZERO manual AWS
calls — the criterion 19c raised, 19e narrowed and this phase did not meet.

## Gotchas
- `sed` by step name found nothing in a job log twice; grepping for content the
  script prints worked both times
- the AWS CLI pager blocks a non-interactive read; `AWS_PAGER=""` everywhere
- bracketed-paste markers reached the shell as literal `00~`/`01~` for half an
  hour because some earlier program left the terminal mode on

# 2026-08-08 — Phase 19g CLOSED: nobody in the loop

One launch, cancelled mid-apply, reclaimed by the run's own teardown with zero
manual AWS calls, no watchdog, no blunt path and nobody dispatching anything.
That sentence has ended four session summaries as a prediction — 19c, 19e, 19f
and 19g. It is now evidence.

```text
00:38:17  launch dispatched from the public button, anonymously
00:42:55  ALB active, ECS cluster up, all three security groups up,
          RDS creating - the full orphan set, richer than any previous cancel
00:44:15  cancelled. Normal cancel, not force: a force-cancel takes the
          `if: always()` destroy job with it, which is the thing under test
00:44:24  destroy job starts by itself
00:45:26  sweep before the teardown: verdict `orphans`, exit 1, five of them
00:45:43  adopted 4 of 4; 0 could not be imported
00:49:09  destroy SUCCESS  (4m45s from the cancellation)
00:49:12  release-lock SUCCESS - it releases only on destroy=success
          (ADR-0036 D2), so it is a second, independent witness
00:49:01  final sweep: verdict `clean`, confirmed present 0, control 49
00:56:57  verified again from OUTSIDE the run: stage destroyed, no ACTIVE
          cluster, no project-tagged security group, control non-empty
```

The run's own conclusion is `cancelled` and always will be — we cancelled it.
Success is visible only at job level, which is where it was read.

## Why it worked, rather than that it worked

A green teardown whose mechanism is unexamined is a teardown that will go red
for an unexamined reason. The adoption step's own output:

```text
tagged in AWS: 44   in Terraform state: 33 identifier(s)
control (whole project): 67 resource(s)
confirmed present: 20   tagged but not there: 24
verdict: orphans
  ORPHAN  security-group/sg-02a3dc750047ba3b0
  ORPHAN  security-group/sg-0e02f3486bd0b8a1d
  ORPHAN  ecs:cluster/aws-devops-sdet-demo-stage-cluster
  ORPHAN  elasticloadbalancing:listener/.../aws-devops-sdet-demo-stage-alb/...
  ORPHAN  rds:db:aws-devops-sdet-demo-stage-db
sweep exit: 1
adopting 4 resource(s) into infra/envs/stage
  adopted module.rds.aws_security_group.rds
  adopted module.ecs.aws_security_group.app
  adopted module.ecs.aws_ecs_cluster.this
  adopted module.rds.aws_db_instance.this
adopted 4 of 4; 0 could not be imported
```

Three things in that block are the three defects of 2026-08-07, each meeting
its own case for the first time:

```text
rds:db reported at all    the colon/slash parser fix. This kind answered
                          `unconfirmed` on every previous teardown, so adoption
                          - which reads `orphans`, never `unconfirmed` - was
                          never offered the one resource that mattered
adopted while `creating`  the null-address fix. The instance was 2 minutes old
                          at adoption and had no endpoint address; yesterday
                          that killed the destroy after the adoption succeeded
zero UNCONFIRMED lines    the existence rules added for cloudwatch:alarm and
                          elasticloadbalancing:listener. Yesterday's live sweep
                          produced two; today's produced none
```

**Five orphans, four adopted, and the fifth was named rather than dropped.**

```text
UNADOPTABLE  ...:listener/app/aws-devops-sdet-demo-stage-alb/...  (no rule for this kind)
```

A listener leaves with its load balancer, and the "Destroy ALB first" step
removed it (`Plan: 0 to add, 0 to change, 1 to destroy`) before the main destroy
took the other 23. The gap between 5 and 4 is the kind of arithmetic that reads
as an oversight when nobody checks it; it was checked, and the log says why.

## Two findings before the button was pressed, both about documents

**1. The endpoint was not parked.** `docs/phase-gates.md` and
`docs/discussion-log.md` both stated the kill switch was engaged by hand after
19c. The control store had no `killswitch` item at all: it was cleared to run
19g's launches and never re-engaged, so the public button has been live since
2026-08-07. Nothing was spent — the day counter shows no launch on the UTC day
it was open — and the guardrails are exactly the ones that were being tested.
The finding is not the exposure, it is that two documents agreed with each other
and neither agreed with the account. **Decided this session: it stays live**,
which is what Phase 19 was built for, and both documents now say so.

**2. A day's launches belong to the UTC day, not to a session.** The counter
read 3 for 2026-08-07 while 19g's summary described two launches. There was no
phantom third: 19f's break test at 00:51 UTC and 19g's two at 04:03 and 07:35
all fall inside one UTC day, and the two sessions shared one cap between them.

The first explanation offered in this session was wrong and is recorded because
the shape recurs: *"session files are named by local date, the counter bins by
UTC, so they cannot be compared."* Checked instead of believed — 19f's file is
named `2026-08-07` and its launch ran at 17:51 **local** on 08-06. Both name the
UTC day; they never disagreed. A plausible cause arriving with a symptom is
exactly what ADR-0037 got wrong about the `creating` RDS instance, one day
earlier.

## Shipped: the watch loop is a script

`scripts/watch-launch.sh`. It had been typed into a terminal on three separate
days and broke the same two ways each time, both recorded in 19g's summary:
started outside the repository, `gh run list` answered "failed to determine base
repo" on every tick and the run column was empty for a whole launch; run in the
foreground, an SSH disconnect took it with it and left a 2h46m hole in the
middle of what it was recording. Neither is a property of the loop — both are
properties of where and how it was started, which is why they recurred every
time it was started again. It now cds to the repository itself, and the
documented usage is `nohup`. ADR-0028's shape, sixth or seventh arrival.

One property the terminal version did not have: **no field may be blank.**
`alb=none` is what a torn-down environment looks like and what an expired token
looks like, and this project has already read nine empty lines as a clean
account. Every field is a value, `none`, or `ERR`; `acct` is re-read on every
tick rather than once at the top; `pipefail` is set because every getter ends in
a pipe and a failed `aws` would otherwise be laundered into an empty string by
`tr`.

Break-tested offline before it recorded anything, all three branches
distinguished — every call failing at startup (refuses, exit 1, logs nothing),
calls failing after startup (every field `ERR`, loop keeps watching), calls
succeeding and empty (`none`, and a real value prints as itself).

## True now

- Phase 19 is complete. The public button is live at https://demo.uveapp.net,
  and a cancelled launch now cleans itself up without a human
- account empty, verified from outside the run with a positive control in the
  same command; `main` = the commit closing this session
- 1 launch used of 3 on UTC day 2026-08-08; `lock` released, no `watchdog` item
- the watchdog and the blunt path were not needed and did not fire. They remain
  as the cover for "Actions is the broken thing", which is what ADR-0038 demoted
  guardrail 5 to
- cost of the run: about **$0.03** — an ALB and an RDS instance for six minutes

## Gotchas

- the AWS CLI pager reappears on every command until `cli_pager` is set empty in
  the profile. Fixed in `demo-admin` rather than worked around per command
- `git am` rewrites the commit hash, so the chat's clone diverges from
  `origin/main` the moment its own patch is applied. Re-fetch before authoring
  the next patch or the base is wrong and the second patch will not apply

# 2026-08-07 — Phase 19g: the teardown reaches the end, and what stood behind it

ADR-0038: a teardown ADOPTS what it does not manage before it destroys. Chosen
over re-dispatch and widen by reading them against the code rather than
comparing their descriptions. Shipped, and then proven twice — the second time
against the exact resource that has failed every teardown since 2026-08-05.

The phase does NOT close. Everything it was written to do was seen working on
live evidence, and no manual AWS call was made all day; but the last teardown of
each launch was dispatched by a human to skip a 90-minute wait, so *nobody in the
loop* is still a prediction. Both of today's launches are spent.

## The decision

Three shapes were on the table. Read against the code, two of them cannot meet
the criterion at all:

```text
re-dispatch  the blunt path deletes what BILLS. The cluster and the security
             groups a cancelled apply leaves are free, so a re-dispatched
             destroy does not manage them either
widen        deleting the rest in the right order is Terraform's job.
             Reimplementing a dependency graph in a Lambda is larger than the
             defect, and it spends the IAM narrowness that makes the blunt path
             safe to have at all
import       the teardown fails because it does not OWN three resources. Let it
             adopt them and the FIRST destroy succeeds
```

The ordering then dissolves instead of being patched: the watchdog already
dispatches destroy once, and that dispatch has always been the retry. It was
ineffective only because the destroy it dispatched could not adopt.

Adoption's input is the gate 19f built. `sweep-orphans.sh` decides what is live
and unmanaged, with ADR-0037's three classes, and adoption imports exactly what
it reports — one definition of "orphan", and the check that names the remainder
became the input to the thing that removes it.

## Three defects, each found by the previous fix working

**1. Four `case` arms in the 19f sweep had never been reached.**
`confirm_exists` computed a resource's kind as everything up to the first SLASH.
AWS separates kind from name with a slash OR a colon, so for the colon ones the
whole rest of the ARN came back as the kind:

```text
arn:aws:rds:...:db:aws-devops-sdet-demo-stage-db
    case key = rds:db:aws-devops-sdet-demo-stage-db    matches nothing
```

`rds:db`, `rds:subgrp`, `logs:log-group` and `secretsmanager:secret` therefore
always answered `unconfirmed`. Adoption reads `orphans` and not `unconfirmed` —
deliberately, because importing what nobody has confirmed is acting on an
unanswered question — so the RDS instance was never offered to it. The run
adopted 4 of 4 and died on `Cannot delete the subnet group ... because at least
one database instance ... is still using it`, with the instance sitting three
lines above the ones it had adopted.

It corrects a diagnosis, which is the worse half. ADR-0037's amendment recorded
that the sweep "did not report the RDS instance because it was still
`creating`". It could not have reported it in any state; a plausible cause
arrived with the symptom and was accepted without a control.

And it was invisible where it was tested. None of those kinds is tagged once an
environment is gone, so the arms never ran and the gate was green — on every
teardown, and on a deliberate read-only run against the empty account ninety
minutes earlier. **A gate is only exercised by the case it was built for.**

**2. An adopted instance that is still `creating` has no address.** With the
parser fixed, the second cancelled launch adopted the RDS instance three minutes
into its creation — 4 of 4, including the one that matters. The destroy then
died evaluating

```text
url = "...@${aws_db_instance.this.address}:5432/..."
      aws_db_instance.this.address is null
```

Terraform evaluates the configuration during a destroy as well, and a null in a
string template is a hard error. The state was unreachable before ADR-0038,
because an apply waits for the instance and a destroy had only ever seen a
finished one. **The fix worked and moved the failure rather than removing it.**

**3. Two kinds a LIVE environment has.** `cloudwatch:alarm` and
`elasticloadbalancing:listener` have no existence rule, and both appeared
`unconfirmed` in the first sweep this project has ever run against a live
environment rather than the remains of one. Neither is adoptable and neither
needs to be — a listener leaves with its load balancer — but `unconfirmed` is
red, and a gate that reddens on a resource behaving normally is a gate on its
way to being switched off.

## The two launches

```text
LAUNCH 1  ss cancelled 04:09, RDS creating
  04:11  in-band destroy: the adoption step DID NOT RUN
         - the patch was on the devbox and not on main, and the workflow comes
           from main. My sequencing error, and the primer says it in one line:
           work is not done until it is pushed
  05:36  watchdog dispatched destroy by itself, 92 minutes after the launch
         adoption ran: 4 orphans, 4 adopted, 0 failed
         destroy failed on the subnet group - the RDS instance was UNCONFIRMED
  ~05:52 blunt path deleted the instance; lock and record released
  07:30  destroy dispatched by hand, green in 1m12s, account empty
         and ZERO UNCONFIRMED lines where the same situation had two

LAUNCH 2  ss cancelled 07:41, RDS creating
  07:43  in-band destroy: adoption ran and adopted 4 of 4 INCLUDING
         module.rds.aws_db_instance.this - the resource whose absence from state
         has failed every teardown since 2026-08-05
         destroy failed on the null address (defect 2)
  07:54  destroy dispatched by hand after the fix, green in 5m27s, and it
         deleted the adopted instance from state as an ordinary managed resource
```

Account verified empty afterwards, twice, with `sts get-caller-identity` first
and every result assigned under `set -e`.

## Break tests kept, all offline, exit codes measured to a file

```text
the map      count added to a mapped resource: RED, naming it
             a resource renamed inside a module: RED
             a module renamed in infra/envs/stage: RED
the plan     a kind with no rule; a counted subnet, which says WHY rather than
             "no rule"; a security group with no Name tag; a name from another
             environment; two groups sharing one Name tag, which adopts NEITHER
             and names the address both claimed
the script   two imports green; the same two with every import failing, which
             CONTINUES and exits 0 by design; an empty plan; an unknown
             environment; no argument; a sweep that refused -> exit 2
the sweep    identical output and exit code with and without SWEEP_KEEP_DIR
the parser   the negative control that matters: the SAME fixture with the old
             slash-only parse answers UNCONFIRMED for both RDS ARNs and ORPHAN
             with the new one. Exactly one thing differs
the arms     the reachability test on the old parser names all four dead arms,
             and has its own positive control - an empty list of arms would
             pass it silently
```

## Findings while writing, before anything shipped

- the first version of "no mapped resource is counted" read the ALB security
  group as indexed. It was matching `for_each` four spaces in, inside a
  `dynamic "ingress"` block — the test was measuring its own regex
- the patch script used to make the edits computed every replacement from the
  original text and wrote them one after another, so a second edit to one file
  silently discarded the first, and it printed success twice

## True now

- account empty, `destroy.yml` green end to end, `main` = 905b4c7
- adoption runs on EVERY teardown; on a healthy one it finds nothing and says so
- tf-fmt clean, tf-validate 8 levels, test-unit 93, docs-check 0 findings,
  action-pins 43, ci green on every push
- the launch lock is still held, correctly: `release-lock` keeps it when destroy
  fails (ADR-0036 D2), and the watchdog releases it once nothing is alive and it
  has expired
- 3 patches, plus this one

## Not proven, and it is the same sentence as 19c, 19e and 19f

A cancelled launch reclaimed with nobody in the loop. Every component was seen
working today and the remaining step is one uninterrupted run: cancel, and watch
the IN-BAND destroy adopt and finish within minutes, without the watchdog and
without the blunt path. That is a prediction. Both of the day's launches are
spent, so it is the first thing the next session does.

## Gotchas

- `sed` by step name found nothing in a job log again; grepping for content the
  script prints worked, as it did on 2026-08-07 and twice before
- the watch loop must be started from the repository, or `gh run list` says
  "failed to determine base repo" and the run column is empty for the whole run
- an SSH disconnect takes a foreground watch loop with it. `nohup` plus a
  separate `tail -f` survives; the evidence log has a gap from 04:26 to 07:12
  for exactly that reason
- two `tail -f` on one file interleave, and the output reads as though the clock
  went backwards

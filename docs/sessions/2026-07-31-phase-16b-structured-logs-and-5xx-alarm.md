# 2026-07-31 — Phase 16b: structured logs and the 5xx alarm

Closed. The application writes one JSON line per request carrying a request id,
a CloudWatch metric filter counts 5xx from those lines, and one alarm reads the
resulting metric. Verified by a full cycle, both environments destroyed.

## What was decided before any code

**ADR-0032.** The two halves of this phase are one decision: the metric filter
reads the log, so the shape of the log decides whether the alarm can exist.

The signal comes from the application's own log rather than from the ALB's free
`HTTPCode_Target_5XX_Count` — the log line names the path, the request id and
the duration, so the alarm and the evidence are the same artifact. What that
choice CANNOT see is written down rather than left implied: an ALB answering 503
with no healthy target writes no application line and will not raise this alarm.

The environment is carried by the metric NAMESPACE, not by a dimension, because
a dimension value is a billable custom metric of its own. And the alarm ships
with no notification action: an SNS email subscription needs a confirmation
click, and a topic beside an environment that is destroyed every cycle would ask
for one every cycle while notifying nobody in the window that matters. **A
notification channel has to outlive the thing it reports on** — the fifth
independent arrival at the ADR-0027 rule, and the first reached from something
other than state.

## What was built

```text
app/src/logging_config.py   JSON formatter + request-id context variable
app/src/main.py             one access line per request, including the ones
                            that raise
tests/unit/                 a new suite: in-process, no network, no database
infra/modules/observability metric filter + alarm
infra/modules/ecs           an `environment` block, which it had never had
```

`tests/unit/` exists for the ADR-0025 reason applied outside Playwright: where a
spec lives decides what it can see. Whether `status` is a number, and whether an
unhandled exception is logged at all, are invisible to every HTTP client — and
both fail in the direction where the alarm never fires while looking correct.

## Four break tests, all fired

```text
status as a string      "status serialised as str; the metric filter compares
                        it numerically and would match nothing"
naive middleware        "expected exactly one access line, got 0"
drop-list removed       ANSI escapes and a duplicate message reach the payload
docs-check              "tests/unit is neither a tracked file nor a directory"
```

The last one was not planned. `make docs-check` reads `git ls-files`, and the
new directory had not been added yet — the gate refusing a documentation change
before CI ever saw it.

## Three findings, all from running rather than reading

**1. `color_message`, found in the first real container.** uvicorn attaches it to
its own startup lines through `extra=`, and the formatter promotes every `extra=`
field to the top level — which is exactly how `status` becomes a comparable
number, and how `[36m` plus a duplicate of each startup line were on their
way to CloudWatch. No fixture had shown it; the container's own output did.

**2. The metric was billable from the first health check.** `default_value = 0`
emits a zero for every NON-matching log event, and the ALB health-checks the
service every 30 seconds — so the custom metric existed from the first check,
while ADR-0032 claimed it does not exist until the first 5xx. Both could not be
true. `get-metric-statistics` returned a flat line of 0.0 datapoints minutes
before anything had failed, and settled it. The `default_value` was removed,
which makes the claim true rather than editing the claim.

**3. The ALARM state lived exactly sixty seconds.** `OK -> ALARM` at 20:09:09,
`ALARM -> OK` at 20:10:09. With no notification action, the only surviving record
was `describe-alarm-history`. A signal that has to be looked at in the right
minute is not a signal. Widened to 1 datapoint out of 5 periods; re-measured
afterwards as ALARM at +2.5 minutes and still ALARM at +5.

Findings 2 and 3 came from the same command output, and neither was reachable by
review. Both are the project's recurring species: a document and a command
disagreeing, with the command right.

## The break test in AWS, joined to the local one by a literal

No fault endpoint was added. `/api/db-check` already returns 503 through its real
path when PostgreSQL is unreachable, so stopping the local database produced a
genuine line. **That line** — not a line of its assumed shape — was put into the
stage log group with exactly one field changed, `env` from `local` to `stage`.

Measured in this order, with the positive control taken BEFORE the injection:

```text
sts get-caller-identity   993912191738
alarm state               OK, "no datapoints were received ... treated as
                          [NonBreaching]" - CloudWatch stating the ADR's
                          decision in its own words
{ $.status >= 500 }       no events
{ $.status = 200 }        live stage lines, env "stage" - the same filter
                          grammar as the metric filter, so the empty result
                          above means something
after injection           metric 1.0 at 20:08
alarm history             OK -> ALARM 20:09:09 -> OK 20:10:09
after the fix             ALARM at +2.5 min, still ALARM at +5 min
prod alarm                OK, 5 periods, 1 datapoint, notBreaching,
                          namespace aws-devops-sdet-demo/prod
```

prod was exercised deliberately rather than taken on trust: the change is in a
SHARED module, and prod in this project once kept a broken shape for seven weeks
because a shared fix was only ever run in stage. No line was injected into prod —
the signal was already proven, and prod was publicly answering at the time.

## Measured

```text
deploy-stage #26   17m41s   first run, RDS created
deploy-stage #27    8m54s   re-run to apply the amended module, image reused
promote-prod #9    14m32s
destroy prod #20    9m47s
destroy stage #21   8m38s
```

Teardown verified from the devbox under `demo-admin`, `sts` first, with a
POSITIVE CONTROL in the same command: `alb`, `rds`, `ecs`, `nat`, `eks` and
`alarms` all empty while `ecr` returned the shared registry.

Cost: roughly $0.17 at list prices by the same method as Phase 16a — stage up
about two hours across two applies, prod about forty minutes.

## Owed to a later phase

An SNS topic at a permanent level, so the alarm can notify. Priced in ADR-0032
and deliberately not built here. `HTTPCode_ELB_5XX_Count` is the second alarm
that would close the gap this one does not cover.

## Documents this session edited outside its own phase

`docs/session-primer.md` was changed, so **the copy in the transfer buffer had
to be refreshed** — done, and verified by comparing it against the pushed
version rather than by assuming the `scp` landed.

The primer's suite list did not mention `tests/unit`, which meant the first file
every session reads described a test layout that no longer existed. Fixing it
there and stopping would have repeated the defect it was fixing: the same list
lives in `.claude/skills/test-dev`, the make-target list in
`.claude/skills/local-dev`, and the teardown verification in
`.claude/skills/teardown` had no idea an environment now creates an alarm. All
four went in one commit, per the rule that a fix reaches every copyable
occurrence.

`docs/discussion-log.md` was the miss that mattered: its "Current state" block —
the narrative a new session reads — still said 16b had not started, while the
cursor said it was done. Two documents in the same repository disagreeing about
the present is exactly what the cursor exists to prevent, and it only prevents
it if everything else defers to it.

# 2026-08-11 — Phase 28: a cycle on a different day, five measured delays, and a qualifier that outlived its premise

The three items `docs/next-phases.md` had carried since 20m, none of which was a
session on its own because each needed a live cycle around it. One cycle was
ordered — stage up, promoted to prod through the approval gate, both torn down,
both priced — and watched through a single tab opened before the first dispatch
and never reloaded, navigated or Refreshed.

**ADR-0062.** Evidence in
`docs/sessions/2026-08-11-phase-28-convergence.log` and
`docs/sessions/2026-08-11-phase-28-watch-convergence-self-test.log`; the
pre-cycle probe in `docs/sessions/2026-08-11-phase-28-not-reached-probe.log`.

## The three items

### `not reached yet` — seen, as a pair

20m raised it and left it open: the branch is `!record && underWay`, every node
has carried a record since 2026-08-09, and a cycle following a completed cycle
cannot reach it. So the absence was ARRANGED — `timeline/<env>/nodes-apply.json`
backed up and deleted from the bucket immediately before a dispatch, restored by
the cycle's own publish at the end.

The evidence is a pair, and the second half alone would have meant nothing:

```text
05:55:21Z   nothing in flight, record absent   not run yet                    all 8 prod nodes
06:01:14Z   promote-prod in flight, absent     not reached yet · a cycle is
                                               under way and has not got here  all 8 prod nodes
06:04:06Z   held                                                               3 samples over 7 min
06:08:16Z   held
```

One tab, one page, and exactly one input changed between the two frames.

The plumbing was read before the bucket was touched — `readJSON` returns null on
a non-ok response, `readRunLayer` skips a null document, `nodeTense` takes the
`!record` branch — and then rendered against a fixture rather than argued. The
probe modelled a 404; production answers **403**, because the bucket is private
behind OAC without `s3:ListBucket`. The predicate is `r.ok`, so both land in the
same branch: the probe was right for a slightly wrong reason, and the live page
is the evidence.

### The map's dating sentence — answered by two dates at once

At rest before the cycle the map read `dated 2026-08-09`; afterwards
`dated 2026-08-11`. Better than the sequence, the cost box held both at the same
instant, one stale and one fresh, each correct:

```text
06:40:33Z   stage $0.0529 .. $0.0584 — the cycle of 2026-08-09
            prod  $0.0229 .. $0.0284 — the cycle of 2026-08-11
```

20m's sentence was that a fresh date and a stale one were indistinguishable.
Simultaneity settles it in a way two consecutive readings could not.

### The convergence delay — five measurements, not one bound

```text
1.1s  1.6s  8.6s     the edge held nothing or an error, and fetched at once
57.6s 61.1s          the edge held a copy with a TTL still to run
```

Roughly uniform in `[0, 60]`: a cached copy lives to the end of its current
window and a write lands anywhere in it. **The two high draws are the
instrument's own doing** — polling every two seconds guarantees the edge always
holds a fresh copy, so a write can never find it empty. That paragraph is in
`scripts/watch-convergence.sh`, because the log without it says the opposite.

And the page's own sentence, `the figures up to a minute behind the write`, is
true. 20k caught that sentence lying once; this is the first time it has been
measured.

## What nobody was looking for

### A qualifier that outlived its premise (ADR-0062 D1)

For about five minutes the page drew `promote-prod #12`'s own figures under the
words `these figures are from the cycle before this one`. The premise in the
code — "nothing publishes until a cycle ends" — is false of a job that publishes
before its last step. The mirror of 20m's third finding, and the same wrong
predicate on both sides: *is a run in flight?* rather than *is this record that
run's?*. The document already carries `cycle.run.id`.

### The first news arrives on the slowest clock (ADR-0062 D2)

`destroy prod #46` was created at 06:19:15Z and the page's first word about it
carried an elapsed of `4m 53s` — 293 s, against the 300 s ceiling that applies
whenever the page believes nothing is running. It speeds up to ~123 s only after
it knows. This lands on `Approve · a human, in the prod environment`: the person
is needed at the start, and the start is when the page is slowest.

Found because the participant said "the page still doesn't say it is waiting for
a reviewer". That is a measurement, not impatience.

### Versioning declared and not applied — NOT DIAGNOSED

`infra/public-site/main.tf` declares `status = "Enabled"` on the dashboard
bucket, above a comment explaining that `status/`, `timeline/` and `reports/`
exist nowhere else and versioning is "the half that survives the guard being
wrong". The account disagrees, and the control differs where it must:

```text
aws-devops-sdet-demo-tfstate-993912191738   rc=0   {"Status": "Enabled"}
aws-devops-sdet-demo-site-993912191738      rc=0   <empty>
```

Both calls succeeded, so the empty answer is an answer. Whether Terraform's state
knows is **not established**: reading `public-site/terraform.tfstate` under
`demo-admin` returns 403, which is itself unexplained given that the deploy roles
read it in CI. Deliberately not pursued at 22:40 with a billable cycle in
progress — 2026-08-05 already cost this project a day by chasing a 403 to a
conclusion that was wrong.

Consequence for this session: the claim "the previous version survives the
deletion" was made in chat on the strength of the code and was WRONG. The file
backup was the only belt, and it held.

## What held, live

- **The badge, twice**: `all 7 succeeded · 1 still going`. 20m's clearest frame
  was `all 10 succeeded` beside `in progress` in one sentence. Phase 25's fix had
  only ever been seen against a fixture.
- **Per-environment binding of the suite qualifier** (ADR-0059 D2, the finding
  the fixture made): during `promote-prod`, prod's suites read
  `2 of 2 · from the previous run` while stage's read `52 of 52 · 5.8s` with no
  qualifier at all.
- **The permanent caption** on `observer: actions` nodes:
  `finished in this run · its step is in Actions, not in a timeline`. Checked
  against `assets/index.template.html:1966` rather than judged from one frame —
  the run layer's word about the step is kept deliberately and the promise of
  figures is replaced. Designed, not defective.
- **Teardown, against the AWS CLI**, account printed first and the whole chain
  under `set -e`: `993912191738`, then ecs, rds, alb, nat and eks all empty.

## The instrument

`scripts/watch-convergence.sh`, delivered before the cycle in two patches
because the devbox found a defect in the first one within an hour: the sighting
was timestamped BEFORE its request, so it could precede the event it reported,
and the self-test's `0 <= d` accepted `-0.002` after printf rounded it to
`-0.00`. Three breaks recorded, one of them that reading verbatim. A fourth was
caught by the self-test mid-fix — `awk $(NF-2)` silently read the wrong column
once a column was added — and it went red rather than quiet.

The cycle then found a fifth: the arithmetic was conditioned on `Age`, which
CloudFront omits on exactly the response that first carries a new object.

## Cost — outside the predicted band, and why

```text
predicted   $0.07  .. $0.08
actual      $0.0846 .. $0.0958      stage $0.0617 .. $0.0674, prod $0.0229 .. $0.0284
```

Declared in advance that anything outside the band was itself a finding, so it is
one. Not the rates — the calendar. stage lived about 80 minutes against 20m's 69,
prod about 40 against 30, because this cycle contained two approval pauses and an
observer sampling the page between runs. **The price of a cycle is a function of
how long a human takes to walk through it**, and a prediction built from a
previous cycle's durations imports that cycle's tempo.

## The method, and the hour it cost

The apply half of `deploy-stage` was NOT watched. The session handed the
participant `gh run watch`, which blocked the terminal for sixteen minutes and
took with it the only turn in which the page could have been sampled — so the
first arrangement of `not reached yet`, on stage, was published over before
anyone looked at it. It was recovered by repeating the arrangement on prod. A
blocking command is a choice about who gets to observe, and it was made without
noticing that.

## Validation

```bash
  bash scripts/watch-convergence.sh --self-test
  make gates
  aws sts get-caller-identity --profile demo-admin
  make docs-check
```

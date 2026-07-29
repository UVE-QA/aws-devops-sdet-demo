# 2026-07-29 — Phase 16a: contract depth and the regression suite

First half of Phase 16, split from it at the start of the session: 16a is the
application contract and the tests that hold it; 16b is observability
(structured logs with a request id, a metric filter on 5xx, an alarm) and has
not started.

Closed with a full AWS cycle. Both environments were destroyed and their
absence was verified against the AWS CLI with a positive control in the same
command.

## Delivered

```text
patch A   GET by id, PATCH, a paginated list envelope, updated_at (ADR-0031),
          the inline edit control in the UI, and the tests for all of it
patch B   the last-page fixture is BUILT rather than looked for
patch C   the page walk counts itself against the total
patch D   the page counts renders, so a test can wait for THIS load
```

Four patches, and every one after the first exists because something was run.
B came from a test that skipped itself on its first run, C from a break test
that failed to break, D from stage failing where localhost could not.

## The contract — ADR-0031

Two of the four additions were decisions rather than code, and the ADR was
written before either:

```text
the envelope   count keeps meaning "items in this response"; total, limit and
               offset join it. The Phase 10 assertion that count == len(items)
               stays true, and the pair can now disagree in a way that names
               the bug: count > limit is a broken limit, total < count is a
               broken count query.
the default    limit defaults to 20 and caps at 100. Pagination that only
               paginates when asked bounds nothing.
the order      stays ascending, so the newest row is on the LAST page. The UI
               moves to it after a create; the API keeps one order.
PATCH          partial, via exclude_unset. Absent leaves a field alone, an
               explicit null clears the description, {} and a null name are
               422. A rename onto a taken name is 409 from the constraint,
               exactly as create does it.
```

`updated_at` (revision 0003) exists for one reason: it is what lets the
assertion after a UI edit say the row was WRITTEN. Without it the check could
only see that the name was different, which a second create would also produce.

## What running it showed that reading it would not

**A test that skips itself is a test that never ran.** The first version of
"deleting the only row on the last page steps back a page" checked whether the
last page happened to hold exactly one row and skipped when it did not — and on
its first run, it did not. A conditional skip reports the same colour whether it
passed or never executed. It now creates however many filler rows are needed to
put the target row alone on the last page, and asserts that arrangement before
exercising the behaviour.

**A break test that fails to break is testing your assumption.** A deliberate
`.offset(offset + 1)` in the list query passed all 50 contract tests on the
devbox. The wiring was fine; the suite's assumption about itself was not. Every
pagination assertion was about rows the test had just created — the NEWEST rows,
at the end of an ascending list — and the row an off-by-one drops is the FIRST
one. The one-row-at-a-time walk then hit an empty page and treated that as the
end. Both walks now compare what they collected against the `total` the API
reports, in the helper rather than in the one test that was being edited. With
that assertion in place the same break turns four tests red.

**Latency is a path, and it had never been exercised.** Two pagination tests
timed out against the stage ALB after passing on localhost — twice each,
including the retry. Neither was about AWS. The page set `data-loaded="true"`
after its first render and never cleared it, so a spec that clicked Next and
waited for that attribute was answered instantly by the render from BEFORE the
click. It then read the pager's enabled state from the stale page, decided to
click again, and by the time the click landed the real render had disabled the
button — so Playwright waited for it to become enabled until the test timed out.
On localhost the response beat the check almost every time. The page now
exposes `data-renders`, incremented by every render, and clears `data-loaded`
synchronously at the top of `load()`; the specs wait on the counter changing,
which is a signal the past cannot satisfy.

**Three existing assertions had quietly become vacuous, and that was found by
reading.** Under pagination, a reload returns to page 1, so "the row I just
created is still there after a reload" would fail once the table outgrew a page,
and "the row I deleted is absent" would pass for a row that was merely on page 2.
Both now walk to the last page first.

**The migration stamps history.** Revision 0003 fills `updated_at` on existing
rows with its own `now()`, so every row that predates it reads as edited without
having been. The probe is created in the same run as the assertion, so the check
is sound — but its meaning is narrower than its name, and that is now written
beside it.

## The cycle

```text
deploy-stage #24   17m59s  FAILED - the two timing tests above
deploy-stage #25   10m20s  green, including the UI-write assertion in AWS
promote-prod #8    14m26s  approved, prod live, rollback steps skipped
destroy prod #18    8m30s  behind the approval gate, as Phase 13 found
destroy stage #19   8m44s
```

`deploy-stage` #25 was the first run of the whole cycle to include the ECS task
that asserts BOTH probes against RDS, and it passed: the create probe exists and
the edit probe was updated 0.2s after it was created. That is a browser action
reaching a database in private subnets, read back by a different process over a
different protocol.

The 15b debt is paid: `setup-terraform` v4 and `configure-aws-credentials` v6
ran in all four dispatch-only workflows for the first time, and none of them
failed. The suspect named in ADR-0030 was innocent.

## Validation

```bash
make test-api            # 50 passed, against Postgres
make test-regression     # 12 passed + both probes asserted in the database
make test-db             # DB assertion: all checks passed
make test-spec-coverage  # 3 spec files, all resolved by a project
make docs-check          # 6 documents, 0 findings
make tf-fmt tf-validate action-pins iac-scan image-scan secret-scan   # all clean
```

`ci` was green on all five AWS-free jobs before the cycle, and `local-ci` ran
the new regression suite on a database created from nothing — the path where no
row predates revision 0003.

Teardown, from the devbox under `demo-admin`, `sts` first and every result
assigned under `set -e` in a subshell:

```text
account: 993912191738
alb: []   rds: []   ecs: []   nat: []   eks: []
ecr (must NOT be empty): [aws-devops-sdet-demo-app]
```

The last line is the point. Phases 13 and 14 ran this check before AND after, so
an empty result meant something; this session only had an after, so a positive
control was put in the same command instead. Credentials that could not read the
account would have failed there rather than rendering five reassuring blanks.

## Break tests

Every new refusal was seen firing, with the status read directly rather than
through a pipe:

```text
assert_ui_write.py   both missing-variable refusals, including a value of only
                     whitespace; a planted row that was never updated (exit 1,
                     with the create half still passing, so the halves are
                     independent); an absent row (exit 1)
the offset walk      .offset(offset + 1) -> 4 contract tests red AFTER patch C,
                     0 before it
the last-page jump   removing it -> exactly one Playwright test red, the one
                     whose whole purpose is that behaviour
```

## Cost

stage was up about 1h15m and prod about 23m, both on the smallest shapes the
project uses. At list prices that is roughly $0.09 for the cycle. Everything
billable is gone and the absence was verified above.

## Follow-ups

```text
- 16b is untouched: structured JSON logs with a request id, a CloudWatch metric
  filter on 5xx, one alarm. It is the half that changes HCL.
- prod runs the smoke suite only, so PATCH and pagination have never executed
  against prod. That is ADR-0025 working as intended, not a gap - but it is
  worth saying out loud rather than discovering at a demo.
- the dashboard UP badge is still a snapshot in the present tense (Phase 13).
  This cycle did not touch it.
- the render counter is a general fix. Any future spec that waits for
  data-loaded alone is waiting for nothing, and nothing enforces that.

# 2026-08-08 — Phase 20b.1: a killed apply is not a cycle

The $0 half of 20b. Terraform's `-json` event stream is captured, folded into a
timeline and back into a readable log, and gated. Nothing was applied, no AWS
API was called, and none of it has met AWS yet.

## What this session established

A run that dies mid-apply cannot be reported as a cycle that happened. That is
the sentence the whole phase is for, and it is now enforced by a gate that has
been made red seven ways.

```text
scripts/tf-stream.sh       runs terraform with -json and captures the stream
scripts/fold-timeline.py   folds every stream into one timeline AND a legible log
scripts/check-timeline.py  the gate
make timeline-check        it, and it runs in ci.yml
tests/fixtures/timeline/   six cases, every one a real terraform run
```

Eight terraform invocations are captured: the stage apply, the prod apply and
the rollback apply, both destroys in `destroy.yml`, and self-service's apply and
both destroys. Each job folds with `if: always()`, because the run that died
half way is the run whose timeline matters.

## Three signals, and the weakest one wins

A stream can look finished and not be. The verdict is not read from the events
alone:

```text
the .rc file   written AFTER terraform returns. Missing means it never returned
               - cancelled, killed, runner lost - and no quantity of
               plausible-looking events outweighs that
the exit code  non-zero is a failure
the terminal   change_summary whose operation is apply or destroy. The "plan"
change_summary one does not count; a stream that stops after it stopped in the
               middle
```

The `.cmd` file — the arguments, written before terraform starts — exists
because of something the real streams said and no reading of the documentation
would have: **an apply that dies before finishing emits a `change_summary` whose
operation is `"plan"`.** A fold reading only the stream would label a
half-finished apply a plan. What was RUN is a fact the runner has and the stream
does not.

## The fixtures are real terraform runs, and one of them was really killed

Every `.jsonl` under `tests/fixtures/timeline/cases/` is actual `-json` output,
produced by `tests/fixtures/timeline/generate.sh`. It costs nothing and touches
no cloud: every resource is the built-in `terraform_data`, so `terraform init`
runs offline and no credential is involved.

Written fixtures were the alternative and they would have been wrong twice over.
Besides the `"plan"` summary above, an apply from a saved plan file — the shape
`deploy-stage` and `promote-prod` actually use — emits ONE `change_summary`, not
two. This repository's name for the general case is that a break test which
fails to break is testing your assumption about the tool.

`apply-killed` is not a truncated file. The generator starts a real apply whose
second resource sleeps, and kills the process while it is inside it.

They were AUTHORED against **OpenTofu 1.10.6**, which is what this chat session
could reach — `releases.hashicorp.com` is not fetchable from it — and that was
the caveat this summary was first written with, at the front rather than the
end. It is discharged: they were regenerated on the devbox with **terraform
1.15.8**, and all six expectations held with no edit.

The evidence for that is not the event counts, which came out identical (16, 15,
14, 10, 13, 13) and would look exactly the same if nothing had been regenerated
at all. It is the streams: `"terraform":"1.15.8"`, `@module: terraform.ui`,
`ui: 1.3`, where the fork wrote `tofu` and `ui: 1.2`, across 8 files and 99
lines. The fold was written against the schema rather than against a fork's
quirk, and it survived a gap larger than any version bump — which is a better
result than the one being tested for.

One asymmetry recorded rather than fixed: **the devbox runs 1.15.8 and the
workflows pin 1.15.5.** Changing what CI runs deserves its own reason and its
own session, and `cases/GENERATED-BY` names whichever binary produced the
fixtures, so the question can never be answered from memory.

## The over-determined case, and the one added to fix it

`apply-killed` is missing three signals at once: no exit code, no terminal
summary, and a resource that started and never finished. Remove any one of the
three rules and it is still correctly incomplete — which sounds like a strength
and is a measurement problem. The case cannot show which rule is doing the work.

So `apply-complete-no-rc` was added: a stream in which every event says the
apply worked, with its `.rc` removed. That is what a process killed between
finishing and recording its status leaves behind, and the fold must still refuse
to call it complete.

Break test 4 then said something better than what it was aimed at. Removing the
missing-`.rc` rule did not turn that case green — it turned it `errored`,
because the next rule down (`exit_code != 0`) catches `None` as well. The rule is
read, and it is not the only thing standing between a lost exit code and a green
timeline. That is worth knowing, and it is only visible because the isolated
case exists.

## Two things the plan did not have

Both found by writing it, and both silent if missed.

```text
key        run id PLUS JOB. self-service launches an environment and destroys it
           again inside ONE run, in two jobs, and both publish. A key of run id
           alone would have the teardown's timeline overwrite the launch's,
           leaving one object that looks like a complete record and is half of
           one. latest.json is overwritten on purpose - it is the at-rest state
--exclude  publish-site.sh syncs site/ with --delete. Without a third exclusion
           the next push to main would delete every published timeline, and the
           map would keep working from the one published minutes earlier until
           it did not
```

Neither needed an IAM change: the narrow publish role already covers the whole
bucket, and nothing here asks for more. No CloudFront invalidation per timeline
write either — a short `max-age` costs a minute of staleness on a picture whose
subject takes fifteen, and an invalidation per write would be several per cycle.

## The regenerator was deleting the expectations

`new_case` wiped the whole case directory, so running `generate.sh` removed
every `expected.json`. Five cases went from green to "no expected.json" at once,
which is at least loud; the same mistake one step subtler would have been
silent. Only `streams/` is regenerated now. `expected.json` is the human half of
a fixture — it says what the case is supposed to MEAN — and nothing generates it.

## Break tests

Seven ways red, both controls green, exit codes taken directly rather than
through a pipe, tree committed before anything was broken. Evidence:
`docs/sessions/2026-08-08-phase-20b-1-timeline-break-tests.log`.

```text
1  a plausible exit code 0 planted beside the KILLED stream
2  the terminal change_summary deleted from a complete stream
3  one line of a stream corrupted mid-write
4  the fold's missing-.rc rule removed
5  a resource that only ever STARTED counted as complete
6  the fixture directory emptied - it refuses rather than passing 0/0
7  the readable log stops printing error diagnostics
0/7  controls: the untouched tree, before and after
```

Test 7 is there because the readable log is half the deliverable. `-json`
REPLACES terraform's human-readable output in the Actions UI, so the fold prints
a per-resource table and every diagnostic in full, with errors OUTSIDE the
collapsed group — a collapsed error is a lost error, and that is the entire cost
of `-json` paid in one place.

## What is NOT done

```text
nothing has run in AWS      no timeline object exists in the bucket
nothing draws it            the page is untouched; the map has no run layer yet
modules unconfirmed         the fixtures use no modules, so what
                            hook.resource.module and addr look like inside one
                            is read from the documentation, not observed. The
                            last piece of the schema not settled on the devbox
the workflow half           if: always() folding a cancelled RUN is proven
                            against fixtures, not against GitHub
```

All of it is 20b.2, and it costs about $0.03.

## Validation

All of it run on the devbox, 2026-08-08.

```bash
tests/fixtures/timeline/generate.sh   # terraform 1.15.8, 6/6 unchanged
make timeline-check
make docs-check
git diff --stat
```

## Files

```text
scripts/tf-stream.sh                        new
scripts/fold-timeline.py                    new
scripts/check-timeline.py                   new
tests/fixtures/timeline/                    new: generate.sh, README.md, 6 cases
scripts/publish-status.sh                   publishes the timeline
scripts/publish-site.sh                     a third --exclude
Makefile                                    timeline-check
.github/workflows/ci.yml                    timeline-check
.github/workflows/deploy-stage.yml          capture, fold, publish
.github/workflows/promote-prod.yml          capture (apply and rollback), fold
.github/workflows/destroy.yml               capture (both destroys), fold
.github/workflows/self-service.yml          capture in both jobs, fold in both
README.md                                   the CI check list, without a total
docs/architecture.md                        the third dashboard source, marked
                                            as never having run
docs/phase-gates.md                         20b split into 20b.1 and 20b.2
docs/next-phases.md                          20b split, with what 20b.2 must show
```

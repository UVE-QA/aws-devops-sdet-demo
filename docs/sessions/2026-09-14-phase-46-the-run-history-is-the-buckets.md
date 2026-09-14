# Phase 46 — The run history is the bucket's

**2026-09-14**, the same night as Phase 45, on `next`. **ADR-0100**, one
record, six decisions — and no cycle yet; the proof is the next one.

## What the owner's screen said, and what the owner knew

*Run history unavailable — HTTP 403 … Last successful read in this browser
session: none yet*, over cycle #32 in flight. The page's answer was the
right one — the button closed on the bucket's pulse, the panels from the
bucket, the cycle honestly *not shown* — and the first diagnosis was the
usual one: the anonymous budget, other tabs, an hour's wait. The owner
knew better:

> ты учитываешь, что у нас есть еще второй проект (зиро траст) который тоже
> отображает живые данные из другого репо тогоже аккаунта ГХ

Sixty requests an hour is per IP address, not per repository. Two
dashboards in one browser page the same sixty, and the conditional-request
and one-poller-per-origin fixes proposed first were polite ways of losing
slower. The decision the owner took in one line — *да, делай после #32* —
is the one that removes the read: the cycle publishes its own history.

## What was built

`scripts/publish-runs.sh` writes `status/runs.json` — the forty newest runs,
the forty newest of `main`, the jobs and steps of one run — with the
runner's token and the site-publish role. Three writers: the progress
watcher every job already runs, once a minute and once at its start;
`publish-status.sh` at a job's end; and `publish-runs.yml`, which GitHub
starts on `workflow_run: completed` for the four lifecycle workflows and
which writes the one reading no job of a run can take. The page reads the
bucket first, on its own tick, with `no-cache` so an unchanged document is
a `304`; GitHub only when the snapshot is missing, or when it claims a run
still going three hours on. The history clock names the snapshot and who
wrote it; the budget line says GitHub was left alone.

Run against the real API for #32 before any of it was wired: 40 runs, 40
of `main`, 8 jobs with their steps, 111 KB.

## The gate

The in-flight check gained a `snapshot` state — in-flight with the document
present and every GitHub request answering 403 — and one claim: the same
cycle, verdict and history the API reading drew, zero requests to GitHub, no
banner, the bucket named on the clock, the button as the API reading drew
it. The claim's first version held the button to *closed* and was wrong:
the in-flight run is an owner's deploy-stage, which the busy rule (launches
and the bucket's pulse) never closed on, and the API reading had it open
too. The claim compares the two readings now rather than deciding alone.
Every older state has no snapshot and gates the fallback as before.

Relayed to the zero-trust-lab session, at the owner's request, with the
shape of the fix.

## The proof, and what it showed beside itself

Cycle #33 from `next`, launched on the owner's word: the first snapshot was
in the bucket 75 seconds after the run began, written by the launch job's
watcher, and the `next` page rendered over the live bucket with every
GitHub request answering 403 drew the cycle from it — zero requests to
GitHub, no banner, the history clock naming the snapshot, the button closed
on the run. And beside it, *Current cycle* showed a finished run of `main`
from two days earlier while three panels said #33 was in progress: the
owner's condition on the released-line rule, come due on a Monday. ADR-0093
D2 is amended a fourth time - a run in flight from any branch is the cycle
view's subject, named with its branch; the history stays the released
line's - and the `foreign-in-flight` state holds both halves.

Also on the way, from the owner's reading of the redrawn picture: who talks
to the database, said as such - the rds module's admitted security groups
drawn from the client to the database, the credentials edge pointing at
Secrets Manager, and in the lab the Deployments that hold `DATABASE_URL`
connecting themselves, web among neither.

## The cycle

```text
#33  34800980236  02:58  success   67 m — launch 20, lab 21, promote 16,
                                   destroy 12, destroy-lab 14, hold 5,
                                   destroy-prod 12, release-lock
```

Three status files `destroyed` from #33. The completion hook did not fire:
a `workflow_run` trigger runs from the default branch's copy of the
workflow, and this one lives on `next` until the merge - so the last
snapshot is the destroy-prod job's, `in_progress` with six jobs done. The
page stops believing such a snapshot after three hours; `publish-runs.yml`
gained a `workflow_dispatch` with a `run_id` so the true one can be written
by hand, and the merge makes the hook real for every cycle after.

## After the merge

`main` fast-forwarded on the owner's word; publish-site and CI green. The
hand dispatch of `publish-runs` for #33 failed twice on the new file - a
checkout pinned to a SHA that did not exist, then the publish role refusing
a job with no environment (its trust is the deployed environments' subjects
and no branch; the job wears `stage`'s now) - and on the third wrote the
true snapshot: #33 `completed success`, eight jobs. And the owner, looking
at the live page: *Current cycle* was #23 from two days before while #33
had ended an hour earlier - ADR-0093 D2 amended a fifth time, the newest
lifecycle run of any branch at rest too, named with its branch.

## What is still open

The second merge, on the owner's word - the picture's tiles and the
cycle view - and the hook watched firing by itself on the next cycle. The picture's tiles - the owner is choosing
between three translucencies with mid-line arrows, sent this session, none
committed. The document's size — a job's steps travel whole — if the
bucket's egress ever matters.

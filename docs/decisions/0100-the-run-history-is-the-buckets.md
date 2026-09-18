# ADR-0100: The run history is the bucket's

## Status
Accepted (Phase 46, 2026-09-14). Amends **ADR-0026** (the page reads the
Actions API anonymously and paces itself by the budget) and **ADR-0062 D2**
(the idle interval derived from the remaining budget): both stay true of the
fallback and stop being the page's normal state. Keeps **ADR-0093** (the
page reports the released line) and **ADR-0035** (the button's refusals live
server-side) exactly where they are.

## Context

The dashboard read the GitHub Actions API from the visitor's browser,
anonymously: 60 requests an hour, and the page grew careful about them —
one list per poll, the released line by name once in ten minutes, the jobs
of a finished run never re-read, the interval derived from what was left.
On 2026-09-14 the owner's screen read *Run history unavailable — HTTP 403 …
Last successful read in this browser session: none yet*, over a cycle in
flight. The budget was gone before the tab's first request.

The number is **per IP address**, not per repository or per page. The
owner's browser reads two dashboards from the same address — this one and
zero-trust-lab's — and each pages the same sixty. Two open tabs during a
cycle are enough. The page's own frugality cannot fix a budget it shares
with a stranger, and conditional requests (a `304` is free) do not help in
the one state that matters, a run in flight, when the list changes on every
poll.

> ты учитываешь, что у нас есть еще второй проект (зиро траст) который тоже
> отображает живые данные из другого репо тогоже аккаунта ГХ

## Decision

**D1. The cycle publishes its own history.** `scripts/publish-runs.sh`
writes `status/runs.json` — the forty newest runs of the repository, the
forty newest of the released line, and the jobs and steps of one run —
taken with the runner's `GITHUB_TOKEN` (`actions: read`, 1 000 requests an
hour for the repository, none of them the visitor's) and put beside the
status documents the page already trusts, under the site-publish role.

*Amended 2026-09-18.* The two lists are the runs of the four lifecycle
workflows - `self-service`, `deploy-stage`, `promote-prod`, `destroy` -
asked for by name, merged and cut at forty, not the newest forty runs of
everything. Four days of the first shape were enough: 18 CI runs, 10
dependabot updates and 9 publishes had pushed all but three cycles out of
the released line's window, and the page's history read *1 of 3 failed*
over a span of days, worse with every push. The page never drew a
non-lifecycle run (its `WRITERS` table is the filter), so nothing on it
changes but the depth: forty cycles of `main` reach back five weeks. The
four names are now in three places - the page, the hook's trigger, the
script - and `lifecycle-list-check` holds them together.

**D2. Three writers, one document.** The progress watcher every job already
runs (ADR-0076) writes it once a minute and once at its start, so the page
learns of a job within a minute of its first step; `publish-status.sh`
writes it when a job ends, with that job's last step in it; and
`publish-runs.yml`, started by GitHub on `workflow_run: completed`, writes
the one reading no job of a run can take — the run with its final
conclusion, because a run is not complete until its last job is. The newest
writing wins; the document is replaced whole, never appended.

**D3. The page reads the bucket first and GitHub only without it.** On the
bucket's tick, with the status documents, the page fetches the snapshot
(`no-cache`, so the ETag makes an unchanged document a `304`). Present and
well-formed, it is the history: the same merge the API's answer went
through, the same jobs document, GitHub not asked at all. Absent, the page
asks GitHub exactly as before, paced as before. A snapshot that claims a run
still going three hours after it was written is a snapshot nobody replaced
and is not believed about the present; GitHub is asked.

**D4. The page says which.** The history clock names the bucket's snapshot,
who wrote it and when; the budget line says GitHub was left alone; the
footer's two clocks are the history's and the status's. The 403 banner is
the fallback's and stays.

**D5. Not a lifecycle workflow.** `publish-runs.yml` writes nothing but the
snapshot; the page's WRITERS table does not name it and it makes no
environment stale. It triggers from the default branch's copy of the file
for runs of the four lifecycle workflows from any branch — a `next` cycle
ending is news about the environments too (ADR-0093 D2, amended).

**D6. Gated on the fixture, both ways.** The in-flight gate gains a
`snapshot` state — in-flight with the document present and the API
answering 403 to everything — and holds the page to drawing the same cycle,
verdict and history it draws from the API, asking GitHub for nothing,
showing no banner, naming the bucket, keeping the button closed. Every
older state has no snapshot and gates the fallback, unchanged.

## Consequences

- Written 2026-09-14: the publisher (run against the real API for #32:
  40 runs, 40 of `main`, 8 jobs with their steps, 111 KB), the watcher's
  minute, the end-of-job call, `publish-runs.yml`, `actions: read` on the
  two workflows that lacked it, the page's snapshot reader with the shared
  merge, the clocks and the footer, the `snapshot` fixture state and its
  claim, and every page check tolerant of the document's absence.
- **Verified by cycle #33 (34800980236, 2026-09-14, 67 minutes, every job
  green - launch 20 m, lab 21 m, promote 16 m, destroy 12 m, destroy-lab
  14 m, hold 5 m, destroy-prod 12 m)**: the first snapshot was in the bucket
  75 seconds after the run began, written by the launch job's watcher; the
  `next` page rendered over the live bucket with every GitHub request
  answering 403 drew the cycle from it - zero requests, no banner, the
  history clock naming the snapshot, the button closed on the run, and once
  ADR-0093 D2 was amended the same night, the run itself as *Current cycle*
  with its steps. Three status files say `destroyed` and name #33. The one
  writer not seen: the completion hook, because a `workflow_run` trigger
  fires from the default branch's copy of the file and this one lived on
  `next` - so the last snapshot, the destroy-prod job's, said `in_progress`
  with six jobs done and one running. D3's three hours cover that once;
  `publish-runs.yml` gained a `workflow_dispatch` with a `run_id` so the true
  snapshot can be written by hand, and after the merge the hook writes it
  itself. The hand dispatch then failed twice before it worked, both times
  on this file: a checkout pinned to a SHA that did not exist (the other
  workflows' v7.0.1 pin now), and `Not authorized to perform
  sts:AssumeRoleWithWebIdentity` - the publish role trusts the deployed
  environments' subjects and no branch, so the job wears stage's
  environment. Third dispatch: `completed - 40 runs, 40 of main, 8 job(s)`,
  and the bucket's snapshot says #33 `completed success`.
- **Verified on the public path by #34 and #35 (2026-09-14), both pressed
  by the owner from a private window.** #34 died in two seconds on a reset
  connection to Docker Hub (the runner's, not ours) - and everything after
  it behaved: both destroys ran, the lock was released, and the completion
  hook fired by `workflow_run` for the first time and wrote the snapshot
  that says #34 failed. The build step got a second and a third try in one
  script (`scripts/build-and-push-image.sh`), then the base images moved to
  AWS's mirror at `public.ecr.aws/docker/library` after the image scan on
  `main` met the same reset. #35 then went green end to end in 67 minutes:
  the first snapshot 16 seconds after the press, the page closing the
  button and drawing the cycle with its steps from the bucket with zero
  requests to GitHub, and the hook writing `completed success` 12 seconds
  after `release-lock`. Three status files say `destroyed` and name #35.
- Relayed to the zero-trust-lab session at the owner's request: the same
  shape applies there, and until it lands the two pages compete for the one
  budget whenever both are open.
- Still to consider: the document is ~110 KB because a job's steps travel
  whole; if the bucket's egress ever matters, the steps of finished jobs can
  be trimmed to their conclusions.
- 2026-09-18: the window's finding from #37, the button's first cycle after
  the plan. Fixed by listing the four workflows by name (D1 amended); proven
  against the real API from the devbox - 40 lifecycle runs of `main` back
  to 2026-08-09 where the snapshot held three - and by a hand dispatch of
  `publish-runs` after the merge.

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

## What is still open

A cycle from `next`, on the owner's word: the snapshot within a minute of
the launch job, the completion hook after `release-lock`, a tab with its
budget spent drawing the cycle regardless. Then the merge. The document's
size — a job's steps travel whole — if the bucket's egress ever matters.

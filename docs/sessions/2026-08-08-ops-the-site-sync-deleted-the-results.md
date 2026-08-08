# 2026-08-08 — Ops: the site sync deleted the results it was publishing a reader for

Found immediately after 20c closed, by running its own validation command
against the live site. `results/stage/latest.json` returned 403.

**ADR-0044.** Break tests in
`docs/sessions/2026-08-08-ops-the-site-sync-deleted-the-results.log`.
Cost: nothing. Five read-only AWS calls under an SSO session, no cycle.

## What happened

`scripts/publish-site.sh` runs `aws s3 sync site/ --delete` and excluded three
prefixes: `status/`, `reports/`, `timeline/`. ADR-0042 added a fourth thing the
lifecycle writes — `results/` — earlier the same day, and nothing added the
matching line.

It stayed harmless for five hours because the two scripts only meet on a push to
`main` that touches `site/`, and there was none. The push that finally did was
**this project's own page release: the commit that taught the map to read those
results.** The sync deleted every one of them.

The comment sitting directly above the exclusion list had predicted it, in
those words:

> ONE PREFIX PER THING THE LIFECYCLE WRITES, and adding a prefix means adding a
> line here in the same commit. timeline/ was the third, and the cost of
> forgetting it would have been silent.

## How it was established, rather than assumed

The first reading was a 403, which is not evidence of deletion — 403 is also what
a bucket with an object-level policy returns for a key that never existed, and
CloudFront caching muddies it further. Four steps, each one narrowing:

```text
1  s3 ls results/            0 objects        - but an empty result is not a
                                                clean result
2  sts get-caller-identity   the ARN printed  - the credential is live, so the
   + ls <root>, timeline/,   541 / 8 / 2 /      empty answer above is an answer
     status/, reports/       528 objects
3  gh run view --log         777 lines for the newest publish-site, and ZERO
                             lines for the previous one. The instrument is
                             silent for exactly the run that would have proved
                             it, which is a documented failure of this tool -
                             so the logs decide nothing
4  s3 ls timeline/           31276975666-deploy.json written 20:44, AFTER the
                             last publish-site at 19:57 and BEFORE this one at
                             22:00
```

Step 4 is the control that differs in one variable. `timeline/` and `results/`
are written by the same script in the same run, minutes apart. One is excluded
from the sync and is still there; the other is not excluded and is empty. No
other difference exists between them.

## What is lost

`results/stage/latest.json` and the run-keyed evidence for cycle `31276975666`.
The bucket has no versioning, so they are not recoverable, and they will not be
reconstructed: the Playwright report survives as a workflow artifact but the
junit XML and the db assertion's log only ever existed on the runner, and folding
the one surviving report would publish a record claiming two suites never ran.

**The suite half of the map is therefore empty until the next cycle**, and that
is expected rather than a defect in the page 20c finished an hour earlier. The
Terraform half is intact: `timeline/`, the node states and every Playwright
report are under excluded prefixes.

## The fix, and why it is a check

One line — `--exclude "results/*"` — and then the rule stops being a sentence.
`scripts/check-publish-prefixes.py` reads every `s3://${SITE_BUCKET}/<prefix>/`
out of `publish-status.sh` and requires each to be excluded in
`publish-site.sh`. `make publish-prefixes-check`, in `ci.yml` beside `docs-check`
and `action-pins`.

Nothing that existed could have caught this. Every other gate here looks at the
repository, or at a fold; this is a relationship between two files in which each
is correct on its own, held together by a comment. A comment cannot fail.

## Six break tests, and two traps walked into while writing them

The first is not planted: it is `publish-site.sh` exactly as it stood at
`4600aeb`, the commit whose push did the deleting, run against the new check. It
reddens on the real defect.

```text
0  the repository as it was at 4600aeb    MISSING EXCLUSION: results/
1  a fifth prefix added to the writer     MISSING EXCLUSION: costs/
2  the sync stops passing --delete        REFUSED  (see below)
3  the writer moved away                  REFUSED
4  the writer names no prefix at all      REFUSED - a check that found nothing
                                          to check is not a green check
5  an exclusion nothing writes any more   a NOTE, still green - it costs nothing
```

**Two documented traps, walked into again in one hour.**

`COMMIT BEFORE BREAKING THINGS ON PURPOSE.` The first sweep restored each break
with `git checkout --` while the fix to `publish-site.sh` was still uncommitted.
It restored the file to HEAD — the broken version — and discarded the fix
silently. Identical in shape to the `ci.yml` pinning edit lost on 2026-07-28,
which is written down in the primer, which I had read four hours earlier. The
sweep was re-run from a committed tree.

`A BREAK TEST THAT FAILS TO BREAK is testing your assumption about the tool.`
Number 2 came back green. The check asked whether `"--delete"` appeared anywhere
in `publish-site.sh`, and the file's own comment explains what `aws s3 sync
--delete` does — so that refusal could never have fired, under any rewrite. It
now looks for the flag as an argument on a non-comment line, and the re-run at
the end of the log fires with the word still sitting in the comment.

## Files

```text
scripts/publish-site.sh              --exclude "results/*", and the comment now
                                     records what the fourth prefix cost
scripts/check-publish-prefixes.py    NEW - the check
Makefile                             publish-prefixes-check
.github/workflows/ci.yml             it runs in terraform-checks
docs/decisions/0044-...              ADR
```

## Validation

```bash
make publish-prefixes-check   # 4 written, all excluded
make docs-check
```

Not re-run here: the five gates 20c closed on, none of which this touches.

## What this leaves open

```text
- bucket versioning is still OFF. It would have made this recoverable, and it
  changes the cost and lifecycle story of a bucket holding every Playwright
  report ever published. Its own decision, deliberately not taken here
- the suite half of the map is empty until a cycle runs. 20d needs no new cycle
  - it reconciles the bill of the one that already ran - so whoever wants the
  page populated again should say so rather than assume 20d will do it
```

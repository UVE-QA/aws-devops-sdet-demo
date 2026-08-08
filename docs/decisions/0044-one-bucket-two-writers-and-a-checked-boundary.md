# ADR-0044: One bucket, two writers, and a boundary that is checked rather than remembered

## Status
Accepted (Ops, 2026-08-08). Written after `results/` — added to the lifecycle by
ADR-0042 the same day — was deleted from the public bucket by the first push to
`main` that touched `site/`.

## Context
Two scripts write to the dashboard bucket and they are not peers:

```text
scripts/publish-status.sh   what a RUN observed. status/, reports/, timeline/
                            and, since ADR-0042, results/. Runs every cycle,
                            under the narrow publish role.
scripts/publish-site.sh     `aws s3 sync site/ --delete`. Runs on every push to
                            main that touches site/, and on dispatch.
```

`--delete` removes anything in the bucket the repository does not contain. So
every prefix the first script writes has to be named in an `--exclude` in the
second, or it is deleted the next time somebody pushes a page change. That rule
was written down, in `publish-site.sh` itself, and it predicted its own breach:

> ONE PREFIX PER THING THE LIFECYCLE WRITES, and adding a prefix means adding a
> line here in the same commit. timeline/ was the third, and the cost of
> forgetting it would have been silent.

The fourth was `results/`. ADR-0042 added it to the writer on 2026-08-08 and
nothing added the exclusion. Nothing went wrong for the rest of that day —
because the two scripts only meet on a push to `main` that touches `site/`, and
there was none. The push that finally did was the one publishing the page that
**reads** those results. It deleted all of them.

The bucket has no versioning. `results/stage/latest.json` and the run-keyed
evidence for cycle `31276975666` are gone, and cannot be reconstructed: the
Playwright report was uploaded as an artifact, but the junit XML and the db
assertion's log were only ever on the runner, and folding the one report that
survives would publish a record claiming two suites never ran.

**Nothing detected this, and nothing could have.** Every existing gate looks at
the repository or at a fold; this is a relationship between two files, in which
each is correct on its own. The comment was the only thing holding it, and a
comment cannot fail.

## Decision

### D1 — the correspondence is read out of both files
`scripts/check-publish-prefixes.py` extracts every
`s3://${SITE_BUCKET}/<prefix>/` destination from `publish-status.sh` and requires
each one to appear as `--exclude "<prefix>/*"` in `publish-site.sh`. `make
publish-prefixes-check`, in `ci.yml` beside `docs-check` and `action-pins` —
repository-wide static checks, no AWS, no cost.

It refuses rather than passing when it cannot see what it is checking: a missing
file, and — the empty result that reads as clean — a writer in which the pattern
matches nothing at all.

### D2 — it also refuses if the sync stops deleting
If `publish-site.sh` no longer passes `--delete`, this check is meaningless
rather than green, and says so. Whoever reads that message decides which it is:
the danger is gone and the check should go, or the sync was rewritten and needs
rereading.

The first version asked whether the string `--delete` appeared in the file. Its
break test came back GREEN, because the file's own comment explains what
`aws s3 sync --delete` does — the refusal could not have fired under any rewrite.
It now looks for the flag as an argument on a non-comment line.

### D3 — a stale exclusion is a note, not a failure
An `--exclude` for a prefix nothing writes any more costs nothing and breaks
nothing. It is reported, because the list is meant to read as the inventory of
what the lifecycle publishes, and an entry that no longer corresponds to
anything makes that list a worse map. It does not redden the build.

## Consequences
- Adding a fifth published prefix now fails CI until the exclusion is added. That
  is the whole point, and it is the only moment at which anybody thinks about
  this file.
- The folded results of cycle `31276975666` are permanently lost. The timeline,
  the node states and the Playwright reports of that cycle survive — they are
  under excluded prefixes — so the map's Terraform half is intact and its suite
  half is empty until the next cycle publishes. **That gap is expected; it is not
  a defect in the page 20c just finished.**
- Bucket versioning is still off. Turning it on was considered and NOT decided
  here: it would have made this recoverable, and it also changes the cost and
  lifecycle story of a bucket that holds every Playwright report ever published.
  Whoever picks it up should treat it as its own decision rather than as a
  footnote to this one.
- `publish-site.sh` keeps both the comment and the check. The comment says why,
  the check says whether, and this ADR exists because the first without the
  second was not enough.

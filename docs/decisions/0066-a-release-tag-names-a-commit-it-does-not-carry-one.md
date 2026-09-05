# ADR-0066: A release tag names a commit; it does not carry one

## Status
Accepted (Phase 31, 2026-09-05). Narrows the mechanism of **ADR-0029**'s release
record without changing what it records. Leaves `contents: write` exactly as wide
as it was, and explains why the obvious fix was refused.

## Context

`promote-prod #14` deployed prod, waited for the service, waited for the public
HTTPS name, migrated, seeded, asserted the write reached RDS, ran the read-only
smoke green, and recorded the digest as the last good release. Then it failed,
and the run is red, on this:

```text
! [remote rejected] release-20260905-1603-3e41e80 -> release-20260905-1603-3e41e80
  (refusing to allow a GitHub App to create or update workflow
   `.github/workflows/publish-site.yml` without `workflows` permission)
```

The step tags **the commit the image was built from**, not the workflow's own
head — deliberately, and its comment says why: *they are usually the same commit,
and the day they are not is the day an untagged release becomes untraceable.*

That day was this one, and the cause was ordinary. Between the stage deploy that
produced the digest (`3e41e80`) and the promotion, a commit landed on `main`
(`e24169c`, ADR-0065) that changed `.github/workflows/publish-site.yml`. The tag
therefore points at a tree whose workflow file differs from the default branch's,
and GitHub's protection against a GitHub App creating or updating workflow files
refuses the push.

**The rollback correctly did not fire.** The pointer is written FIRST of the three
records precisely so a tagging failure is loud without being dangerous, and that
ordering held: prod stayed up, healthy, and serving the promoted digest, with the
rollback steps skipped. What was lost is the traceability record, not the release.

**The ECR half had already succeeded.** `aws ecr put-image` runs before the git
push in the same step, so the registry carries `release-20260905-1603-3e41e80`
and git does not. One step, two records, one of them written — which is the
failure mode the step's own comment worried about, reached by a route nobody
had named.

## Decision

### D1 — the tag is created through the Git Data API, not by `git push`

Two calls: `POST /repos/{repo}/git/tags` for the annotated tag object, then
`POST /repos/{repo}/git/refs` for `refs/tags/<name>`.

The protection being tripped exists to stop an App from INTRODUCING workflow
content. This ref introduces none — it points at a commit the repository already
holds. The API is the honest way to say exactly that: it takes a SHA and refuses
one the server does not have, so it cannot carry a tree with it. A `git push`
cannot say it, because a push is a transfer of objects and the server has to
assume the general case.

The credential does not change. It is the same `github.token` the push used; what
changes is the call.

The `git config user.name/email` above it goes with the `git tag` it existed for.
It was there because an annotated tag needs a committer and a runner has none —
itself a failure that once cost a step that had already published the ECR half.
The API supplies the tagger.

### D2 — `workflows: write` is refused, and the reason is written down

The one-line fix is to widen the token. It is declined.

This is the most privileged workflow in the repository and the comment above its
`contents: write` already calls that a widening. `workflows: write` is a token
that can rewrite CI definitions — including the definitions of the gates that
decide whether anything reaches prod at all. Weighed against an untagged release,
that is the larger hole by a long way, and the repository is public and argues
this posture in `docs/security-posture.md`.

Recording the refusal matters as much as the fix. The next person to meet this
error will find `workflows: write` at the top of every search result.

## Consequences

- The release tag stops depending on the relationship between the promoted commit
  and the default branch. It never should have: a tag names a commit.
- `release-20260905-1603-3e41e80` exists in ECR and not in git, and this change
  does not create it retroactively. The cycle of 2026-09-05 has a registry release
  record and no git one; that asymmetry is on the record here rather than repaired
  quietly.
- Nothing checks that `image_tag` is on the default branch, and this does not add
  such a check — the input is validated against ECR, not against git. The API call
  does not need it, and the gap is named rather than closed by implication.
- The two records in one step remain two records in one step. Splitting them so
  each fails on its own is not done here; it would change what a red promote-prod
  means, and that is ADR-0029's territory.

# ADR-0068: The public path reaches prod, and that sentence used to be the guarantee

## Status
Accepted (Phase 33, 2026-09-05). **Reverses ADR-0034's central property** and
narrows **ADR-0035**. Does not touch ADR-0021's IAM shape or ADR-0025's suite
split. Supersedes the paragraph in `docs/security-posture.md` about prod's
reviewer gate and the sentence in `README.md` about approval.

## Context

The dashboard's button ran stage and only stage. A visitor pressed it, watched
an environment come up, watched the suites run, and watched it torn down. What
they never saw was the half the project is actually about: a tested digest
promoted to a real prod behind HTTPS, and then that prod destroyed.

The owner asked for the whole lifecycle, unattended, from one press: stage up,
prod up, stage down, a visible five-minute countdown, prod down. Capped at three
a day for the public path, unlimited for the owner, who dispatches the workflows
directly and always could.

## What this costs, stated before what it buys

**ADR-0034 has a section headed "The public path targets stage. It cannot reach
prod."** It was not a check that could be relaxed. It was structural:

> prod has the approval gate in both halves (`trust_branch_ref = false` in IAM
> and the reviewer-gated GitHub Environment). The launch workflow resolves the
> stage deploy role only and declares no prod environment, so there is no value
> of any input that produces a prod credential.

That is now false, and this ADR exists so that it is false *on the record*
rather than quietly. Three documents claimed it and all three are rewritten in
the same commit range as the code, because a security claim that outlives its
premise is the exact defect **ADR-0062** was written about — and that one was
about a page qualifier, not about who can reach production.

The concern was raised twice before any code was written, and the trade was
taken deliberately by the owner. What is being traded:

```text
lost      an anonymous visitor could not obtain a prod credential. Now the
          cycle they start deploys and destroys prod.
lost      the `approve` in `deploy -> test -> approve -> promote -> destroy`.
          Removing the reviewer rule removes it from the OWNER's manual
          promotions too, not only from the unattended path.
lost      the page's own sentence - "the page holds no credential and cannot
          approve anything itself, which is the property that lets it be public
          at all" - is no longer the whole truth and is rewritten.
kept      the digest is still only promoted from a GREEN stage. `promote` is
          conditioned on `needs.launch.result == 'success'`, so the one thing
          the deploy -> test -> promote shape exists to prevent is still
          prevented.
kept      three launches a day, one environment at a time, the lock, the nonce,
          the kill switch. All of it lives in the Lambda and none of it moved.
kept      a dedicated AWS member account, `main` only, no static keys.
```

The blast radius is a demo account running this repository's own application
from `main`. That is a real bound and it is not the same as no bound.

## Decision

### D1 — the cycle CALLS the workflows it needs; it does not copy them

`promote-prod.yml` and `destroy.yml` gain `workflow_call` alongside their
existing `workflow_dispatch`, and `self-service.yml` calls them.

What would otherwise have been duplicated: digest resolution, the rollback
pointer, the ECS stability and public-HTTPS waits, the prod smoke, the release
record, the security-group revoke, orphan adoption, the ALB-before-IGW ordering,
the verification against the AWS CLI, and the cost fold. Two copies would be two
definitions of what *promoted* and *destroyed* mean. This project has paid for a
definition on two hosts twice — the image scan that scanned postgres, and the
palette parsed in two places — and does not need a third.

`confirm: DESTROY` stays in the callable signature rather than being defaulted
away. The point of that string is that something has to say it out loud, and a
caller exempt from saying it would be a caller that never had to mean it.

### D2 — the order is what a visitor watches, not what is convenient

```text
launch        stage up, migrate, seed, the suites
promote       the tested digest to prod           needs: launch, green only
destroy       stage down                          needs: launch, promote
hold          publish the deadline, wait 5 min    needs: launch, promote, destroy
destroy-prod  prod down                           needs: promote, hold
release-lock  the lock, last of all               needs: everything
```

Stage cannot come down before the digest it proved has been promoted, and the
lock cannot be released while prod is still up — a second visitor starting a
cycle on top of a live one is the failure this ordering exists to prevent.

`destroy-prod` is `if: always()` and is NOT conditioned on the hold succeeding.
The hold is a sleep and a bucket write; neither is a reason to leave prod
running. If it dies, prod still comes down and the visitor simply never saw the
clock.

### D3 — the countdown publishes an INSTANT, and the page owns the arithmetic

`status/countdown.json` carries `starts_at`, not a number of seconds. A duration
would have been wrong the moment it was written; an instant is true whenever it
is read. The page computes the remainder against its own clock and reticks once
a second beside the elapsed clocks — the same argument **ADR-0067** makes about
an open cost, and the second time that shape has earned its place.

A deadline already past draws **nothing**, not a zero and not a negative. The
hold removes the document when it wakes, but a page can be holding a copy up to
one bucket-read old, and *"-00:07 to go"* is the kind of sentence a state nobody
designed produces.

It lives under `status/` on purpose. `publish-site.sh` already excludes that
prefix from its `--delete` sync; a new prefix would have needed a line there
too, and **ADR-0044** exists because that line was once forgotten and a cycle's
folded results were deleted from a bucket with no versioning.

### D4 — one path may be absent, and it is named rather than patterned

`check-page-inflight.mjs` refuses on any origin 404, because **ADR-0059 D5** was
written after ten run-layer documents 404ed in silence and every layout figure
since 20e turned out to have measured a shorter page.

`status/countdown.json` is a different category: it exists only in the few
minutes of a hold, so its absence is the state this page is in almost always. It
is exempted by an explicit one-item set with the reason beside it.

**A `status/` prefix would have been the wrong shape** and is refused: it would
have swallowed `stage.json` and `prod.json`, which are exactly the documents
whose silent absence that rule exists to catch.

## Consequences

- **The watchdog cannot reach prod, and this ADR does not fix it.** Its IAM
  policy scopes it to `Environment=stage`; ADR-0035's own words are that prod is
  "unreachable from this function by policy". So a run that dies after the
  promotion — force-cancelled, dead runner, GitHub unavailable — leaves prod up
  with **no out-of-band net at all**. `if: always()` is, in ADR-0035's phrase, a
  promise made by the thing that might not be there. Closing this needs the
  watchdog's policy widened to prod, prod resources tagged `Launch`/`ExpiresAt`,
  and a `terraform apply` on `infra/self-service`. **Until that apply, the
  unattended path's worst case is an indefinitely running prod.**
- **The TTL does not fit the longer cycle.** 90 minutes against a 45-minute
  launch job plus a promotion, a stage teardown, a five-minute hold and a prod
  teardown. `var.ttl_minutes` and the job timeouts are coupled by ADR-0035
  guardrail 3 and move together or not at all.
- The reviewer rule on the `prod` GitHub Environment is removed. That is UI
  state, which `docs/security-posture.md` already notes git cannot assert —
  so it is recorded here and nowhere enforceable, the same category as the
  fork-PR setting and the NS delegation.
- A full unattended cycle costs roughly the $0.0836 .. $0.0928 measured on
  2026-09-05, so three a day is about $0.28 and a bad month is under $9.
- The cost fold now has a reason to run on an environment nobody watched come
  up, which is what **ADR-0067**'s open figure was built for one phase earlier.

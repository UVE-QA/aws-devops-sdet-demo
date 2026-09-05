# Phase 31 — The page a stranger gets, and the two documents that had no policy

**2026-09-05.** Driven from the devbox with a live cycle. **ADR-0064**,
**ADR-0065**.

`main` was four commits BEHIND what this devbox held when the session opened:
Phase 30's whole instrument — `scripts/watch-page.mjs`, four commits — had been
committed on 2026-08-12 and never pushed, along with its two watch logs and
their 11 MB of jsonl. Nothing on GitHub knew Phase 30 existed. That is the
second thing this session found before it started, and the first is below.

## The subject

A reader who arrives from outside, spends under two minutes, and leaves. Every
page decision from 20e to 29 was made for a different subject: *is this true,
and does the page say when it is true*. This one asks *does a stranger reach the
conclusion the page is evidence for*. Two of the four findings below are only
visible from that seat.

## What the Dependabot backlog actually was

Four PRs open, the oldest 33 days, all red. **Not one of them was red because of
its own bump.** Every one failed `image-scan` on the same 36 FIXABLE HIGH
findings across four CVEs — `CVE-2026-53612/13/14/15` — in the `util-linux` and
`shadow` packages of the `python:3.12-slim` base image. All OS packages; no
Python or npm dependency appeared in any of them.

The gate was doing its job. `scripts/summarise-trivy.py` fails on fixable-only
and reports the rest, which is the policy that stops a red build from training
people to ignore it. What it was failing on was a base image nobody had rebuilt
since 2026-08-12 — **which is also the last time `main` ran CI at all**. The four
PRs were the only thing in the repository still asking the question.

Verified before touching anything: pulled a fresh base locally and ran
`make image-scan`, which came back **0 fixable, 54 with no fix available**, exit
0. Debian had shipped `2.41.5-0+deb13u1`. So the four runs were re-run on their
existing head SHAs rather than rebased or overridden, and went green.

`#9` had a second failure of a different kind: `local-ci` **cancelled after
6h00m15s**, hung on the Playwright smoke step. The same job on rerun took 2m13s.
A hang, not a defect in a patch bump of sqlalchemy.

All four squash-merged. Zero open.

## Two gates caught real drift on the way back to green

Both from the merges, and both worth recording because one of them refused
rather than answered:

- `site-data-check` wanted `topology.json` regenerated — the ADR count moves when
  `docs/decisions/` gains a file, which is Phase 22's finding still working.
- `suite-inventory-check` **REFUSED**: the repository now pinned
  `@playwright/test` 1.62.1 and this devbox had run 1.62.0. It declines to compare
  inventories collected by two versions, because the difference would be reported
  as drift in the suites. A gate that says "I cannot answer this" instead of
  answering it wrongly.

## ADR-0064 — the header states the claim, and the control outranks the clocks

The identity bar described the system and never said what the system
demonstrates. One sentence added to the paragraph that was already there — no new
element, no section, no heading — saying that there is no manual AWS operation
anywhere in the lifecycle, teardown included, and that every state it leaves is
read back out of AWS afterwards rather than taken from the run that claimed it.

Deliberately not the words already on the Environments panel. A claim in the
header and its evidence in the panel below should not be the same sentence.

The Launch control was drawn in less weight than two timestamps. ADR-0048 D1 put
it in the Environments panel — correctly, and that reasoning is untouched — and
called it the panel's footer. The clocks then landed in the same panel and are
the panel's footnote *by their own comment*. So the only control on the page that
spends money ranked below the two timestamps that date the thing it acts on, in
the same outline weight as `Refresh`, which re-reads a JSON document. Nothing
decided that; it is what two correct decisions made separately add up to.

One word of D1 withdrawn — *footer*. Same panel, same refusals, still hidden
entirely while disabled. Filled with `var(--accent)` on `var(--bg)` text so it
follows the theme, measured 4.6:1 light and 8.2:1 dark.

**Named rather than quietly accepted:** `contrast-check` does not cover this. Its
contract is the map's state boundaries and a control is not a state, so those two
ratios were computed by hand and no gate will notice a palette edit that takes
them under the floor.

## ADR-0065 — the page that says "observed" had no policy about its own freshness

Found by opening the live page in a browser rather than by reading anything.

A fresh tab rendered the PREVIOUS page — old header, `64 decision records` —
minutes after a publish whose CloudFront invalidation had completed, while
`curl` against the same URL in the same minute returned the new one. A hard
reload fixed it, which is the signature of heuristic freshness, not of a stale
edge.

`scripts/publish-status.sh` has always set `no-cache, max-age=0` on the documents
a CYCLE writes. `scripts/publish-site.sh` set nothing on the page itself, so
`index.html` and `data/topology.json` went to S3 with no `Cache-Control` at all —
which is not uncached but heuristically cached, commonly a tenth of the
document's age. The page live that morning was 24 days old, which buys a
returning visitor's browser roughly two days of a copy that a new publish has
already replaced. The invalidation does not reach it; it only empties the edge.

The finding is not the two days. It is which document had no policy: the page
whose whole argument is that state should be observed rather than assumed was the
one making no claim about whether what you were reading was current.

Second load-bearing flag missing from the same `aws s3 sync`, after the
`--exclude` that ADR-0044 exists for. The path filter gains
`scripts/publish-site.sh` in the same commit — the workflow fired on `site/**`
and on itself but not on the script that decides what is uploaded and with what
metadata, which is a publish path that does not fire on a change to the publish
path.

Verified live after the republish: `cache-control: no-cache` on `/` and on
`/data/topology.json`, both bare an hour earlier.

## ADR-0044's exclusions, proven live and by accident

The cache fix was pushed WHILE the cycle was running, which fires `publish-site`
and its `aws s3 sync --delete` across the bucket the cycle is writing into. That
is precisely the hazard ADR-0044 was written for — after a publish deleted the
folded results of cycle 31276975666, which do not exist any more.

All five run-layer documents survived: `/results/{stage,prod}/latest.json`,
`/cost/{stage,prod}/latest.json`, `/timeline/stage/latest.json`. The exclusions
held under a real concurrent cycle for the first time; nothing had ever exercised
them that way, and this session did it by accident.

(A first check reported 403 on two of them and was wrong about the paths, not the
objects. This bucket answers **403 for a missing object**, being private behind
OAC without `ListBucket` — which Phase 28 already recorded.)

## The cycle, and what it found

Ordered explicitly after the three cleanup tasks were reported, and watched
throughout by `scripts/watch-page.mjs` — Phase 30's instrument, which had been
built on 2026-08-12 and never pushed. **1009 lines, 16 CHANGED frames**, one tab
held open from before the first dispatch, sentinel intact throughout.

```text
deploy-stage #35   success   29/29 steps
promote-prod #14   FAILURE   32 of 33, on the last line of the tagging step
destroy stage      success   "OK: no billable stage resources remain"
destroy prod       NOT RUN   prod deliberately left up (below)
```

### What the page got right, watched live

- **The per-environment tense.** With stage fresh and prod not yet promoted, the
  stage nodes carried unqualified figures and every prod node still read *these
  figures are from the cycle before this one*. That is Phase 25's fourth finding —
  every prod verdict reading `from the previous run` during a stage-only deploy —
  holding on a live cycle for the first time.
- **The node-level run layer.** `stage.migrate → its phase is running`,
  `suite.db.stage → running now · its report arrives when the step ends`, and
  `prod.vpc` moving from `destroyed · from the cycle that ended` to
  `measured · from the cycle before this one` the moment prod began applying.
  ADR-0054's process/state split, doing real work.
- **The derived poll interval.** `GitHub every 138 s` → `126 s` → `73 s` as the
  hour's anonymous budget was spent. ADR-0063 D2 live.
- **The human gate.** With `promote-prod` waiting, the page rendered a
  `Review deployment on GitHub →` button and the sentence that is the whole
  security posture of a public dashboard: *the page holds no credential and
  cannot approve anything itself — which is the property that lets it be public
  at all.*
- **The staleness went.** `dated 2026-08-12` → `dated 2026-09-05`, which was the
  entire point of ordering the cycle.

### ADR-0066 — the promotion failed on its last line, and prod was fine

Covered in full in the ADR. Prod deployed, waited, migrated, seeded, asserted the
UI write reached RDS and smoked green; the run is red because a `git push` of the
release tag was refused. The **rollback correctly did not fire**, because the
last-good pointer is written first of the three records for exactly this reason.

**Two records, one step, one of them written.** `aws ecr put-image` runs before
the `git push` in the same step, so `release-20260905-1603-3e41e80` exists in the
registry and not in git. Not repaired retroactively.

**Self-inflicted, and that is the useful part.** The cause was ADR-0065's own
commit changing a workflow file between the tested digest and the promotion. A
cycle run from a quiet tree would not have found it, and the step's comment had
already worried about the two commits diverging without naming this route.

### ADR-0044's exclusions, proven live and by accident

The ADR-0065 fix was pushed WHILE the cycle ran, firing `publish-site` and its
`aws s3 sync --delete` across the bucket the cycle was writing into — the exact
hazard that ADR exists for, after a publish once deleted the folded results of
cycle 31276975666. All five run-layer documents survived. Nothing had ever
exercised those exclusions against a real concurrent cycle.

## What is left open

- **Prod is deliberately still up**, decided at 16:20 rather than destroyed:
  a live `https://app.demo.uveapp.net` is stronger for a first-time reader than
  a destroyed one, and the submission is imminent. Priced from the repository's
  own `rates.json`: ALB $0.0225/h + RDS $0.0160/h + Fargate $0.0123/h ≈
  **$0.051/h ≈ $1.22/day**, plus ~$0.08/day of gp3. **The cost fold prices by
  LIFETIME, so this cycle's prod figure stays open until prod is destroyed.**
- **The release tag for this cycle** exists in ECR and not in git. ADR-0066 does
  not create it retroactively.
- **The run badge counts unrelated workflows.** `all 3 succeeded · 1 still going`
  mixed this session's docs CI and publish-site runs in with the lifecycle, and
  the count went DOWN from 4 to 3 as they displaced older ones. A reader cannot
  tell which runs are the cycle.
- **The Launch button is fully enabled during a cycle**, and pressing it would
  get a refusal the page already has the state to predict.
- **Two comments with no gate behind them**: the launch button's contrast
  (ADR-0064) and the page's cache policy (ADR-0065). Both say *why*; neither has
  anything saying *whether*, unlike the publish prefixes, which do.

## Validation

```text
make gates                12/12 green
docs-check                6 documents, 0 findings
site-page-check           matches the template
contrast-check            7 states, 3 ancestries, both themes
page-tense-check          16 cases, 49 calls
page-freshness-check      3 cases
page-inflight-check       every claim held, both states
image-scan (local)        0 fixable, 54 with no fix available
live                      cache-control: no-cache on / and /data/topology.json
```

---

# Phase 32 — An open cycle publishes a rate, not a figure

Same session, same day. Taken because leaving prod up made the gap impossible to
look away from: the cost box read *What the last cycle cost* over the CLOSED
figure of 2026-08-12 while prod was demonstrably running. **ADR-0067.**

`fold-cost.py` could already price an open cycle — `--destroy` has always been
optional — and `publish-status.sh` refused to publish the result. **That refusal
was right about what it refused**, and every word of it survives. What changed is
what an open document CARRIES: `usd_per_second` per open row, so the document is
the INPUTS rather than a figure that ages, and the page multiplies against its
own clock. Measured $0.0409 → $0.0418 over 60 s, exactly rate × 60, no `render()`.

## Two things went wrong, and both are the phase

**The gate was green over the new field before it checked it.** `check-cost.py`'s
`diff()` iterates `for key in expected`, so a key the fold emits and no fixture
names is invisible — the first 11/11 was vacuous. Now named in the open case's
`expected.json`, derived from that fixture's own `usd / seconds` rather than from
the new code, and a break test bites: a per-minute rate gives `expected 0.001,
folded 0.06`, control green either side.

**The page crashed on a document shape this repository already contains.**
`resources` is a LIST from the fold and an OBJECT keyed by address in
`tests/fixtures/page-inflight/`. `.filter()` on the object is undefined,
`renderCostLine()` threw, `render()` never ran: an empty map, no visible error,
the panel above it rendering happily. Third renderer here to die half way down
the page. `page-inflight-check` caught it; **`make gates` was 12/12 green over
the crash**, because every gate in the cheap list reads a file rather than a
rendered page.

The bisect was **three wrong guesses long** — the tick, the heading, then a
suspicion of flake. What settled it was making the branch unreachable while
leaving the code in place: the only variant that separates *this code is wrong*
from *this code runs at all*.

## What this phase did not do

It is **not visible on the live page**. The wiring runs at apply time and the
prod that is up was applied before it existed, so the open figure appears at the
next `deploy-stage` or `promote-prod`. Nothing hand-published to the bucket.

## Validation

```text
make gates                12/12 green
check-cost.py             11/11 fixtures, incl. the rate under gate
break test                per-minute rate caught by name, control both sides
page-inflight-check       every claim held, in both states
page-tense/freshness/contrast/live-state   all pass
ci on main                green, all four jobs
```

---

# Phase 33 — The public path reaches prod, and that sentence used to be the guarantee

Same session. The dashboard button ran stage and only stage; it now runs the
whole lifecycle unattended. **ADR-0068.**

```text
launch        stage up, migrate, seed, four suites
promote       the tested digest -> prod        needs: launch, GREEN only
destroy       stage down                       needs: launch, promote
hold          publish the deadline, 5 min      needs: launch, promote, destroy
destroy-prod  prod down                        needs: promote, hold
release-lock  last of all                      needs: everything
```

Three a day, one environment at a time, same lock, nonce and kill switch. **The
Lambda needed no change at all** — it dispatches `self-service.yml` by filename
and that file simply does more.

## What was traded, said before what was built

ADR-0034 had a section headed *The public path targets stage. It cannot reach
prod*, and it was not a check but a structural fact. That is false now. The
concern was raised **twice** before any code was written and the trade was taken
deliberately.

Four documents claimed it — the ADR, `docs/security-posture.md`, the README, and
the page's own strongest sentence. All four are rewritten. ADR-0034's section is
**kept and marked reversed** rather than struck out: deleting the reasoning would
hide what was given up.

The reviewer rule is removed from the `prod` environment, which takes the gate
off the **owner's** promotions too. The IAM half is untouched and still the
stronger half. The way back is one API call, written down for the reason the
kill switch's `delete-item` is written down.

## The cycle calls; it does not copy

`promote-prod.yml` and `destroy.yml` gain `workflow_call`. Two copies would be
two definitions of what *promoted* and *destroyed* mean, and this project has
paid for a definition on two hosts twice. `confirm: DESTROY` stays in the
callable signature: a caller exempt from saying it is a caller that never had to
mean it.

## Two gate catches, both self-inflicted

- The tile was first rendered from `renderBanners()` in the **first** script
  while `RUNSTATE` lives in the second — a `ReferenceError` on every render and
  two red gates. Same cross-script coupling Phase 22 paid for, same file, four
  phases later.
- `page-inflight-check` refuses on **any** origin 404 (ADR-0059 D5). A document
  whose absence is its normal state is named in an explicit **one-item** set; a
  `status/` prefix would have swallowed `stage.json` and `prod.json`, which are
  exactly what that rule protects.

## Not applied, and that is the open risk

`infra/self-service` carries `watched_environments = ["stage", "prod"]` and
`ttl_minutes` 90 -> 150, and **neither is applied**. Until that apply, a run that
dies after the promotion leaves prod up with nothing able to remove it —
`if: always()` is, in ADR-0035's phrase, a promise made by the thing that might
not be there. `terraform validate` and `fmt` are clean, which is all a checkout
can say and is not the same as a net.

## And session-close was green over this phase being unrecorded

It compares the narrative's phase against the newest session file. With no
Phase 33 file, both said 32 and agreed — about a picture that had simply
stopped. **A record that contradicts itself is caught; a record that ends is
not.** Tenth time in this project that a gate has been green over its own
subject, and the first where the subject was the record itself.

## Validation

```text
make gates                    12/12 green
page-inflight/tense/freshness/contrast/live-state   all pass
terraform validate            infra/self-service valid; fmt clean
countdown                     4 min 11 sec -> 3 min 08 sec over 63 s; removed past zero
prod environment              protection rules now [branch_policy] only, verified
ci on main                    green
```

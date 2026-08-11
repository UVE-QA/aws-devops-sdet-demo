# Phase 26 — Every figure measured the short page

**2026-08-11. $0, no AWS call, nothing applied. ADR-0060.**

Closes **ADR-0059 D5**, the thing Phase 25 found and could not stop to fix:
`measure-page.mjs` mocked three of the page's four sources and let the fourth —
the run layer, ten origin-relative documents — 404 against its own static
server. So every layout figure this project has argued from since 20e measured a
page on which no node printed a figure.

Main was green when this session started: `ci #31454354555` on `440f988`,
checked before anything was touched.

## What changed

```text
scripts/measure-page.mjs               serves the layer over the top of site/,
                                       refuses on an origin 404, parses every
                                       layer document before the browser starts
tests/fixtures/page-measure/layer/     the ten documents, REAL and unmodified
tests/fixtures/page-measure/README.md  four sources, not three
scripts/remeasure-page-figures.sh      the comparison, re-runnable
```

## The finding, and why the instrument could not have found it

The guard `measure-page.mjs` already had watches what LEAVES the origin. The run
layer is origin-RELATIVE, so those ten requests went to the instrument's own
static server, which does not contain them and never will — the layer is what a
cycle publishes into the bucket beside the page. The page's own reader is
`r.ok ? r.json() : null` inside a `.catch(() => null)`: no banner, no error,
every node reading `not run yet`, and a page shorter and quieter than the one a
visitor gets.

Fourth time here that a sound instrument was aimed at the wrong scope and read
green — after 20a's document-level overflow, 20m's two pages converging on the
same wrong caption, and 25's gate aimed at a function the renderer skipped.

**It was found by building a fixture for a different gate.** Phase 25 needed the
run layer for `page-inflight`, discovered no fixture here had ever supplied it,
and wrote the note this phase implements. Nothing about running `measure-page`
would have said anything.

## The fixture is real, and deliberately not tidied

The ten documents were captured from `https://demo.uveapp.net` on 2026-08-11,
byte for byte: the cycle 20m ran on 2026-08-09 — `deploy-stage #32`,
`promote-prod #11`, `destroy #45`, `destroy #44`. The page draws
`stage $0.0529 .. $0.0584` and `prod $0.0182 .. $0.0237` from them, which are
the two prices 20m recorded in the cursor. That agreement is the fixture's own
provenance check.

One copy serves both sets, because both declare the same `meta.now`.

The layer's cycle is 18 hours AFTER that clock and it was left there rather than
shifted back a day. Nothing on the page turns it into an age — the figures are
durations, the cycle carries a date, and every `… ago` string comes from
`runs.json` and the status files — and that was established by reading the
rendered page, not by reasoning about it.

## D2 was not in the plan

The plan said: serve the layer, refuse on a 404. Asking what the 404 refusal
does NOT cover produced the other half. `.catch(() => null)` makes a MALFORMED
document indistinguishable from an absent one, and a 404 check cannot see it —
the request succeeded. So every file under the layer is parsed before the
browser starts, and the break test for it is `[3]`.

## The break tests

`docs/sessions/2026-08-11-phase-26-layer-break-test.log`, taken on the devbox on
the pinned chromium, tree committed first, exit codes read straight after a
redirect and never through the pipe into `tee`.

```text
[0] control, the layer in place                     exit=0   3321px
[1] one document removed                            exit=2   names it
[2] the whole layer directory gone                  exit=2   names the directory
[3] a document present and unreadable               exit=2   names the parse error
[4] control again                                   exit=0   3321px
```

`[4]` matters as much as the three refusals: the same figure to the pixel, so
the restores were clean and `[1]`–`[3]` were measuring what they claimed to.

**The 403 branch is carried and is NOT claimed as exercised.** It fires on a
path that escapes both roots, and no browser can produce one: `..` above the
document root is normalised away before the request is sent. It is kept
byte-identical to `check-page-inflight.mjs`'s for the same reason that one
exists, and this paragraph is here so a later session does not read the branch
as tested.

## The remeasurement

`scripts/remeasure-page-figures.sh`, output in
`docs/sessions/2026-08-11-phase-26-remeasurement.log`. Five commits, each
measured TWICE: with the instrument that produced its figures, and with this
one. The baseline half is what makes the comparison instrument-to-instrument
instead of figure-to-memory, and it did its job — every recorded figure came
back exactly, 1878, 1760/1790/2190, 2039 and 1.9 screens, 8682, 3116, 7979,
1432.28, 967.85, 694.72, 143.69, 295.58.

One exception, recorded rather than rounded away: 20j's `909.65px` of air at
1440 comes back as `909.63px`, on both hosts.

The table is **ADR-0060 D4**. Three sentences from it:

- **`--node-min: 18.5rem` is untouched to the hundredth of a pixel.** The floor
  is a horizontal measurement of node names; what the layer adds is vertical.
  The one figure in this project that set a CSS variable is the one the defect
  could not reach.
- **`main: 120rem` is untouched and slightly better than recorded** — the saving
  grows from 88px to 107px at 1920, and 1440 is unchanged either way, exactly as
  ADR-0050 D1 said.
- **ADR-0052 D3's comb saving is 3.5x smaller at 1920** — `1432.28 -> 967.85`
  becomes `1214.93 -> 1083.51`. And the correction does not have one sign: at
  1440 the saving is LARGER, 267px against 215px. Air is the gap between a box
  and the row it shares, and filling the boxes moves both terms.

ADR-0058 D6 survives: the claim it rests on is that the total content got
shorter with the cuts open, and it did — by 674px rather than 703px. The page it
accepted is 3.1 screens rather than 2.9.

## Two things the remeasurement found that nobody was looking for

**The broken-word report was short too.** On the desktop the old instrument
found one split word (`read-only`, which ADR-0058 called a false positive); the
new one finds two. The second is `promote-prod`, in a `#map-sub` sentence the
run layer writes. Both are hyphen breaks — the rule exempts fields marked
`overflow-wrap: anywhere` and has no concept of a hyphen. One was an oddity; two
is a rule that will keep producing them.

**The two fixture sets converge inside the map.** Sharing one layer, `at-rest`
and `in-flight` both pack at 852.31px in 4 columns with 1420.28px of air, where
the short page had them differing. They still differ in total height, 3321
against 3343. What the two-set design buys is the panels above the map, and
inside the map it buys less than it looked like it did.

## Instrument parity, measured

chromium-1234 on the devbox and chromium-1194 in the chat sandbox agree to the
PIXEL at 2560, 1920 and 1440, and differ by up to 15px at 390x844. Phase 25
flagged its sandbox break tests for being taken off the pinned build; for a
phase whose whole subject is measurement that flag had to be answered with a
number rather than a promise, and every figure in ADR-0060 D4 is the devbox's.

## What this does not do

It does not re-lay-out the page. That is a decision, it needs this number first,
and ADR-0058 D6's declined levers are now known to have been measured on the
short page as well.

`make measure-page` is still a REPORT: no verdict, not in `assets/gates.json`,
nothing in `ci.yml` depends on it.

## Validation

```bash
  make gates                                   # 12/12
  make measure-page                            # devbox only
  make site-data-check site-page-check
  make live-state-check page-tense-check page-inflight-check
  make contrast-check page-freshness-check     # devbox only
  make docs-check
```

## Cost

Nothing. No AWS call, no cycle, nothing applied.

**One line of the published page changes, and it was nearly missed.**
`site/data/topology.json` counts the decision records — `generate-topology.py`
globs `docs/decisions/*.md` — so ADR-0060 takes `adrs` from 60 to 61 and
`make site-data-check` would have gone red on a documentation-only patch. That
is 20i's finding, still doing its job. `site/index.html` is byte-identical: the
count is fetched at run time rather than built in. The next push to `main`
republishes.

Every figure in ADR-0060 D4 was measured before that regeneration. The delta is
one integer in the identity bar, of the same digit count, and it moves no box —
but the order is recorded rather than glossed, because "it cannot have mattered"
is how a figure stops being a measurement.

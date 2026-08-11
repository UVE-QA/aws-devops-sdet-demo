# ADR-0060: A measurement is of the page a visitor gets

## Status
Accepted (Phase 26, 2026-08-11). Closes **ADR-0059 D5**. Does not retract
**ADR-0050**, **ADR-0052** or **ADR-0058 D6**; it remeasures them and states the
difference.

## Context

`measure-page.mjs` was written to stop layout figures becoming folklore: quoted,
un-reproducible, and eventually wrong without anybody editing them. It froze the
three sources the sandbox cannot reach, pinned the clock, and refused to print a
figure when a request left the origin unmocked or when the page drew a
source-failure banner.

There were four sources. The fourth is the RUN LAYER — ten origin-relative
documents a cycle publishes into the bucket beside the page — and the guard
watched only what LEAVES the origin. Those ten 404ed against the instrument's own
static server, every time, on both fixture sets. The page's own reader is
`r.ok ? r.json() : null` inside a `.catch(() => null)`, so nothing was raised:
every node read `not run yet`, not one figure was printed, and the page was
shorter and quieter than the page a visitor gets.

So every layout figure this project has argued from since 20e measured the short
bodies. This was not found by the instrument, and could not have been: it was
found in Phase 25 by building a fixture for a different gate, which meant asking
what the page actually reads (**ADR-0059 D5**).

It is the fourth time here that an instrument was aimed at the wrong scope and
read green — after 20a's document-level overflow, 20m's two pages converging on
the same wrong caption, and 25's gate aimed at a correct function the renderer
skipped. The shape is constant: the check was sound, and it was pointed at
something other than the thing.

## Decision

### D1 — The layer is served, and an origin 404 is a refusal

From `tests/fixtures/page-measure/layer/`, over the top of `site/`, at the same
paths, by the same method `check-page-inflight.mjs` already used. Every request
this instrument's own server cannot answer is recorded and refuses the run, with
the paths named.

The refusal is the load-bearing half. Serving the layer without it would leave
exactly the same failure one edit away, and silent: a fixture that loses a
document, or a page that starts reading an eleventh, would go back to measuring
the short bodies with nothing to say so.

### D2 — A document that is present and unreadable is the same defect one step in

`.catch(() => null)` makes a malformed document indistinguishable from an absent
one, and a 404 check cannot see it — the request succeeded. So every file under
the layer is parsed before the browser starts.

This was not in the plan. It was found by asking what the 404 refusal does NOT
cover, which is the question the plan's own framing invites.

### D3 — One layer for both sets, because both sets pin the same clock

`at-rest` and `in-flight` declare the same `meta.now`, so a second copy would be
the same documents under the same clock. What makes one of the two sets tall is
what the Actions API and the bucket say, not what the last cycle measured.

The documents are REAL and unmodified — captured 2026-08-11 from
`https://demo.uveapp.net`, the cycle 20m ran on 2026-08-09 — and they are NOT
shifted to sit before the fixture's clock. The layer's cycle is 18 hours after
`meta.now` and nothing on the page turns that into an age: the figures are
durations, the cycle carries a date rather than an age, and every `… ago` string
comes from `runs.json` and the status files. Checked by reading the rendered
page, not by reasoning about it.

### D4 — The old figures stand as measured, and the difference is the finding

Every recorded figure was reproduced first, by the instrument that produced it,
on the commit it was produced on, in this session on the devbox. So what follows
is instrument-to-instrument, not figure-to-memory.

```text
ADR-0050 D1   in-flight, cuts closed        recorded   with the layer
  2560  before (d5dbbaf)                      1878px         1948px   +70
  2560  after  (c845476)                      1760px         1812px   +52
  1920  before                                1878px         1948px   +70
  1920  after                                 1790px         1841px   +51
  1440  before / after                        2190px         2337px   unchanged
                                                                      either way

ADR-0052      at-rest, 1920, cuts closed
  the floor, every word whole                143.69px       143.69px   0
  the floor, every name unwrapped            295.58px       295.58px   0
  air, before 20j (21062cc)                 1432.28px      1214.93px  -217
  air, after  20j (fd76351)                  967.85px      1083.51px  +116
  air at 1440, before / after         909.65 -> 694.72  1025.29 -> 758.20

ADR-0058 D6   at-rest, 1920
  cuts closed, before (6d0ee53)      2039px (1.9)   2215px (2.1)   +176
  cuts closed, after  (440f988)      3116px (2.9)   3321px (3.1)   +205
  cuts OPEN,   before                     8682px         9091px    +409
  cuts OPEN,   after                      7979px         8417px    +438
```

**Two conclusions are untouched and one is materially weaker.**

`--node-min: 18.5rem` (**ADR-0052 D1**) is untouched, and the reason is worth
stating: the floor is a HORIZONTAL measurement of node names, and what the layer
adds is vertical. The single figure in this project that set a CSS variable is
the one figure the defect could not have reached. 143.69px and 295.58px, to the
hundredth, with and without.

`main: 120rem` (**ADR-0050 D1**) is untouched and slightly better than recorded:
the saving grows from 88px to 107px at 1920 and from 118px to 136px at 2560, and
1440 is unchanged either way, exactly as recorded.

**ADR-0052 D3's comb saving is 3.5x smaller than recorded, at 1920.** 20j
recorded `1432.28 -> 967.85`, a 464px reduction in air under the phases. With
the nodes carrying figures it is `1214.93 -> 1083.51` — 131px. The correction
does not have one sign: at 1440 the same change reads `1025.29 -> 758.20`, a
267px saving against the 215px recorded, so the win there is LARGER. Air is the
gap between a box and the row it shares, and filling the boxes changes both
terms.

**ADR-0058 D6 survives with its arithmetic moved.** The claim it rests on is
that the total content got shorter with the cuts open; it did, by 674px rather
than 703px. The page it accepted is 3.1 screens rather than 2.9. The two levers
it DECLINED are not remeasured — they were hypothetical edits, never committed,
and their ~290px and ~260px were themselves measured on the short page. Taken at
face value against the new baseline they reach about 2.6 screens rather than the
2.4 recorded, so the decision to decline them stands on a slightly worse number
than it was written with.

### D5 — The remeasurement is a script in the repository, not a session's scratch

`scripts/remeasure-page-figures.sh` carries the commits, the fixtures and the
baseline instrument for each figure above. The whole reason this instrument
exists is that the harness which produced 20e's figures was thrown away with the
session that wrote it. A remeasurement delivered as a paragraph would be the same
mistake with better manners.

## Consequences

- `make measure-page` measures a page with figures on it. It refuses when the
  layer is absent, when a document under it 404s, and when one is present and
  unparseable. Three refusals, each fired on the devbox with a control green
  either side, in
  `docs/sessions/2026-08-11-phase-26-layer-break-test.log`.
- It is still a REPORT. It has no verdict, it is not in `assets/gates.json`, and
  nothing in `ci.yml` depends on it. A phase that wants the page height gated
  has to say so.
- Every figure in ADR-0050, ADR-0052 and ADR-0058 D6 now carries a pointer to
  the table in D4. None is retracted: they were honestly measured with an
  instrument whose limit nobody knew, and pretending otherwise would lose the
  only thing that makes the difference legible.
- **The broken-word report was short too, and nobody would have predicted where.**
  On the desktop the old instrument found one word split across lines
  (`read-only`, which ADR-0058 named a false positive); the new one finds two.
  The second is `promote-prod`, in `#map-sub`, in a sentence the run layer
  writes. Both are hyphen breaks, which is the same false positive twice — the
  rule exempts fields marked `overflow-wrap: anywhere` and has no concept of a
  hyphen. One was an oddity; two is a rule that will keep producing them, and it
  is the smaller item Phase 27 travels with.
- **The two fixture sets now converge inside the map.** With one layer shared,
  `at-rest` and `in-flight` both pack at 852.31px in 4 columns with 1420.28px of
  air, where the short page had them at 813.75/1304.6 and 827.78/1346.69. They
  still differ in total height (3321 against 3343). What the two-set design buys
  is the panels above the map, and it buys less inside it than it looked like it
  did.
- Instrument parity was measured rather than assumed, and it is better than this
  project's own warnings would suggest: chromium-1234 on the devbox and
  chromium-1194 in the chat sandbox agree to the PIXEL at 2560, 1920 and 1440,
  and differ by up to 15px at 390x844. Every recorded figure reproduced exactly
  on both, with one exception — 20j's 909.65px of air at 1440 comes back as
  909.63px on both hosts. Two hundredths of a pixel, recorded rather than
  rounded away.

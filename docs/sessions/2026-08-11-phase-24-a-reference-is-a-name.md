# 2026-08-11 — Phase 24: the three contours drawn, and the noun the run layer cannot reach

The cursor's next allowed step after 23: **the composition, redrawn for three
contours**. The model was decided in 21 (**ADR-0054**) and put in the data in 22
(**ADR-0056**); this session draws it. No cycle, no AWS call, nothing applied.
**Cost: $0.** **ADR-0058.**

Break-test output in
`docs/sessions/2026-08-11-phase-24-live-state-break-test.log`.

**Phase 24 is closed.** Every clause of its closing sentence was exercised on
the devbox in this session: the three contours are drawn, all five suites are in
the assertions contour, the retired figures are re-measured and written down,
the contrast refusal was fired by name, and all three browser targets are green.
One item is deliberately carried forward rather than done — the contrast
contract's second ancestry, section 5.

## 1. Main was green when this session started

Checked before anything was touched: `ci #198` and `publish-site #35`, both on
`6d0ee53`, both green. Phase 22 is the reason this is the first thing in every
summary now.

## 2. What was drawn

```text
ESTATE       the nouns, out of the map and out from under a cut.
             Two environments with their resource nodes at the map's own
             legibility floor, then the six permanent levels. One caption for
             the whole contour, which is ADR-0054 D6.
CYCLE        the map. A phase draws its own steps and NAMES what it touches.
ASSERTIONS   all five suites, tenseless, from the repository. tests/unit -
             inventoried, counted in counts.suites and drawn nowhere since it
             was written - carries its own reason for being outside a cycle.
```

The load-bearing line is four words long:

```js
function phaseNodes(p) { return (p && p.nodes) || []; }
```

Phase 22 resolved a phase's `creates` touches into drawable children here, which
kept the map identical to schema 2 while the model under it changed. It also
kept the defect: an estate node reached through a phase is handed a RUN-LAYER
state, and the run layer is the one source **ADR-0051 D2** forbids re-deriving
an observation from. That is how `prod.rds` stood at full colour with the
previous cycle's figures for twelve measured minutes while prod was being
deleted — the destroy phase could not reach it, so nothing unlit it.

## 3. Two phases now draw nothing, and that is the honest picture

`Apply — stage` and `Apply — prod` have no node of their own. Their whole
content is the line naming the nouns they create. It reads as an empty box until
you notice that an apply IS the creation of those nouns, and that the boxes it
used to hold were the same boxes the panel three inches above it was already
drawing — the duplication the whole model exists to end.

`layout.columns` falls **10 → 8** and `layout.wide` empties, both computed, both
predicted by ADR-0054 in exactly those words. The two wide phases were wide
because of resource nodes that have left.

## 4. The gate got a fourth claim, and the first break test did not prove it

`scripts/check-live-state.mjs` claim 4: **no estate id may appear in the run
layer's output**, checked against every case rather than against a case written
for it — because the defect it replaces arrived through a phase nobody was
looking at.

Reverting `phaseNodes()` reddens four cases, and each estate node produces TWO
findings: the gate's existing both-directions comparison already objects to a
node the case does not expect. **So that break does not prove claim 4 has any
force of its own** — it proves the comparison works, which was never in doubt.

The break that proves it puts the seven resource nodes back into
`an-apply-lights-the-phase-not-a-resource/expected.json` as well, so the case
AGREES with the machine, `compare()` is silent, and claim 4 is the only thing
that speaks. It does. Both of its refusals — a snapshot with no `estate`, an
`estate` holding no nodes — were fired too, with a control green either side of
every break.

This is the sibling of the 2026-07-28 finding about a break test that fails to
break, arriving from the other direction: there a green reading hid a rule that
did not match, here a red reading credited the new claim with a refusal that
came from somewhere else. **A break test has to be able to fail for the reason
you think it is failing.**

## 5. What is carried forward, and why it is a decision rather than an omission

The measurement itself is done — section 5b — because it moved to the devbox,
where the pinned browser is. What remains is one finding, and it is a finding
rather than a missing step:

```text
- THE CONTRAST GATE'S ANCESTRY IS THE MAP'S, AND THERE ARE TWO NOW. assets/contrast-contract.json's `chain` is
  main > .cycle > .phase > .set; the estate contour draws the same six states
  under .contour > .estate-env > .set.estate-set. No ancestor in either chain
  paints a background, so the computed colours SHOULD be identical - and
  `should` is what "an instrument aimed at the wrong scope reads green" is made
  of. Supporting two chains is a schema change to the contract and a change to
  the script that reads it, so it is written down (ADR-0058) rather than
  smuggled in here
```

## 5a. A render smoke was run, and it is not a measurement

The built page was served and loaded in the sandbox's chromium — a DIFFERENT
build from the one this repository pins. Recorded in the log, and worth exactly
what it is: evidence that the page draws and that nothing throws, and no
evidence at all about a figure.

```text
2 environments, 15 estate nodes, 6 permanent
8 phases, 11 phase-own nodes = 1 + 0 + 1 + 4 + 1 + 0 + 2 + 2
7 touch lines (approve touches nothing), 15 touched-by lines
5 suites, 1 of them with no run node - tests/unit, carrying its own reason
no pageerror; every box inside its own container at 1280
```

The 404s and the CORS failure in that log are the page offline: no
`status/*.json`, no timeline objects, no Actions API. That is also why the
estate caption reads "nothing has measured these resources yet".

## 5b. Measured on the devbox, and the compaction that followed

The figures, `cuts closed`, at-rest, against the SAME instrument run on
`6d0ee53` in the same session — the old page measured, not the retired numbers
translated:

```text
  viewport     before      after       delta
  2560x1440    2039px      3194px      +1155     1.4 -> 2.2 screens
  1920x1080    2039px      3194px      +1155     1.9 -> 3.0 screens
  1440x900     2354px      3373px      +1019     2.6 -> 3.7 screens
  390x844      5507px      8920px      +3413     6.5 -> 10.6 screens
```

**And the reading that changes what it means:** `cuts open` at 1920 went 8682 →
**8057**. The total content SHRANK by 625px. Nothing was added — the estate came
out from under a cut, which is exactly what ADR-0054 D5 asked for. What grew is
the default view, and the first screen was fought for across three sessions.

So the growth was attacked where it was repetition, not where it was content:

```text
- the environment tag, drawn on all seven nodes under a header that says
  `stage`. ADR-0047 D3, which the map has refused since 20e.1; it is passed as
  a shared env through the same parameter, so there is one rule and not two
- the steps touching a noun, four phase labels wrapping to two lines on every
  card. The verb is the information and the phase is a pointer, and the map
  draws a number on every phase for pointing with:
  `creates 2 · provisions 3 · asserts 4 · destroys 8`
```

The 390px overflow — 169.13px in `#history > table` — is in the BEFORE column at
the same size. Pre-existing, checked rather than assumed.

Two broken words are this contour's own, and `measure-page` found both on its
first run over it. `tests/playwright/tests/regression` sat in
`.node .head .name`, which sets `overflow-wrap: break-word` precisely so that a
broken name is a defect; the suite's own name goes there now and the path joins
the collector on the breakable meta line. `read-only` is prose with a hyphen and
is left for the next measurement to answer — guessing whether a reflow moves it
is the kind of claim this repository measures instead.

## 5c. The compaction bought 78px, and the height was then decided rather than chased

```text
  viewport     before(6d0ee53)  drawn     compacted   vs before
  2560x1440    2039px           3194px    3116px      +1077   1.4 -> 2.2 scr
  1920x1080    2039px           3194px    3116px      +1077   1.9 -> 2.9 scr
  1440x900     2354px           3373px    3266px      + 912   2.6 -> 3.6 scr
  390x844      5507px           8920px    8579px      +3072   6.5 -> 10.2 scr
  cuts OPEN at 1920: 8682 -> 7979. The total is 703px SHORTER than the page
  this phase started from.
```

Seventy-eight pixels, and that is the whole story of it: one row of environment
tag across four estate rows. The touched-by line was two lines only on `rds`,
and a grid row is as tall as its tallest card, so shortening the others changed
nothing. Estate height is rows × card height, the rows come from the 18.5rem
step, and that step is 20j's measured "a name does not wrap" figure — 295.58px,
re-measured here and unchanged. There are no cheap hundreds of pixels in it.

Two levers would have moved it, and both were declined **as decisions, with
their numbers**: the permanent levels back under a cut (≈ −290px) undoes
ADR-0054 D5 in the phase that implements it, and a narrower estate step
(≈ −260px) contradicts ADR-0058 D4 and 20j's floor. Neither reaches 1.9 screens,
because 1.9 screens was a page with its nouns under a cut — which is the thing
ADR-0054 retired. **ADR-0058 D6** records the acceptance and both figures, so a
later session can reverse it against numbers rather than against a feeling.

The first screen is untouched: `p-env`, `p-arch` and `p-run` sit exactly where
20e.1 put them, and the map's packing is unchanged at 813.75px in 4 columns with
1304.6px of air.

## 5d. One broken word survives, and it is a false positive

`read-only`, in `#suites .asserts` at 1920. The rule exempts fields marked
`overflow-wrap: anywhere` — identifiers — and this is prose breaking at its own
hyphen, which the rule has no concept of. `make measure-page` is a REPORT: it is
not in `assets/gates.json` and this reddens nothing. Recorded rather than fixed,
because mangling the data with a non-breaking hyphen to quiet a report line is
the worse trade.

## 5e. The contrast refusal, fired by name

A seventh state was added to `assets/contrast-contract.json` whose probe asks the
chain for something that is not a colour:

```text
contrast-check: the state "seventh" could not be measured in the light theme:
cannot read border-image-source as a colour: "none"
```

`exit=2` is make's number for a failed recipe, not the script's — measured
rather than reasoned about, exactly as on 2026-07-28. Control green either side.

## 6. Validation

```bash
make gates                     # 12/12 green, 19 named as not runnable here
make site-data-check
make site-page-check
make live-state-check
make page-tense-check
make docs-check
```

On the devbox, all run in this session and all green:

```bash
make measure-page
make contrast-check          # 6 states, both themes, none under the floor
make page-freshness-check    # 3 cases
```

## 7. Cost

Nothing. No AWS call, no cycle, nothing applied. The published page changes, so
the next push to `main` republishes it.

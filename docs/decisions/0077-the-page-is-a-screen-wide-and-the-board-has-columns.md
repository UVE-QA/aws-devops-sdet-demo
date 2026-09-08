# ADR-0077: The page is a screen wide, and the board has columns

## Status
Accepted (Phase 39, 2026-09-08). Sizes what **ADR-0075** drew. Narrows
**ADR-0076 D4** on the strength of a live cycle rather than an argument.
**ADR-0052**'s heights are re-measured here rather than assumed unchanged, and
they moved.

## Context

Two things arrived together and turned out to be the same problem.

**The board used half the glass.** The owner opened the page on a fullHD screen
and the estate stopped at 947px in a 1865px column: fifteen tiles at a fixed
6.9rem, with the run panel above them spanning the whole width. `main` was
capped at `120rem` — 1920px, which is not a screen anybody here reads on, so on
1920 the page filled the glass and on 2560 it sat in a 400px margin, and the
board used half of either.

**And the bar was lying, on every cycle rather than on the first.** ADR-0076 D4
called it a count and not a forecast, which was right about forecasts and wrong
about the count. Watched live on 2026-09-08 during self-service #14:

    17:12:13   vpc  incomplete  4 of 7
    17:12:29   vpc  measured    9 of 9

`resources_observed` is not how many resources a node has. It is how many have
**started** — the fold sees a resource when its `apply_start` arrives — so the
denominator grows and a bar against it stands at 100% on a node that is not
finished. The map's own `resources` is not a total either: it counts resource
*blocks* in `infra/`, and `count`/`for_each` turn stage.vpc's six blocks into
nine instances at apply time. **Nothing knows how many there will be until the
apply is over**, which is what *being created* means.

The same reading shows the state itself moving backwards — `rds` read `measured
(2/2)` at 17:13 and `incomplete (3/4)` at 17:14, when the DB instance started.
That is not a defect: `measured` from a partial fold means *everything that has
started has finished*, and a node genuinely goes back to being built when
another member starts.

## Decision

**D1. `main` is capped at the width of a screen, not at a round number.**
`94.5rem` — 1512px, the logical width of a 15-inch MacBook Air, which is a
display this page is actually read on. The board is sized against the same
number, so on every screen wider than it the two agree and the margin is margin
rather than a gap inside the content.

**D2. The board has as many columns as the widest environment has nodes.**
`--estate-cols` is set once by `renderEstate()` from the data — the largest node
count across the environments — and **both rows use it**. That is the whole
point: the rows are read by column. VPC over VPC, RDS over RDS, and the column
stage leaves empty is a statement rather than a gap, because prod carries a
Route 53 record stage does not.

`auto-fill` is wrong here for the reason `1fr` was wrong in ADR-0075 D1: it
gives whatever fits, so a 1512px row becomes thirteen columns of which five are
empty in both rows. **The number of columns is a property of the estate, not of
the viewport**, so it comes from `topology.json` — which is generated from
`infra/` — and not from a number in the stylesheet.

Below about 1000px eight columns are already down to `--tile`, so the board
falls back to wrapping fixed tiles and the marks return to `--tile-icon`. The
rows no longer line up by column there and cannot: a row that wraps has no
columns to line up.

**D3. The bar carries no number.** It is the indeterminate kind — a sliver that
travels — which says *working* and claims nothing, because *working* is the only
thing about a running apply that is knowable from outside it. The tile's sentence
loses its denominator with it: `4 created so far`, not `4 of 7`.

This is the cost box's rule applied to progress. Publish what is known; never a
figure that ages into a lie.

**D4. A tile that goes back to `being created` is telling the truth.** More of it
started. The mark stays in colour once anything of it exists — only `absent` and
`gone` are greyed — so what flickers is the pulse and the word, and both are
accurate at the moment they are drawn.

## Consequences

**The page got taller, and the figure is here rather than in a stylesheet.**
`measure-page`, at rest, cuts closed:

    2560x1440    3387px  ->  3624px      2.4 screens  ->  2.5
    1920x1080    3387px  ->  3624px      3.1 screens  ->  3.4
    1440x900     3631px  ->  3699px      4.0 screens  ->  4.1
    390x844      9060px  ->  9464px     unchanged in kind

Narrower page, more wrapping, more height. That is the trade the cap buys and it
is not free. Below 1512 nothing much moves, which is the point: the cap changes
what happens *above* the width the page was designed at, and above it the page
was previously spending its width on nothing.

**ADR-0076's fixture still says `2 of 5 resource blocks`** in the sentence its
own break test greps for, because the fixture is a frozen document and the
wording it produces changed. The gate reads `data-observed`, not the wording, so
nothing there depends on the string — but a reader comparing the two will find
them different and this is why.

**The 120rem cap was never measured against a display.** It is the kind of number
that arrives as a plausible maximum and is never revisited; this one survived
until somebody opened the page on a monitor and said the board looked lost. Worth
remembering the next time a limit is chosen for how large it sounds.

# 2026-08-09 — Phase 20e: the figures get an instrument

Break tests in
`docs/sessions/2026-08-09-phase-20e-measure-instrument-break-tests.log`.
Cost: nothing. No cycle, no AWS call, nothing applied, no `site/` change — so
this one does not even republish the page.

The cursor's next allowed step was **20e — the phone**, and the same line told
this session to measure before changing anything. It measured, and the layout is
not started. What it established instead is that the measurement now survives the
session that took it.

## Why an instrument came first

Every figure this phase has argued from — 10.5 screens, 4.2, 5.8, "52px wider
than a 390px viewport" — was produced by a harness written inside a session and
thrown away with it. The numbers outlived the thing that made them. That is how
a figure becomes folklore: quoted in the next session, un-reproducible, and
eventually wrong without anybody editing a word around it.

So `scripts/measure-page.mjs` and `make measure-page` are committed. **It is not
a gate**: no verdict, nothing in `ci.yml` depends on it, exit 0 when it measured
and 2 when it refused to.

```text
height         document.scrollHeight, and screens of the viewport
beyond-parent  every box whose border edge sticks out of its PARENT'S padding
               edge, by more than 1px
content-wide   every box whose own content is wider than its own box
```

The second line is the point. 20a measured the DOCUMENT's `scrollWidth` at four
viewports and was green at all four while a phase row was 7px wider than the box
it had been packed into and every node head up to 22px wider than its own node.
A box that overflows its parent never reaches the document if anything above it
clips — an instrument aimed at the wrong scope reads green. This one asks every
box about its own container.

## What it refuses to measure

The page reads three sources this sandbox cannot reach. Measured with them
unreachable it renders banners and "no observation" panels and is SHORTER than
the page a visitor gets — ADR-0047's discovery said exactly that about its own
figures. A missing source does not look like an error here; it looks like a
short page. So the sources are frozen in `tests/fixtures/page-measure/`, and:

```text
an unmocked request leaving the origin      refuses the run, naming the URL
a source-failure banner on the rendered page refuses the run, quoting it
meta.now missing                             refuses - the clock would drift
```

`meta.now` pins the clock, so `12 min ago` stays `12 min ago` and two
measurements a year apart are comparable.

Two fixture sets, because the page has two shapes and a layout decided on the
short one is decided on the page's quiet day:

```text
at-rest    nothing running, both environments destroyed. BOTH status files are
           real captures from the live bucket, 2026-08-09.
in-flight  a deploy running with 25 steps, one of them in flight; stage stale
           against that run, with its last reported values shown; prod up with
           every optional field present.
```

## The break tests

```text
CONTROL 0   both fixtures, the phone, measured                        exit 0
BREAK 1     the GitHub mock removed - the page asks for a source
            nobody declared                                           REFUSED
BREAK 2     that source mocked and answering 503 - the page draws
            its banner and the run is refused, not measured           REFUSED
BREAK 3     meta.now removed from a fixture                           REFUSED
BREAK 4     a fixture set that does not exist                         REFUSED
CONTROL 1   restored - identical to CONTROL 0, line for line          exit 0
```

BREAK 2 is the one worth keeping. BREAK 1's failure is loud in any harness; a
source that ANSWERS, wrongly, is the one that produces a plausible number.

## The baseline, and a cross-check nobody planned

Same fixtures either side is the rule; this session could not have them, because
the previous harness is gone. What it has instead is an accidental replication:
entirely different fixtures, written from the page's own schema, and the heights
land within a tenth of a screen of what 20e.1 reported.

```text
                  20e.1 reported     measured here (at-rest / in-flight)
2560x1440   1.3                      1.2 / 1.3     the stated primary target
1920x1080   1.8                      1.7 / 1.7
1440x900    2.5                      2.4 / 2.4
390x844     5.8                      5.6 / 5.7
```

Two harnesses, two fixture sets, one answer. The baseline is now checked rather
than inherited.

**Cuts OPEN had never been measured**: 5.9 to 6.0 screens at 2560, and **19.6 to
20.2 screens on the phone**. The fold is not a detail of the phone problem.

At 390, closed, the page divides as: identity 268px, first screen 1358px, map
2011px (42%), the fold and the five cuts the rest.

## Two findings

**A — the phone. Exactly ONE box overflows its parent, at any viewport: the
history table.** And the recorded "52px" is not a constant. It is a property of
what happened to run recently:

```text
 84.6px   a history with no self-service launch in it
169.1px   with one (at-rest)
174.6px   in-flight
```

Its 475px of min-content in a 306px box, by column:

```text
run          147px   the unbreakable token ss-9f4c1d7b3a2e8065
environment  120px   set by the HEADER WORD, not by "stage"
result 65px · duration 88px · when 55px
```

What splits the table is the run-name of a public launch — produced by the
button on this same page. A figure measured before anyone had pressed it was
always going to understate it.

**B — not the phone at all. Every viewport, including the primary target.** The
text glyphs on the map and in the request path are wider than the badge they sit
in, and paint outside its dashed border:

```text
WWW    +11px   the request path's browser hop
TEST    +6px   x6, the suite nodes
YOU     +2px
DEL, CI  0px
28 AWS icons   0px - .icon.aws sets overflow: hidden, the text .icon does not
```

`.icon` is a 1.4rem box with a 3-4 letter uppercase label centred in it. Nothing
in this repository could have seen this: it is not a colour, not a build drift,
not a state, and the only layout measurement that existed was aimed at the
document. It arrived with the composition in 20e.1 — the glyph and the tool on
every hop — and was on the page for a day.

Not fixed here. It is a desktop defect and the cursor's step is the phone;
the two are separate pieces of work and the second one has not been decided yet.

## Validation

```bash
make measure-page            # CHROMIUM_PATH= if chromium is not the pinned build
make site-page-check site-data-check docs-check
```

`site/` is untouched, so `contrast-check` and `live-state-check` have nothing new
to say — they were run anyway and are green.

## Next

The phone is still the next allowed step, and it now has a baseline that can be
re-measured after every change. The open question the session stopped on is
whether finding B is fixed on the way or recorded and left; `docs/phase-gates.md`
carries it.

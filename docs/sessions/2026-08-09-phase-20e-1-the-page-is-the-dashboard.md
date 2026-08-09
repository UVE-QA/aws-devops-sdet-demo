# 2026-08-09 — Phase 20e.1: the composition on the real page

**ADR-0049.** Break tests in
`docs/sessions/2026-08-09-phase-20e-1-composition-break-tests.log`.
Cost: nothing. No cycle, no AWS call, nothing applied. `site/index.html` and
`site/data/topology.json` change, so the published dashboard changes with the
next push — a static sync, no infrastructure.

The session took the cursor's next allowed step and finished it: ADR-0047 D1-D6
and ADR-0048 implemented on `assets/index.template.html`, in two commits, with
every gate green and three new refusals broken on purpose.

## What the page is now

```text
identity bar     name, claim, live badge, and THE LINKS - repository, the
                 decision records (COUNTED, not written), Actions. Discovery
                 measured the repository link at 100% of scroll depth.
environments     one line each; what it is made of behind the panel's own
                 disclosure; the Launch button as the panel's FOOTER
where it lives   the request path, and the TOOL on every hop
current cycle    three lines - the step in flight, the one before, the one
                 after - and the whole list one disclosure away
the map          one grid, eight phases, one row at 1920 and above
the fold         five cuts, each answering its own question in its header
```

## Measured, with the same fixtures either side

Mocked GitHub API and status files, four viewports, cuts closed and open, the
page before this session and after it:

```text
                     before      after commit 1     after commit 2
1920x1080            4781px      3033px             1935px   1.8 screens
2560x1440            4781px      3033px             1935px   1.3 screens
1440x900             4781px      3033px             2265px   2.5 screens
390x844             10544px      7075px             4915px   5.8 screens
```

The primary target is the desktop monitor, stated by the person who asked for
the page. 2560x1440 is the number to read.

The sketch measured 1.1 screens at 1920 and this page measures 1.8. The
difference is not layout: the sketch had placeholder figures, no launch control,
and no environment saying `unknown` with the reason printed under it. Those are
the honest halves of the panel and they cost about 400px.

## What implementing it decided (ADR-0049)

Six things the sketch could not settle, in the ADR: one page width with the
reading measure on the prose; the map folding into whole ROWS rather than taking
the columns that fit (nine of ten at 1920 stranded phase 8 - the exact picture
ADR-0047 D5 exists to end, rebuilt by the code meant to end it); the legibility
floor being a property of the NODE SHAPE, so 12rem becomes 7rem for the composed
node and stays as `--card-min` for the cards under the cuts; a state's edge
being a background COLOUR and never a gradient; the environment tag being a
shared attribute and said once like a shared state; and the request path being
generated from citations rather than written.

## The break tests

Committed before anything was broken. Full output in the log beside this file.

```text
CONTROL 0   every gate green                                          exit 0
BREAK 1     a hop cites a node the map does not draw                  REFUSED
BREAK 2     the request path deleted from the editorial input         REFUSED
BREAK 3     the computed column total edited by hand in the JSON      DRIFT
CONTROL 1   contrast-check through the NEW channel, green             exit 0
BREAK 4     one state loses its 4px edge rule -> falls back to --line
            done: 3.37 -> 1.39 light, 5.35 -> 1.27 dark               FAILED
BREAK 5     that edge drawn as a gradient, as the sketch drew it
            working: 1.00 in both themes                              FAILED
CONTROL 2   restored, green again                                     exit 0
```

BREAK 5 is the one worth keeping. The sketch drew the `working` edge as
`repeating-linear-gradient`, and an element painted with a gradient resolves
`background-color` to `transparent` — the state would have been on the page and
off the instrument. It reads 1.00:1 and the gate refuses, loudly. Copying the
sketch verbatim would have shipped a state nobody was measuring.

The contrast contract predicted its own move: "the channel that carries a state
is about to move... Moving the probe is an edit here, not a rewrite of
scripts/check-contrast.mjs." It was exactly that — the chain and six probes —
and the six numbers came back identical to the hundredth through the new
channel, in both themes.

## Two things found on the way

```text
- docs/demo-script.md said "thirty-nine ADRs". There are fifty. A count in
  prose, in a document read aloud at an interview - the class of defect
  ADR-0039 D1 exists to end, in the one place the generator does not reach.
  Replaced with no number at all; the page counts them.
- the history table is 52px wider than a 390px viewport with the cuts open. It
  was 73px before this session, in the same table. Not a regression, and the
  phone stays deferred - recorded so the next session measuring the phone does
  not think it found something new.
```

## Validation

```bash
make site-page-check site-data-check docs-check
make contrast-check          # CHROMIUM_PATH= on a machine whose chromium is not the pinned build
make live-state-check
```

All green on the sandbox. The map's own run-layer state machine is untouched:
`live-state-check` lifts it out of the built page and folded 12 of 12
observations exactly as before.

## Next

The composition is done and the phone is not. `docs/phase-gates.md` carries the
next allowed step.

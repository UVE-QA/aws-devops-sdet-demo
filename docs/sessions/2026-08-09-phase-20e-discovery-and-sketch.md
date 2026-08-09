# Phase 20e.0 — The dashboard is composed, not scrolled

2026-08-09. Discovery and a sketch. No implementation, no AWS call, $0.
**ADR-0047.**

## What this session was for

The cursor pointed at "20e — the dashboard is navigable", with a discovery step
first. The discovery renamed its own phase.

## The complaint, measured instead of quoted

The page was rendered locally in headless Chromium at four viewports, with
`data/topology.json` read from disk so the map draws in full. Three remote
sources were unreachable from the session sandbox — the Actions API, the
bucket's `status/*.json`, and the self-service endpoint — so Environments,
Current cycle and Recent runs rendered as one-line stubs and the Launch button
stayed hidden. **Every figure therefore understates the live page.**

```text
1920x1080  3866px  3.6 screens      1440x900  3866px  4.3 screens
2560x1440  3866px  2.7 screens      390x844   8835px 10.5 screens

in <main>:  0 in-page anchors   0 <nav>   0 sticky or fixed elements
```

The last line is the finding, and it is literal: the page contains no
navigation affordance of any kind. Two more fell out of the same run — the
per-cycle map is 46% of the page on a laptop and 53% on a phone, so half the
strip is one section; and the repository link, the single thing a
thirty-second visitor needs, is in the footer at 100% of scroll depth.

## The requirement was not what the plan said, again

The previous session had restated 20e around **wayfinding**, and that is close
enough to be dangerous. Asked directly, the requirement came back as:

```text
it should look like a DASHBOARD, not a long list of resources
the main thing is visual: where things are, how they connect, WHICH TOOLS are
  used, in what order
composed in blocks
all the extra detail below the first screen, under cuts
```

A section index — which is what "wayfinding" would have bought — makes a long
strip traversable. It does not make it stop being a long strip. The candidate
was withdrawn in the session that proposed it, before anything was built.

The desktop monitor was named as the primary target in the same exchange, and
the phone as last in the queue. Both are recorded because both change what gets
optimised.

## Two things the reader saw that no gate could have

**Long lists should collapse to their current lines, with GitHub Actions'
logic** — per-step status inside, presence or absence of errors in the header.
The first version of this rule, written before that correction, collapsed a run
to "the current step", which for a FINISHED run is the last step: a green tick
where the thing broke. ADR-0047 D2 takes the header/lines split instead, and
names the failing step in the header of a failed run.

**The outlines are hard to see, and the pulse with them.** Measured on the live
page against WCAG 1.4.11's 3:1 floor:

```text
light theme                          dark theme
  live        solid 1px  4.63:1        7.62:1
  failed-now  solid 1px  3.17:1        3.29:1
  working     dashed 1px 2.67:1  <     3.65:1
  done        solid 1px  2.41:1  <     3.28:1
  suite       solid 1px  1.98:1  <     2.73:1  <
  absent      dashed 1px 1.34:1  <     1.35:1  <
```

Five of six states ride a 1px border and nothing else. Solid versus dashed at
one pixel is not a channel, which is exactly what was reported by eye. The pulse
does not save the one state that has it: a 1px ring in the accent colour
animating `opacity: 0.9 -> 0`, fainter than the border it sits on for most of
every beat.

## The measurement that was wrong, and how it said so

The first contrast run reported 20.92:1 for six different colours in the light
theme and 1.23:1 for the same six in the dark. Both readings are wrong and both
look like findings. `color-mix()` resolves to `color(srgb 0.44 0.62 0.90)`,
whose components are already 0..1, and the parser divided them by 255.

This is the pipe lesson in a new instrument — the shell stood between the defect
and the reading there, the colour parser here. What settled it was a CONTROL
inside the measurement: black on white must read 21:1, and it must read 21:1
through both notations. It does now, and it is printed on every run.

## The sketch

`docs/sessions/2026-08-09-phase-20e-sketch.html`, built from the real
`site/data/topology.json` and `site/data/suites.json` — 8 phases, 26 nodes, 116
resource blocks, 5 suites, 180 tests — with PLACEHOLDER environment, run and
cost figures, stated on the page itself.

```text
                sketch            live page (understated)
1920x1080   1233px 1.1 screens    3866px 3.6 screens
2560x1440   1440px 1.0 screens    3866px 2.7 screens
1440x900    1451px 1.6 screens    3866px 4.3 screens
390x844     3515px 4.2 screens    8835px 10.5 screens
```

Boxes overflowing their own parent: 0, at all four, in both. That measure is
20a's lesson applied — and it earned its place immediately by catching a table
74px past its container on the phone, which the document-level measure that
20a's pilot used could not have seen.

Two layout findings worth carrying forward. `grid-template-columns:
repeat(auto-fit, minmax(...))` chose, at 1920, a count that left phase 8 alone
on a second row with a screen of air beside it — the column count is
deterministic now, and its span total must be computed from the data rather than
written down (ADR-0047 D5). And a phase whose nodes all say the same thing says
it once in its header: the disclosure ADR-0043 D4 requires is stated, and not
printed twenty-six times.

## The state encoding, after

Each state carries a 4px edge AND a word, and the running one a beating dot:

```text
                light   dark
running now     4.48    8.08     solid edge, beating dot, the word
phase running   4.48    8.08     dashed edge, the word
finished in run 4.91    9.40
failed in run   5.18    7.18
suite           4.88    7.90
not run yet     1.10    1.19     DELIBERATE
```

`not run yet` stays under the floor on purpose — the absence of state is carried
by the word, and drawing "nothing happened" as brightly as "this failed" is a
claim about importance the page should not make. Written into ADR-0047 D6 so the
next session does not fix it.

The pulse animates `1.0 -> 0.45`, so its dimmest frame is still above the floor.

## Left open, deliberately

```text
- the Launch button (Phase 19, endpoint LIVE) has no place in the composition
- the legend has no home now that the encoding changed
- a compact node has nowhere for a duration or a suite's counts
- the phone at 4.2 screens, deferred by the person who asked for the page
- the contrast floor has no gate. ADR-0047's consequences call for one, and it
  needs breaking on purpose like every other gate here
- the column span total is a literal in the sketch and must become computed
```

## Housekeeping

Four patches from 20f were still sitting in the transfer buffer's `outbox/` at
the start of this session, all eight of their commits already in `origin/main`.
A chat cannot delete from the buffer; reported rather than left silent.

## Cost

Nothing. No cycle, no AWS API call, nothing applied. `site/` and `assets/` were
not touched: the only generated file that changed is `site/data/topology.json`,
whose ADR count moved with the new decision record.

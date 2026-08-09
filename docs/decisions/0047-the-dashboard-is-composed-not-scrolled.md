# ADR-0047: The dashboard is composed, not scrolled — and no state rides a 1px border

## Status
Accepted (Phase 20e discovery, 2026-08-09). Implements the requirement
`docs/next-phases.md` restated on 2026-08-08 after the hover line turned out to
be a spontaneous example. Narrows nothing in ADR-0043; adds a measured floor
under the state encoding ADR-0043 D2 introduced.

## Context

The page had grown by accretion, each phase adding its section under the last,
and the complaint it earned was that it is a long strip you cannot navigate.
That complaint was carried into this phase as prose. Measured instead, at four
viewports, with three remote sources unreachable — so every figure below
UNDERSTATES the live page rather than flattering the replacement:

```text
1920x1080   3866px   3.6 screens
2560x1440   3866px   2.7 screens
1440x900    3866px   4.3 screens
390x844     8835px  10.5 screens

in <main>:  0 in-page anchors   0 <nav>   0 sticky or fixed elements
```

The last line is the finding. "You cannot navigate it" is not a metaphor: the
page contains no navigation affordance of any kind. And two structural facts
came out of the same measurement:

```text
the per-cycle map is 46% of the page on a laptop and 53% on a phone. It is a
destination that was laid out as a stretch of road.

the repository link — the one thing a thirty-second visitor needs — is in the
footer, at 100% of scroll depth.
```

Then the requirement was restated by the person who asked for it, and it is not
the requirement the previous session recorded:

```text
it should look like a DASHBOARD, not a long list of resources
the main thing is visual: where things are, how they connect, WHICH TOOLS are
  used, in what order
composed in blocks
all the extra detail below the first screen, under cuts
```

"Wayfinding" was the previous session's word for it and it was close but wrong
in a way that costs a phase: adding a section index would have made a long strip
traversable, which is not the same as not being a long strip. The instrument was
aimed at the symptom.

Two further observations arrived while a sketch was in front of a reader, and
both survived measurement:

```text
long lists should collapse to one to three CURRENT lines, expandable — with
GitHub Actions' logic: per-step status inside, presence or absence of errors in
the header.

the outlines are hard to see, solid and dashed alike, and the pulse is
therefore hard to tell apart.
```

The second was measured on the live page, against WCAG 1.4.11's 3:1 floor for a
boundary that identifies state. The first attempt to measure it was wrong and
said so loudly enough to be caught: `color-mix()` resolves to
`color(srgb 0.44 0.62 0.90)`, the parser divided those by 255, and six different
colours came back as 20.92:1. Re-measured with a control that reads 21:1 for
black on white in both notations:

```text
light theme                         dark theme
  live        solid 1px  4.63:1       7.62:1
  failed-now  solid 1px  3.17:1       3.29:1
  working     dashed 1px 2.67:1  <    3.65:1
  done        solid 1px  2.41:1  <    3.28:1
  suite       solid 1px  1.98:1  <    2.73:1  <
  absent      dashed 1px 1.34:1  <    1.35:1  <
```

Five of the six states are carried by a 1px border and nothing else, and three
of them sit under the floor in the light theme. The pulse does not rescue the
one state that has it: it is a 1px ring in the same accent colour animating
`opacity: 0.9 -> 0`, so for most of every 1.6s cycle it is fainter than the
already-faint border it sits on.

None of this is a regression. It is a channel that was never measured, in a
project that measures everything else.

## Decision

### D1 — the first screen IS the dashboard

Not an introduction to one. The first screen carries, as composed blocks rather
than as a column of prose:

```text
identity      name, one-line claim, live badge, and the LINKS — repository,
              decision records, Actions. The footer keeps them too; it stops
              being the only place they are.
environments  what is observed in AWS, per environment
where it lives the request path, left to right, with the TOOL named on each hop
current cycle the run in flight, collapsed per D2
the cycle     all eight phases, every node, in one block
```

Everything else is below the fold and under a cut. Measured on the sketch built
from the real `site/data/topology.json` — 8 phases, 26 nodes, 116 resource
blocks — at the same four viewports:

```text
1920x1080   1233px  1.1 screens      2560x1440  1440px  1.0 screens
1440x900    1451px  1.6 screens      390x844    3515px  4.2 screens
```

The desktop monitor is the primary target, stated by the person who asked for
the page. The phone is last in the queue and is expected to reflow to a column.

### D2 — a long list collapses; the header carries the verdict

Taken from GitHub Actions, which solved this already:

```text
the header of a collapsed list answers ONE question: is anything wrong.
  finished green  one line: verdict, duration, when. Nothing to open.
  finished red    the verdict AND the name of the failing step
  running         the step in flight
  aggregate       "7 passed · 1 failed · 2 skipped"
the lines inside answer WHICH: per-step status marks and durations.
```

The failing step, not the last step. Collapsing a failed run to its final line
shows a green tick where the thing broke, which is this project's recurring
defect — the empty result that looks clean — rebuilt on purpose.

### D3 — the per-node disclosure stays visible; a shared state is said once

ADR-0043 D4 is not narrowed. What a node does not know — *its phase is running,
and which node is not published until the cycle ends*, *not reported*, *not run
yet* — stays on the node, never behind a disclosure.

What changes is repetition, not visibility: when every node in a phase carries
the same state, the phase header says it once instead of the phase printing it
twenty-six times. The information is stated; the noise is not.

### D4 — the tool is named in text; vendor marks are separate work

Ten of the map's 28 nodes draw a text glyph rather than an AWS icon, and that is
deliberate — `assets/aws-icons/NOTICE.md` and `assets/github-logo/NOTICE.md`
record why. But the request was broader than icons and the gap is real:
Terraform, Docker, Playwright, pytest and Alembic appear nowhere on the map, and
`TEST` does not distinguish Playwright from pytest.

Each node and each phase names its tool in TEXT. Where the name can be derived
it is derived — `collector` in `site/data/suites.json` (pytest / playwright),
`observer` in `site/data/topology.json` (terraform) — and where it cannot, it is
editorial and says so, exactly as `assets/cost-model.json` already is.

Official vendor marks for the non-AWS tools are a separate piece of work: each
needs its terms read at the source and its own NOTICE, which is what was done
once already for GitHub's mark. Recorded as available, not as decided.

### D5 — the map's column count is computed, not chosen by auto-fit

`grid-template-columns: repeat(auto-fit, minmax(...))` chose, at 1920, a count
that left phase 8 alone on a second row with a screen of air beside it. The
column count is deterministic, and the span total is COMPUTED from the data —
six narrow phases plus two wide ones is ten columns today, and writing ten into
the stylesheet is the stale literal ADR-0039 D1 exists to end.

A phase with six or more nodes takes two columns instead of twice the height.
Reading order stays left to right and then to the next row, so ADR-0039 D5's
`generated, exact` row is untouched: the layout approximates, the sequence does
not.

### D6 — no state rides a 1px border, and the floor is 3:1

Every state carries at least two channels: a 4px edge AND a word. Measured on
the sketch, edge against node background:

```text
                light   dark
running now     4.48    8.08     solid edge + a beating dot + the word
phase running   4.48    8.08     dashed edge + the word
finished in run 4.91    9.40
failed in run   5.18    7.18
suite           4.88    7.90
not run yet     1.10    1.19     DELIBERATE — see below
```

`not run yet` is under the floor on purpose: the absence of state is carried by
the word alone. Drawing "nothing has happened" as brightly as "this failed" is a
claim about importance that the page should not make. Written down here because
a future session reading the table without this paragraph will "fix" it.

The pulse animates `1.0 -> 0.45`, never to zero, so its dimmest frame is still
above the floor. The old one faded a 1px ring to `opacity: 0`, which is why it
was legible for a fraction of each beat and invisible for the rest.

## Consequences

```text
- The contrast floor is a checkable condition, so it gets a gate: the edge
  colours are measured against their backgrounds, in both themes, in CI. Three
  states went under the floor without anybody choosing it, because color-mix()
  toward --line quietly eats contrast — it will happen again at the next palette
  edit unless something refuses.
- D5 needs the span total computed in the generator, not written in CSS. Until
  it is, the sketch's literal is a known stale number.
- D2 changes what a cut MEANS on this page. A cut is no longer hidden content;
  it is an answer that does not need opening. A green run has nothing worth
  expanding, and that is the point.
- Four things are open and named rather than quietly dropped: the Launch button
  (Phase 19, and the endpoint is live) has no place in the composition; the
  legend has no home now that the state encoding changed; where a node's
  duration and a suite's counts live inside a compact node is undecided; and the
  phone is 4.2 screens, deferred by the person who asked for the page.
- The sketch is evidence, not an implementation. It renders REAL topology and
  suite data and PLACEHOLDER run, environment and cost figures, and says so on
  its own face. Nothing in site/ or assets/ changed in this session.
```

# ADR-0048: The three things the composition was waiting on — and one row of ADR-0047's table is wrong

## Status
Accepted (Phase 20e.1, 2026-08-09). Closes three of the six items ADR-0047 left
open and named rather than dropped. Narrows nothing; ADR-0047 D1 and D6 stand as
written, and D6's Consequences are now implemented rather than pending.

## Context

ADR-0047 designed the composition and stopped at four places where the design
had no answer yet:

```text
- the Launch button (Phase 19, endpoint LIVE) has no place in the composition
- the legend has no home now that the state encoding changed
- where a node's duration and a suite's counts live inside a compact node
- the phone, at 4.2 screens, deferred by the person who asked for the page
```

The first three decide space and therefore block layout; the phone is last in
the queue by the same person's instruction and stays open. Deciding these before
touching `assets/index.template.html` is the point — the previous phase's whole
finding was that aiming an instrument before establishing the requirement costs
a phase.

## Decision

### D1 — the Launch button is the Environments panel's footer

Not the identity bar, and not the "current cycle" panel.

```text
identity bar    repository, decision records, Actions. NAVIGATION. A control
                that spends real money does not belong in a row of links.
current cycle   its content varies with what is running, and a control that
                moves is worse than one in a boring place.
environments    what the button ACTS ON, and where its result appears. Its
                refusals - one at a time, a daily quota - are statements about
                environment state, so the refusal and the reason it happened
                are finally in the same box.
```

The behaviour Phase 19 chose does not change: the button is hidden ENTIRELY
while disabled, because a visible inert control cannot be told apart from a
broken one. The panel gets shorter; nothing else moves.

### D2 — the legend is a cut on the map, and the sketch's strip is not the page

D6 gave every state a word on the node itself, so the legend stopped being a
decoder and became reference material. Reference material does not get a section
on the first screen of a dashboard.

```text
where   a cut in the header of the per-cycle map, closed by default, next to
        the thing it describes
why     ADR-0047 D2's own rule, applied to the legend: a cut is an answer that
        does not need opening. Every node already says its state in words.
```

And explicitly, because this is the kind of thing an implementation copies
without asking: **the sketch's `State encoding` strip does not go on the real
page.** It is on the sketch because the sketch had to show a reader the new
encoding side by side. That is evidence for a decision, not an element of a
dashboard.

### D3 — one state line under the head, the word first and the figure after

```text
the head        icon + name, and nothing else. The map has to read as a map.
the state line  <word> · <figure>, in that order:
                  running now · 4m 12s
                  passed · 31 of 31 · 48s
                  finished in this run · figures publish at the end
                  not run yet
```

No badge in the head, no second row, no figure without its word. And where
there is no figure, the separator is not printed either: `passed · ` with
nothing after the dot is the empty result that looks clean, which is the defect
this whole part of the project exists to remove.

The word first is not a style preference. ADR-0047 D6 makes the word the second
channel carrying the state; putting the number first buries the channel that the
colour measurement cannot check.

### D4 — ADR-0047's `absent` row is superseded, and the other five stand

The gate this session built measures the states independently, in a browser,
with a control on every run. It reproduces ADR-0047's table **to the hundredth**
on five of six states in both themes — written from scratch, sharing no code
with the discovery's throwaway script, which was never committed.

```text
                 ADR-0047        measured now
  live           4.63 / 7.62     4.63 / 7.62
  failed-now     3.17 / 3.29     3.17 / 3.29
  working        2.67 / 3.65     2.67 / 3.65
  done           2.41 / 3.28     2.41 / 3.28
  suite          1.98 / 2.73     1.98 / 2.73
  absent         1.34 / 1.35     1.15 / 1.12
```

Five identical readings are strong evidence that both instruments are right
about the model. The sixth is the only state carrying `opacity: 0.45`, and
1.34:1 is not reachable for `#d8dbe2` against anything lighter than itself — the
ceiling is 1.27, against pure white. So the older figure is not a different
model, it is unreproducible, and the committed measurement replaces it.

Nothing follows from the change. `absent` is exempt from the floor by D6, on
purpose, and it was under the floor on both readings.

## Consequences

```text
- The palette moved BEFORE the layout, and it moved on the live page: the
  boundary colours are tokens in :root, `.node.done` and `.phase.done` now
  share one definition instead of two matching literals, and working/done/suite
  went to 70/70/80% - the smallest 5% step clearing the floor with a margin in
  both themes. Published pages change with the next push to site/.
- The gate lands GREEN. A gate that arrives red on a shared dependency reddens
  every open pull request over findings none of them introduced, which happened
  once already with the image scan. The fix goes in first, in its own commit.
- `make contrast-check` is the first gate here that needs a browser, so it
  belongs to ci.yml's local-ci job, after the smoke step whose side effects are
  playwright and chromium (ADR-0042 D2). It installs nothing and refuses,
  naming the command, if they are missing.
- The contract is DATA. The channel moves from a 1px border to a 4px edge when
  the composition lands, and that is an edit to
  assets/contrast-contract.json - a probe, not a rewrite. A state the contract
  does not name is not checked, and the gate says so rather than passing.
- Three of ADR-0047's six open items remain: the phone, the map's computed
  column span total, and the composition itself.
```

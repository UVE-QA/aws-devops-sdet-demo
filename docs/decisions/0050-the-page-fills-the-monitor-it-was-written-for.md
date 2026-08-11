# ADR-0050: The page fills the monitor it was written for

## Status
Accepted (Phase 20g, 2026-08-09, the desktop). Supersedes **ADR-0049 D1**'s
figure — one width, and the reading measure on the prose, is unchanged; the
number is not.

**Remeasured in Phase 26 (ADR-0060 D4).** Every figure below was taken on a page
whose run layer 404ed, so no node printed a figure and the bodies were short.
D1's heights are 51–70px taller when the layer is served, the saving grows
rather than shrinks (88 → 107px at 1920, 118 → 136px at 2560), 1440 is unchanged
either way exactly as recorded, and the decision is untouched. The figures below
are left as they were measured.

## Context

ADR-0049 D1 set `main` to 96rem because that is "what the map's computed column
count needs at the legibility floor". Nothing else asked for a number, so the
map's floor became the whole page's ceiling.

Measured on the built page rather than argued from, that ceiling is 1536px. The
stated primary target is a 2560 desktop monitor (ADR-0047 D1), so the page was
using 60% of it and leaving 1024px of margin. At 1920 the page is *also* 1536px
wide — which is the finding: the desktop this page was laid out for is 1920, and
the monitor it was written FOR gets the leftovers.

The cost was not only air. Ten columns inside 1536px are about 147px each, and a
column that narrow breaks words across lines — `environme|nt` at 2560,
`Secrets Mana|ger`, `RDS PostgreSQ|L` at 1440. `overflow-wrap: break-word` only
fires when a word cannot fit at all, so each of those breaks is the layout
reporting that the column is narrower than the text it was given. A reader sees
a rendering fault, not a choice.

This was found by looking. `make measure-page` reports overflow, and none of
these overflow: they are the page correctly obeying an instruction that was
wrong. The instrument said so only in the aggregate — 1.3 screens at 2560 — and
the aggregate looked good.

## Decision

### D1 — `main` goes to 120rem, and the reason is the monitor rather than the map

1920px. The page fills a 1920 screen, keeps a margin on a 2560 one, and every
map column widens past the longest word either of them draws. `96rem` was a
floor promoted to a ceiling; `120rem` is stated as what the primary target is.

Still no `100vw` anywhere, for ADR-0049 D1's reason: that is the viewport
including the scrollbar, and this map has been bitten once by being laid out
against a width a scrollbar then took back.

Measured, in-flight fixture, cuts closed:

```text
              before    after
2560x1440     1878px    1760px     1.3 -> 1.2 screens
1920x1080     1878px    1790px     1.7 screens, and now the full width
1440x900      2190px    2190px     unchanged - it was never at the cap
```

### D2 — a text badge sizes to its word; the AWS mark stays a square

`.icon` was a fixed 1.4rem box, right for the single glyph it was written for
and wrong for every longer one: `WWW` measured 31px of content in a 20px box,
`TEST` 26px in seven places, `YOU` 22px — at EVERY viewport including 2560.

`.icon.aws` never showed it because it sets `overflow: hidden`. Copying that to
the text badge would have been the wrong repair: it clips a WORD, and the word
is the content. So the box grows — `width: fit-content` with `min-width: 1.4rem`
keeps the square for a single glyph, and 0.2rem of padding keeps the letters off
the dashed edge.

The AWS mark keeps its exact 1.4rem square. It holds an unmodified Architecture
Icon (ADR-0039), and a mark that changes size is a different mark.

### D3 — a fix that costs a third of a screen is not a fix, and the figure is recorded

At 1440 the request path gets 5 of 12 columns — about 100px per hop — which is
where `RDS PostgreSQ|L` and the wrapped `docker ·` separator come from. Moving
the `.p-arch` breakpoint from 1100 to 1500 gives the path the full row and fixes
both.

It was tried, measured and reverted: 2123 -> 2412 at rest, 2190 -> 2480 in
flight. 2.4 screens becomes 2.7. A word break is cosmetic; a third of a screen
on a page whose whole phase is "composed, not scrolled" is not. The breakpoint
stays at 1100 and the 1440 break is an open item, for the session that repacks
that row rather than for this one.

The number is in the stylesheet beside the rule, so the next session does not
re-derive it by trying the same thing.

## Consequences

```text
- Every overflow this repository can measure on a DESKTOP viewport is now gone.
  What `make measure-page` still reports is one box, at 390 only: the history
  table. The phone is deferred far, and this ADR does not touch it.
- The phone got 23px taller (4818 -> 4841 in flight, cuts closed) because the
  text badges grew. It is 5.7 screens either way, and the phone is not in the
  near plan.
- 1440 is unchanged by D1: it was never at the 96rem cap. The laptop gets
  nothing from this ADR except the badges, and keeps its word break.
- The comb was NOT touched. At 2560 the map is one row of ten columns whose
  tallest phase is 513px, and the air under the other seven sums to 1582px; the
  top row is 573 / 279 / 235px. Both are real, both are measured, and both are a
  packing decision rather than a width one - deliberately left to their own
  session.
- `--node-min` is unchanged. This ADR widens the columns by widening the page,
  not by raising the floor, so ADR-0049 D3 still means what it says.
```

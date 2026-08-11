# Phase 27 — The third ancestry, and a premise that was not true

**2026-08-11. $0, no AWS call, nothing applied. ADR-0061.**

The smaller of the two items Phase 24 handed forward, carried past 25 and 26.
`assets/contrast-contract.json` probed one ancestry; the page has three.

## What changed

```text
assets/contrast-contract.json     `chain` -> `chains`, three of them, and a
                                  seventh state
scripts/check-contrast.mjs        probes each chain, five new refusals, and
                                  prints which ancestor actually paints
scripts/break-contrast-chains.sh  the refusals, fired
```

## Three, not two

ADR-0058's finding named two ancestries. There are three: the assertions contour
hangs its suite nodes straight off `div.suites`, with no `.set` in between.

It was found by walking upwards from a real node on the rendered page. The
template would have answered the question too, and reading the template is where
the count of two came from.

The third chain carries `adds: "assertion"` — that contour puts the class on
every node it draws, `.node.assertion` sets `opacity: 1`, and this gate
composites by opacity. Measured rather than assumed: `absent` still reads 0.45
there, because `.node.absent` comes later in the stylesheet at equal specificity
and wins. The `adds` earns itself anyway — a chain that draws a node the page
never draws is measuring nothing.

## A seventh state the contract had already asked for

The estate contour draws `div.node.measured.gone`, and `gone` was not in the
contract. The file's own paragraph says a state it does not name is not checked
and that the gate should say so out loud. It was written down and never acted
on, and it took asking what the second chain actually draws to notice — the same
shape as the finding the whole phase is about.

## The answer is green and the reason was wrong

The five states under the floor read **identically across all three
ancestries, in both themes**. ADR-0058's conclusion holds and 24's open item
closes with a measurement instead of an argument.

Its premise does not. It said no ancestor in either chain paints a background;
`section.phase` paints `color(srgb 1 1 1 / 0.55)`, and the gate now prints that
from the backdrop walk rather than asserting the opposite:

```text
  cycle       paints: section.phase color(srgb 1 1 1 / 0.55)
  estate      no ancestor paints a background
  assertions  no ancestor paints a background
```

The two exempt states carry the evidence — 1.15/1.12 under the map against
1.14/1.13 under the other two — because they are the only ones drawn with a
transparent own background at 45% opacity, so the backdrop reaches both terms of
the ratio unequally. The five with an opaque `::before` colour are invariant to
what is behind them, which is exactly why a false premise produced a true
answer.

0.01 on two exempt states is worth nothing by itself. The premise is worth
something: it is the sentence that would have been quoted the next time.

## The break tests

`docs/sessions/2026-08-11-phase-27-chains-break-test.log`, tree committed first
— the script refuses to run otherwise, because restoring a file with
`git checkout` after a deliberate break is how a completed edit was silently
lost on 2026-07-28.

```text
[0] control                                        exit=0   7 states, 3 ancestries
[1] a probe that asks for something not a colour   exit=2   names state, theme, ancestry
[2] the old `chain` key                            exit=2
[3] `chains` present and empty                     exit=2
[4] the same chain id twice                        exit=2
[5] a chain declaring no nodes                     exit=2
[6] one state's edge lowered in the built page     exit=1   named in all three
[7] control again                                  exit=0   the same table
```

`[6]` is the one that is not about the schema: a real floor failure, reported
once per ancestry, which is what the gate is for.

## Validation

```bash
  make gates                                   # 12/12
  make contrast-check                          # devbox only
  make site-data-check site-page-check docs-check
```

## Cost

Nothing. No AWS call, no cycle, nothing applied. As in Phase 26, one line of
`site/data/topology.json` moves — ADR-0061 takes `adrs` from 61 to 62 — so the
next push republishes.

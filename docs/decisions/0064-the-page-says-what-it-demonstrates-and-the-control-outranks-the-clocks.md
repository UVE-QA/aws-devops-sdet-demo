# ADR-0064: The page says what it demonstrates, and the control outranks the clocks

## Status
Accepted (2026-09-04). Narrows **ADR-0048 D1** — the panel it chose stands, the
ordering inside that panel does not. Extends **ADR-0047 D1**, which put the
identity bar first because the one thing a thirty-second visitor needs was the
last thing on the page.

## Context

The dashboard is cited by a reader who arrives from outside, spends under two
minutes, and leaves. That reader is a different subject from the one every page
decision so far was made for. Every previous one asked *is this true, and does
the page say when it is true*. This one asks *does a stranger, in ninety
seconds, reach the conclusion the page is evidence for*.

Two things were found by reading the page as that stranger.

**The page describes the system and never states what the system demonstrates.**
The identity bar says what the pipeline does and why the page outlives it. The
Environments panel says its figures are observed rather than inferred. Both are
true and neither is the sentence a stranger needs: that the whole lifecycle,
teardown included, runs with nobody in a console, and that what is then reported
was read back out of AWS. The page assumed a reader who would assemble that from
the parts. Thirty seconds is not enough to assemble anything.

**A control that provisions AWS was drawn in less weight than two timestamps.**
ADR-0048 D1 correctly refused the identity bar and put the Launch button in the
Environments panel, next to the state it acts on, and called it that panel's
footer. The clocks then landed in the same panel and are, by their own comment,
"the panel's own footnote". So the order down the panel became: the state, the
footnote that dates the state, and last the only control on the page that spends
money — an outlined button in the same weight as `Refresh`, which re-reads a
JSON document. Nothing decided that ranking; it is what two correct decisions
made separately add up to.

## Decision

### D1 — the identity bar states the claim, in one sentence, in the existing paragraph

Added to the `.claim` paragraph, between what the pipeline is and why this page
survives it:

```text
There is no manual AWS operation anywhere in that sentence, teardown included,
and every state it leaves is read back out of AWS afterwards rather than taken
from the run that claimed it.
```

No new element, no new section, no heading. It is a sentence in a paragraph that
already exists, and it is deliberately the page's own register: it states the
fact and lets the reader draw the inference, in the same shape as "observed in
AWS, not inferred from a green run".

It says "read back out of AWS afterwards" rather than repeating that phrase,
because a claim in the identity bar and its evidence in the panel below should
not be the same words — a reader who sees the sentence twice reads one assertion
made twice, not an assertion and the thing that backs it.

### D2 — the Launch control sits above the clocks, and is filled rather than outlined

ADR-0048 D1's reasoning is untouched: the button acts on what this panel
observes, its refusals are statements about that state, and the identity bar is
navigation and no place for a control that spends money. What is withdrawn is
one word — *footer*. Inside the panel the order becomes:

```text
the environments      what is observed in AWS
the Launch control    the one thing a visitor can do to that state
the clocks            when the two reads above happened
```

The clocks date the panel. A footnote goes under the thing it annotates, and the
control is not part of what it annotates.

The button is filled with `var(--accent)` on `var(--bg)` text rather than
outlined. Every other control on the page re-reads something already there; this
one provisions real infrastructure under a TTL and a watchdog, and it was the
rarest thing on the page drawn in the most ordinary weight available. The text
colour is `var(--bg)` and not a literal white so it follows the theme:
measured 4.6:1 on the light accent and 8.2:1 on the dark one, both above 4.5:1
for text at this size.

Phase 19's behaviour is unchanged and not re-opened: the control is still hidden
ENTIRELY while disabled, because a visible inert control cannot be told apart
from a broken one.

## Consequences

- `assets/index.template.html` is the edit; `site/index.html` is rebuilt by
  `make site-page` and committed with it, as `site-page-check` requires.
- The Environments panel grows by roughly the height of one line and the button's
  extra padding. It is the panel that got shorter when ADR-0048 D1 moved the
  button into it, so this does not put the composition back where 20e found it.
- `contrast-check` does not cover this button. Its contract is the map's state
  boundaries, and a control is not a state — the two ratios in D2 were computed
  by hand from the palette, and no gate will notice if a future palette edit
  takes them under the floor. That is a real gap and it is named rather than
  quietly accepted; the honest fix is a second contract, and it is not this
  change's job.
- The claim sentence is now a THIRD place the "no manual AWS operation" assertion
  is written, after `README.md` and `docs/`. If the assertion is ever narrowed
  the way the static-keys claim was narrowed in Phase 19a, three documents move,
  not two.

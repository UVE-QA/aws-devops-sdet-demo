# ADR-0051: The page says which cycle a figure is about

## Status
Accepted (Phase 20i, 2026-08-09, the page's tense). Does not supersede
anything. It states a property the map was assumed to have and never had, and
puts the three decisions that carry it behind a gate.

## Context

Every figure the map draws comes out of a file that is published when a cycle
ENDS (ADR-0039 D3, ADR-0043 D2). Two consequences follow, and neither had ever
been said out loud:

```text
while a run is going    the page is describing the cycle BEFORE it
at rest                 the page is describing a cycle, not the present
```

Phase 20h ran one live stage cycle and watched the page do its job. It said
three things in the present tense that were not about the present:

**A phase that finished mid-run printed the previous cycle's duration beside a
green `done`, unlabelled.** The label existed — `last time ` — and was hung on
`since`, which is set only while a phase is RUNNING. So the one state where the
figure is most likely to be misread as this run's is the one state that never
got the label. The apply took 8m 30s; the page said 8m 26s. **Four seconds** —
close enough that no eye could have caught it, and asserted by nothing:
`last time` appears nowhere outside `site/index.html`.

**`ECR push` and `migrate + seed` read `not run yet` minutes after running.**
Terraform reports resources; neither of them is one, so no timeline will ever
carry them. The sentence was not stale — it was permanently false, and would
have been printed for the life of the page. The human approval gate is the
third node in that class.

**A stage verified gone from AWS kept every icon at full colour, while prod —
in the identical state — was grey.** A destroy publishes node states for the
destroy node alone, so the apply's figures sit there afterwards describing
resources that no longer exist. `absent` means "nothing has been recorded",
never "not in AWS", and the two had been drawn alike since the map existed. Two
environments in one state, drawn as opposites, three inches below a panel that
correctly read `destroyed`.

The fourth thing 20h found is not tense: **the cost line was read past by the
person who had just run the cycle to produce the number.** It rendered as an
unheaded grey paragraph under the map. Every other figure on the page is in a
bordered box with a label over it.

## Decision

### D1 — a published figure is labelled whenever anything has happened since it was published

The question is not "is this phase running". It is "has the page got a reason
to believe what it is showing is not current" — and while ANY run is in flight,
the answer is yes for every figure on the page, including on a phase whose turn
has not come. `figuresAreOlder(observation)` asks it once, of the whole page.

A completed run is deliberately not "older": its publish step has already run,
so the figures ARE that run's, and labelling them would be a second wrong claim
in the other direction. The same reasoning `bindingState()` uses to say nothing
about a completed run, asked for the opposite purpose.

### D2 — "is it in AWS" is the environments panel's answer, taken and not re-derived

The panel above the map already reads `status/<env>.json`, already decides
whether the newest run makes that reading stale, and already draws `up`,
`destroyed` or `unknown`. The map is handed that verdict on the existing
`cycle:observed` event, which was built for exactly this (ADR-0026's rate
budget: the map may not read a source twice).

It is not re-derived from the timelines, and the alternative was available —
comparing the destroy timeline's date against the apply's would have worked
today. It is refused because it is a SECOND definition of "destroyed" on a
second host, which is this repository's `docker compose config --images` trap
exactly, and because it would answer where the panel says `unknown`. The map is
not entitled to a firmer answer than the panel it is drawn under.

A node whose environment is gone keeps its figures and changes the word around
them: they were measured, and they are about a cycle that ended. The destroy
node is the exception, and the reason is the point of the whole phase — it is
the one node a teardown actually measured, and greying it would erase the
evidence that the teardown ran.

### D3 — a node says which kind of not-knowing it is in

`not run yet` and "nothing will ever measure this" are different sentences and
were one. The distinction is not written beside the map: `observer` is already
on every node in `assets/topology-groups.json` and already reaches
`data/topology.json` — `terraform`, `report` or `actions`. A node observed by
Actions says `not measured here`, permanently, and that is the true thing about
it. ADR-0043 D4 keeps what a node does not know visible; this says which.

### D4 — the tense decisions are a lifted block, and the gate proves they are asked

The three decisions live in one marked block in the page and
`scripts/check-page-tense.mjs` lifts it out of the BUILT page and runs it,
exactly as `check-live-state.mjs` does for the run-layer state machine and for
the same reason (ADR-0043 D3): the rule runs in the visitor's browser, so a
copy of it in Python would be one definition on two hosts.

**The gate also requires each function to be CALLED outside its own block.** A
block that is correct and unused renders exactly the page 20h found, and every
case would stay green — the gate that has only ever been seen green, arriving
from the one direction its cases cannot look.

### D5 — the cost line is a labelled box, in the page's own vocabulary

The same `.panel` the environments and the current cycle are drawn in, under
the map, with the heading carrying "last cycle" so the paragraph does not. No
new element type: the finding was that this figure was the only one NOT in the
shape the page uses for figures.

## Consequences

```text
- The page is now allowed to be about a cycle rather than about now, and says
  so. Nothing that follows removes that: the figures still publish at the end,
  and every one of them is still about a cycle that has finished.

- `make page-tense-check` runs in ci.yml's `checks` job. It reads the BUILT
  page, so a template edited without rebuilding reddens it - the property
  site-page-check exists for, arriving here for free.

- WHAT THE GATE CANNOT SEE, and it is half of this: it proves what the block
  ANSWERS and that something asks. It does not prove the answer reaches the
  pixels. What draws a node is not in a liftable block, needs a DOM, and is
  gated by nothing. The honest reading of a green page-tense-check is "the
  decision is right and it is consulted", never "the map is right".

- The coupling check was itself found broken by its own break test, twice, and
  the second reading is the one worth carrying: the phase header's COMMENT says
  "figuresAreOlder() is that question", so a search for the name in the built
  page passed with every call deleted. A check satisfied by prose about the
  thing is not a check. Comments are stripped now; the break log is kept.

- A destroyed environment goes grey only when the panel is sure. During a
  teardown, and whenever the Actions read has failed, the map keeps the last
  picture it could stand behind rather than guessing in either direction.

- `.node.gone` is drawn identically to `.node.absent` on purpose. What a reader
  needs from both is the same - do not read this as live - and the WORD is what
  tells them apart, which is ADR-0047 D6's second channel used for the thing it
  was added for.
```

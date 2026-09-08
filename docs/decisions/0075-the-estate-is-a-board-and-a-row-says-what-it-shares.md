# ADR-0075: The estate is a board, and a row says once what every tile shares

## Status
Accepted (Phase 39, 2026-09-08). Applies **ADR-0047 D3** — the rule that a phase
says a shared word in its header rather than twenty-six times under it — to the
estate contour drawn by **ADR-0054 D1/D5**. It does not touch **ADR-0047 D6**'s
contrast floor, and it does not change what any node decides: `nodeTense()` is
untouched, and every word on this page is still the word it returns.

**ADR-0074** is the dashboard-wide redesign and is still *Proposed*. This is not
a slice of it: it changes one contour that already exists, on the page as it is,
and would be equally right if 0074 were abandoned.

## Context

The owner asked for the estate to be *enlivened* — large service marks, lit in
the order the graph builds them, so a reader can see what exists without reading.
The visual was settled over five prototype rounds in the scratchpad before any
page code was written, per the working agreement that we converge in conversation
first.

The estate contour drew fifteen nouns as cards in a `minmax(18.5rem, 1fr)` grid.
Each card carried a 1.4rem mark and four lines of text, so the answer to *what is
in AWS right now* was fifteen paragraphs, read left to right. The AWS
Architecture Icons were on it already and were the smallest thing on it.

Drawn as a board — the mark at 2.9rem, leading, with the words under it — three
sentences turned out to be printed once per tile and to be identical across a
whole environment:

    terraform                                                    ×15
    these figures are from the cycle that ended                  ×7  (stage)
    last seen destroyed in AWS; a cycle is under way and has
      not reported                                               ×8  (prod)

On a 18.5rem card that is a line each. On a 6.9rem tile the last one is five
lines under a mark meant to be read at a glance, and it is the same five lines
seven tiles running. This is ADR-0047 D3's finding exactly — *the information is
stated; the repetition is not* — reached by a different route.

## Decision

**D1. The estate contour is a board of marks, in `topology.json`'s own order.**
Fixed-width tiles, not fractional ones: `auto-fit` with `1fr` stretched seven
tiles across the stage row and eight across the prod row, so the same service sat
at two different sizes one line apart — the one thing a board that exists to be
compared across environments must not do. The order is not sorted on the page;
`scripts/generate-topology.py` writes the nodes in the order `infra/` builds
them, and a board that re-sorted them would be a second opinion about the graph,
held on the page, drifting from the graph the moment a module moved.

**D2. What every tile of a row would say, the row says once, in its header.**
The state word, the sentence qualifying it, and the tool. Same two-pass shape a
phase has used since 20e.1: draw the nodes, ask the drawn elements what they
carry, draw them again without whatever all of them carry. Read back off the
elements and never re-derived — a second copy of `nodeTense()`'s branches living
in `renderEstate()` would agree with the real one right up until it did not,
which is this repository's `docker compose config --images` trap.

**Computed, never assumed.** `nodeTense()` takes a per-RECORD branch —
`published_by` is a property of the document a node was measured by, not of the
environment — so two nodes of one environment *can* disagree. On the day they do,
the sentence stays on every tile and the header says nothing.

**D3. Nothing on a dead tile is coloured, including the phase reference.**
ADR-0058 draws the verb of a `touches` reference in the accent. On a card among
cards that is right. On a torn-down row those verbs were the brightest marks on
the screen, under a grey icon, saying `destroys 8` in the colour this page uses
for what is happening — which is the complaint ADR-0070 was written for, arriving
again through a different element. The reference stays; it stops being the
loudest thing in a row that exists to look quiet.

**D4. On this board, `gone` and `absent` stop looking alike.** Everywhere else
they are drawn identically on purpose, and the comment above `.node.absent` gives
the reason: what a reader needs from both is *do not read this as live*, and the
WORD tells them apart. On a board that reasoning inverts — the word is the
smallest thing on a tile and the shape is the largest, and two faint dashed rows
one above the other are indistinguishable at a glance in exactly the case this
contour exists for: an environment just torn down sitting under one that has not
been.

So the board separates them by the one thing that is actually different: **`gone`
was measured and `absent` never was.** A destroyed tile is filled, solid-edged,
and keeps the figures it earned while it stood. A tile nothing has observed is an
empty dashed outline with no figures, because the future is not measured. Neither
is coloured — both are past or absent, and colour on this board means present.

`contrast-check` exempts both states with *"the word carries it"*. That stays
true: the word is on the row header, and when a row is mixed the hoist does not
happen and every tile keeps its own.

**D5. A gate that reads one place now reads the union of two, and a break test
says it still bites.** `claimFiguresDated()` in `check-page-inflight.mjs` read
`.nstate` on the node. With the sentence on the row header it reported seven
undated figures under a header dating all seven — a true statement about the DOM
and a false one about the page. It now reads the node's line *and* the header
that governs it, harvested through `closest()` rather than assumed.

A claim that reads more places is satisfied by more pages, so
`scripts/break-estate-hoisted-note.sh` reintroduces both ways the sentence can be
lost and requires the gate to fail:

  * **[B]** `nodeTense()` never produces it — the defect the claim was written for
  * **[C]** every tile correctly declines to repeat a sentence the row shares, and
    the row never draws it — the defect the hoist ADDS, and the one a per-node
    reading would have caught for free

## Consequences

The board is *shorter* than the cards it replaces, which was not the aim:
`measure-page` puts the page at 3387px against 3458px at 2560×1440 at rest, and
9060px against 9458px on the phone. The repetition was the height.

**This is a still picture, and the enlivening the owner asked for is not in it.**
The estate is painted without the run layer by ADR-0054 D3, and
`check-live-state.mjs` fails the build if an estate node ever reaches it. Node
states are published once, by `publish-status.sh`, after `terraform apply` has
returned — so a whole environment changes at once, when its job ends. Icons
lighting one at a time *at the moment each resource is created* needs a reading
that does not exist yet: a fold of the partial event stream, published while the
apply is still running. `scripts/fold-timeline.py` already records exactly the
three states that would need — complete, started-and-unfinished, absent — and
already refuses to call a stream without its `.rc` file complete, which is the
correct answer for a killed run and the wrong one for a live one. That is a
separate decision, about the runner and the publish path, and it costs a cycle to
verify. It is not taken here.

`--tile` and `--tile-icon` join `--node-min` and `--card-min` as measured floors.
Like those, they are figures that were measured once; unlike those, they are two
numbers sized against each other, so moving one alone is a change to the other.

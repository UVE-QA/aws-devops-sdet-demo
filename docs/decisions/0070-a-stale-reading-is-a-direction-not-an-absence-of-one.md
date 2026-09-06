# ADR-0070: A stale reading is a direction, not an absence of one

## Status
Accepted (Phase 35, 2026-09-06). Narrows the rule recorded in the page-tense case
`a-reading-that-could-not-be-checked-is-not-a-verdict`, and finishes what
**ADR-0053**'s 20h finding started. **ADR-0047 D6**'s contrast floor is untouched;
this is about which nodes are dimmed, not about how dim they are.

## Context

The owner looked at the estate while a cycle was starting and asked why every
service card was at full colour "as if they already existed". Nothing existed:
a sweep of the account at that moment returned 0 RDS, 0 load balancers, 0 ECS
services.

The panel three inches above the cards read **UNKNOWN**, with *"Last reported
values, shown for reference only"*. The cards silently contradicted it.

`envTense()` returned `"unknown"` for any stale observation, and `unknown` is
drawn like `exists`. It is not only the in-flight case: on the at-rest fixture,
where both environments are verified **destroyed** and the observation is seven
hours old, all eight estate nodes came back `class="node measured"` and **zero**
nodes carried `gone`.

That is the shape of the 20h finding recorded in the comment above `nodeTense()`:

> a stage verified gone from AWS kept every icon at full colour, while prod — in
> the identical state — stayed grey

Fixed then for a *verified* destroyed environment, and reachable ever since by
the route that comment does not cover: **staleness**.

### The prior decision, and why it does not hold

This was not an oversight. The case said so:

> The map is not entitled to a firmer answer than the panel gives — so a stale
> `destroyed` must not grey the map, and a stale `up` must not colour it.

The principle is right and the application inverted it, because it assumed grey
means *destroyed*. This page's own CSS says otherwise:

> `absent` and `gone` look alike because what a reader needs from both is the
> same — **do not read this as live**

*Do not read this as live* is **weaker** than the panel's `unknown`, not firmer.
The firmer answer is the lit one — *read this as live* — and that is what was
being drawn.

**The second half of that rule never held either.** It says a stale `up` must
not colour the map; a stale `up` returns `unknown`, and `unknown` renders lit.
The prose asserted a behaviour the implementation did not have, and the gate
could not catch it because it checks the word `envTense` returns and not what
that word is drawn as.

## Decision

### D1 — a stale reading keeps the state it had, because a cycle is a transition

A cycle moves an environment **between** two states. Until it reports, the
honest reading is that it is still the one it was:

```text
was destroyed, now stale    it is not up YET      -> grey
was up, now stale           it is not gone YET    -> lit
```

So `envTense()` gains one value, `destroyed-unverified`, and `nodeTense()` a
branch for it. The other direction needs nothing: `unknown` already renders lit,
which is the correct answer for an environment being torn down that has not yet
been reported gone.

Only one direction gets a name because only one was wrong. Symmetry for its own
sake would have dimmed a live prod the moment a teardown started, before
anything had confirmed it — losing exactly the signal a reader wants most.

### D2 — the word may not claim what the colour implies

`gone: true` for the same reason as the verified case: what a reader needs is
*do not read this as live*. But the word may not say the environment **is**
destroyed, because a run is under way whose purpose is to change that. It says
what was last seen and that nothing has confirmed it since:

```text
word  destroyed
note  last seen destroyed in AWS; a cycle is under way and has not reported
```

### D3 — the node that did the destroying keeps its figures

`node.service !== "destroy"` guards the new branch exactly as it guards the
verified one. A teardown is the one thing on the map that cycle really measured,
and it is not dimmed by the outcome it produced. Covered by its own check rather
than inherited by argument.

## Consequences

- The page-tense case is rewritten rather than deleted, and carries both the old
  rule and why it is narrowed. 16 cases, 49 calls -> 51.
- **No gate would have caught this.** `page-tense-check` reads the word a
  function returns; nothing checks what that word is DRAWN as, which is how a
  case could assert "a stale up must not colour it" while the page coloured it.
  The finding came from a person looking at the page and saying the cards looked
  wrong. That is the fourth time on this dashboard, and the second where the
  contradiction was between two elements three inches apart.
- **Untested against a live teardown.** The direction that changed is
  destroyed -> up, which this cycle exercises. The other direction is asserted by
  argument and by one case, and the owner has already said that if it reads badly
  during a real destroy we take the symmetric option instead. Named so the next
  session knows it is a prediction, not an observation.
- `destroyed-unverified` is a fifth value from `envTense()`, and the signature
  string at the bottom of the page includes it, so a change of direction now
  moves the layer signature. That is correct - it is a change in what the page
  says - and it means a stale environment flipping direction redraws the map.

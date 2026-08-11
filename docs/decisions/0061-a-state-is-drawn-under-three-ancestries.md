# ADR-0061: A state is drawn under three ancestries, and the reason it looks the same was wrong

## Status
Accepted (Phase 27, 2026-08-11). Closes the item **ADR-0058** carried forward
and Phase 25 and Phase 26 did not reach. Extends **ADR-0047 D6**: the floor and
the six states it measured are unchanged; what changes is where they are
measured and how many there are.

## Context

`assets/contrast-contract.json` declared one probe chain,
`main > .cycle > .phase > .set`. Since Phase 24 the estate contour draws the
same states under a chain of its own, so the gate was measuring one ancestry and
saying nothing about the other. ADR-0058 wrote the finding down and closed it
with an argument rather than a measurement:

> No ancestor in either chain paints a background, so the colours SHOULD be
> identical — and `should` is what "an instrument aimed at the wrong scope reads
> green" is made of.

That sentence is right about the method and wrong about the fact.

## Decision

### D1 — `chain` becomes `chains`, and the old key is a refusal rather than a migration

A contract still carrying `chain` would measure one ancestry and read green
about the rest, which is the defect this phase closes, surviving the fix. It is
named out loud instead:

```text
the contract carries `chain` and not `chains`. Since Phase 27 the page has three
ancestries and this gate probes each; a single chain would measure one of them
and say nothing about the other two.
```

Four more refusals come with the schema: no chains at all, a chain with no `id`,
the same id twice, and a chain declaring no nodes — the last because its probes
would hang off `<body>` and measure an ancestry the page does not have. Every
one was fired, and the by-name state refusal was fired again on the new shape,
where it now names the ancestry as well as the state and the theme.

### D2 — There are THREE, and the third was found by measuring the built page

ADR-0058's finding named two. The assertions contour hangs its suite nodes
straight off `div.suites`, with no `.set` in between:

```text
cycle       main > div#rows.cycle > section.phase > div.set > div.node
estate      main > section#c-estate.contour > div#estate-envs >
              section.estate-env > div.set.estate-set > div.node
assertions  main > section#c-assertions.contour > div#suites.suites > div.node
```

Read off the rendered page with a walk from a real node upwards, not off the
template. The template would have answered too, and it is where the count of two
came from.

The third chain carries `adds: "assertion"`, because that contour puts the class
on every node it draws and `.node.assertion` sets `opacity: 1` — and this gate
composites by opacity. A chain that drew a node the page never draws would be
measuring nothing.

### D3 — `gone` is the seventh state, and the contract had already asked for it

The contract's own paragraph said: *"A seventh state on the map means a seventh
line here — a state the contract does not name is not checked, and the gate says
so out loud rather than passing quietly."* The estate contour draws
`div.node.measured.gone`, and `gone` was not in the file. Written down once,
never acted on, and it took asking what the second chain actually draws to
notice — which is the same shape as the finding this whole phase is about.

It is exempt from the floor for `absent`'s reason and not a second decision:
every CSS rule that names one names the other, and neither sets a `::before`
colour, so both fall to the base edge.

### D4 — The ancestries agree, the argument for why did not, and both are printed

```text
                         cycle          estate     assertions*
  state          light    dark   light    dark   light    dark
  live           4.63    7.62    4.63    7.62    4.63    7.62
  failed-now     3.17    3.29    3.17    3.29    3.17    3.29
  working        3.22    4.76    3.22    4.76    3.22    4.76
  done           3.37    5.35    3.37    5.35    3.37    5.35
  suite          3.38    5.50    3.38    5.50    3.38    5.50
  gone           1.15    1.12    1.14    1.13    1.14    1.13   exempt
  absent         1.15    1.12    1.14    1.13    1.14    1.13   exempt
```

**The five floored states are identical across all three, in both themes.** The
conclusion ADR-0058 reached by argument is the conclusion the measurement
reaches, and 24's open item closes green.

**The premise it argued from is false, and the gate now prints it from the
backdrop walk rather than asserting it:**

```text
  cycle       paints: section.phase color(srgb 1 1 1 / 0.55)
  estate      no ancestor paints a background
  assertions  no ancestor paints a background
```

`.phase` paints at 55% alpha. The two exempt states show it — 1.15/1.12 under
the map against 1.14/1.13 under the other two — because they are the only states
drawn with a transparent own background at `opacity: 0.45`, so what is behind
them reaches both terms of the ratio unequally. The five with an opaque
`::before` colour are invariant to their backdrop, which is why the wrong
premise produced the right answer.

0.01 of contrast on two states that are exempt from the floor is worth nothing
by itself. The reasoning is worth something, because reasoning is what gets
reused: "no ancestor paints a background" would have been quoted the next time
this question came up, and it was not true when it was written.

## Consequences

- `make contrast-check` measures 7 states x 3 ancestries x 2 themes, with the
  control re-measured inside every chain — the backdrop walk starts at the
  probe's parent, so a control taken once outside would be a different
  measurement from the ones it is vouching for.
- Adding a contour to the page means adding a chain here, exactly as adding a
  state means adding a line. Both are now stated in the contract's own prose,
  and the second one is stated as a promise that was already broken once.
- `scripts/break-contrast-chains.sh` fires all six refusals and one real floor
  failure, with a control green either side. It is committed because the subject
  is a SCHEMA: the next change to it owes the same proof, and a break test
  nobody can re-run is a break test nobody re-runs. Output in
  `docs/sessions/2026-08-11-phase-27-chains-break-test.log`.
- The floor, the six original states and their exemptions are untouched.
  ADR-0047 D6 stands as written.

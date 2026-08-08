# 2026-08-08 — Phase 20a: the layout, looked at before it was reasoned about

The layout is the only part of Phase 20 that cannot be derived from the
repository, so it was built in a chat sandbox with a clone and a headless
Chromium, rendered against a hand-built fixture, and LOOKED AT — three times,
each time changing something the previous picture had made obvious. Nothing was
applied, nothing was published, `site/index.html` was not touched.

## The finding: a picture makes claims too

The first attempt did what ADR-0039 D5 describes literally — fold the chain
serpentine when it does not fit — and folded it node by node. It read well. It
was also wrong, and wrong in this project's oldest way:

```text
drawn      VPC -> Secrets Manager -> RDS -> ALB -> ECS -> CloudWatch
true       Terraform creates them from a DAG. Nothing in infra/ orders those
           six, and several of them run concurrently
```

An arrow is a claim about order. ADR-0026's rule — a source may only assert what
it observes — was written about JSON documents and applies unchanged to a
diagram, which is a thing this project had not yet had to notice.

The fix moves the unit of sequence up one level: **the phase carries the
sequence, and the nodes inside a phase are a set with no arrows between them.**
Phases fold serpentine; a cluster does not.

It also fixed a legibility problem nobody had raised. In the node-level fold,
one row read across three different phases — six services from the stage apply,
then the provisioning task, then a test suite — and the phase a node belonged to
survived only as a digit in a chip. Grouping was not a cosmetic improvement on
top of the correctness fix; it was the same fix.

## What the pictures settled

```text
packing    serpentine at PHASE level; odd rows read right to left, so the
           direction arrows carry information rather than decorate
floor      node width and every type size have a minimum and are never scaled
           to fit. Columns are DERIVED from that floor - 3 clusters at 1440,
           2-3 at 1180, 1-2 at 834, 1 at 390
mobile     free, and exactly as ADR-0039 D5 predicted: at one column the
           serpentine has nothing to fold, so the same code renders the
           vertical column. No second layout, no media query for the map
priority   desktop and laptop are the intended view and the page SAYS so, in
           the legend. Decided with the user: state it rather than engineer
           around it, and revisit after a real cycle rather than before
states     absent / at rest / live are distinguishable at a glance. Absent is
           the same icon in greyscale, not a second set of marks
```

## Icons: the question ADR-0039 refused to let anyone guess

The ADR required 20a to establish AWS's terms from AWS's own pages, or sidestep
the set with project glyphs. Established — and the answer is that **AWS does not
say**. The icons page permits use "to create architecture diagrams" and lists
materials "like whitepapers, presentations, data sheets, and posters", links no
licence document specific to the package, and never uses the word website; the
trademark guidelines give no blanket permission to display marks publicly and
forbid altering them; the site terms forbid reproduction "for any commercial
purpose without express written consent". None of the three names a public web
page, in either direction.

So what was taken is a DECISION in the absence of a "no", not a permission, and
`assets/aws-icons/NOTICE.md` exists to keep those two apart after the conversation
is forgotten. Seventeen icons, unmodified, folded into one inline sprite so the
page keeps the property it has had since 11.1c: one file, no build step at
request time, no runtime dependency. ~48 KB inline, ~12 KB over the wire.

**A test suite, a human approval and a teardown got project glyphs.** They are
not AWS services, and drawing them in AWS's visual language would be a claim
about what they are — the same species of error as the arrow above, in a
different medium.

## Two things the tools got wrong, both caught by measuring twice

**The instrument, not the page.** A raw `chrome --headless --screenshot
--window-size=390` produced a phone screenshot with the heading clipped and the
permanent band running off the right edge — an unmistakable overflow bug. There
was no bug. Driven through Playwright with a real viewport, `scrollWidth ==
clientWidth` at all four widths. Old headless does not set the layout viewport
from `--window-size` the way the flag implies. This is the primer's "a break test
measured through a pipe measures the pipe", in a browser: the reading was
indistinguishable from a real defect, and the only thing that separated them was
measuring again with a different instrument.

**The gate, doing its job on its author.** `make docs-check` went red on the
first attempt at this session's `docs/phase-gates.md` entry: it named `make
site-data-check`, a target 20a has not built yet. A planned target, written in
the present tense, in a copyable form — exactly the defect the gate exists for,
committed by the session that was writing about not committing it.

## Delivered

```text
assets/map-pilot.template.html the page: layout, states, legend, counts
site/map-pilot.html            built from it; committed so a clone can open it
site/data/topology.json        FIXTURE, hand-built from infra/ and tests/ at
                               4a4f056, and it says so in its first field
assets/aws-icons/*.svg        17 unmodified AWS Architecture Icons + NOTICE.md
scripts/build-icon-sprite.py   folds them into one sprite; make site-pilot
docs/decisions/0039-…          the icons answer, recorded where the ADR asked
docs/next-phases.md            what the pilot settled, and what it left open
docs/phase-gates.md            20a marked PART done: layout only
```

The fixture is where the schema came from, which is the direction this session
was run in on purpose: the layout decided what `topology.json` must carry, and
the generator now has a contract to satisfy rather than a shape to invent.

Two refusals of the sprite builder were exercised and both were red: a missing
icon file, and a template that has lost its injection marker.

## Not done, and not claimed

The generator, the `site-data-check` drift gate and its two break tests, and
folding the map into `site/index.html`. Left open until a real cycle can speak:
autoscroll (nothing in a fixture exercises it), whether the phone should collapse
the two large phases by default, and a node labelled "Route 53 + ACM" carrying
one mark for two services.

Cost: **$0**. No AWS API was called and no environment existed at any point.

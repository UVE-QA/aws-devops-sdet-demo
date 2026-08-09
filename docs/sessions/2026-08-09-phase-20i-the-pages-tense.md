# 2026-08-09 — Phase 20i: the page's tense

Evidence — the break test of the new gate, ten probes with controls either side,
in `docs/sessions/2026-08-09-phase-20i-page-tense-break-test.log`.
Cost: nothing. No cycle, no AWS call, nothing applied. `site/` changes, so the
next push republishes the static page.

The cursor's next allowed step was **the page's tense**, in four clauses:

```text
a figure is never printed without the cycle it belongs to
`not run yet` is not said about something that just ran
a destroyed environment does not read as a live one
the cost line gets a place
```

All four were found by watching one live cycle (20h). All four are reachable on
fixtures, which is why they were a $0 session — and why each could carry the
break test this project requires before a gate means anything.

## The one root, and why it is not a bug

Every figure the map draws comes out of a file published when a cycle **ENDS**.
So the page is never describing the present: during a run it is describing the
cycle before it, and at rest it is describing a cycle rather than now. That is a
property of the design (ADR-0039 D3), not a defect. The defect was that the page
had never been made to SAY it — and the three ways it failed to are the three
findings.

**ADR-0051** records the decisions. The three that carry the tense now live in
one lifted, gated block; the fourth clause is markup.

## 1 — the label was on the wrong question

`last time ` existed. It was hung on `since`, which is set only while a phase is
RUNNING. So a phase that **finished** mid-run — the one state where a stale
figure is most likely to be read as this run's — was the one state that never
got it. This run's apply took 8m 30s and the page printed 8m 26s beside a green
`done`.

Four seconds. A defect that answers rather than one that stops, invisible to any
eye, and asserted by nothing: `last time` appeared nowhere outside
`site/index.html`.

The rule is now asked of the whole page rather than of one phase, because the
old rule also missed a phase whose turn had not come yet — same run, same stale
figure, no label, and nobody had noticed that half at all.

## 2 — three nodes that will never be measured said they had not run yet

`ECR push`, `migrate + seed` and the human approval gate. Terraform reports
resources; none of the three is one, so no timeline will ever carry them. `not
run yet` about them was not stale — it was permanent, and it was being printed
minutes after two of them ran.

Nothing new is written beside the map to fix it. `observer` is already on every
node in `assets/topology-groups.json` (`terraform`, `report`, `actions`) and
already reaches `data/topology.json`; the page had simply never read it.

## 3 — two environments in one state, drawn as opposites

stage was verified gone from AWS and kept every icon at full colour. prod, in
the identical state, was grey. Three inches above both, the environments panel
correctly read `destroyed`.

The cause is publishing, again: a destroy writes node states for the destroy
node alone, so the apply's figures sit there afterwards describing resources
that no longer exist. `absent` means "nothing has been recorded", never "not in
AWS".

**The fix takes the panel's answer rather than working one out.** Comparing the
destroy timeline's date against the apply's would have worked today, and was
refused: it is a second definition of `destroyed` on a second host — this
repository's `docker compose config --images` trap — and it would answer where
the panel says `unknown`. The verdict rides the `cycle:observed` event that
already exists for exactly this hand-over (ADR-0026's rate budget).

Two things follow that are worth naming. A node keeps its figures and changes
only the word around them: they were measured, and they are about a cycle that
ended. And **the destroy node keeps its colour** — it is the one node a teardown
actually measured, and greying it would erase the evidence that the teardown
ran. That case is in the fixtures as a control, because a fix that greys
everything in a destroyed environment passes every red case in the directory.

## 4 — the cost line gets a place

It was an unheaded grey paragraph under the map, and the person who had just run
the cycle to produce the number read straight past it. It is now the same
`.panel` the environments and the current cycle are drawn in, with the heading
carrying "last cycle" so the sentence does not repeat it. No new vocabulary: the
finding was that this was the only figure on the page NOT in the shape the page
already uses for figures.

No gate. Nothing here is a rule — it is markup, and `site-page-check` is what
keeps it from drifting out of the template.

## The gate, and the half of it that failed first

`make page-tense-check` lifts the marked `PAGE TENSE` block out of the BUILT
page and runs it against eleven flat fixture cases — the same move
`check-live-state.mjs` makes on the same file, for the same reason (ADR-0043
D3). Eight of the cases are controls: the states that must NOT change.

It also asks something the cases cannot: **that each function is called outside
its own block.** A block that is correct and unused renders exactly the page 20h
found, with all eleven cases green.

That check was itself broken by its own break test, twice, and the second
reading is the finding of this session:

```text
7a  one of two callers removed  -> green, and correctly: the check asks for
                                   at least one, and the page really did still
                                   ask. A badly aimed probe, mine.
7b  BOTH callers removed        -> still green. The phase header's own COMMENT
                                   reads "figuresAreOlder() is that question",
                                   and the search found the name in it.
```

A coupling check satisfied by prose ABOUT the coupling is not a check. Comments
are stripped before the search now, and 7b refuses. It was found only because a
break test that failed to break was written up instead of pushed past — which is
the rule the primer already carries, arriving for the third time.

## What the gate cannot see

It proves what the block ANSWERS, and that something asks. **It does not prove
the answer reaches the pixels.** What draws a node needs a DOM, is not in a
liftable block, and is gated by nothing — so a green `page-tense-check` means
"the decision is right and it is consulted", never "the map is right".

The rendering half was not attempted here and the reason is worth recording
rather than leaving as an omission: this sandbox has no browser, and the two
instruments that do have one — `check-contrast.mjs` and `measure-page.mjs` —
both need the Playwright install that lives with the suites. A rendering check
also needs published node records, which `measure-page`'s fixtures deliberately
do not carry: adding them would move its height baseline and invalidate the
figures 20e and 20g were decided on.

## Break test

Ten probes, controls either side, in
`docs/sessions/2026-08-09-phase-20i-page-tense-break-test.log`. Every break is
made in `assets/index.template.html` and BUILT, so the gate reads it out of
`site/index.html` the way a browser would. Exit statuses are `make`'s and are
labelled as such — a status taken through a pipe measures the pipe.

```text
1  a run WAITING for approval treated as no run at all      RED
2  a stale reading believed                                 RED
3  the observer clause disabled -> `not run yet` returns    RED  (the 20h defect)
4  the destroyed clause removed -> full colour returns      RED  (the 20h defect)
5  the destroy node greyed with its environment             RED  (the control)
6  REFUSAL: the end marker renamed                          REFUSED
7  REFUSAL: the block correct and nothing asking it         green, then REFUSED
8  REFUSAL: cases/ moved away, and cases/ empty             REFUSED, twice
0  and 9, 10  controls: green before, green after, clean tree
```

## Validation

```bash
make page-tense-check     # 11 cases, 23 calls
make site-page-check      # the committed page matches the template
make live-state-check     # 12/12 - the block beside this one still folds
make site-data-check      # the map's data unchanged
make docs-check           # 6 documents, 0 findings
```

Not run here, and it should be run on the devbox where a browser exists:

```bash
make measure-page         # the cost box adds a row under the map
make contrast-check       # .node.gone reuses .node.absent's palette
```

## What this session did not do

The packing left by 20g — the comb at 2560 and the ragged top row — is
untouched, as 20g left it. The rendering half of the tense, above. And no cycle
was ordered: nothing here needs one, and the next one will be the first to show
these four sentences against real records.

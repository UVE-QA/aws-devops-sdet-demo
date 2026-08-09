# ADR-0053: The page re-reads what it draws, and says which not-yet it means

## Status
Accepted (Phase 20l, 2026-08-09). Closes the finding **Phase 20k** recorded and
the mirror clause it left beside it. Extends **ADR-0039 D4** — the run layer is a
layer over the permanent map — with WHEN that layer is fetched, which D4 never
said. **ADR-0026**'s rate budget is unchanged and is the reason only the bucket
joins the poll. **ADR-0043 D4** and **ADR-0051** are the rules the mirror clause
belongs to.

## Context

20k opened the dashboard, ran a full cycle past it — stage up, promoted to prod,
both torn down, both priced — and watched the page fail to deliver its own
figures to a reader who left the tab open.

`readRunLayer()` fetches the five things the map draws numbers from, per
environment: `timeline/<env>/nodes-apply.json`, `nodes-destroy.json`,
`latest.json`, `results/<env>/latest.json` and `cost/<env>/latest.json`. It was
called ONCE, in the bootstrap chain, beside `data/topology.json`. Meanwhile
`tick()` re-read `status/*.json` and the Actions API every 30 seconds, and the
Refresh button was a forced `tick()`.

So the WORDS refreshed and the FIGURES never did — and that combination is worse
than staleness, because the words move confidently over numbers that cannot:

```text
a green promotion left phase 6 reading `not run yet`, minutes after the same
  phase had said `done` while it ran
a green prod teardown left its node `not run yet` while the published record
  said `measured` at 467s
prod's price could not reach the cost box, so the box stayed off the page
Refresh changed only the sentence around the old numbers
```

Three minutes untouched — six bucket polls at the cadence the page prints about
itself — did not converge. One hard reload fixed all four, and that reload was
written down as a prediction before it was pressed.

**No fixture here could have found it.** `make measure-page` mocks every remote
source and never polls; `check-live-state.mjs` and `check-page-tense.mjs` lift a
pure block out of the built page and hand it data. Between them they can say
what the page ANSWERS. None of them can say when it asks.

Beside the finding, 20k left a mirror. A node has no published record until its
cycle ENDS, so while a cycle runs every phase ahead of the front says `not run
yet` — the same words as a phase nothing has ever measured. For most of a cycle
that is most of the map.

## Decision

### D1 — The run layer is re-read; the repository's files are not

The ten objects a CYCLE publishes are re-read. `data/topology.json` and
`data/suites.json` are generated from the repository and cannot change without
the page itself being republished, so they are read once — a reader holding a
superseded page is a reload's problem, not a poll's. A suites read that FAILED is
retried, because the alternative is that one bad response removes the
collected-tests sentence for the life of the tab.

### D2 — On the bucket tick, through the event that already exists

`tick()` → `renderAll()` → `announceCycle()` fires `cycle:observed` once per
bucket tick, and Refresh is a forced tick. The re-read hangs off that event: one
clock for both paths, no second timer, and the map still learns nothing about the
dashboard's internals — which is the boundary `announceCycle()` was built to
keep. The Actions API stays handed over rather than fetched twice (ADR-0026: 60
anonymous requests an hour is the whole budget). The bucket has no such budget.

One re-read at a time. A tick that arrives while one is in flight draws the words
and skips the fetch rather than queueing a second set behind a set that has not
come back.

### D3 — The layer is REBUILT, never appended to

The old body pushed into four arrays and merged into a fifth, which was correct
exactly once. Called twice it duplicated the cycle list and the `unknown` ledger,
and a node dropped from a republished file lingered for as long as the tab
stayed open. The sources are folded into a fresh object and swapped in at the
end, so a read that half-failed cannot leave the page holding half of one cycle
and half of another. `observation`, `envs`, `phase` and `node` are not touched:
they come from the event, not from these files.

### D4 — The re-render signature grew a figures half

`livePrev` decided whether to redraw, and it was made of STATES: phase states,
node states, the environment tense, older-or-current. The run layer can change
without any of them moving — a teardown publishes a price, an apply publishes a
duration, a suite publishes a verdict. Without this clause D1–D3 fetch new
numbers on time and decline to draw them, which is the same page as before the
fix arriving by a different route.

### D5 — Two things drawn from the layer moved out of the bootstrap chain

The sentence under the map dates the cycle and says what the suites reported;
the disclosure cut carries the ledger of what a cycle touched and the map does
not draw. Both were written once, at load. Re-reading the figures and leaving
those where they were would have put fresh numbers under a stale date — the same
defect one level up, which is this project's most reliable shape.

### D6 — `not reached yet` is not `not run yet`

`nodeTense()` gains a fourth argument. When a cycle is under way AND it is about
this node's environment, a node with no record says `not reached yet — a cycle is
under way and has not got here`, dimmed like the other unobserved states, with
its own line in the legend. Otherwise `not run yet` keeps meaning what it has
always meant: nothing recorded.

"About this environment" is `underWayHere()`, and it reads the run's environment
list from the observation the dashboard hands over — never re-derived, because
that list comes from parsing `run-name`, and one definition on two hosts is the
trap this repository has already paid for. A deploy to stage says nothing about
prod, and a map that told every prod node to expect figures would have replaced
one false sentence with a louder one.

### D7 — The gate is a browser, and its property is the reload

`make page-freshness-check` / `scripts/check-page-freshness.mjs`. Freshness is
not a property of a liftable block, so the gate drives the built page in
chromium on measure-page.mjs's harness — same loader, same static server, same
refusal on a request nobody declared — with a verdict, which measure-page
deliberately has not got.

The property is the reload that fixed all four symptoms:

```text
A TAB LEFT OPEN CONVERGES ON WHAT A FRESH LOAD OF THE SAME SOURCES SHOWS.
```

Three cases: one bucket tick on a pushed clock, the Refresh button, and three
ticks in a row — the third is where an appending layer shows up. Counting
requests was considered and rejected: a page can re-fetch and decline to draw,
and D4 is exactly that failure, which a request count would have called green.

### D8 — The control must be able to speak, region by region

The two fixture sets are rendered cold and every compared region is required to
DIFFER between them. "Differs somewhere" was the first version and a break test
walked through it: with the map's sentence unhooked from the re-read, that region
holds the same static markup in both sessions, converges trivially, and its
silence reads as agreement. A region that cannot move cannot testify.

### D9 — What the page cannot fix, it says

These objects are published `max-age=60` with no CloudFront invalidation, on
purpose (`scripts/publish-status.sh` trades a minute of staleness against an
invalidation quota). So a figure arrives up to a minute after it is written
whatever the timer does. The line beside Refresh now says what the bucket read
covers and admits that ceiling, because the sentence a reader trusts about this
page's cadence is the exact thing 20k caught being untrue.

Not decided here, and left as its own trade: invalidating the run-layer prefixes
on write, and moving the read cadence to match the object's TTL.

## Consequences

- A reader can leave the dashboard open for a cycle. That is what the page is
  for, and until now it was the one way of using it that did not work.
- Eleven bucket objects per tick per reader instead of two. At CloudFront's
  request pricing this is fractions of a cent per open tab per hour, and it is
  the same class of request the status poll already makes.
- A new gate that needs chromium, so it sits in `ci.yml`'s `local-ci` job beside
  `contrast-check`, not in `checks` — same placement rule as ADR-0042 D2.
- The gate found a defect nobody was looking for, on its first run: the FIRST
  observation is announced from `load()` before `topology.json` has come back, and
  the map dropped it. For 30 seconds after a cold load, every node of a destroyed
  environment was drawn as though it still stood — the claim ADR-0051's destroy
  rule exists to prevent. It is held and replayed now. Nothing was watching for
  this; the gate found it because comparing against a fresh load means asking
  what a fresh load shows, and in 20k the reload was the fix rather than the
  subject.
- `nodeTense()` is a four-argument function and `check-page-tense.mjs` gained a
  name in its API list. Existing cases pass three arguments and still hold.
- One more word on the map, and a legend that is now six entries. ADR-0048 D2
  said the legend is a closed cut and 20k recorded that nobody opened it; this
  adds to a list nobody reads, which is accepted because the word on the node is
  where the meaning is and the cut is where it is DEFINED.

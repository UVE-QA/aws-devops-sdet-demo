# ADR-0067: An open cycle publishes a rate, not a figure

## Status
Accepted (Phase 32, 2026-09-05). Narrows **ADR-0046** — the teardown is no longer
the only thing that prices a cycle — and reverses one refusal in
`scripts/publish-status.sh` while keeping the reason that refusal was written
for. **ADR-0045** stands unchanged: still a lifetime, still a band, still an
estimate, still no billing API.

## Context

An environment that is UP had no price anywhere. The fold runs in the teardown
(ADR-0046, "the teardown prices the cycle"), so while prod was live on
2026-09-05 the dashboard's cost box showed **the closed figure from 2026-08-12**
beside an environment that was demonstrably running. Not stale by a subtlety —
the box said *What the last cycle cost* over a cycle that had not ended.

`scripts/fold-cost.py` could already price it. `--destroy` has always been
optional: without it every lifetime runs to `as_of`, every priced row comes back
`state: "open"`, and `cycle.status` is `open`. Nothing called it that way.

The refusal that stopped it was explicit, and it was right:

> Only a CLOSED cycle is published. An open one is a real thing fold-cost.py can
> produce — priced to an instant — but **it goes stale by the second, and a
> figure that ages silently on a public page is the claim this project keeps
> retracting.**

Every word of that survives. A figure priced at 16:22 and read at 17:40 is
wrong, and wrong in the direction that flatters — it understates what is still
running. Publishing it as-is would have been the fourth time this project put a
number on a page that aged out from under its own sentence.

## Decision

### D1 — what is published for an open cycle is the RATE, and the reader does the multiplication

`component_cost()` is linear in `seconds`: every component is
`quantity x unit price x hours`. So one number per second is the whole of a
resource's pricing, and an open row now carries it as `usd_per_second`.

That changes what the document IS. A closed document is a finding. An open
document is **inputs**: creation timestamps and a rate. The page multiplies
against its own clock, once a second, next to the elapsed clocks that already
tick there. The figure on screen is as of now, not as of the last write — so the
objection above is answered at its root rather than tolerated. Nothing ages
silently because nothing is held.

The model is NOT copied. Which unit price applies to which resource kind lives
in `assets/cost-model.json` and is read by `scripts/fold-cost.py`; the page never
sees it and cannot disagree with it. A second copy in JavaScript is the
definition-on-two-hosts trap this project has already paid for twice — the image
scan that scanned postgres, and the palette parsed in two places.

**The rate is omitted, not caveated, where linearity stops.** Below
`minimum_seconds` the fold charges the floor, so a rate multiplied by a smaller
elapsed would understate. Such a row publishes no rate, and `openCost()` in the
page returns null if any priced row is missing one — a partial sum is never drawn
as a whole one.

### D2 — the keying differs, because the evidence differs

```text
closed   <run id>-<job>.json AND latest.json
         The run-id object is immutable evidence of a cycle that is over.
open     latest.json ONLY
         An open cycle is superseded by its own next observation and then by the
         teardown's closed figure. Keying it by run id would litter the bucket
         with snapshots of one lifetime, each true for a second, none the record.
```

### D3 — the heading moves with the tense

`What the last cycle cost` over a figure that is still climbing is the page
saying something untrue in the largest text on the box. It reads
`What this cycle has cost so far` while any environment is open, and the line
adds one sentence saying the figure is computed here against this page's clock.

### D4 — a document and a clock that disagree is a refusal, not a zero

If a resource's creation is in the page's future, `openCost()` returns null
rather than clamping to zero. A clamp prints a confident `$0.0000` for an
environment that is demonstrably up, and a zero that means *inconsistent* cannot
be told from a zero that means *just created*. Same rule this project applies to
an empty read everywhere else.

Found by getting a fixture's date wrong — three days out — which produced exactly
that confident `$0.0000`. The harness was wrong and the page was happy, which is
how it would have reached a visitor.

## Consequences

- `deploy-stage` and `promote-prod` each gain one `continue-on-error` step. An
  estimate is not worth reddening a deploy or a promotion over — and this
  workflow has just been reminded what a last step that reddens a green release
  costs (**ADR-0066**).
- **`check-cost.py` was green over this field before it checked it.** `diff()`
  iterates `for key in expected`, so a key the fold emits and the fixture does
  not name is invisible. The summary now carries `usd_per_second` and the open
  case's `expected.json` names it — derived from that fixture's own published
  `usd / seconds`, not from the new code — and a break test confirms it: a rate
  emitted per minute instead of per second is caught by name, `expected 0.001,
  folded 0.06`, with a control green either side. Ninth time here that a gate has
  been green over the thing it was supposed to be watching.
- The page now renders TWO cost tenses in one line — `stage … the cycle of
  2026-08-09; prod … still up, and still spending, since …`. That is the same
  per-environment split ADR-0059 made for figures, applied to money.
- **`check-page-freshness.mjs` reads `#cost-line` and will now see a string that
  changes every few seconds.** It compares an open tab against a reload, and both
  are computed from the same clock, so it holds — but the cost line is no longer
  a stable string and a future gate that assumes it is will be wrong.
- **`resources` IS NOT ALWAYS AN ARRAY, and assuming it was crashed the page.**
  `openCost()` called `.filter()` on it; `scripts/fold-cost.py` publishes a LIST,
  and `tests/fixtures/page-inflight/` carries the same document keyed BY ADDRESS
  — the shape `check-cost.py`'s `summarise()` produces. On the object shape
  `.filter` is undefined, `renderCostLine()` threw, and `render()` never ran:
  an EMPTY MAP, no error visible on the page, and the environments panel above it
  rendering happily. The reader handles both shapes now and refuses anything else.

  Third time here that a renderer has died half way down the page and left a
  plausible-looking one behind — after Phase 22's `historyTally()` and 20c's
  vanished state. `page-inflight-check` caught it, and nothing else did: `make
  gates` was 12/12 green over the crash, because every gate in the cheap list
  reads a file rather than a rendered page. **The bisect that found it was three
  wrong guesses long** — the tick, then the heading, then a suspicion of flake —
  and what settled it was making the branch unreachable while leaving the code in
  place, which is the only variant that separates "this code is wrong" from
  "this code runs at all".
- Not done: the open figure is not written into the run-id keyed history, so
  there is no record of what an environment cost at any particular moment while
  it was up. Only the closed figure is evidence. That is deliberate and it means
  "what was it costing at 16:00" is not a question this bucket can answer.

# ADR-0046: The teardown prices the cycle, and refuses a pair it cannot vouch for

## Status
Accepted (Phase 20f, 2026-08-08). Completes ADR-0045, which built the
computation and left it running by hand, and names the pairing rule that ADR's
own consequences said had to exist first.

## Context

ADR-0045 ended with three sentences that were true and uncomfortable:

```text
The fold is not wired into any workflow yet. It runs by hand against two
published timelines; putting it in the destroy job means pairing that run with
the apply that created what it is deleting, and the pairing rule needs its own
break test before it is trusted.
```

So a cycle could not say what it cost without somebody running a command
afterwards — and the reason it could not was a missing guarantee rather than
missing plumbing. `scripts/fold-cost.py` is the only thing in this repository
that takes input from two RUNS, because a lifetime spans the apply that created
a resource and the destroy that removed it. Handed two timelines, it believed
them.

That is worse than it sounds, and the reason is the shape this project keeps
meeting: **a mismatched pair does not crash.** `span()` clamps a negative
lifetime to zero, so pricing a stage apply against a prod teardown returns a
small, plausible, entirely wrong number. A defect that stops is cheap. A defect
that answers is not.

## Decision

### D1 — four clauses, and the fourth is deliberately weak

`pairing_refusals()` runs before anything is priced, and `build()` raises rather
than returning a figure it cannot stand behind:

```text
1 environment    both timelines and --environment name the same one. A timeline
                 carrying NO environment is refused too: fold-timeline.py has
                 always written the field, so its absence means the file did not
                 come from here
2 completeness   the apply must be `complete`. A partial apply priced against a
                 finished teardown reports lifetimes for the resources terraform
                 reached and silence for the ones it never started
3 order          the teardown may not START before the apply FINISHED
4 intersection   the two resource sets must have something in common
```

The fourth is the interesting one, and its weakness is the decision rather than
a compromise. **ADR-0038 adopts orphaned resources into the state before a
teardown**, so a destroy legitimately removes things its apply never created; a
refusal on any orphan at all would fire on a working cycle. The existing fixture
`a-delete-with-no-create-is-named` is exactly that case and stays green,
unchanged. Only a teardown with NOTHING in common is refused.

Note what already existed: `orphan_deletes` is computed and reported today, and
nothing refused on it. The detector was there, at the wrong threshold and
wired to nothing. That is the whole distance between ADR-0045 and this one.

### D2 — the anchor rides the rule that already gates the numbers

The teardown needs the apply timeline, with its per-resource windows, which the
node states aggregate away. `timeline/<env>/latest.json` cannot be that anchor:
this teardown overwrites it minutes later, so a second destroy would pair itself
with the first.

So `publish-status.sh` writes `timeline/<env>/apply.json` **inside the block that
publishes `nodes-apply.json`, under the same kind and the same completeness**.
One condition, evaluated once, in one place — the anchor and the at-rest numbers
beside each node cannot disagree about which cycle they came from, because
neither exists unless the other does.

The rejected alternative was deriving apply-vs-destroy again in `jq`. It would
have been four lines and a second definition of a thing `node-states.py` already
decides, which is the mistake that handed the image scan `postgres:16`.

### D3 — the read is anonymous HTTPS, not S3

The destroy job fetches the anchor from the public dashboard URL. The object is
public already, so this needs no credential, no IAM grant and no policy review —
and this project's own record says a genuinely new path costs one failed run.
The cheapest new path is the one that is not new.

### D4 — pricing may not fail a teardown

The step is `continue-on-error`. A red destroy job holds the launch lock (19f,
19g), and an estimate on a dashboard does not justify that trade.

The cost of this is real and is accepted with its eyes open: **a pairing rule
that refuses forever would produce no cost object and redden nothing.** What
answers it is that the refusal is loud in the log and the publish step SAYS the
object is absent rather than passing over it in silence — the "an empty result
is not a clean result" rule applied to the one place here that is allowed to
fail quietly.

### D5 — no attribution rather than a partial one

The fold is not given `--nodes`. Phase attribution folded from the teardown's
own phases would answer "where did the money go" over a window covering a
twentieth of the lifetime, and ADR-0045's finding was that five sixths of a
cycle accrues outside every phase. A missing key is honest; a partial
attribution reads like a whole one.

### D6 — the page shows the band, dated, and calls itself an estimate

One line, hidden until a teardown has priced something. Three things it will not
do: render a single figure instead of the band, render a cost without the date
of the cycle it came from, or call itself anything but an estimate. All three
are ADR-0045; the last is ADR-0026's rule about sources applied to money.

Where that line belongs on the page is 20e's question. That it is reachable at
all is this decision's.

## Consequences

- `cost/` is the first prefix added to `publish-status.sh` since ADR-0044, and
  `make publish-prefixes-check` **went red on this change's first draft**,
  naming the remedy. The deletion of 2026-08-08 was prevented rather than
  repeated, by a gate whose first real exercise this was. A gate that has caught
  something it was not shown in advance is a different object from one that has
  only ever been broken on purpose.
- The fold now refuses inputs it used to accept, so anyone running it by hand
  against two arbitrary timelines will meet a refusal. That is the point, and
  the message names the clause.
- **A gate measured through a bytecode cache measures the cache.** Break-testing
  D1 produced two readings that could not both be true — four different defects
  reddening one fixture, then all four green — because CPython validates a `.pyc`
  on (mtime in whole seconds, source size) and every one-clause break leaves
  `fold-cost.py` at exactly the same size. Five gates load a script under test
  through `importlib`; all five now write no cache. Same family as the exit
  status taken after a pipe in 15b: the instrument sat between the defect and
  the reading.
- Break-testing found a clause nobody was testing. Neutering the
  "names no environment" refusal left every fixture green — written, shipped and
  unexercised, which is the same thing as not having it.
- Nothing here costs anything to run and nothing was applied. The end-to-end
  check reproduces ADR-0045's hand-computed figure for the cycle of 2026-08-08,
  $0.018339 .. $0.023797, from the wired path.

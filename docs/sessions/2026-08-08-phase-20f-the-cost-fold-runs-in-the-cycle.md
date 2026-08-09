# 2026-08-08 — Phase 20f: the cost fold runs in the cycle

Two things, and the first was not on anybody's plan.

**ADR-0046.** Break tests in
`docs/sessions/2026-08-08-phase-20f-the-cost-fold-runs-in-the-cycle.log`.
Cost: nothing. No cycle, no AWS call, nothing applied.

## The plan said hover, and nobody had decided it

The session opened where the cursor pointed: 20e, and the two collisions
`docs/next-phases.md` said to settle first. Reading the page to settle them
produced a finding about the plan instead.

One of the five lines of 20e — *captions: the per-node prose moves into hover* —
was a **spontaneous example**, never a decision. It had been written into the
plan with a costed collision worked out beneath it, in the one document a session
reads to find out what to do next. Asked directly, the person who wrote the
request said so.

The usual stale document says something that WAS true. This one said something
that never was, formatted exactly like the four lines around it that were, and
the worked-out collision underneath made it read as more considered rather than
less.

What the requirement actually is, in the words it was given in: the dashboard
should be compact and informative, and today it is **a long strip you cannot
navigate** — it is not clear how or where to move to reach the thing you need at
that moment. That is wayfinding, not density. A denser page with no route through
it is the same defect in less space. 20e is restated around that, opens with a
discovery step of its own, and moves after the wiring.

Three findings from reading the page went into the plan so the UI phase does not
rediscover them:

```text
the node prose is    .meta / .asserts / .counts are ADR-0043 D4 verbatim - the
not decoration       page saying what it does NOT know. Hiding them behind
                     anything restores the silence that ADR ended
skyline breaks the   a free tetris pack can place phase 7 above phase 6, and
reading order        sequence sits in ADR-0039 D5's `generated, exact` row
the weight is not    measured: body markup is 3.0% of site/index.html, the icon
the text             sprite 32.9%, the two scripts 49.7%. "Compact" cannot mean
                     fewer bytes here
```

The letters run out of order on purpose. 20e is already used, in ADR-0045 and in
a dated session summary, to mean the phase that RENDERS the cost — and a session
record is not rewritten to free up a name.

## The wiring, and the rule it was blocked on

ADR-0045 left the fold running by hand and said why: pairing a teardown with the
apply that created what it is removing needs a rule, and the rule needs a break
test. **ADR-0046** is that rule — four clauses, the fourth deliberately weak
because ADR-0038 adopts orphans before a teardown, so some deleted resource the
apply never created is legitimate.

`orphan_deletes` was already computed and already in the output. Nothing refused
on it. The detector existed at the wrong threshold, wired to nothing.

The anchor is `timeline/<env>/apply.json`, written inside the block that already
publishes `nodes-apply.json`, under the same kind and the same completeness — so
the anchor and the numbers beside each node cannot disagree about which cycle
they are. It is fetched over anonymous HTTPS rather than from S3: the object is
public already, and the cheapest new path is the one that is not new.

End to end against the real cycle of 2026-08-08: **$0.018339 .. $0.023797**,
which is what 20d computed by hand.

## The break test broke, and it was the instrument

Four different one-clause defects each reddened the SAME fixture. A later run of
the identical loop reported all four GREEN. Both readings are indistinguishable
from a gate that cannot fail, which is the thing this repository breaks gates to
rule out.

The gate was blameless. CPython validates a cached `.pyc` on **(source mtime in
whole SECONDS, source size)**. Every break replaces `problems.append(` with a
same-length no-op, so all five variants leave `fold-cost.py` at exactly 18911
bytes, and a loop breaking each clause in turn finishes well inside one second.
The loader kept serving the compile of the previous break.

What settled it was measuring the five variants' sizes rather than reasoning
about them — all identical, which nobody would have predicted. Same family as
15b's exit status taken after a pipe: the instrument sat between the defect and
the reading, and the reading looked like a verdict.

Five gates load a script under test through `importlib` — `check-cost`,
`check-node-states`, `check-rates`, `check-results`, `check-timeline`. All five
fixed in one commit, because the next person to break a gate on purpose will not
be looking for this.

Then the re-run found something real: **neutering clause #1 left every fixture
green.** The refusal for a timeline carrying no environment at all was written,
shipped and unexercised, which is the same thing as not having it. It has a
fixture now.

Final: five clauses, five different fixtures reddened, green control either side,
11/11.

## The gate that exists for this fired, unprompted

`cost/` is the first prefix added to `publish-status.sh` since ADR-0044, and
`make publish-prefixes-check` went red on the first draft of the change, naming
the remedy: `add --exclude "cost/*"`. That is the deletion of 2026-08-08
prevented rather than repeated — and it is the first time that gate has caught
something it was not shown in advance.

## What is deliberately not covered

- **Pricing cannot fail a teardown** (`continue-on-error`), because a red destroy
  job holds the launch lock. The accepted cost: a pairing rule that refused
  forever would produce no cost object and redden nothing. The refusal is loud in
  the log and the publish step says the object is absent.
- **No phase attribution.** Folded from the teardown's phases alone it would
  answer over a twentieth of the lifetime. A missing key is honest.
- **No live cycle was ordered.** The wired path has not run in anger; it has been
  driven end to end against the real timelines of 2026-08-08 offline. The next
  teardown is its first live exercise, and it costs nothing extra to wait for one.

## Validation

```bash
  make docs-check cost-check rates-check node-states-check results-check \
       timeline-check site-page-check site-data-check live-state-check \
       publish-prefixes-check action-pins
```

All eleven green, on the devbox and in the session's own clone. `make cost-check`
is 11/11.

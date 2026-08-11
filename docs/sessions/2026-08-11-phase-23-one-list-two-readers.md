# 2026-08-11 — Phase 23: one list of gates, two readers

The cursor's next allowed step after 22 named Phase 23 as three things at once:
the composition redrawn, the gate for a cycle in flight, and two items Phase 22
handed forward. The session took the **two-list problem** first, because it is
the one that keeps reddening `main` while a session reports itself closed, and
renumbered the rest per **ADR-0055**: the composition is Phase 24, the in-flight
gate is Phase 25.

`assets/gates.json` is now the one list of gates. `make gates` runs the ones a
plain checkout can run; `scripts/session-close.sh` and
`.github/workflows/ci.yml` are its two readers. No cycle, no AWS call, nothing
applied. **Cost: $0.** **ADR-0057.**

Break-test output in
`docs/sessions/2026-08-11-phase-23-one-list-break-test.log`.

**Main was green when this session started**, checked before anything was
touched: run 31363443181 on `19bb1c0`, and `scripts/verify-schema3.sh` 12/12
with the two browser gates skipped. That control is here because 22 ran it and
found main red; running it when it says nothing is the only way it can ever say
something.

## 1. The gap was four gates wider than the handover sentence said

Phase 22 wrote the item down as *"ci.yml runs five more cheap gates that
session-close does not — timeline, node-states, results, live-state,
page-tense."* Counted from the two files instead:

```text
session-close ran   check-docs-references.py, generate-topology.py --check,
                    build-site-page.py --check          — three
ci.yml ran          those three, plus timeline-check, node-states-check,
                    results-check, live-state-check, page-tense-check,
                    publish-prefixes-check, cost-check, rates-check,
                    action-pins                          — twelve
```

Nine missing, not five. The four nobody named — `publish-prefixes-check`,
`cost-check`, `rates-check`, `action-pins` — are in a different part of the
workflow, after the Checkov install, and the handover sentence was written from
the five gates that session had been reading. It is the small version of *a
claim about state is not state*, and it cost nothing only because the fix does
not depend on the number.

The two readers also disagreed about what a gate IS: `session-close.sh` invoked
the scripts, `ci.yml` invoked the make targets. Two spellings of the same three
checks, which is how the drift stayed invisible while both were green.

## 2. One list can shrink in silence; two lists cannot

This is the thing the two-list shape was accidentally protecting, and it is the
argument for the second half of the change rather than against the first:

```text
two lists   deleting a gate from one leaves the other still running it. The
            failure is disagreement, and it is loud the moment one goes red.
one list    deleting a line weakens BOTH readers at once, and nothing anywhere
            disagrees. The failure is silence.
```

So the list is not trusted on its own. `make gates-check` **discovers** what
ought to be in it, out of the repository rather than out of a second list:

```text
a Makefile target whose name ends in -check
a Makefile target whose recipe runs a scripts/check-* program
any target ci.yml invokes as `make <target>`, on a line that is not a comment
```

minus the two targets the list names as its own runner and checker. The middle
rule earns its place: **`action-pins` is a gate whose name does not say so**, and
the first and third rules would both have missed it — the third only because
this change removed its step from `ci.yml`. A rule set that passes today and
fails after your own edit is worth writing down.

The refusals: something discovered and not listed; an entry naming a target the
Makefile does not define; an exclusion with no reason; a target listed twice; an
empty list; and `ci.yml` missing, because half a discovery is not a discovery.
They run FIRST inside `make gates`, so a broken list refuses instead of quietly
running a shorter suite — which is the failure this phase is about, one level
down.

## 3. Six breaks, a control either side, and the defect itself reproduced

The tree was committed before anything was broken (`4e4199e`), per the rule this
project wrote after losing a finished edit to `git checkout`.

```text
CONTROL                                          exit 0
gate deleted from the list                       red, names timeline-check
entry naming a target that does not exist        red, names it
the list emptied                                 red
an exclusion with no reason                      red, names contrast-check
ci.yml moved away                                red, refuses to check half
CONTROL between every one of them                exit 0
```

Then the defect itself, which is the one that matters: an ADR planted in
`docs/decisions/` and nothing regenerated — the exact 20i/21 shape, since
`topology.json` counts those files.

```text
make gates                 site-data-check FAIL — the reader ci.yml uses
scripts/session-close.sh   the same table, the same failure, fail=1
CONTROL, ADR removed       12/12 green
```

Both readers, one list, one failure. Before this phase the second of those two
lines was three checks' worth of silence.

## 4. The exit numbers in that log are make's, not the script's

Every break above was measured through `make`, which reports a failed recipe as
**2** whatever the recipe returned. The refusals return 1. Same shape as the
2026-07-28 reading taken through a pipe: the instrument was between the defect
and the number. It is harmless here because both readers test for non-zero, but
it is recorded rather than reasoned about — the addendum in the log measures
`python3 scripts/run-gates.py --check` directly, and gets 1 and 0.

## 5. What this cost, deliberately

`terraform-checks` used to show twelve named steps in the Actions UI and now
shows one, `Every cheap gate, from the one list session-close also reads`. A red
build says which gate failed in the log rather than in the job list.

Accepted rather than worked around, and worth being plain about: **twelve
readable step names are also what made two lists look maintainable for eleven
phases.** The runner prints a table whose failing row is the first thing in the
output, and `gates: 1 of 12 failed. CI runs this same list and will say the same
thing.` is the last.

The twelve step comments were not deleted. Each gate was already documented
beside its target in the Makefile; the four sentences that existed only in
`ci.yml` moved there, and the new step's comment carries only what belongs to
the step.

## 6. The list carries twelve things that are not gates

`ci.yml` invokes `local-up`, `migrate`, `seed`, `docker-build`, `test-smoke` and
the rest, and the discovery cannot tell a gate from a step. Rather than a fourth
rule to exclude them, they are listed with what they need. The runner's second
table then says, in one place, what a plain clone of this repository cannot
verify about itself:

```text
19 gate(s) need more than a checkout — a browser, docker, terraform, a scanner,
                                       a virtualenv, or a live Function URL
```

That was a side effect, and it is the better half of the output.

## 7. There was a third list, and it was already four short

`scripts/verify-schema3.sh` — written the day before, in Phase 22 — held its own
array of **eight** cheap gates while `ci.yml` ran twelve and `session-close` ran
three. Nobody put it there carelessly; it was the runner for a migration, and it
listed the gates that mattered to that migration. One day later it was a third
copy of a list that disagreed with both others, which is the sentence
`docs/next-phases.md` used to describe the problem before this phase started.

It now calls `make gates` for the cheap half — one row in its table — and reads
the two browser gates out of `assets/gates.json` via a `browser: true` flag,
rather than naming them again. There is no gate list in that file any more.

## 8. The break test for that refusal failed to break, and then its correction
## was measured through a pipe

Two instrument failures in ten minutes, both of them this repository's own
documented traps, both found by writing the break test rather than by reasoning.

**The refusal did not fire.** With `browser: true` removed from every entry, the
run was expected to refuse. It printed a green table instead — with a SKIP row
that had *no name*, and `Run these where chromium is: make ` with nothing after
it. The refusal was blameless: `mapfile` over a python program that prints an
empty line produces an array holding **one empty string**, so `${#ARRAY[@]}` was
1 and the guard stayed quiet. Empty lines are dropped now.

**Then the corrected reading was taken through `| tail -6`,** and recorded
`exit 0` for a script that exits 1 — the 2026-07-28 pipe finding, verbatim,
written into the paragraph that was documenting an instrument standing between a
defect and its reading. Both are in the log, with the corrections under them,
because the pair is worth more than a tidy file.

## Validation

```bash
make gates                # 12/12, 19 named as not runnable here
make gates-check
bash scripts/verify-schema3.sh
make page-freshness-check contrast-check     # devbox only, needs chromium
```

The two browser gates are untouched by this phase and cannot run in the chat
sandbox; they are named here rather than omitted, because a gate absent from a
list looks exactly like a gate that passed.

## Cost

Nothing. No AWS call, no cycle, nothing applied.

## Next

**Phase 24 — the composition, redrawn for three contours**, carrying the
assertions contour Phase 22 was forbidden to draw. Phase 25 is the in-flight
gate after it. Both are $0 until the in-flight fixture needs a real cycle behind
it, which is a separate, billable decision.

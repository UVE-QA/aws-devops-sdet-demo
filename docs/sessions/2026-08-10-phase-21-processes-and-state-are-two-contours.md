# 2026-08-10 — Phase 21: processes and state are two contours

A decisions session. No code, no cycle, nothing applied, nothing measured.
Cost: nothing. **ADR-0054** and **ADR-0055**.

The cursor's next allowed step after 20m was *fix what the map says while it
runs, and gate it* — the three findings a live cycle had produced. This session
did not do that, and the reason is the session's whole content: the question
"why is the map wrong while a cycle runs" was asked one level down and answered
somewhere else.

## The observation that opened it

Put plainly, from outside the code: the map mixes **processes** — deploy,
provision, destroy — with the **state of an environment**, which is what those
processes produce. They are different kinds of thing and the map draws them as
one sequence.

The first thing checking that turned up is that the page already agrees:

```text
p-env   "Environments — observed in AWS, not inferred from a green run"
p-run   "Current cycle — the step in flight, not the whole log"
map     "What a cycle does, in the order it does it"
          └─ stage.vpc, stage.rds, stage.alb, prod.rds, prod.ecs …
```

Two panels that separate state from process, and beneath them a map with a
process title holding every state node as a child. Each environment is drawn
twice. Where the two accounts disagree, the arbitration exists — as the name of
a fixture case, `an-environment-is-what-the-panel-above-the-map-says-it-is`.
Somebody had to decide it and the decision landed in a filename.

## Why it is the root of 20m, and of exactly two thirds of it

`stage-apply created stage.rds` is a **reference**. The map stores it as
**containment**, and containment gives a noun one verb forever. Four verbs touch
that database: apply creates it, provision migrates into it, the quality gate
asserts against it, destroy deletes it. The map can express the first.

- 20m's finding (2), the renderer consulting the run layer before `nodeTense`:
  for a node that IS a step, the run layer is the authoritative source. It is
  only wrong because the node is not really a step.
- 20m's finding (3), `prod.rds` at full colour with last cycle's figures for
  twelve measured minutes while prod was being deleted: it is drawn under
  `prod-apply`, and the destroy phase has no path to it.
- 20m's finding (1), the history badge scoring an in-flight run as a success:
  **not this.** Numerator of completed runs over denominator of all of them —
  a counting bug inside the process contour, unaffected by any of it. Written
  down as such in ADR-0054 D7 so that nobody later reads the restructuring as
  having covered it.

## What the model costs, priced before deciding

The encouraging half: most of it already exists without a name.

```text
assets/topology-groups.json   groups[].kind = permanent | node | hidden
observer on every node        terraform | report | actions, and ADR-0051 D3
                              already routes rendering off it
perm.ecr / build.ecr          the registry-noun and the push-verb, already apart
destroy.stage / destroy.prod  a verb referencing a whole level by path
request_path (ADR-0049 D6)    citation BY ID with a build that refuses an
                              unresolvable one — both refusals exercised
envObservation / envPanel     stage and prod, present tense, from
                              status/<env>.json, which never mentions a run,
                              and envTense refuses to re-derive it (ADR-0051 D2)
```

The expensive half, and the part that decided the phase split:

```text
SUPERSEDED   ADR-0039 D2b (first half), ADR-0047 D1, ADR-0052 D2, ADR-0052 D3
RETIRED      every measured layout figure in ADR-0050 and ADR-0052. They measure
             an object that stops existing, so they are re-measured, never
             translated
REWRITTEN    generate-topology.py's assembly (most of the work), the live-state
             gate and its hand-written cases, node-states.py's four indexers,
             one comprehension in check-results.py
RE-RUN ONLY  site-page-check, timeline-check (it never reads the topology),
             suite-inventory-check, page-tense-check, contrast-check — whose
             probe ancestry is data in assets/contrast-contract.json
```

One thing turned out cheaper than it looks: ADR-0046 D5 — the wired teardown
does not pass `--nodes`, so per-phase cost attribution is not computed in
production today at all.

## The clause that had to be overturned rather than extended

**ADR-0039 D2b**: *"each suite that runs appears as its own node in the
sequence — beside the services, not in a panel next to them. A separate tests
panel would be a second place telling the same story."*

That is the direct negation of a third contour, and its argument is the same
argument used here for the split. The resolution is that D2b applied the
principle to the wrong object: a suite carries **two** facts, what it contains
and how it ran, and ADR-0042 D5 had already separated exactly those two into
`site/data/suites.json` and `results/<env>/latest.json`. The duplication D2b
feared is what the page does now, with environments, in the place nobody checked.

Its second half — *"a node is a suite × ENVIRONMENT, not a suite"* — is kept
rather than overturned. It was always a statement about a run.

## Found for free

`counts.suites` reports 5. The map draws 4. `tests/unit` is inventoried,
counted, and invisible — and no check objects, although D2b itself claims *"a
spec directory belonging to no display node is a red build"*. That is enforced
between suites and collectors, never between suites and the map. Phase 22 writes
the missing refusal.

## The other decision: the alphabet

Phase 20 ran to thirteen entries. **ADR-0055** retires the lettered sub-phase,
and the reasoning is not tidiness: the letter was meant to mean one session and
never did — 20a took three, 19g took two — so the letters were a symptom. The
cause is that Phase 20's title has no condition of completion, so nothing could
end it. From 21 the identifier is an integer and a phase is planned together
with the checkable sentence that closes it. Phase 22's and Phase 23's are
written in `docs/next-phases.md`.

Nothing before 21 is renumbered. Those identifiers are in the session filenames,
in every row of `INDEX.md`, and in the ADRs that cite them.

## What this session deliberately did not do

Write any code. The temptation was to fix the badge — it is a few characters and
it is genuinely independent — and it was left to Phase 22 with a case attached,
because a decisions session that ships one small fix is how a decisions session
becomes an implementation session with no plan.

## Next

**Phase 22 — the model in the data.** The page is not touched. Its closing
condition is in `docs/next-phases.md` and is checkable rather than a feeling.
